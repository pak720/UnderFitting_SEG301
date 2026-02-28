"""BM25 ranking algorithm implementation"""
import math
from typing import Dict, List, Tuple, Any, Optional
from collections import defaultdict
import time
import heapq


class BM25Ranker:
    """BM25 ranking algorithm implementation (no library calls)"""

    def __init__(self, inverted_index: Dict[str, List[Tuple[int, int]]],
                 doc_info: Dict[int, Dict[str, Any]],
                 k1: float = 1.5, b: float = 0.75):
        """
        Initialize BM25 ranker

        Args:
            inverted_index: Dictionary mapping term to list of (doc_id, freq) pairs
            doc_info: Dictionary mapping doc_id to document information
            k1: BM25 parameter (controls term frequency saturation)
            b: BM25 parameter (controls document length normalization)
        """
        self.inverted_index = inverted_index
        self.doc_info = doc_info
        self.k1 = k1
        self.b = b

        # Precompute IDF and document statistics
        self.N = len(doc_info)  # Total number of documents
        self.idf_cache = {}  # Cache IDF values
        self.avg_doc_length = self._compute_average_doc_length()

        # Light-weight query/result cache to speed up repeated searches in console mode.
        # Key format: (tuple(query_terms), top_k)
        self.query_cache: Dict[Tuple[Tuple[str, ...], int], List[Tuple[int, float, Any]]] = {}

        # Lazy cache for lowercased important fields, built per doc only when needed.
        # This avoids creating huge duplicated strings for the whole corpus at startup.
        self._doc_text_cache: Dict[int, Dict[str, str]] = {}

        # Field weights for better keyword precision.
        # Match in company name should be stronger than match in address.
        self.field_boosts = {
            'Tên doanh nghiệp': 2.5,
            'Tên giao dịch': 2.0,
            'Ngành nghề kinh doanh': 1.4,
            'Địa chỉ': 1.1,
        }

        # Column-aware intent disambiguation rules.
        # Goal: avoid mixing nearby domains (electric power vs electronics vs home appliances).
        self.intent_column_rules = {
            'electric_power': {
                'positive': {'điện_lực', 'điện_năng', 'phát_điện', 'truyền_tải_điện', 'phân_phối_điện'},
                'negative': {'điện_tử', 'linh_kiện_điện_tử', 'thiết_bị_điện_tử', 'điện_gia_dụng', 'đồ_điện_gia_dụng', 'điện_lạnh'}
            },
            'electronics': {
                'positive': {'điện_tử', 'linh_kiện_điện_tử', 'thiết_bị_điện_tử'},
                'negative': {'điện_lực', 'điện_năng', 'phát_điện', 'truyền_tải_điện', 'phân_phối_điện'}
            },
            'home_appliance': {
                'positive': {'điện_gia_dụng', 'đồ_điện_gia_dụng', 'điện_lạnh', 'thiết_bị_điện'},
                'negative': {'điện_lực', 'điện_năng', 'phát_điện'}
            },
            'technology': {
                # Tech companies should contain tech-related terms in business columns.
                'positive': {'công_nghệ', 'công_nghệ_thông_tin', 'phần_mềm', 'dữ_liệu_lớn'},
                # Optional light negatives to reduce off-topic industrial hits.
                'negative': {'khai_thác_than', 'than_cứng'}
            },
            'food_service': {
                # Food/F&B queries should prefer food business lines.
                'positive': {'thực_phẩm', 'ăn_uống', 'dịch_vụ_ăn_uống', 'nhà_hàng', 'quán_ăn', 'đồ_uống'},
                # Avoid medical/pharmacy-like lines for pure food intent.
                'negative': {'dược_phẩm', 'thuốc', 'y_tế', 'mỹ_phẩm'}
            },
        }

        print(f"BM25 Ranker initialized:")
        print(f"  - Total documents: {self.N}")
        print(f"  - Average document length: {self.avg_doc_length:.2f} tokens")
        print(f"  - k1={k1}, b={b}")

    def _compute_average_doc_length(self) -> float:
        """Compute average document length"""
        if not self.doc_info:
            return 0

        total_length = sum(doc['length'] for doc in self.doc_info.values())
        return total_length / len(self.doc_info)

    def _compute_idf(self, term: str) -> float:
        """
        Compute IDF (Inverse Document Frequency) for a term
        IDF = log((N - n + 0.5) / (n + 0.5))
        where N is total docs, n is docs containing term
        """
        if term in self.idf_cache:
            return self.idf_cache[term]

        if term not in self.inverted_index:
            idf = math.log((self.N + 1) / (1))
        else:
            postings = self.inverted_index[term]
            n = len(postings)  # Number of documents containing term
            idf = math.log((self.N - n + 0.5) / (n + 0.5))

        self.idf_cache[term] = idf
        return idf

    def _get_doc_fields_lower(self, doc_id: int) -> Dict[str, str]:
        """
        Return lowercased field text for a document (lazy-cached).
        Used by boosting logic for more accurate ranking.
        """
        if doc_id in self._doc_text_cache:
            return self._doc_text_cache[doc_id]

        if doc_id not in self.doc_info:
            # Defensive guard for inconsistent posting/doc_info data.
            return {field: '' for field in self.field_boosts.keys()}

        original_doc = self.doc_info[doc_id]['original_doc']
        fields = {
            field: str(original_doc.get(field, '')).lower()
            for field in self.field_boosts.keys()
        }
        self._doc_text_cache[doc_id] = fields
        return fields

    def _term_variants(self, term: str) -> List[str]:
        """
        Build equivalent forms for matching segmented/non-segmented terms.
        Example: "dệt_may" <-> "dệt may".
        """
        variants = {term}
        if '_' in term:
            variants.add(term.replace('_', ' '))
        if ' ' in term:
            variants.add(term.replace(' ', '_'))
        return list(variants)

    def _text_contains_term(self, text: str, term: str) -> bool:
        """Check whether text contains a term in any equivalent representation."""
        for variant in self._term_variants(term):
            if variant and variant in text:
                return True
        return False

    def _doc_contains_intent_primary(self, doc_id: int, terms: List[str]) -> bool:
        """
        Strict intent check on Industry field only.
        User requirement: keyword intent should be matched in
        "Ngành nghề kinh doanh" instead of other fields.
        """
        if not terms:
            return True

        fields = self._get_doc_fields_lower(doc_id)
        industry_text = fields.get('Ngành nghề kinh doanh', '')
        return any(self._text_contains_term(industry_text, term) for term in terms)

    def _doc_passes_intent_column_rules(self, doc_id: int, intent_group: Optional[str]) -> bool:
        """
        Apply column-aware intent rules on Industry field.
        If group has positive terms, doc should match at least one positive term.
        If group has negative terms, doc should not be dominated by those terms.
        """
        if not intent_group:
            return True

        rule = self.intent_column_rules.get(intent_group)
        if not rule:
            return True

        fields = self._get_doc_fields_lower(doc_id)
        industry_text = fields.get('Ngành nghề kinh doanh', '')

        positive = rule.get('positive', set())
        negative = rule.get('negative', set())

        has_positive = any(self._text_contains_term(industry_text, term) for term in positive) if positive else True
        has_negative = any(self._text_contains_term(industry_text, term) for term in negative) if negative else False

        # Strict: must satisfy positive intent and avoid negative intent in Industry column.
        return has_positive and not has_negative

    def _compute_keyword_boost(self, query_terms: List[str], raw_query: str, doc_id: int) -> float:
        """
        Compute additional relevance boost for exact/near-exact keyword matching.

        Why this helps:
        - BM25 is strong but may still rank docs where terms are scattered.
        - This boost prioritizes docs where important fields contain exact keywords/phrases.
        """
        fields = self._get_doc_fields_lower(doc_id)
        boost = 0.0

        # 1) Exact phrase bonus on highly important fields.
        if raw_query:
            if raw_query in fields.get('Tên doanh nghiệp', ''):
                boost += 3.0
            if raw_query in fields.get('Tên giao dịch', ''):
                boost += 2.5
            if raw_query in fields.get('Ngành nghề kinh doanh', ''):
                boost += 1.5

        # 2) Per-term field-aware bonus.
        for term in query_terms:
            for field_name, weight in self.field_boosts.items():
                field_text = fields.get(field_name, '')
                if self._text_contains_term(field_text, term):
                    boost += 0.25 * weight

                # Extra phrase bonus for segmented industry terms (contains "_").
                # Example: "dệt_may", "điện_lực" should have stronger impact.
                if '_' in term and self._text_contains_term(field_text, term):
                    boost += 0.35 * weight

        return boost

    def _compute_bm25_score(self, term: str, doc_id: int, term_freq: int,
                           doc_length: int) -> float:
        """
        Compute BM25 score for a single term in a document
        BM25 = IDF * ((tf * (k1 + 1)) / (tf + k1 * (1 - b + b * (doc_length / avg_doc_length))))
        """
        idf = self._compute_idf(term)

        # Normalize document length
        norm_factor = 1 - self.b + self.b * (doc_length / self.avg_doc_length)

        # Calculate BM25 component
        numerator = term_freq * (self.k1 + 1)
        denominator = term_freq + self.k1 * norm_factor

        score = idf * (numerator / denominator)
        return score

    def _doc_contains_any_term(self, doc_id: int, terms: List[str]) -> bool:
        """
        Check whether a document contains at least one term in important fields.
        Used by strict mode to avoid irrelevant results.
        """
        if not terms:
            return True

        fields = self._get_doc_fields_lower(doc_id)
        combined_text = ' '.join(fields.values())
        # Use variant-aware term matching to support phrase tokens like dệt_may.
        return any(self._text_contains_term(combined_text, term) for term in terms)

    def rank_documents(
        self,
        query_terms: List[str],
        top_k: int = 10,
        raw_query: str = "",
        intent_terms: Optional[List[str]] = None,
        strict_intent: bool = False,
        intent_group: Optional[str] = None
    ) -> List[Tuple[int, float, Any]]:
        """
        Rank documents for given query terms using BM25

        Args:
            query_terms: List of preprocessed query terms
            top_k: Number of top results to return

        Returns:
            List of tuples (doc_id, score, original_document)
        """
        if not query_terms:
            return []

        # Remove duplicate terms while preserving order to avoid duplicated scoring work.
        # Example: query "công ty công ty" should not process same term twice.
        query_terms = list(dict.fromkeys(query_terms))

        # Use cache for repeated queries in console app.
        cache_key = (tuple(query_terms), top_k)
        if cache_key in self.query_cache and not raw_query:
            return self.query_cache[cache_key]

        # Find all documents matching any query term
        candidate_docs = defaultdict(float)
        matched_terms_per_doc = defaultdict(set)

        for query_term in query_terms:
            if query_term not in self.inverted_index:
                continue

            # Get postings for this term
            postings = self.inverted_index[query_term]

            for doc_id, term_freq in postings:
                if doc_id not in self.doc_info:
                    continue

                # Get document length
                doc_length = self.doc_info[doc_id]['length']

                # Compute BM25 score for this term in this document
                score = self._compute_bm25_score(query_term, doc_id, term_freq, doc_length)

                # Add to document score (sum of all term scores)
                candidate_docs[doc_id] += score
                matched_terms_per_doc[doc_id].add(query_term)

        if not candidate_docs:
            return []

        # Optional strict filtering by intent terms.
        # Example: query "electric company" => keep docs that mention electric concepts.
        if strict_intent and intent_terms:
            filtered_docs = {
                doc_id: score
                for doc_id, score in candidate_docs.items()
                if self._doc_contains_intent_primary(doc_id, intent_terms)
            }

            # Fallback safety: if strict filter eliminates everything,
            # keep original candidates to avoid returning empty results too often.
            # BUT: if we already identified a concrete intent group, do NOT fallback,
            # because fallback may re-introduce irrelevant results.
            if filtered_docs:
                candidate_docs = filtered_docs
            elif intent_group:
                return []

        # Additional strict column-based intent disambiguation.
        # This ensures terms from column A don't spill into column B intent.
        if strict_intent and intent_group:
            group_filtered_docs = {
                doc_id: score
                for doc_id, score in candidate_docs.items()
                if self._doc_passes_intent_column_rules(doc_id, intent_group)
            }

            # Fallback safety to avoid zero results for sparse data.
            if group_filtered_docs:
                candidate_docs = group_filtered_docs
            else:
                # With explicit group intent, prefer no result over irrelevant result.
                return []

        # Coverage bonus: documents matching more query terms should rank higher.
        # This improves precision for multi-keyword queries.
        query_term_count = len(query_terms)
        if query_term_count > 1:
            # Only score docs that are still in candidate set (after strict filtering).
            for doc_id in list(candidate_docs.keys()):
                matched_terms = matched_terms_per_doc.get(doc_id, set())
                coverage_ratio = len(matched_terms) / query_term_count
                candidate_docs[doc_id] += coverage_ratio * 1.2

        # Intent boost: documents containing intent terms are likely to match user need better.
        if intent_terms:
            for doc_id in list(candidate_docs.keys()):
                if self._doc_contains_intent_primary(doc_id, intent_terms):
                    # Stronger boost when intent matches business fields.
                    candidate_docs[doc_id] += 1.8
                elif self._doc_contains_any_term(doc_id, intent_terms):
                    # Weaker boost when only secondary fields match.
                    candidate_docs[doc_id] += 0.4

        # Group-level score shaping.
        if intent_group:
            for doc_id in list(candidate_docs.keys()):
                if self._doc_passes_intent_column_rules(doc_id, intent_group):
                    candidate_docs[doc_id] += 2.0

        # For performance: only compute expensive keyword/phrase boosts on top candidates.
        # We first take a wider pool, then rerank with boosting.
        rerank_size = min(len(candidate_docs), max(top_k * 8, top_k))
        pre_top = heapq.nlargest(rerank_size, candidate_docs.items(), key=lambda x: x[1])

        raw_query_lower = raw_query.strip().lower()
        if raw_query_lower:
            boosted_docs = []
            for doc_id, base_score in pre_top:
                boost = self._compute_keyword_boost(query_terms, raw_query_lower, doc_id)
                boosted_docs.append((doc_id, base_score + boost))
        else:
            boosted_docs = pre_top

        # Final top-k selection. heapq is faster than full sort for large candidate lists.
        ranked_docs = heapq.nlargest(top_k, boosted_docs, key=lambda x: x[1])

        # Return top-k with original documents
        results = []
        for doc_id, score in ranked_docs:
            if doc_id not in self.doc_info:
                continue
            original_doc = self.doc_info[doc_id]['original_doc']
            results.append((doc_id, score, original_doc))

        # Keep cache small to avoid unbounded memory growth.
        if len(self.query_cache) > 200:
            self.query_cache.clear()
        if not raw_query:
            self.query_cache[cache_key] = results

        return results

    def batch_rank(self, queries: List[str], preprocessor, top_k: int = 10) -> Dict[str, List[Tuple[int, float, Any]]]:
        """
        Rank documents for multiple queries

        Args:
            queries: List of query strings
            preprocessor: TextPreprocessor instance
            top_k: Number of top results per query

        Returns:
            Dictionary mapping query to ranked results
        """
        results = {}

        for query in queries:
            # Preprocess query
            query_terms = preprocessor.process(query, remove_stops=True)

            # Rank documents
            ranked = self.rank_documents(query_terms, top_k, raw_query=query)
            results[query] = ranked

        return results

    def explain_score(self, query_terms: List[str], doc_id: int) -> Dict[str, Any]:
        """
        Explain BM25 score calculation for a document

        Args:
            query_terms: List of preprocessed query terms
            doc_id: Document ID

        Returns:
            Dictionary with score breakdown
        """
        if doc_id not in self.doc_info:
            return {'error': 'Document not found'}

        explanation = {
            'doc_id': doc_id,
            'doc_length': self.doc_info[doc_id]['length'],
            'avg_doc_length': self.avg_doc_length,
            'terms': {},
            'total_score': 0
        }

        for term in query_terms:
            if term not in self.inverted_index:
                explanation['terms'][term] = {'score': 0, 'reason': 'not in index'}
                continue

            # Find term in document
            postings = self.inverted_index[term]
            term_freq = None

            # Postings are sorted by doc_id, use binary search for faster lookup.
            left, right = 0, len(postings) - 1
            while left <= right:
                mid = (left + right) // 2
                mid_doc_id, mid_freq = postings[mid]
                if mid_doc_id == doc_id:
                    term_freq = mid_freq
                    break
                if mid_doc_id < doc_id:
                    left = mid + 1
                else:
                    right = mid - 1

            if term_freq is None:
                explanation['terms'][term] = {'score': 0, 'reason': 'not in document'}
                continue

            # Calculate components
            idf = self._compute_idf(term)
            doc_length = self.doc_info[doc_id]['length']
            score = self._compute_bm25_score(term, doc_id, term_freq, doc_length)

            explanation['terms'][term] = {
                'score': score,
                'idf': idf,
                'tf': term_freq,
                'doc_length': doc_length,
                'length_norm': 1 - self.b + self.b * (doc_length / self.avg_doc_length)
            }

            explanation['total_score'] += score

        return explanation
