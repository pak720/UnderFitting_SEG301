"""Hybrid Search combining BM25 + Vector Search."""

from typing import List, Dict, Tuple, Any
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)


class HybridSearch:
    """Combine BM25 and Vector Search results."""

    def __init__(self,
                 bm25_ranker,
                 vector_searcher,
                 bm25_weight: float = 0.5,
                 vector_weight: float = 0.5):
        """
        Initialize Hybrid Search.

        Args:
            bm25_ranker: BM25Ranker instance
            vector_searcher: VectorSearcher instance
            bm25_weight: Weight for BM25 scores (0-1)
            vector_weight: Weight for vector scores (0-1)
        """
        self.bm25_ranker = bm25_ranker
        self.vector_searcher = vector_searcher

        total_weight = bm25_weight + vector_weight
        self.bm25_weight = bm25_weight / total_weight
        self.vector_weight = vector_weight / total_weight

        logger.info(f"HybridSearch initialized:")
        logger.info(f"  BM25 weight: {self.bm25_weight:.2%}")
        logger.info(f"  Vector weight: {self.vector_weight:.2%}")

    def _normalize_bm25_scores(self,
                               bm25_results: List[Tuple[int, float, Dict]],
                               max_score: float = None) -> Dict[int, float]:
        """
        Normalize BM25 scores to 0-100 scale.

        Args:
            bm25_results: Results from BM25Ranker
            max_score: Reference score for normalization (auto-detect if None)

        Returns:
            Dict mapping doc_id -> normalized_score
        """
        if not bm25_results:
            return {}

        # Get max score for normalization
        if max_score is None:
            max_score = max((score for _, score, _ in bm25_results), default=1.0)
            max_score = max(max_score, 1.0)  # Avoid division by zero

        bm25_scores = {}
        for doc_id, score, _ in bm25_results:
            # Normalize to 0-100
            normalized = (score / max_score) * 100
            bm25_scores[doc_id] = min(normalized, 100)  # Cap at 100

        return bm25_scores

    def _normalize_vector_scores(self,
                                vector_results: List[Tuple[int, float, Dict]]) -> Dict[int, float]:
        """
        Normalize vector scores (already in 0-100 scale).

        Args:
            vector_results: Results from VectorSearcher

        Returns:
            Dict mapping doc_id -> normalized_score
        """
        vector_scores = {}
        for doc_id, score, _ in vector_results:
            # Already in 0-100 scale from VectorSearcher
            vector_scores[doc_id] = min(score, 100)

        return vector_scores

    def search(self,
              query: str,
              top_k: int = 10,
              return_details: bool = False) -> List[Tuple[int, float, Dict[str, Any]]]:
        """
        Perform hybrid search.

        Args:
            query: Search query
            top_k: Number of results to return
            return_details: Include score breakdown in results

        Returns:
            List of (doc_id, hybrid_score, document) tuples
        """
        # Get BM25 results
        bm25_results = self.bm25_ranker.rank_documents(
            query_terms=query.lower().split(),
            top_k=top_k * 2  # Get more candidates for merging
        )

        # Get Vector Search results
        vector_results = self.vector_searcher.search(
            query=query,
            top_k=top_k * 2
        )

        # Normalize scores
        bm25_scores = self._normalize_bm25_scores(bm25_results)
        vector_scores = self._normalize_vector_scores(vector_results)

        # Merge results
        hybrid_scores = defaultdict(lambda: {'bm25': 0, 'vector': 0, 'doc': None})

        for doc_id, score, doc in bm25_results:
            hybrid_scores[doc_id]['bm25'] = bm25_scores[doc_id]
            hybrid_scores[doc_id]['doc'] = doc

        for doc_id, score, doc in vector_results:
            hybrid_scores[doc_id]['vector'] = vector_scores[doc_id]
            if doc_id not in hybrid_scores or hybrid_scores[doc_id]['doc'] is None:
                hybrid_scores[doc_id]['doc'] = doc

        # Calculate hybrid scores
        ranked_results = []
        for doc_id, scores in hybrid_scores.items():
            hybrid_score = (
                self.bm25_weight * scores['bm25'] +
                self.vector_weight * scores['vector']
            )

            result_doc = scores['doc']
            if result_doc:
                if return_details:
                    # Add score breakdown
                    result_doc = dict(result_doc)
                    result_doc['_hybrid_scores'] = {
                        'hybrid': hybrid_score,
                        'bm25': scores['bm25'],
                        'vector': scores['vector']
                    }

                ranked_results.append((doc_id, hybrid_score, result_doc))

        # Sort by hybrid score and return top K
        ranked_results.sort(key=lambda x: x[1], reverse=True)
        return ranked_results[:top_k]

    def search_with_explanation(self,
                               query: str,
                               top_k: int = 10) -> Dict[str, Any]:
        """
        Search with detailed explanation of score contributions.

        Returns:
            {
                'query': query,
                'bm25_weight': float,
                'vector_weight': float,
                'results': [(doc_id, hybrid_score, doc_with_breakdown), ...],
                'breakdown_sample': {
                    'hybrid': float,
                    'bm25': float,
                    'vector': float
                }
            }
        """
        results = self.search(query, top_k=top_k, return_details=True)

        breakdown = {}
        if results:
            first_result = results[0][2]
            if '_hybrid_scores' in first_result:
                breakdown = first_result['_hybrid_scores']

        return {
            'query': query,
            'weight_config': {
                'bm25_weight': self.bm25_weight,
                'vector_weight': self.vector_weight
            },
            'num_results': len(results),
            'results': results,
            'sample_score_breakdown': breakdown
        }

    def set_weights(self, bm25_weight: float, vector_weight: float) -> None:
        """Adjust hybrid weights."""
        total = bm25_weight + vector_weight
        self.bm25_weight = bm25_weight / total
        self.vector_weight = vector_weight / total
        logger.info(f"Updated weights: BM25={self.bm25_weight:.2%}, Vector={self.vector_weight:.2%}")
