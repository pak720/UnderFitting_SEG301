"""
Vector Indexer — builds a compact FAISS index for semantic search.

Key changes vs previous version:
- Stores only (faiss_idx → byte_offset) instead of full documents.
  Memory: 12 MB for 1.5 M docs instead of 3-4 GB.
- Uses IndexIVFPQ for ~30x smaller index file and faster ANN search.
- Checkpoint no longer stores doc content, only embeddings + offsets.
"""

import json
import threading
import queue as _queue
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from datetime import datetime
import numpy as np
from tqdm import tqdm
import logging

try:
    import faiss
except ImportError:
    faiss = None

try:
    import torch
    _TORCH_AVAILABLE = True
except ImportError:
    _TORCH_AVAILABLE = False

from sentence_transformers import SentenceTransformer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_CHECKPOINT_META = 'build_checkpoint.json'
_CHECKPOINT_EMBS = 'build_embeddings.npy'
_CHECKPOINT_OFFS = 'build_offsets.npy'   # replaces build_docs.pkl

_BATCH_SIZE_GPU = 256
_BATCH_SIZE_CPU = 32


def _detect_device() -> str:
    if _TORCH_AVAILABLE and torch.cuda.is_available():
        return 'cuda'
    return 'cpu'


def _log_device_info(device: str) -> None:
    if device.startswith('cuda') and _TORCH_AVAILABLE:
        for i in range(torch.cuda.device_count()):
            props = torch.cuda.get_device_properties(i)
            logger.info(f"  GPU {i}: {props.name} "
                        f"({props.total_memory / 1024**3:.1f} GB VRAM)")
    else:
        import os
        logger.info(f"  CPU ({os.cpu_count()} logical cores)")


class VectorIndexer:
    """Build a semantic search index from a JSONL file."""

    def __init__(self,
                 model_name: str = 'intfloat/multilingual-e5-base',
                 batch_size: Optional[int] = None,
                 device: str = 'auto',
                 fp16: bool = False):
        if faiss is None:
            raise ImportError("FAISS not installed. Run: pip install faiss-cpu")

        self.device = _detect_device() if device == 'auto' else device
        self.batch_size = batch_size or (
            _BATCH_SIZE_GPU if self.device.startswith('cuda') else _BATCH_SIZE_CPU)
        self.fp16 = fp16 and self.device.startswith('cuda')
        self.model_name = model_name

        logger.info(f"Device  : {self.device}")
        _log_device_info(self.device)
        logger.info(f"Model   : {model_name}")
        logger.info(f"Batch   : {self.batch_size}")
        logger.info(f"FP16    : {self.fp16}")

        self.model = SentenceTransformer(model_name, device=self.device)
        if self.fp16:
            self.model.half()
            logger.info("Model converted to FP16")

        self.embedding_dim = self.model.get_sentence_embedding_dimension()
        logger.info(f"Emb dim : {self.embedding_dim}")

    # Four embeddings per document: name, industry, address, full-doc.
    # Single-field queries match the dedicated field embedding (high precision).
    # Multi-field queries ("công nghệ hà nội") match the full-doc embedding
    # which captures all fields together — no single field can win on its own.
    NUM_FIELDS = 4

    # ------------------------------------------------------------------
    # Text extraction — multi-field with e5 passage prefix
    # ------------------------------------------------------------------

    def _extract_fields(self, doc: Dict[str, Any]) -> List[str]:
        """Return three passage strings: [name, industry, address].

        Each is prefixed with 'passage: ' as required by multilingual-e5
        for asymmetric (query → passage) retrieval.
        """
        def _clean(val: Any) -> str:
            s = str(val or '').strip()
            return '' if s.lower() in ('nan', 'none', '') else s

        name     = _clean(doc.get('Tên doanh nghiệp',     ''))
        trade    = _clean(doc.get('Tên giao dịch',         ''))
        industry = _clean(doc.get('Ngành nghề kinh doanh', ''))
        address  = _clean(doc.get('Địa chỉ',               ''))

        # Province = last comma-separated segment of address
        # "Số 2, Xã A, Huyện B, Bình Định" → "Bình Định"
        province = address.rsplit(',', 1)[-1].strip() if ',' in address else address

        name_body     = ' '.join(filter(None, [name, trade])) or name or 'unknown'
        industry_body = industry or 'unknown'
        # Use province only (not full address) so location queries match cleanly.
        address_body  = province or address or 'unknown'

        # Full-document passage: compact representation of all fields.
        # This is the embedding that wins for multi-field queries like
        # "công nghệ hà nội" — both "công nghệ" and "hà nội" must appear.
        full_parts = [p for p in [name_body, industry_body, address_body]
                      if p and p != 'unknown']
        full_body = ' '.join(full_parts) or 'unknown'

        return [
            f"passage: {name_body}",
            f"passage: {industry_body}",
            f"passage: {address_body}",
            f"passage: {full_body}",
        ]

    def _extract_text(self, doc: Dict[str, Any]) -> str:
        """Single-string fallback (legacy checkpointing path)."""
        return ' '.join(self._extract_fields(doc))

    # ------------------------------------------------------------------
    # Checkpoint helpers (now store only embeddings + byte offsets)
    # ------------------------------------------------------------------

    def _save_checkpoint(self, index_dir: Path, jsonl_path: str,
                         lines_read: int,
                         byte_offsets: List[int],
                         embeddings: np.ndarray) -> None:
        embs_tmp = index_dir / 'build_embeddings.tmp.npy'
        offs_tmp = index_dir / 'build_offsets.tmp.npy'
        meta_tmp = index_dir / (_CHECKPOINT_META + '.tmp')

        np.save(str(embs_tmp), embeddings)
        np.save(str(offs_tmp), np.array(byte_offsets, dtype=np.int64))
        meta = {
            'jsonl_path': str(jsonl_path),
            'model_name': self.model_name,
            'lines_read': lines_read,
            'docs_processed': len(byte_offsets),
            'saved_at': datetime.now().isoformat(),
        }
        with open(meta_tmp, 'w', encoding='utf-8') as f:
            json.dump(meta, f, indent=2)

        embs_tmp.replace(index_dir / _CHECKPOINT_EMBS)
        offs_tmp.replace(index_dir / _CHECKPOINT_OFFS)
        meta_tmp.replace(index_dir / _CHECKPOINT_META)

    def _load_checkpoint(self, index_dir: Path,
                         jsonl_path: str) -> Tuple[int, List[int], Optional[np.ndarray]]:
        """Return (start_line, byte_offsets, embeddings) or fresh state."""
        meta_path = index_dir / _CHECKPOINT_META
        if not meta_path.exists():
            return 0, [], None
        try:
            with open(meta_path, encoding='utf-8') as f:
                meta = json.load(f)
            if meta.get('jsonl_path') != str(jsonl_path):
                logger.warning("[RESUME] Different JSONL — ignoring checkpoint")
                return 0, [], None
            if meta.get('model_name') != self.model_name:
                logger.warning("[RESUME] Different model — ignoring checkpoint")
                return 0, [], None
            byte_offsets = np.load(str(index_dir / _CHECKPOINT_OFFS)).tolist()
            embeddings   = np.load(str(index_dir / _CHECKPOINT_EMBS))
            start_line   = meta['lines_read']
            logger.info(f"[RESUME] {len(byte_offsets)} docs already embedded, "
                        f"resuming from line {start_line} "
                        f"(saved {meta.get('saved_at', '?')})")
            return start_line, byte_offsets, embeddings
        except Exception as exc:
            logger.warning(f"[RESUME] Cannot load checkpoint ({exc}) — starting fresh")
            return 0, [], None

    def _clear_checkpoint(self, index_dir: Path) -> None:
        for name in (_CHECKPOINT_META, _CHECKPOINT_EMBS, _CHECKPOINT_OFFS):
            p = index_dir / name
            if p.exists():
                p.unlink()

    # ------------------------------------------------------------------
    # FAISS index builder
    # ------------------------------------------------------------------

    def _build_faiss_index(self, embeddings: np.ndarray) -> 'faiss.Index':
        """
        Build FAISS index using exact cosine similarity.

        Sentence-Transformer embeddings are trained for cosine similarity, NOT L2
        distance.  We L2-normalise all vectors so that inner product == cosine.

        IndexFlatIP is used for all dataset sizes:
        - Exact (no approximation) — avoids the quantisation errors that IVFPQ
          introduces, which are often larger than the real similarity gaps for
          text queries (cosine ≈ 0.05-0.20) and cause completely wrong rankings.
        - Search time: ~30-80 ms for 1.5 M docs on CPU (FAISS uses SIMD).
        """
        N = embeddings.shape[0]

        # L2-normalise in-place: inner_product(a, b) == cosine_similarity(a, b)
        faiss.normalize_L2(embeddings)
        logger.info("Embeddings L2-normalised (inner product = cosine similarity)")

        logger.info(f"Building IndexFlatIP — {N:,} docs, exact cosine search")
        index = faiss.IndexFlatIP(self.embedding_dim)
        index.add(embeddings)
        return index

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def build_index(self,
                    jsonl_path: str,
                    index_dir: str = 'vector_index',
                    max_docs: Optional[int] = None,
                    resume: bool = True,
                    prefetch_batches: int = 4) -> None:
        """
        Build vector index from a JSONL file.

        Saves:
          vector.index      — FAISS index (IVFPQ for large datasets)
          idx_offsets.npy   — int64 array: idx_offsets[faiss_idx] = byte offset
          metadata.json     — model info + jsonl_path for DocStore reconstruction
        """
        index_dir  = Path(index_dir)
        index_dir.mkdir(exist_ok=True, parents=True)
        jsonl_path = str(jsonl_path)

        if resume:
            start_line, byte_offsets, all_embeddings = self._load_checkpoint(
                index_dir, jsonl_path)
        else:
            start_line, byte_offsets, all_embeddings = 0, [], None
            logger.info("[RESUME] Disabled — building from scratch")

        already_done = len(byte_offsets)

        # --- Producer thread ---
        batch_queue: _queue.Queue = _queue.Queue(maxsize=prefetch_batches)
        producer_error: List[Exception] = []

        def producer() -> None:
            batch_texts: List[str] = []
            batch_offs:  List[int] = []
            current_line = start_line

            try:
                with open(jsonl_path, 'r', encoding='utf-8') as f:
                    line_no = 0
                    while True:
                        pos  = f.tell()
                        line = f.readline()
                        if not line:
                            break
                        stripped = line.strip()
                        if not stripped:
                            continue

                        if line_no < start_line:
                            line_no += 1
                            continue
                        current_line = line_no + 1

                        if max_docs and (already_done + len(batch_offs)
                                         + sum(len(b[2]) for b in list(batch_queue.queue))
                                         >= max_docs):
                            line_no += 1
                            break

                        try:
                            doc = json.loads(stripped)
                            field_texts = self._extract_fields(doc)
                            batch_texts.extend(field_texts)  # NUM_FIELDS per doc
                            batch_offs.append(pos)           # 1 offset per doc
                        except json.JSONDecodeError:
                            logger.warning(f"Skipping invalid JSON at line {line_no}")

                        line_no += 1

                        # Flush when batch reaches batch_size docs
                        if len(batch_offs) >= self.batch_size:
                            batch_queue.put((current_line, batch_texts, batch_offs))
                            batch_texts, batch_offs = [], []

                if batch_offs:
                    batch_queue.put((current_line, batch_texts, batch_offs))
            except Exception as exc:
                producer_error.append(exc)
            finally:
                batch_queue.put(None)

        reader = threading.Thread(target=producer, daemon=True)
        reader.start()

        # --- Consumer (main thread / GPU) ---
        pbar = tqdm(desc=f"Embedding [{self.device.upper()}]",
                    unit="doc", initial=already_done)
        lines_read = start_line

        try:
            while True:
                item = batch_queue.get()
                if item is None:
                    break
                lines_read, batch_texts, batch_offs = item

                batch_embs = self.model.encode(
                    batch_texts,
                    batch_size=self.batch_size * self.NUM_FIELDS,
                    show_progress_bar=False,
                    convert_to_numpy=True,
                ).astype(np.float32)
                # shape: (len(batch_offs) * NUM_FIELDS, dim)

                byte_offsets.extend(batch_offs)
                all_embeddings = (
                    batch_embs if all_embeddings is None
                    else np.vstack([all_embeddings, batch_embs])
                )

                pbar.update(len(batch_offs))  # progress in docs
                self._save_checkpoint(
                    index_dir, jsonl_path, lines_read,
                    byte_offsets, all_embeddings)
                pbar.set_postfix(docs=len(byte_offsets), ckpt="saved")

        except KeyboardInterrupt:
            pbar.close()
            logger.warning(
                f"\n[INTERRUPTED] {len(byte_offsets)} docs embedded. "
                "Run again to resume automatically.")
            raise
        finally:
            pbar.close()
            reader.join(timeout=2)

        if producer_error:
            raise producer_error[0]
        if not byte_offsets:
            raise ValueError("No valid documents found in JSONL file")

        all_embeddings = np.asarray(all_embeddings, dtype=np.float32)
        logger.info(f"Embeddings shape: {all_embeddings.shape}")

        # --- Build FAISS index ---
        logger.info("Building FAISS index …")
        faiss_index = self._build_faiss_index(all_embeddings)

        # --- Persist ---
        logger.info("Saving to disk …")
        faiss.write_index(faiss_index, str(index_dir / 'vector.index'))

        idx_offsets = np.array(byte_offsets, dtype=np.int64)
        np.save(str(index_dir / 'idx_offsets.npy'), idx_offsets)

        metadata = {
            'model_name': self.model_name,
            'num_fields': self.NUM_FIELDS,
            'embedding_dim': self.embedding_dim,
            'num_documents': len(byte_offsets),
            'jsonl_path': jsonl_path,
            'index_type': 'FlatIP(cosine)',
            'normalized': True,
            'metric': 'cosine',
            'device': self.device,
            'fp16': self.fp16,
        }
        with open(index_dir / 'metadata.json', 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)

        self._clear_checkpoint(index_dir)
        logger.info(f"Done — {len(byte_offsets):,} docs indexed in '{index_dir}'")
