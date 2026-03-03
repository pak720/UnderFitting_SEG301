import math
from typing import Dict, List, Tuple, Any, Optional
from collections import defaultdict
import heapq


class BM25Ranker:
    def __init__(self,
                 inverted_index: Dict[str, List[Tuple[int, int]]],
                 doc_info: Dict[int, Dict[str, Any]],
                 k1: float = 1.5,
                 b: float = 0.75):

        self.inverted_index = inverted_index
        self.doc_info = doc_info
        self.k1 = k1
        self.b = b

        self.N = len(doc_info)
        self.idf_cache = {}

        # Precompute avg doc length
        self.avg_doc_length = sum(
            doc['length'] for doc in doc_info.values()
        ) / self.N if self.N > 0 else 0

        # Precompute length normalization
        self.length_norm = {
            doc_id: 1 - b + b * (info['length'] / self.avg_doc_length)
            for doc_id, info in doc_info.items()
        }

        # Token cache (IMPORTANT)
        self.doc_token_cache: Dict[int, set] = {}

        # Intent rules (converted to sets)
        self.intent_column_rules = {
            'technology': {
                'positive': {'công_nghệ', 'công_nghệ_thông_tin', 'phần_mềm', 'dữ_liệu_lớn'},
                'negative': {'khai_thác_than', 'than_cứng'}
            },
            'food_service': {
                'positive': {'thực_phẩm', 'ăn_uống', 'dịch_vụ_ăn_uống'},
                'negative': {'dược_phẩm', 'thuốc'}
            }
        }

    # ===============================
    # Token handling
    # ===============================

    def _get_doc_tokens(self, doc_id: int) -> set:
        if doc_id in self.doc_token_cache:
            return self.doc_token_cache[doc_id]

        original_doc = self.doc_info[doc_id]['original_doc']

        combined_text = ' '.join([
            str(original_doc.get('Tên doanh nghiệp', '')).lower(),
            str(original_doc.get('Tên giao dịch', '')).lower(),
            str(original_doc.get('Ngành nghề kinh doanh', '')).lower(),
            str(original_doc.get('Địa chỉ', '')).lower(),
        ])

        tokens = set(combined_text.split())
        self.doc_token_cache[doc_id] = tokens
        return tokens

    # ===============================
    # IDF
    # ===============================

    def _compute_idf(self, term: str) -> float:
        if term in self.idf_cache:
            return self.idf_cache[term]

        if term not in self.inverted_index:
            idf = 0
        else:
            n = len(self.inverted_index[term])
            idf = math.log((self.N - n + 0.5) / (n + 0.5) + 1)

        self.idf_cache[term] = idf
        return idf

    # ===============================
    # BM25 scoring
    # ===============================

    def _compute_bm25_score(self,
                            term: str,
                            doc_id: int,
                            term_freq: int) -> float:

        idf = self._compute_idf(term)
        norm = self.length_norm[doc_id]

        numerator = term_freq * (self.k1 + 1)
        denominator = term_freq + self.k1 * norm

        return idf * (numerator / denominator)

    # ===============================
    # Intent filtering
    # ===============================

    def _doc_passes_intent(self,
                           doc_id: int,
                           intent_group: Optional[str]) -> bool:

        if not intent_group:
            return True

        rule = self.intent_column_rules.get(intent_group)
        if not rule:
            return True

        tokens = self._get_doc_tokens(doc_id)

        positive = rule['positive']
        negative = rule['negative']

        has_positive = bool(tokens & positive) if positive else True
        has_negative = bool(tokens & negative) if negative else False

        return has_positive and not has_negative

    # ===============================
    # Keyword boost (FAST)
    # ===============================

    def _compute_keyword_boost(self,
                               doc_id: int,
                               query_terms: List[str]) -> float:

        tokens = self._get_doc_tokens(doc_id)

        overlap = len(tokens & set(query_terms))
        return overlap * 0.8

    # ===============================
    # Ranking
    # ===============================

    def rank_documents(self,
                       query_terms: List[str],
                       top_k: int = 10,
                       intent_group: Optional[str] = None
                       ) -> List[Tuple[int, float, Any]]:

        if not query_terms:
            return []

        query_terms = list(dict.fromkeys(query_terms))

        candidate_docs = defaultdict(float)

        # BM25 scoring
        for term in query_terms:
            if term not in self.inverted_index:
                continue

            postings = self.inverted_index[term]

            for doc_id, term_freq in postings:
                score = self._compute_bm25_score(term, doc_id, term_freq)
                candidate_docs[doc_id] += score

        if not candidate_docs:
            return []

        # Intent filtering (FAST)
        if intent_group:
            candidate_docs = {
                doc_id: score
                for doc_id, score in candidate_docs.items()
                if self._doc_passes_intent(doc_id, intent_group)
            }

        if not candidate_docs:
            return []

        # Keyword boost
        for doc_id in candidate_docs:
            candidate_docs[doc_id] += self._compute_keyword_boost(
                doc_id, query_terms
            )

        # Top K
        top_docs = heapq.nlargest(
            top_k,
            candidate_docs.items(),
            key=lambda x: x[1]
        )

        results = []
        for doc_id, score in top_docs:
            results.append((
                doc_id,
                score,
                self.doc_info[doc_id]['original_doc']
            ))

        return results