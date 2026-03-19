"""Hybrid Search — combines BM25 and Vector Search scores."""

from typing import List, Dict, Tuple, Any
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)


class HybridSearch:
    """Combine BM25 and Vector Search using score fusion."""

    def __init__(self,
                 bm25_ranker,
                 vector_searcher,
                 preprocessor,
                 bm25_weight: float = 0.5,
                 vector_weight: float = 0.5):
        """
        Args:
            preprocessor: TextPreprocessor — used to build BM25 query terms
                          (same preprocessing as the console app).
        """
        self.bm25_ranker     = bm25_ranker
        self.vector_searcher = vector_searcher
        self.preprocessor    = preprocessor

        total = bm25_weight + vector_weight
        self.bm25_weight   = bm25_weight / total
        self.vector_weight = vector_weight / total

        logger.info(f"HybridSearch — BM25 {self.bm25_weight:.0%} / "
                    f"Vector {self.vector_weight:.0%}")

    # ------------------------------------------------------------------
    # Score normalisation helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _normalise_bm25(results: List[Tuple[int, float, Dict]]) -> Dict[int, float]:
        if not results:
            return {}
        max_score = max(s for _, s, _ in results) or 1.0
        return {doc_id: min(score / max_score * 100, 100)
                for doc_id, score, _ in results}

    @staticmethod
    def _normalise_vector(results: List[Tuple[int, float, Dict]]) -> Dict[int, float]:
        return {doc_id: min(score, 100) for doc_id, score, _ in results}

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def search(self,
               query: str,
               top_k: int = 10,
               return_details: bool = False) -> List[Tuple[int, float, Dict[str, Any]]]:
        """
        Fetch candidates from both systems, normalise scores, fuse, and rank.

        Uses TextPreprocessor for BM25 (same as console app) so query terms
        are properly segmented and expanded.
        """
        candidate_k = top_k * 3   # over-fetch for better recall before fusion

        # BM25 — with proper Vietnamese preprocessing
        query_terms, _ = self.preprocessor.build_search_terms(query)
        bm25_results = self.bm25_ranker.rank_documents(
            query_terms=query_terms, top_k=candidate_k)

        # Vector — encodes query with SentenceTransformer
        vector_results = self.vector_searcher.search(
            query=query, top_k=candidate_k)

        bm25_norm   = self._normalise_bm25(bm25_results)
        vector_norm = self._normalise_vector(vector_results)

        # Collect docs (prefer BM25 doc object when both have the same id)
        doc_map: Dict[int, Dict] = {}
        for doc_id, _, doc in bm25_results:
            doc_map[doc_id] = doc
        for doc_id, _, doc in vector_results:
            if doc_id not in doc_map:
                doc_map[doc_id] = doc

        # Fuse scores
        all_ids = set(bm25_norm) | set(vector_norm)
        ranked: List[Tuple[int, float, Dict]] = []
        for doc_id in all_ids:
            b_score = bm25_norm.get(doc_id, 0.0)
            v_score = vector_norm.get(doc_id, 0.0)
            hybrid  = self.bm25_weight * b_score + self.vector_weight * v_score

            doc = doc_map.get(doc_id)
            if doc is None:
                continue
            if return_details:
                doc = dict(doc)
                doc['_hybrid_scores'] = {
                    'hybrid': hybrid, 'bm25': b_score, 'vector': v_score}
            ranked.append((doc_id, hybrid, doc))

        ranked.sort(key=lambda x: x[1], reverse=True)
        return ranked[:top_k]

    def set_weights(self, bm25_weight: float, vector_weight: float) -> None:
        total = bm25_weight + vector_weight
        self.bm25_weight   = bm25_weight / total
        self.vector_weight = vector_weight / total
        logger.info(f"Updated weights: BM25={self.bm25_weight:.0%}, "
                    f"Vector={self.vector_weight:.0%}")
