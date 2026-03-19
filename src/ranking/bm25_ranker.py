"""BM25 Ranker — uses compact numpy doc_lengths + DocStore for on-demand retrieval."""
import math
from typing import Dict, List, Tuple, Any, Optional
from collections import defaultdict
import heapq

import numpy as np

from src.indexer.doc_store import DocStore


class BM25Ranker:
    def __init__(self,
                 inverted_index: Dict[str, List[Tuple[int, int]]],
                 doc_lengths: np.ndarray,
                 doc_store: DocStore,
                 k1: float = 1.5,
                 b: float = 0.75):
        """
        Args:
            inverted_index : term → [(doc_id, freq), …]
            doc_lengths    : int32 array, doc_lengths[doc_id] = token count
            doc_store      : DocStore for on-demand full-document retrieval
        """
        self.inverted_index = inverted_index
        self.doc_lengths    = doc_lengths
        self.doc_store      = doc_store
        self.k1 = k1
        self.b  = b

        self.N = len(doc_lengths)
        self.avg_doc_length = float(doc_lengths.mean()) if self.N else 0.0
        self.idf_cache: Dict[str, float] = {}

        # Precompute per-doc BM25 length normalisation factor (numpy, fast)
        self.length_norm = np.where(
            self.avg_doc_length > 0,
            1.0 - b + b * (doc_lengths.astype(np.float32) / self.avg_doc_length),
            1.0
        )

        # Intent filtering: pre-build doc-id sets from the inverted index so
        # we never load full document text during scoring.
        self._intent_column_rules = {
            'technology': {
                'positive': {'công_nghệ', 'công_nghệ_thông_tin', 'phần_mềm', 'dữ_liệu_lớn'},
                'negative': {'khai_thác_than', 'than_cứng'},
            },
            'food_service': {
                'positive': {'thực_phẩm', 'ăn_uống', 'dịch_vụ_ăn_uống'},
                'negative': {'dược_phẩm', 'thuốc'},
            },
        }
        all_intent_terms: set = set()
        for rule in self._intent_column_rules.values():
            all_intent_terms |= rule['positive'] | rule['negative']

        self._intent_doc_sets: Dict[str, frozenset] = {
            term: frozenset(doc_id for doc_id, _ in inverted_index[term])
            if term in inverted_index else frozenset()
            for term in all_intent_terms
        }

    # ------------------------------------------------------------------
    # IDF
    # ------------------------------------------------------------------

    def _compute_idf(self, term: str) -> float:
        if term in self.idf_cache:
            return self.idf_cache[term]
        if term not in self.inverted_index:
            idf = 0.0
        else:
            n = len(self.inverted_index[term])
            idf = math.log((self.N - n + 0.5) / (n + 0.5) + 1)
        self.idf_cache[term] = idf
        return idf

    # ------------------------------------------------------------------
    # BM25 score
    # ------------------------------------------------------------------

    def _compute_bm25_score(self, term: str, doc_id: int,
                             term_freq: int) -> float:
        idf  = self._compute_idf(term)
        norm = float(self.length_norm[doc_id])
        tf   = term_freq * (self.k1 + 1) / (term_freq + self.k1 * norm)
        return idf * tf

    # ------------------------------------------------------------------
    # Intent filtering (no disk I/O — uses pre-built doc-id frozensets)
    # ------------------------------------------------------------------

    def _doc_passes_intent(self, doc_id: int,
                            intent_group: Optional[str]) -> bool:
        if not intent_group:
            return True
        rule = self._intent_column_rules.get(intent_group)
        if not rule:
            return True
        has_pos = any(doc_id in self._intent_doc_sets.get(t, frozenset())
                      for t in rule['positive'])
        has_neg = any(doc_id in self._intent_doc_sets.get(t, frozenset())
                      for t in rule['negative'])
        return has_pos and not has_neg

    # ------------------------------------------------------------------
    # Ranking
    # ------------------------------------------------------------------

    def rank_documents(self,
                       query_terms: List[str],
                       top_k: int = 10,
                       intent_group: Optional[str] = None
                       ) -> List[Tuple[int, float, Any]]:
        """
        Returns [(doc_id, score, doc_dict), …] sorted by score descending.
        Full document content is fetched from DocStore only for the top-k hits.
        """
        if not query_terms:
            return []

        query_terms = list(dict.fromkeys(query_terms))
        candidate_docs: Dict[int, float] = defaultdict(float)

        for term in query_terms:
            if term not in self.inverted_index:
                continue
            for doc_id, term_freq in self.inverted_index[term]:
                candidate_docs[doc_id] += self._compute_bm25_score(
                    term, doc_id, term_freq)

        if not candidate_docs:
            return []

        if intent_group:
            candidate_docs = {
                doc_id: score
                for doc_id, score in candidate_docs.items()
                if self._doc_passes_intent(doc_id, intent_group)
            }

        if not candidate_docs:
            return []

        top_docs = heapq.nlargest(top_k, candidate_docs.items(), key=lambda x: x[1])

        # Fetch full documents in offset order (sequential reads = fast)
        doc_ids = [doc_id for doc_id, _ in top_docs]
        docs    = self.doc_store.get_many(doc_ids)

        return [(doc_id, score, docs[doc_id]) for doc_id, score in top_docs]

    def explain_score(self, query_terms: List[str],
                      doc_id: int) -> Dict[str, Any]:
        explanation: Dict[str, Any] = {'doc_id': doc_id, 'terms': {}}
        for term in query_terms:
            if term not in self.inverted_index:
                continue
            freq = next(
                (f for d, f in self.inverted_index[term] if d == doc_id), 0)
            score = self._compute_bm25_score(term, doc_id, freq) if freq else 0.0
            explanation['terms'][term] = {'freq': freq, 'score': score}
        return explanation
