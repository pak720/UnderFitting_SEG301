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

    # Vietnamese provinces and cities for city detection in search2 command
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

    def _extract_city_from_address(self, address: str) -> str:
        """
        Extract city/province name from Vietnamese address.
        Tries multiple strategies to find the city/province.
        
        Example: "Đường Trần Phú, Phường 3, Thành Phố Bạc Liêu, Bạc Liêu" -> "bạc liêu"
        """
        if not address:
            return ""
        
        address_lower = address.lower().strip()
        
        # Strategy 1: Look for "tỉnh <Name>" pattern
        if 'tỉnh ' in address_lower:
            parts = address_lower.split('tỉnh ')
            if len(parts) > 1:
                city_part = parts[-1].split(',')[0].strip()
                return city_part
        
        # Strategy 2: Look for "thành phố <Name>" pattern
        if 'thành phố ' in address_lower:
            parts = address_lower.split('thành phố ')
            if len(parts) > 1:
                city_part = parts[-1].split(',')[0].strip()
                return city_part
        
        # Strategy 3: Check segments from end for known cities (skip "việt nam")
        segments = [s.strip() for s in address_lower.split(',')]
        non_city_words = {'việt nam', 'việt', 'nam'}
        
        for segment in reversed(segments):
            if not segment or segment in non_city_words:
                continue
            
            # Check if segment matches any known Vietnamese city
            for city in self.VIETNAMESE_CITIES:
                if city == segment or city in segment or segment in city:
                    return segment
            
            # Fallback: if segment is long enough, return it
            if len(segment) > 2:
                return segment
        
        return ""

    def _extract_city_from_query(self, query: str) -> tuple:
        """
        Extract city name from search query by checking if any Vietnamese city appears.
        Returns: (industry_query, city_name)
        
        Example: "nhà hàng hà nội" -> ("nhà hàng", "hà nội")
        """
        query_lower = query.lower().strip()
        
        # Check for multi-word cities first (like "hồ chí minh" sorted by length desc)
        for city in sorted(self.VIETNAMESE_CITIES, key=len, reverse=True):
            if query_lower.endswith(city):
                industry = query_lower[:-len(city)].strip()
                return industry, city
        
        # If no city found, return full query as industry and empty city
        return query, ""

    def _filter_by_city(self, results: List, city: str) -> List:
        """
        Filter search results by city/province.
        Matching is done on the city extracted from address field.
        Uses both exact and partial matching for robustness.
        """
        if not city:
            return results
        
        city_lower = city.lower().strip()
        filtered = []
        
        for doc_id, score, doc in results:
            address = doc.get('Địa chỉ', '')
            extracted_city = self._extract_city_from_address(address)
            
            if not extracted_city:
                continue
            
            # Exact match or one is substring of the other
            if city_lower == extracted_city:
                filtered.append((doc_id, score, doc))
            elif city_lower in extracted_city:
                filtered.append((doc_id, score, doc))
            elif extracted_city in city_lower:
                filtered.append((doc_id, score, doc))
        
        return filtered

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

    def search_by_industry_and_city(self, industry_query: str, city_query: str, top_k: int = 10) -> None:
        """
        Search for documents matching both industry and city.
        Uses industry field for industry matching and address field for city matching.
        
        Algorithm:
        1. Search for industry keywords in Industry field
        2. Filter results by city extracted from Address field
        3. Display combined results with city information
        
        Args:
            industry_query: Industry/business type query (ngành nghề)
            city_query: City/province name (thành phố/tỉnh)
            top_k: Number of results to return
        """
        if self.ranker is None:
            print("❌ Index not loaded! Please load or build index first.")
            return

        if not industry_query.strip():
            print("❌ Empty industry query!")
            return

        if not city_query.strip():
            print("❌ Empty city query!")
            return

        print(f"\n🔍 Searching by Industry + City")
        print(f"   Industry: {industry_query}")
        print(f"   City: {city_query}")
        print("-" * 80)

        start_time = time.perf_counter()

        # Build enhanced terms for industry query
        query_terms, intent_terms = self._build_search_terms(industry_query)
        intent_group = self.preprocessor.detect_intent_group(query_terms)

        if not query_terms:
            print("❌ Industry query has no meaningful terms after preprocessing")
            return

        print(f"Industry query terms: {', '.join(query_terms)}")
        if intent_terms:
            print(f"Intent terms (strict): {', '.join(intent_terms)}")
        if intent_group:
            print(f"Intent group: {intent_group}")
        print("-" * 80)

        # First: get results by industry (get more candidates to filter by city)
        results = self.ranker.rank_documents(
            query_terms,
            top_k * 3,  # Get more candidates to filter by city
            raw_query=industry_query,
            intent_terms=intent_terms,
            strict_intent=True,
            intent_group=intent_group
        )

        if not results:
            print(f"No results found matching industry")
            return

        # Second: filter by city
        results_with_city = self._filter_by_city(results, city_query)

        # Trim to top_k results
        results_with_city = results_with_city[:top_k]

        end_time = time.perf_counter()
        search_time = end_time - start_time

        if not results_with_city:
            print(f"No results found in {search_time*1000:.2f}ms matching both industry and city")
            return

        # Display results
        print(f"\nFound {len(results_with_city)} results in {search_time*1000:.2f}ms\n")

        for rank, (doc_id, score, doc) in enumerate(results_with_city, 1):
            address = doc.get('Địa chỉ', 'N/A')
            city = self._extract_city_from_address(address)
            
            print(f"\n📄 Rank {rank}")
            print(f"   Score: {score:.4f}")
            print(f"   Company: {doc.get('Tên doanh nghiệp', 'N/A')[:60]}")
            print(f"   Tax ID: {doc.get('Mã số thuế', 'N/A')}")
            print(f"   Industry: {doc.get('Ngành nghề kinh doanh', 'N/A')}")
            print(f"   City: {city if city else 'N/A'}")
            print(f"   Address: {address[:60]}")
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

OPTION 1: Search by Industry (Ngành nghề)
        search <query>          : Search for documents by industry
        search <query> --top N  : Search and return top N results (max 100)

OPTION 2: Search by Industry + City (Ngành nghề + Thành phố)
        search2 <industry> <city>           : Auto-detect city from query
        search2 <industry> <city> --top N   : Search with top N limit

OTHER COMMANDS:
  explain <query> [n]     : Explain ranking for n-th result (0-indexed)
  exit                    : Exit the application
  help                    : Show this help message

EXAMPLES:
───────────────────────────────────────────────────────────────────────────

OPTION 1 - By Industry (Ngành nghề):
        search công nghệ
        search công ty dệt may
        search thực phẩm --top 20

OPTION 2 - By Industry + City (Auto-detect city):
        search2 nhà hàng hà nội
        search2 dệt may hải phòng
        search2 công ty công nghệ tp hcm --top 10
        search2 thực phẩm thái nguyên

NOTES:
───────────────────────────────────────────────────────────────────────────
  • Stopwords are automatically removed during processing
  • Results are ranked by BM25 + keyword precision boosting
  • English query terms are expanded to related Vietnamese domain terms
  • Strict intent filtering is enabled for better precision
  • search2: City name is automatically detected from end of query
  • search2: Filters results by address field for location accuracy
  • Top 10 results are returned by default
  • Search is case-insensitive and accents are normalized
  • Supports 63 Vietnamese provinces and cities
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

                elif cmd == "search2":
                    # Parse: search2 <industry> <city> [--top N]
                    # Auto-detects city if it's a Vietnamese province/city name
                    remaining = user_input[len("search2"):].strip()
                    
                    if not remaining:
                        print("❌ Usage: search2 <industry> <city> [--top N]")
                        print("   Examples:")
                        print("      search2 nhà hàng hà nội")
                        print("      search2 dệt may hải phòng --top 20")
                        continue
                    
                    # Split on --top to handle optional limit
                    if " --top " in remaining:
                        content, tail = remaining.rsplit(" --top ", 1)
                        try:
                            top_k = min(int(tail.strip()), 100)
                        except ValueError:
                            top_k = 10
                    else:
                        content = remaining
                        top_k = 10
                    
                    # Auto-detect city from content
                    industry_query, city_name = self._extract_city_from_query(content)
                    
                    if not industry_query.strip() or not city_name.strip():
                        print("❌ Usage: search2 <industry> <city> [--top N]")
                        print("   Examples:")
                        print("      search2 nhà hàng hà nội")
                        print("      search2 công ty công nghệ tp hcm")
                        print("      search2 dệt may hải phòng --top 15")
                        print(f"\n   Supported cities: 63 Vietnamese provinces and cities")
                    else:
                        self.search_by_industry_and_city(industry_query, city_name, top_k=top_k)
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
