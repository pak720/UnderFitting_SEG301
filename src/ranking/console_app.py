"""
Console Search Application
Compatible with:
- TextPreprocessor.build_search_terms()
- BM25Ranker.rank_documents(query_terms, top_k, intent_terms)
"""

import os
import sys
import time
from pathlib import Path
from typing import Tuple

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from indexer.preprocessor import TextPreprocessor
from indexer.storage import InvertedIndexStorage
from ranking.bm25_ranker import BM25Ranker


class SearchEngine:

    def __init__(self, index_dir: str = "inverted_index"):
        self.index_dir = index_dir
        self.storage = InvertedIndexStorage(index_dir)
        self.preprocessor = TextPreprocessor()
        self.ranker = None
        self.inverted_index = None
        self.doc_info = None

    # =====================================================
    # LOAD INDEX
    # =====================================================

    def load_index(self):

        if not os.path.exists(os.path.join(self.index_dir, "postings.bin")):
            print("❌ Index not found! Build index first.")
            return False

        print("Loading index...")

        try:
            self.inverted_index, self.doc_info = self.storage.load_final_index()
            self.ranker = BM25Ranker(self.inverted_index, self.doc_info)

            print("✓ Index loaded successfully!")
            print(f"  - Total documents: {len(self.doc_info)}")
            print(f"  - Total terms: {len(self.inverted_index)}")
            return True

        except Exception as e:
            print("❌ Error loading index:", e)
            return False

    # =====================================================
    # PARSE INPUT
    # =====================================================

    def _parse_search_input(self, user_query: str) -> Tuple[str, int]:

        query = user_query.strip()
        top_k = 10

        if " --top " in query:
            raw, tail = query.rsplit(" --top ", 1)
            try:
                value = int(tail.strip())
                if value > 0:
                    top_k = min(value, 100)
                    query = raw.strip()
            except:
                pass

        return query, top_k

    # =====================================================
    # SEARCH
    # =====================================================

    def search(self, query: str, top_k: int = 10):

        if self.ranker is None:
            print("❌ Index not loaded!")
            return

        print(f"\n🔍 Searching for: {query}")
        print("-" * 80)

        start_time = time.perf_counter()

        # ✅ Correct preprocessing
        query_terms, intent_terms = self.preprocessor.build_search_terms(query)

        if not query_terms:
            print("❌ Query has no meaningful terms.")
            return

        print("Expanded terms:", ", ".join(query_terms))
        print("Intent terms:", ", ".join(intent_terms))
        print("-" * 80)

        # ✅ Correct BM25 call
        results = self.ranker.rank_documents(
            query_terms=query_terms,
            top_k=top_k
        )

        elapsed = (time.perf_counter() - start_time) * 1000

        if not results:
            print(f"No results found in {elapsed:.2f} ms")
            return

        print(f"\nFound {len(results)} results in {elapsed:.2f} ms")

        for rank, (doc_id, score, doc) in enumerate(results, 1):

            print("\n" + "=" * 80)
            print(f"Rank {rank}")
            print(f"Score: {score:.4f}")
            print("-" * 80)

            print("Tên doanh nghiệp:",
                  doc.get("Tên doanh nghiệp", "N/A"))

            print("Mã số thuế:",
                  doc.get("Mã số thuế", "N/A"))

            print("Ngành nghề:",
                  doc.get("Ngành nghề kinh doanh", "N/A"))

            print("Địa chỉ:",
                  doc.get("Địa chỉ", "N/A"))

            print("Tình trạng:",
                  doc.get("Tình trạng hoạt động", "N/A"))

    # =====================================================
    # EXPLAIN
    # =====================================================

    def explain(self, query: str):

        query_terms, intent_terms = self.preprocessor.build_search_terms(query)

        results = self.ranker.rank_documents(
            query_terms=query_terms,
            top_k=1
        )

        if not results:
            print("No result to explain.")
            return

        doc_id, score, doc = results[0]

        print("\n📊 Score Explanation")
        print("Company:", doc.get("Tên doanh nghiệp"))
        print("Total Score:", score)
        print("-" * 60)

        explanation = self.ranker.explain_score(query_terms, doc_id)

        for term, info in explanation["terms"].items():
            print(f"{term}: {info['score']:.4f}")

    # =====================================================
    # CONSOLE LOOP
    # =====================================================

    def run(self):

        print("\n" + "=" * 80)
        print("         🔍 SEARCH ENGINE (SPIMI + BM25)")
        print("=" * 80)
        print("Type 'help' for commands\n")

        self.load_index()

        while True:
            try:
                user_input = input("➤ ").strip()

                if not user_input:
                    continue

                parts = user_input.split(maxsplit=1)
                cmd = parts[0].lower()

                if cmd == "exit":
                    print("👋 Goodbye!")
                    break

                elif cmd == "search":
                    if len(parts) < 2:
                        print("Usage: search <query>")
                    else:
                        query, top_k = self._parse_search_input(parts[1])
                        self.search(query, top_k)

                elif cmd == "explain":
                    if len(parts) < 2:
                        print("Usage: explain <query>")
                    else:
                        self.explain(parts[1])

                elif cmd == "help":
                    print("\nCommands:")
                    print(" search <query>")
                    print(" search <query> --top N")
                    print(" explain <query>")
                    print(" exit")

                else:
                    print("Unknown command")

            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break


def main():
    engine = SearchEngine()
    engine.run()


if __name__ == "__main__":
    main()