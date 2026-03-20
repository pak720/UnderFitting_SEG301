"""
Vector Indexer — builds a compact FAISS index for semantic search.

Key design:
- 4 fields embedded separately per doc: name, industry, address, full-doc.
  Each stored as a consecutive FAISS slot (faiss_idx = doc_id * 4 + field_idx).
  Short queries match dedicated field embeddings (high precision).
  Long queries (3+ words) match the full-doc embedding (multi-concept).
- Streaming binary file for embedding accumulation → RAM = 1 batch, not full corpus.
- IndexIVFPQ for ~30x smaller index file vs IndexFlatIP.
- Checkpoint stores byte offsets + streaming file; resumes mid-corpus.
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
_CHECKPOINT_OFFS = 'build_offsets.npy'
_CHECKPOINT_EMBS_BIN = 'build_embeddings.bin'   # streaming float32 binary

_BATCH_SIZE_GPU = 512   # outer batch: docs fetched per queue item
_BATCH_SIZE_CPU = 32
_ENCODE_BATCH_GPU = 64  # actual GPU forward-pass size (prevent VRAM OOM)
_ENCODE_BATCH_CPU = 16
_CKPT_INTERVAL_DOCS = 5000  # checkpoint every N docs (not every batch)

# 4 consecutive FAISS slots per document:
#   slot 0 = name embedding      (matches "tên công ty ABC")
#   slot 1 = industry embedding  (matches "công nghệ thông tin")
#   slot 2 = address embedding   (matches "Hà Nội", "Bình Định")
#   slot 3 = full-doc embedding  (matches multi-concept "công nghệ hà nội")
NUM_FIELDS = 4


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
        self.encode_batch = (
            _ENCODE_BATCH_GPU if self.device.startswith('cuda') else _ENCODE_BATCH_CPU)
        self.fp16 = fp16 and self.device.startswith('cuda')
        self.model_name = model_name

        logger.info(f"Device  : {self.device}")
        _log_device_info(self.device)
        logger.info(f"Model   : {model_name}")
        logger.info(f"Batch   : outer={self.batch_size} docs, encode={self.encode_batch} texts/pass")
        logger.info(f"FP16    : {self.fp16}")
        logger.info(f"Fields  : {NUM_FIELDS} (separate FAISS slots per doc)")

        self.model = SentenceTransformer(model_name, device=self.device)
        if self.fp16:
            self.model.half()
            logger.info("Model converted to FP16")

        self.embedding_dim = self.model.get_sentence_embedding_dimension()
        logger.info(f"Emb dim : {self.embedding_dim}")

    # ------------------------------------------------------------------
    # Text extraction — 3 separate passages, prefixed for e5
    # ------------------------------------------------------------------

    def _extract_fields(self, doc: Dict[str, Any]) -> List[str]:
        """Return 4 passage strings: [name, industry, address, full-doc].

        Each prefixed with 'passage: ' as required by multilingual-e5
        for asymmetric (query → passage) retrieval.

        Stored as 4 consecutive FAISS slots per doc so the searcher can
        apply different strategies per query length (MAX for short queries,
        full-doc only for multi-concept long queries).
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
        address_body  = province or address or 'unknown'

        # Full-doc passage: all fields combined so multi-concept queries
        # ("công nghệ hà nội") find docs where both concepts appear.
        full_parts = [p for p in [name_body, industry_body, address_body]
                      if p and p != 'unknown']
        full_body = ' '.join(full_parts) or 'unknown'

        return [
            f"passage: {name_body}",
            f"passage: {industry_body}",
            f"passage: {address_body}",
            f"passage: {full_body}",
        ]

    # ------------------------------------------------------------------
    # Checkpoint helpers — streaming binary for embeddings
    # ------------------------------------------------------------------

    def _embs_bin_path(self, index_dir: Path) -> Path:
        return index_dir / _CHECKPOINT_EMBS_BIN

    def _save_checkpoint(self, index_dir: Path, jsonl_path: str,
                         lines_read: int,
                         byte_offsets: List[int],
                         docs_done: int) -> None:
        """Save offset array + meta; embeddings already flushed to binary file."""
        offs_tmp = index_dir / 'build_offsets.tmp.npy'
        meta_tmp = index_dir / (_CHECKPOINT_META + '.tmp')

        np.save(str(offs_tmp), np.array(byte_offsets, dtype=np.int64))
        meta = {
            'jsonl_path': str(jsonl_path),
            'model_name': self.model_name,
            'embedding_dim': self.embedding_dim,
            'lines_read': lines_read,
            'docs_processed': docs_done,
            'saved_at': datetime.now().isoformat(),
        }
        with open(meta_tmp, 'w', encoding='utf-8') as f:
            json.dump(meta, f, indent=2)

        offs_tmp.replace(index_dir / _CHECKPOINT_OFFS)
        meta_tmp.replace(index_dir / _CHECKPOINT_META)

    def _load_checkpoint(self, index_dir: Path,
                         jsonl_path: str) -> Tuple[int, List[int], int]:
        """Return (start_line, byte_offsets, docs_done) or fresh state."""
        meta_path = index_dir / _CHECKPOINT_META
        embs_bin  = self._embs_bin_path(index_dir)
        if not meta_path.exists() or not embs_bin.exists():
            return 0, [], 0
        try:
            with open(meta_path, encoding='utf-8') as f:
                meta = json.load(f)
            if meta.get('jsonl_path') != str(jsonl_path):
                logger.warning("[RESUME] Different JSONL — ignoring checkpoint")
                return 0, [], 0
            if meta.get('model_name') != self.model_name:
                logger.warning("[RESUME] Different model — ignoring checkpoint")
                return 0, [], 0
            if meta.get('embedding_dim') != self.embedding_dim:
                logger.warning("[RESUME] Different embedding dim — ignoring checkpoint")
                return 0, [], 0

            docs_done    = meta['docs_processed']
            byte_offsets = np.load(str(index_dir / _CHECKPOINT_OFFS)).tolist()

            # Verify binary file size matches docs_done * NUM_FIELDS vectors
            expected_bytes = docs_done * NUM_FIELDS * self.embedding_dim * 4  # float32
            actual_bytes   = embs_bin.stat().st_size
            if actual_bytes != expected_bytes:
                logger.warning(
                    f"[RESUME] Binary size mismatch "
                    f"(expected {expected_bytes}, got {actual_bytes}) — ignoring checkpoint")
                return 0, [], 0

            start_line = meta['lines_read']
            logger.info(
                f"[RESUME] {docs_done:,} docs already embedded, "
                f"resuming from line {start_line} "
                f"(saved {meta.get('saved_at', '?')})")
            return start_line, byte_offsets, docs_done

        except Exception as exc:
            logger.warning(f"[RESUME] Cannot load checkpoint ({exc}) — starting fresh")
            return 0, [], 0

    def _clear_checkpoint(self, index_dir: Path) -> None:
        for name in (_CHECKPOINT_META, _CHECKPOINT_OFFS, _CHECKPOINT_EMBS_BIN):
            p = index_dir / name
            if p.exists():
                p.unlink()

    # ------------------------------------------------------------------
    # FAISS index builder
    # ------------------------------------------------------------------

    _IVFPQ_NLIST  = 256
    _IVFPQ_M      = 32    # must divide dim (768 / 32 = 24) ✓
    _IVFPQ_NBITS  = 8
    _IVFPQ_NPROBE = 32
    _IVFPQ_MIN_TRAIN = _IVFPQ_NLIST * 39   # = 9,984

    def _build_faiss_index(self, embeddings: np.ndarray) -> 'faiss.Index':
        N = embeddings.shape[0]
        faiss.normalize_L2(embeddings)
        logger.info("Embeddings L2-normalised (inner product = cosine similarity)")

        if N >= self._IVFPQ_MIN_TRAIN:
            logger.info(
                f"Building IndexIVFPQ — {N:,} docs "
                f"(nlist={self._IVFPQ_NLIST}, M={self._IVFPQ_M}, "
                f"nbits={self._IVFPQ_NBITS}, nprobe={self._IVFPQ_NPROBE})"
            )
            quantizer = faiss.IndexFlatIP(self.embedding_dim)
            index = faiss.IndexIVFPQ(
                quantizer, self.embedding_dim,
                self._IVFPQ_NLIST, self._IVFPQ_M, self._IVFPQ_NBITS,
            )
            index.metric_type = faiss.METRIC_INNER_PRODUCT
            logger.info(f"Training IVFPQ on {N:,} vectors …")
            index.train(embeddings)
            index.add(embeddings)
            index.nprobe = self._IVFPQ_NPROBE
        else:
            logger.info(
                f"Dataset too small for IVFPQ (N={N} < {self._IVFPQ_MIN_TRAIN}), "
                "falling back to IndexFlatIP"
            )
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

        RAM usage:
          - Only 1 batch of embeddings (batch_size * 3 * 768 * 4 B) in RAM at a time.
          - Mean-pooled results streamed to a binary file on disk.
          - Final FAISS build reads from memmap — no second full-corpus copy.

        Saves:
          vector.index      — FAISS index (IVFPQ for large datasets)
          idx_offsets.npy   — int64 array: idx_offsets[faiss_idx] = byte offset
          metadata.json     — model info + jsonl_path for DocStore reconstruction
        """
        index_dir  = Path(index_dir)
        index_dir.mkdir(exist_ok=True, parents=True)
        jsonl_path = str(jsonl_path)

        if resume:
            start_line, byte_offsets, already_done = self._load_checkpoint(
                index_dir, jsonl_path)
        else:
            start_line, byte_offsets, already_done = 0, [], 0
            logger.info("[RESUME] Disabled — building from scratch")

        # Open binary file for streaming embedding writes (append or create-new)
        embs_bin_path = self._embs_bin_path(index_dir)
        embs_bin_mode = 'ab' if already_done > 0 else 'wb'
        embs_bin_file = open(embs_bin_path, embs_bin_mode)

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
                            field_texts = self._extract_fields(doc)   # 3 strings
                            batch_texts.extend(field_texts)
                            batch_offs.append(pos)
                        except json.JSONDecodeError:
                            logger.warning(f"Skipping invalid JSON at line {line_no}")

                        line_no += 1

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
        docs_done  = already_done

        try:
            while True:
                item = batch_queue.get()
                if item is None:
                    break
                lines_read, batch_texts, batch_offs = item
                n_docs = len(batch_offs)

                # Encode: use encode_batch (GPU-safe size), not outer batch × 4
                # batch_texts = n_docs * NUM_FIELDS strings; encode in slices
                raw_embs = self.model.encode(
                    batch_texts,
                    batch_size=self.encode_batch,
                    show_progress_bar=False,
                    convert_to_numpy=True,
                ).astype(np.float32)
                # shape: (n_docs * NUM_FIELDS, dim)
                # layout: [doc0_name, doc0_industry, doc0_addr, doc0_full, doc1_name, ...]

                # Stream to disk — no RAM accumulation
                embs_bin_file.write(raw_embs.tobytes())
                embs_bin_file.flush()

                byte_offsets.extend(batch_offs)
                docs_done += n_docs

                # Checkpoint every _CKPT_INTERVAL_DOCS docs (not every batch)
                if docs_done % _CKPT_INTERVAL_DOCS < n_docs:
                    self._save_checkpoint(
                        index_dir, jsonl_path, lines_read,
                        byte_offsets, docs_done)
                    pbar.set_postfix(docs=docs_done, ckpt="saved")
                else:
                    pbar.set_postfix(docs=docs_done)

                pbar.update(n_docs)

        except KeyboardInterrupt:
            pbar.close()
            # Save final checkpoint so we can resume
            self._save_checkpoint(index_dir, jsonl_path, lines_read,
                                  byte_offsets, docs_done)
            embs_bin_file.close()
            logger.warning(
                f"\n[INTERRUPTED] {docs_done} docs embedded. "
                "Run again to resume automatically.")
            raise
        finally:
            pbar.close()
            embs_bin_file.close()
            reader.join(timeout=2)

        # Final checkpoint flush (may have missed last partial interval)
        self._save_checkpoint(index_dir, jsonl_path, lines_read,
                              byte_offsets, docs_done)

        if producer_error:
            raise producer_error[0]
        if not byte_offsets:
            raise ValueError("No valid documents found in JSONL file")

        # --- Load embeddings via memmap (no extra RAM copy) ---
        # Shape: (docs_done * NUM_FIELDS, dim) — FAISS sees each field slot separately.
        total_vecs = docs_done * NUM_FIELDS
        logger.info(f"Loading {total_vecs:,} embeddings ({docs_done:,} docs × {NUM_FIELDS} fields) via memmap …")
        all_embeddings = np.memmap(
            embs_bin_path, dtype=np.float32, mode='r',
            shape=(total_vecs, self.embedding_dim),
        ).copy()   # .copy() gives writable array needed by faiss.normalize_L2
        logger.info(f"Embeddings shape: {all_embeddings.shape}")

        # --- Build FAISS index ---
        logger.info("Building FAISS index …")
        faiss_index = self._build_faiss_index(all_embeddings)
        del all_embeddings   # free RAM before writing index

        # --- Persist ---
        logger.info("Saving to disk …")
        faiss.write_index(faiss_index, str(index_dir / 'vector.index'))

        idx_offsets = np.array(byte_offsets, dtype=np.int64)
        np.save(str(index_dir / 'idx_offsets.npy'), idx_offsets)

        n = len(byte_offsets)
        used_ivfpq = (n * NUM_FIELDS) >= self._IVFPQ_MIN_TRAIN
        metadata = {
            'model_name': self.model_name,
            'num_fields': NUM_FIELDS,
            'embedding_dim': self.embedding_dim,
            'num_documents': n,
            'jsonl_path': jsonl_path,
            'index_type': 'IVFPQ(cosine)' if used_ivfpq else 'FlatIP(cosine)',
            'nprobe': self._IVFPQ_NPROBE if used_ivfpq else None,
            'normalized': True,
            'metric': 'cosine',
            'device': self.device,
            'fp16': self.fp16,
            'field_layout': ['name', 'industry', 'address', 'full_doc'],
            'fields': [
                'Tên doanh nghiệp', 'Ngành nghề kinh doanh',
                'Địa chỉ', 'full_combined',
            ],
        }
        with open(index_dir / 'metadata.json', 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)

        self._clear_checkpoint(index_dir)
        logger.info(f"Done — {n:,} docs indexed in '{index_dir}'")
