"""Console application for search engine"""
import os
import sys
import time
import json
from pathlib import Path
from typing import Tuple, List

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from indexer.preprocessor import TextPreprocessor
from indexer.storage import InvertedIndexStorage
from ranking.bm25_ranker import BM25Ranker


class SearchEngine:
    """Main search engine console application"""

    def __init__(self, index_dir: str = "inverted_index"):
        self.index_dir = index_dir
        self.storage = InvertedIndexStorage(index_dir)
        self.preprocessor = TextPreprocessor()
        self.ranker = None
        self.inverted_index = None
        self.doc_info = None
        # Cache query preprocessing results to reduce repeated tokenization cost.
        self._query_terms_cache = {}

    def _parse_search_input(self, user_query: str) -> Tuple[str, int]:
        """
        Parse input for optional top-k.
        Syntax supported:
          - search công nghệ
          - search công nghệ --top 20
        """
        query = user_query.strip()
        top_k = 10

        if " --top " in query:
            raw, tail = query.rsplit(" --top ", 1)
            try:
                value = int(tail.strip())
                if value > 0:
                    top_k = min(value, 100)  # hard limit for safe console output
                    query = raw.strip()
            except ValueError:
                # Keep defaults if parse fails.
                pass

        return query, top_k

    def _get_query_terms(self, query: str):
        """Get query terms with small cache for repeated console searches."""
        cache_key = query.strip().lower()
        if cache_key in self._query_terms_cache:
            return self._query_terms_cache[cache_key]

        terms = self.preprocessor.process(query, remove_stops=True)
        if len(self._query_terms_cache) > 300:
            self._query_terms_cache.clear()
        self._query_terms_cache[cache_key] = terms
        return terms

    def _build_search_terms(self, query: str) -> Tuple[List[str], List[str]]:
        """
        Build (expanded_terms, intent_terms) from query.

        - expanded_terms: used to retrieve more relevant candidates.
        - intent_terms: used to enforce/boost precision (strict mode in ranker).
        """
        cache_key = f"enhanced::{query.strip().lower()}"
        if cache_key in self._query_terms_cache:
            return self._query_terms_cache[cache_key]

        expanded_terms, intent_terms = self.preprocessor.build_search_terms(query)
        if len(self._query_terms_cache) > 300:
            self._query_terms_cache.clear()
        self._query_terms_cache[cache_key] = (expanded_terms, intent_terms)
        return expanded_terms, intent_terms

    def load_index(self) -> bool:
        """Load existing index from disk"""
        if not os.path.exists(os.path.join(self.index_dir, "postings.bin")):
            print("❌ Index not found!")
            print(f"   Run 'build' command first to create index from JSONL file")
            return False

        print("Loading index...")
        try:
            self.inverted_index, self.doc_info = self.storage.load_final_index()
            self.ranker = BM25Ranker(self.inverted_index, self.doc_info)
            print(f"✓ Index loaded successfully!")
            print(f"  - Total documents: {len(self.doc_info)}")
            print(f"  - Total terms: {len(self.inverted_index)}")
            return True
        except Exception as e:
            print(f"❌ Error loading index: {e}")
            return False

    def search(self, query: str, top_k: int = 10) -> None:
        """Search for documents matching the query"""
        if self.ranker is None:
            print("❌ Index not loaded! Please load or build index first.")
            return

        if not query.strip():
            print("❌ Empty query!")
            return

        print(f"\n🔍 Searching for: {query}")
        print("-" * 80)

        # perf_counter gives better precision for short operations.
        start_time = time.perf_counter()

        # Build enhanced terms for better precision on multilingual/domain queries.
        query_terms, intent_terms = self._build_search_terms(query)
        intent_group = self.preprocessor.detect_intent_group(query_terms)

        if not query_terms:
            print("❌ Query has no meaningful terms after preprocessing")
            return

        print(f"Query terms: {', '.join(query_terms)}")
        if intent_terms:
            print(f"Intent terms (strict): {', '.join(intent_terms)}")
        if intent_group:
            print(f"Intent group: {intent_group}")
        print("-" * 80)

        # Rank documents
        # Pass raw query to enable exact phrase/keyword boosting in ranker.
        results = self.ranker.rank_documents(
            query_terms,
            top_k,
            raw_query=query,
            intent_terms=intent_terms,
            strict_intent=True,
            intent_group=intent_group
        )

        end_time = time.perf_counter()
        search_time = end_time - start_time

        if not results:
            print(f"No results found in {search_time*1000:.2f}ms")
            return

        # Display results
        print(f"\nFound {len(results)} results in {search_time*1000:.2f}ms\n")

        for rank, (doc_id, score, doc) in enumerate(results, 1):
            print(f"\n📄 Rank {rank}")
            print(f"   Score: {score:.4f}")
            print(f"   Company: {doc.get('Tên doanh nghiệp', 'N/A')[:60]}")
            print(f"   Tax ID: {doc.get('Mã số thuế', 'N/A')}")
            print(f"   Industry: {doc.get('Ngành nghề kinh doanh', 'N/A')}")
            print(f"   Address: {doc.get('Địa chỉ', 'N/A')[:60]}")
            print(f"   Status: {doc.get('Tình trạng hoạt động', 'N/A')}")

    def explain_query(self, query: str, result_index: int = 0) -> None:
        """Explain BM25 scores for a query"""
        if self.ranker is None:
            print("❌ Index not loaded!")
            return

        if not query.strip():
            print("❌ Empty query!")
            return

        # Get results
        query_terms, intent_terms = self._build_search_terms(query)
        intent_group = self.preprocessor.detect_intent_group(query_terms)
        if not query_terms:
            print("❌ Query has no meaningful terms")
            return

        results = self.ranker.rank_documents(
            query_terms,
            10,
            raw_query=query,
            intent_terms=intent_terms,
            strict_intent=True,
            intent_group=intent_group
        )

        if result_index >= len(results):
            print(f"❌ Result index out of range (0-{len(results)-1})")
            return

        doc_id, score, doc = results[result_index]

        print(f"\n📊 Score Explanation for Result #{result_index + 1}")
        print(f"   Company: {doc.get('Tên doanh nghiệp', 'N/A')}")
        print(f"   Total Score: {score:.4f}")
        print("-" * 80)

        explanation = self.ranker.explain_score(query_terms, doc_id)

        print(f"Document Length: {explanation['doc_length']} tokens")
        print(f"Average Document Length: {explanation['avg_doc_length']:.2f} tokens")
        print(f"\nTerm Contributions:")

        for term, info in explanation['terms'].items():
            if info['score'] > 0:
                print(f"  {term}:")
                print(f"    - Score: {info['score']:.4f}")
                print(f"    - IDF: {info['idf']:.4f}")
                print(f"    - TF: {info['tf']}")
                print(f"    - Length Norm: {info['length_norm']:.4f}")

    def display_help(self) -> None:
        """Display help information"""
        help_text = """
╔════════════════════════════════════════════════════════════════════════════╗
║                    SEARCH ENGINE CONSOLE APPLICATION                      ║
║                      (SPIMI Indexing + BM25 Ranking)                      ║
╚════════════════════════════════════════════════════════════════════════════╝

AVAILABLE COMMANDS:
───────────────────────────────────────────────────────────────────────────

        search <query>          : Search for documents. Example: search công ty TP.HCM
        search <query> --top N  : Search and return top N results (max 100)
  explain <query> [n]     : Explain ranking for n-th result (0-indexed)
  exit                    : Exit the application
  help                    : Show this help message

EXAMPLES:
───────────────────────────────────────────────────────────────────────────

        search doanh nghiệp công nghệ
        search electric company
    search doanh nghiệp công nghệ --top 20
  search địa chỉ hà nội
  explain doanh nghiệp công nghệ 0
  explain doanh nghiệp công nghệ 5

NOTES:
───────────────────────────────────────────────────────────────────────────
  • Stopwords are automatically removed during processing
        • Results are ranked by BM25 + keyword precision boosting
    • English query terms are expanded to related Vietnamese domain terms
    • Strict intent filtering is enabled for better precision
  • Top 10 results are returned by default
  • Search is case-insensitive and accents are normalized
"""
        print(help_text)

    def run(self) -> None:
        """Run interactive console"""
        print("\n" + "="*80)
        print(" " * 20 + "🔍 SEARCH ENGINE (SPIMI + BM25)")
        print("="*80)
        print("\nType 'help' for available commands\n")

        # Try to load existing index
        if not os.path.exists(os.path.join(self.index_dir, "postings.bin")):
            print("⚠️  No index found. Please build index first using:")
            print("   python index_builder.py <path_to_jsonl_file>\n")
        else:
            self.load_index()
            print()

        while True:
            try:
                user_input = input("➤ ").strip()

                if not user_input:
                    continue

                parts = user_input.split(maxsplit=1)
                cmd = parts[0].lower()

                if cmd == "exit":
                    print("\n👋 Goodbye!")
                    break

                elif cmd == "help":
                    self.display_help()

                elif cmd == "search":
                    if len(parts) < 2:
                        print("❌ Usage: search <query>")
                    else:
                        query, top_k = self._parse_search_input(parts[1])
                        if not query:
                            print("❌ Usage: search <query> [--top N]")
                        else:
                            self.search(query, top_k=top_k)

                elif cmd == "explain":
                    if len(parts) < 2:
                        print("❌ Usage: explain <query> [result_index]")
                    else:
                        query = parts[1]
                        result_idx = 0

                        # Check for optional result index
                        remaining = user_input[len("explain"):].strip()
                        tokens = remaining.split()
                        if len(tokens) > 1:
                            try:
                                result_idx = int(tokens[-1])
                            except ValueError:
                                pass

                        self.explain_query(query, result_idx)

                else:
                    print(f"❌ Unknown command: {cmd}")
                    print("   Type 'help' for available commands")

            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")


def main():
    engine = SearchEngine(index_dir="inverted_index")
    engine.run()


if __name__ == "__main__":
    main()
