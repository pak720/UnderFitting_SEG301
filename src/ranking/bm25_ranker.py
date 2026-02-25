"""BM25 ranking algorithm implementation"""
import math
from typing import Dict, List, Tuple, Any
from collections import defaultdict
import time


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

    def rank_documents(self, query_terms: List[str], top_k: int = 10) -> List[Tuple[int, float, Any]]:
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

        # Find all documents matching any query term
        candidate_docs = defaultdict(float)

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

        # Sort by score descending
        ranked_docs = sorted(candidate_docs.items(), key=lambda x: x[1], reverse=True)

        # Return top-k with original documents
        results = []
        for doc_id, score in ranked_docs[:top_k]:
            original_doc = self.doc_info[doc_id]['original_doc']
            results.append((doc_id, score, original_doc))

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
            ranked = self.rank_documents(query_terms, top_k)
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

            for doc_id_posting, freq in postings:
                if doc_id_posting == doc_id:
                    term_freq = freq
                    break

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
