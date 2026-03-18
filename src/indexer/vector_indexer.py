"""Vector Indexer for building semantic search index."""

import json
import threading
import queue as _queue
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime
import numpy as np
from tqdm import tqdm
import pickle
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
_CHECKPOINT_DOCS = 'build_docs.pkl'
_CHECKPOINT_EMBS = 'build_embeddings.npy'

# Batch sizes tuned per device type
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
            mem_gb = props.total_memory / 1024 ** 3
            logger.info(f"  GPU {i}: {props.name}  ({mem_gb:.1f} GB VRAM)")
    else:
        import os
        cpu_count = os.cpu_count()
        logger.info(f"  CPU  ({cpu_count} logical cores)")


class VectorIndexer:
    """Build vector index using embeddings for semantic search."""

    def __init__(self,
                 model_name: str = 'distiluse-base-multilingual-cased-v2',
                 batch_size: Optional[int] = None,
                 device: str = 'auto',
                 fp16: bool = False):
        """
        Initialize Vector Indexer.

        Args:
            model_name: Sentence-Transformers model name.
            batch_size: Batch size for encoding. None = auto (256 GPU / 32 CPU).
            device: 'auto' | 'cpu' | 'cuda'. auto selects GPU when available.
            fp16: Use half-precision (float16) on GPU for ~2x speed, ~half VRAM.
        """
        if faiss is None:
            raise ImportError("FAISS not installed. Run: pip install faiss-cpu")

        # Resolve device
        self.device = _detect_device() if device == 'auto' else device

        # Auto batch size
        self.batch_size = batch_size or (
            _BATCH_SIZE_GPU if self.device.startswith('cuda') else _BATCH_SIZE_CPU
        )

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

        self.index = None
        self.id_to_doc: Dict[int, Dict] = {}
        self.texts: List[str] = []

    # ------------------------------------------------------------------
    # Text extraction
    # ------------------------------------------------------------------

    def _extract_text(self, doc: Dict[str, Any]) -> str:
        """Extract searchable text fields from a document."""
        fields = [
            'Tên doanh nghiệp',
            'Tên giao dịch',
            'Ngành nghề kinh doanh',
            'Địa chỉ',
        ]
        parts = [str(doc[f]).strip() for f in fields if doc.get(f)]
        return ' '.join(parts)

    # ------------------------------------------------------------------
    # Checkpoint helpers
    # ------------------------------------------------------------------

    def _save_checkpoint(self, index_dir: Path, jsonl_path: str,
                         lines_read: int,
                         documents: List[Dict], texts: List[str],
                         embeddings: np.ndarray) -> None:
        """Atomically save checkpoint: write to .tmp files first, then rename.

        If the process is killed mid-write, only the .tmp files are corrupt;
        the previous checkpoint remains intact and will be used on resume.
        """
        # np.save() automatically appends '.npy' if not present, so we must
        # give the tmp file a name that already ends with '.npy' to avoid
        # double-extension ('build_embeddings.npy.tmp.npy').
        embs_tmp  = index_dir / 'build_embeddings.tmp.npy'
        docs_tmp  = index_dir / (_CHECKPOINT_DOCS  + '.tmp')
        meta_tmp  = index_dir / (_CHECKPOINT_META  + '.tmp')

        # 1. Write to temp files
        np.save(str(embs_tmp), embeddings)
        with open(docs_tmp, 'wb') as f:
            pickle.dump((documents, texts), f)
        meta = {
            'jsonl_path': str(jsonl_path),
            'model_name': self.model_name,
            'lines_read': lines_read,
            'docs_processed': len(documents),
            'saved_at': datetime.now().isoformat(),
        }
        with open(meta_tmp, 'w', encoding='utf-8') as f:
            json.dump(meta, f, indent=2)

        # 2. Atomic rename: replaces target only after all 3 files are ready
        embs_tmp.replace(index_dir / _CHECKPOINT_EMBS)
        docs_tmp.replace(index_dir / _CHECKPOINT_DOCS)
        meta_tmp.replace(index_dir / _CHECKPOINT_META)

    def _load_checkpoint(self, index_dir: Path, jsonl_path: str):
        """Return (start_line, documents, texts, embeddings) or fresh state."""
        meta_path = index_dir / _CHECKPOINT_META
        if not meta_path.exists():
            return 0, [], [], None
        try:
            with open(meta_path, encoding='utf-8') as f:
                meta = json.load(f)
            if meta.get('jsonl_path') != str(jsonl_path):
                logger.warning("[RESUME] Different JSONL file — ignoring checkpoint")
                return 0, [], [], None
            if meta.get('model_name') != self.model_name:
                logger.warning("[RESUME] Different model — ignoring checkpoint")
                return 0, [], [], None
            with open(index_dir / _CHECKPOINT_DOCS, 'rb') as f:
                documents, texts = pickle.load(f)
            embeddings = np.load(str(index_dir / _CHECKPOINT_EMBS))
            start_line = meta['lines_read']
            logger.info(
                f"[RESUME] {len(documents)} docs already embedded, "
                f"resuming from line {start_line} (saved {meta.get('saved_at', '?')})"
            )
            return start_line, documents, texts, embeddings
        except Exception as e:
            logger.warning(f"[RESUME] Cannot load checkpoint ({e}) — starting fresh")
            return 0, [], [], None

    def _clear_checkpoint(self, index_dir: Path) -> None:
        for name in (_CHECKPOINT_META, _CHECKPOINT_DOCS, _CHECKPOINT_EMBS):
            p = index_dir / name
            if p.exists():
                p.unlink()

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

        Uses a producer-consumer pipeline: a background thread reads and
        pre-processes text while the main thread (GPU) encodes embeddings,
        so I/O and compute overlap.

        Args:
            jsonl_path: Path to input JSONL file.
            index_dir: Directory to write the finished index.
            max_docs: Cap on documents to index (None = all).
            resume: Continue from last checkpoint if available.
            prefetch_batches: Number of batches to prefetch in the queue.
        """
        index_dir = Path(index_dir)
        index_dir.mkdir(exist_ok=True, parents=True)
        jsonl_path = str(jsonl_path)

        # --- Resume or fresh start ---
        if resume:
            start_line, documents, texts, all_embeddings = self._load_checkpoint(
                index_dir, jsonl_path
            )
        else:
            start_line, documents, texts, all_embeddings = 0, [], [], None
            logger.info("[RESUME] Disabled — building from scratch")

        already_done = len(documents)

        # ------------------------------------------------------------------
        # Producer thread: reads JSONL, extracts text, pushes batches to queue
        # ------------------------------------------------------------------
        batch_queue: _queue.Queue = _queue.Queue(maxsize=prefetch_batches)
        producer_error: List[Exception] = []   # shared error slot

        def producer() -> None:
            batch_docs: List[Dict] = []
            batch_texts: List[str] = []
            current_line = start_line

            try:
                with open(jsonl_path, 'r', encoding='utf-8') as f:
                    for line_no, line in enumerate(f):
                        if line_no < start_line:
                            continue
                        current_line = line_no + 1

                        # Honor max_docs across checkpoint + new docs
                        total = already_done + len(batch_docs) + sum(
                            len(b[1]) for b in list(batch_queue.queue)
                        )
                        if max_docs and total >= max_docs:
                            break

                        try:
                            doc = json.loads(line.strip())
                            text = self._extract_text(doc)
                            if text.strip():
                                batch_docs.append(doc)
                                batch_texts.append(text)
                        except json.JSONDecodeError:
                            logger.warning(f"Skipping invalid JSON at line {line_no}")

                        if len(batch_docs) >= self.batch_size:
                            batch_queue.put((current_line, batch_docs, batch_texts))
                            batch_docs, batch_texts = [], []

                # flush tail
                if batch_docs:
                    batch_queue.put((current_line, batch_docs, batch_texts))
            except Exception as exc:
                producer_error.append(exc)
            finally:
                batch_queue.put(None)  # sentinel

        reader = threading.Thread(target=producer, daemon=True)
        reader.start()

        # ------------------------------------------------------------------
        # Consumer (main thread / GPU): encode batches as they arrive
        # ------------------------------------------------------------------
        pbar = tqdm(desc=f"Embedding [{self.device.upper()}]",
                    unit="doc", initial=already_done)
        lines_read = start_line

        try:
            while True:
                item = batch_queue.get()
                if item is None:
                    break

                lines_read, batch_docs, batch_texts = item

                # Encode on GPU — blocks until done; producer runs concurrently
                batch_embs = self.model.encode(
                    batch_texts,
                    batch_size=self.batch_size,
                    show_progress_bar=False,
                    convert_to_numpy=True,
                ).astype(np.float32)

                documents.extend(batch_docs)
                texts.extend(batch_texts)
                all_embeddings = (
                    batch_embs if all_embeddings is None
                    else np.vstack([all_embeddings, batch_embs])
                )

                pbar.update(len(batch_docs))

                # Save checkpoint after every completed batch
                self._save_checkpoint(
                    index_dir, jsonl_path, lines_read,
                    documents, texts, all_embeddings
                )
                pbar.set_postfix(docs=len(documents), ckpt="saved")

        except KeyboardInterrupt:
            pbar.close()
            # Checkpoint of the last completed batch is already on disk.
            # The batch currently being encoded (if any) is simply discarded
            # and will be re-processed on the next run.
            logger.warning(
                f"\n[INTERRUPTED] Stopped at line {lines_read} "
                f"({len(documents)} docs embedded).\n"
                f"Run the same command again to resume automatically."
            )
            raise  # re-raise so the caller/CLI sees a non-zero exit

        finally:
            pbar.close()
            reader.join(timeout=2)

        if producer_error:
            raise producer_error[0]

        if not documents:
            raise ValueError("No valid documents found in JSONL file")

        all_embeddings = np.array(all_embeddings, dtype=np.float32)
        logger.info(f"Embeddings shape: {all_embeddings.shape}")

        # --- Build FAISS index ---
        logger.info("Building FAISS index...")
        self.index = faiss.IndexFlatL2(self.embedding_dim)
        self.index.add(all_embeddings)

        # --- Persist ---
        logger.info("Saving index to disk...")
        faiss.write_index(self.index, str(index_dir / 'vector.index'))

        self.id_to_doc = {i: doc for i, doc in enumerate(documents)}
        with open(index_dir / 'id_to_doc.pkl', 'wb') as f:
            pickle.dump(self.id_to_doc, f)

        with open(index_dir / 'texts.pkl', 'wb') as f:
            pickle.dump(texts, f)

        metadata = {
            'model_name': self.model_name,
            'embedding_dim': self.embedding_dim,
            'num_documents': len(documents),
            'num_embeddings': int(all_embeddings.shape[0]),
            'jsonl_path': jsonl_path,
            'device': self.device,
            'fp16': self.fp16,
        }
        with open(index_dir / 'metadata.json', 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)

        self._clear_checkpoint(index_dir)
        logger.info(f"Done — {len(documents)} documents indexed in {index_dir}")

    # ------------------------------------------------------------------
    # Load & query
    # ------------------------------------------------------------------

    def load_index(self, index_dir: str = 'vector_index') -> None:
        """Load a previously built index from disk."""
        index_dir = Path(index_dir)
        if not (index_dir / 'vector.index').exists():
            raise FileNotFoundError(f"Index not found at {index_dir}")

        logger.info(f"Loading index from {index_dir}")
        self.index = faiss.read_index(str(index_dir / 'vector.index'))

        with open(index_dir / 'id_to_doc.pkl', 'rb') as f:
            self.id_to_doc = pickle.load(f)

        with open(index_dir / 'texts.pkl', 'rb') as f:
            self.texts = pickle.load(f)

        logger.info(f"Loaded {len(self.id_to_doc)} documents")

    def embed_query(self, query: str) -> np.ndarray:
        """Encode a single query string to a float32 vector."""
        return self.model.encode([query], convert_to_numpy=True)[0].astype(np.float32)
