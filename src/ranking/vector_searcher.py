"""Vector Searcher — semantic search via FAISS + DocStore."""

import json
from pathlib import Path
from typing import List, Tuple, Dict, Any
import numpy as np
import logging

try:
    import faiss
except ImportError:
    faiss = None

from sentence_transformers import SentenceTransformer
from src.indexer.doc_store import DocStore

logger = logging.getLogger(__name__)


class VectorSearcher:
    """Semantic search using a pre-built FAISS index + DocStore."""

    def __init__(self, index_dir: str = 'vector_index', device: str = 'cpu'):
        if faiss is None:
            raise ImportError("FAISS not installed. Run: pip install faiss-cpu")

        index_dir = Path(index_dir)

        with open(index_dir / 'metadata.json', encoding='utf-8') as f:
            metadata = json.load(f)

        self.model_name    = metadata['model_name']
        self.embedding_dim = metadata['embedding_dim']
        self.num_documents = metadata['num_documents']
        self.num_fields    = metadata.get('num_fields', 1)
        jsonl_path         = metadata['jsonl_path']

        # SentenceTransformer — needed to encode each query at search time
        self.model = SentenceTransformer(self.model_name, device=device)

        # FAISS index
        self.index = faiss.read_index(str(index_dir / 'vector.index'))
        # Restore nprobe for IVFPQ indexes (not always persisted in index file)
        nprobe = metadata.get('nprobe')
        if nprobe and hasattr(self.index, 'nprobe'):
            self.index.nprobe = nprobe

        # Compact offset array (replaces id_to_doc.pkl ~844 MB → 12 MB)
        idx_offsets = np.load(str(index_dir / 'idx_offsets.npy'))

        # DocStore for on-demand doc retrieval
        self.doc_store = DocStore(jsonl_path, idx_offsets)

        logger.info(f"VectorSearcher ready — {self.num_documents:,} docs, "
                    f"index type: {metadata.get('index_type', 'unknown')}")

    def search(self,
               query: str,
               top_k: int = 10) -> List[Tuple[int, float, Dict[str, Any]]]:
        """
        Search for semantically similar documents.

        Query is L2-normalised before searching so the inner-product score
        equals cosine similarity ∈ [-1, 1].  We map it to [0, 100].

        Returns [(faiss_idx, score, doc_dict), …] sorted by score descending.
        """
        # multilingual-e5 requires "query: " prefix for asymmetric retrieval.
        # The index was built with "passage: <text>" prefixes on each document.
        query_text = f"query: {query.strip()}"
        query_vec = self.model.encode(
            [query_text], convert_to_numpy=True
        )[0].astype(np.float32).reshape(1, -1)

        # Normalise to match how the index was built
        faiss.normalize_L2(query_vec)

        # --- Multi-field grouping strategy ---
        # Each document occupies num_fields consecutive FAISS slots:
        #   slot 0 → name embedding
        #   slot 1 → industry embedding
        #   slot 2 → address/province embedding
        #   slot 3 → full-document embedding  (last slot)
        #
        # Strategy:
        #   Default: MAX over all field embeddings (works for most queries).
        #   Multi-concept (industry + geo): use ONLY full-doc slot so the model
        #     must find both concepts together, preventing a single-field match
        #     from dominating (e.g. "công nghệ hà nội" → industry AND location).
        #
        # Multi-concept detection: query must contain a Vietnamese city/province
        # phrase. Pure domain queries like "vận chuyển hàng hóa" are single-concept
        # even if they have many words — forcing full-doc only causes 0 results.
        nf = self.num_fields
        full_doc_slot = nf - 1   # last slot is always full-doc

        _GEO_TERMS = {
            'hà_nội', 'hồ_chí_minh', 'đà_nẵng', 'hải_phòng', 'cần_thơ',
            'bình_dương', 'đồng_nai', 'long_an', 'bình_định', 'khánh_hòa',
            'thanh_hóa', 'nghệ_an', 'thái_nguyên', 'bắc_ninh', 'quảng_ninh',
            'lâm_đồng', 'đắk_lắk', 'bình_thuận', 'tây_ninh', 'bình_phước',
            'hà_tĩnh', 'quảng_nam', 'quảng_ngãi', 'phú_yên', 'vĩnh_long',
        }
        import unicodedata

        def _norm(s: str) -> str:
            return unicodedata.normalize('NFC', s).lower()

        query_lower = _norm(query)
        detected_geo = next(
            (geo.replace('_', ' ') for geo in _GEO_TERMS
             if geo.replace('_', ' ') in query_lower),
            None
        )
        is_multi_concept = detected_geo is not None

        # Fetch more candidates when multi-concept so slot-3 coverage is sufficient.
        # multi-concept: fetch_k = top_k * nf * 20 → enough full-doc hits after geo filter
        # default:       fetch_k = top_k * nf * 5
        fetch_multiplier = 20 if is_multi_concept else 5
        fetch_k = min(top_k * nf * fetch_multiplier,
                      self.num_documents * nf)
        distances, indices = self.index.search(query_vec, k=fetch_k)

        valid = [(int(idx), float(dist))
                 for idx, dist in zip(indices[0], distances[0])
                 if idx != -1]

        if not valid:
            return []

        doc_best: dict = {}
        for faiss_idx, inner_product in valid:
            doc_id    = faiss_idx // nf
            field_idx = faiss_idx % nf

            if is_multi_concept and field_idx != full_doc_slot:
                continue   # ignore per-field embeddings for geo queries

            if doc_id not in doc_best or inner_product > doc_best[doc_id]:
                doc_best[doc_id] = inner_product

        # Sort all candidates — we need more than top_k to geo-filter
        all_ranked = sorted(doc_best.items(), key=lambda kv: kv[1], reverse=True)

        # For geo queries: fetch a larger pool and hard-filter by address field.
        # Fixes "bình định" vs "bình dương" confusion — embeddings are too similar
        # for the model to distinguish Vietnamese province names reliably.
        if detected_geo:
            pool_size = min(len(all_ranked), top_k * 10)
            pool_ids  = [doc_id for doc_id, _ in all_ranked[:pool_size]]
            pool_docs = self.doc_store.get_many(pool_ids)

            results = []
            for doc_id, inner_product in all_ranked[:pool_size]:
                doc     = pool_docs[doc_id]
                address = _norm(doc.get('Địa chỉ', ''))
                if detected_geo in address:
                    score = max(0.0, inner_product) * 100.0
                    results.append((doc_id, score, doc))
                if len(results) >= top_k:
                    break

            # Fallback: if no docs match the geo filter (sparse province),
            # return unfiltered top_k so the page isn't empty.
            if results:
                return results

        ranked  = all_ranked[:top_k]
        doc_ids = [doc_id for doc_id, _ in ranked]
        docs    = self.doc_store.get_many(doc_ids)

        return [(doc_id, max(0.0, ip) * 100.0, docs[doc_id])
                for doc_id, ip in ranked]

    def search_with_explanation(self,
                                query: str,
                                top_k: int = 10) -> Dict[str, Any]:
        import time
        start = time.time()
        results = self.search(query, top_k=top_k)
        return {
            'query': query,
            'model': self.model_name,
            'num_results': len(results),
            'results': results,
            'execution_time_ms': (time.time() - start) * 1000,
        }
