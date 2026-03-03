"""Console application for search engine"""
import os
import sys
import time
from pathlib import Path
from typing import Tuple, List

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from indexer.preprocessor import TextPreprocessor
from indexer.storage import InvertedIndexStorage
from ranking.bm25_ranker import BM25Ranker
from search_cache import SearchCache

class SearchEngine:
    """Main search engine console application"""

    # Vietnamese provinces and cities for city detection
    VIETNAMESE_CITIES = {
        'hà nội', 'hồ chí minh', 'đà nẵng', 'hải phòng', 'cần thơ',
        'thái nguyên', 'tuyên quang', 'sơn la', 'bắc ninh', 'phú thọ',
        'yên bái', 'hòa bình', 'lạng sơn', 'cao bằng', 'quảng ninh',
        'thanh hóa', 'nghệ an', 'hà tĩnh', 'quảng bình', 'quảng trị',
        'thừa thiên huế', 'quảng nam', 'quảng ngãi', 'bình định', 'phú yên',
        'khánh hòa', 'ninh thuận', 'bình thuận',
        'long an', 'đồng tháp', 'an giang', 'kiên giang', 'cà mau',
        'bến tre', 'trà vinh', 'vĩnh long', 'tiền giang',
        'bình dương', 'bình phước', 'đồng nai', 'tây ninh',
        'lâm đồng', 'đắk lắk', 'đắk nông',
        'điện biên', 'lai châu', 'hà giang',
    }

    def __init__(self, index_dir: str = "inverted_index"):
        self.index_dir = index_dir
        self.storage = InvertedIndexStorage(index_dir)
        self.preprocessor = TextPreprocessor()
        self.ranker = None
        self.inverted_index = None
        self.doc_info = None
        self._query_terms_cache = {}
        self.cache = SearchCache()

    def _parse_search_input(self, user_query: str) -> Tuple[str, int]:
        """Parse input for optional top-k."""
        query = user_query.strip()
        top_k = 10
        if " --top " in query:
            raw, tail = query.rsplit(" --top ", 1)
            try:
                value = int(tail.strip())
                if value > 0:
                    top_k = min(value, 100)
                    query = raw.strip()
            except ValueError:
                pass
        return query, top_k

    def _build_search_terms(self, query: str) -> Tuple[List[str], List[str]]:
        cache_key = f"enhanced::{query.strip().lower()}"
        if cache_key in self._query_terms_cache:
            return self._query_terms_cache[cache_key]
        expanded_terms, intent_terms = self.preprocessor.build_search_terms(query)
        if len(self._query_terms_cache) > 300:
            self._query_terms_cache.clear()
        self._query_terms_cache[cache_key] = (expanded_terms, intent_terms)
        return expanded_terms, intent_terms

    def _extract_city_from_query(self, query: str) -> tuple:
        query_lower = query.lower().strip()
        for city in sorted(self.VIETNAMESE_CITIES, key=len, reverse=True):
            if query_lower.endswith(city):
                industry = query_lower[:-len(city)].strip()
                return industry, city
        return query, ""

    def _filter_by_city(self, results: List, city: str) -> List:
        if not city: return results
        city_lower = city.lower().strip()
        filtered = []
        for doc_id, score, doc in results:
            addr = doc.get('Địa chỉ', '').lower()
            if city_lower in addr:
                filtered.append((doc_id, score, doc))
        return filtered

    def load_index(self) -> bool:
        if not os.path.exists(os.path.join(self.index_dir, "postings.bin")):
            print("❌ Index not found!")
            return False
        try:
            self.inverted_index, self.doc_info = self.storage.load_final_index()
            self.ranker = BM25Ranker(self.inverted_index, self.doc_info)
            print(f"✓ Index loaded: {len(self.doc_info)} docs")
            return True
        except Exception as e:
            print(f"❌ Load error: {e}")
            return False

    def _print_result_format(self, rank, score, doc):
        """Standardized full output format."""
        print(f"Rank {rank}")
        print(f"Score: {score:.4f}")
        print(f"Company: {doc.get('Tên doanh nghiệp', 'N/A')}")
        print(f"Tax ID: {doc.get('Mã số thuế', 'N/A')}")
        print(f"Industry: {doc.get('Ngành nghề kinh doanh', 'N/A')}")
        print(f"Address: {doc.get('Địa chỉ', 'N/A')}")
        print(f"Status: {doc.get('Tình trạng hoạt động', 'N/A')}")
        print("-" * 40)

    def search(self, query: str, top_k: int = 10) -> None:
        if self.ranker is None: return
        
        start_time = time.perf_counter()
        
        # Try cache first
        cached = self.cache.get(query, top_k, mode="search")
        if cached:
            results = [(item["doc_id"], item["score"], item["doc"]) for item in cached]
            speed_label = "⚡ Cache hit"
        else:
            query_terms, intent_terms = self._build_search_terms(query)
            intent_group = self.preprocessor.detect_intent_group(query_terms)
            results = self.ranker.rank_documents(
                query_terms, top_k, raw_query=query,
                intent_terms=intent_terms, strict_intent=True, intent_group=intent_group
            )
            self.cache.set(query, top_k, results, mode="search")
            speed_label = "⏳ Retrieval"

        end_time = time.perf_counter()
        duration = (end_time - start_time) * 1000

        if not results:
            print(f"No results found ({duration:.2f}ms).")
            return

        print(f"\nFound {len(results)} results in {duration:.2f}ms ({speed_label})\n")
        for rank, (doc_id, score, doc) in enumerate(results, 1):
            self._print_result_format(rank, score, doc)

    def search_by_industry_and_city(self, industry_query: str, city_query: str, top_k: int = 10) -> None:
        if self.ranker is None: return
        
        start_time = time.perf_counter()
        cache_key = f"{industry_query}_{city_query}"
        
        cached = self.cache.get(cache_key, top_k, mode="search2")
        if cached:
            results = [(item["doc_id"], item["score"], item["doc"]) for item in cached]
            speed_label = "⚡ Cache hit"
        else:
            query_terms, intent_terms = self._build_search_terms(industry_query)
            intent_group = self.preprocessor.detect_intent_group(query_terms)
            raw_results = self.ranker.rank_documents(
                query_terms, top_k * 5, raw_query=industry_query,
                intent_terms=intent_terms, strict_intent=True, intent_group=intent_group
            )
            results = self._filter_by_city(raw_results, city_query)[:top_k]
            self.cache.set(cache_key, top_k, results, mode="search2")
            speed_label = "⏳ Retrieval"

        end_time = time.perf_counter()
        duration = (end_time - start_time) * 1000

        if not results:
            print(f"No results found ({duration:.2f}ms).")
            return

        print(f"\nFound {len(results)} results in {duration:.2f}ms ({speed_label})\n")
        for rank, (doc_id, score, doc) in enumerate(results, 1):
            self._print_result_format(rank, score, doc)

    def run(self) -> None:
        print("\n🔍 SEARCH ENGINE CONSOLE")
        self.load_index()
        while True:
            try:
                user_input = input("➤ ").strip()
                if not user_input: continue
                parts = user_input.split(maxsplit=1)
                cmd = parts[0].lower()

                if cmd == "exit": break
                elif cmd == "search":
                    if len(parts) < 2: continue
                    query, top_k = self._parse_search_input(parts[1])
                    self.search(query, top_k=top_k)
                elif cmd == "search2":
                    if len(parts) < 2: continue
                    industry, city = self._extract_city_from_query(parts[1])
                    if not city:
                        print("❌ City not detected. Use: search2 <industry> <city>")
                    else:
                        self.search_by_industry_and_city(industry, city)
            except KeyboardInterrupt: break

if __name__ == "__main__":
    SearchEngine().run()