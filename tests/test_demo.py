"""Test and demo script for search engine"""
import os
import sys
from pathlib import Path
import json
import time

# Force UTF-8 encoding for output
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

sys.path.insert(0, str(Path(__file__).parent))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.indexer.spimi_indexer import SPIMIIndexer
from src.indexer.storage import InvertedIndexStorage
from src.ranking.bm25_ranker import BM25Ranker
from src.indexer.preprocessor import TextPreprocessor


def demo_preprocessing():
    """Demonstrate text preprocessing"""
    print("\n" + "="*80)
    print(" " * 20 + "TEXT PREPROCESSING DEMO")
    print("="*80)

    preprocessor = TextPreprocessor()

    test_texts = [
        "Công ty TNHH Công Nghệ Thông Tin ABC tại Hồ Chí Minh",
        "Doanh nghiệp kinh doanh dịch vụ tư vấn quản lý",
        "Tổ chức, chi nhánh của doanh nghiệp nước ngoài",
    ]

    for text in test_texts:
        print(f"\nOriginal: {text}")
        tokens = preprocessor.tokenize(text)
        print(f"Tokenized: {tokens}")
        cleaned = preprocessor.remove_stopwords(tokens)
        print(f"Cleaned: {cleaned}")


def demo_indexing(jsonl_path: str, sample_size: int = 1000):
    """Demonstrate SPIMI indexing"""
    print("\n" + "="*80)
    print(" " * 20 + "SPIMI INDEXING DEMO")
    print("="*80)

    if not os.path.exists(jsonl_path):
        print(f"\n[ERROR] File not found: {jsonl_path}")
        print("   Please run: python index_builder.py data_sample/sample_cleaned.jsonl")
        return False

    # Get file size
    file_size_mb = os.path.getsize(jsonl_path) / (1024 * 1024)
    print(f"\nFile size: {file_size_mb:.2f} MB")

    # Count documents
    print("Counting documents...")
    doc_count = sum(1 for _ in open(jsonl_path, encoding='utf-8'))
    print(f"Total documents in file: {doc_count}")

    if sample_size and sample_size < doc_count:
        print(f"Using first {sample_size} documents for demo")

    # Create indexer with 100MB limit for demo
    indexer = SPIMIIndexer(memory_limit_mb=100, index_dir="inverted_index_demo")

    print("\nStarting indexing...")
    start_time = time.time()

    # Index only first sample_size documents if specified
    if sample_size and sample_size < doc_count:
        temp_path = "temp_sample.jsonl"
        with open(jsonl_path, 'r', encoding='utf-8') as infile, \
             open(temp_path, 'w', encoding='utf-8') as outfile:
            for i, line in enumerate(infile):
                if i >= sample_size:
                    break
                outfile.write(line)

        total_docs, num_blocks = indexer.index_documents(temp_path)
        os.remove(temp_path)
    else:
        total_docs, num_blocks = indexer.index_documents(jsonl_path)

    # Merge blocks and finalize index
    print("\nMerging and finalizing index...")
    merged_index = indexer.merge_blocks()
    doc_info = indexer.finalize(merged_index)

    end_time = time.time()

    print(f"\nIndexing completed in {end_time - start_time:.2f}s")
    print(f"Documents indexed: {total_docs}")
    print(f"Blocks created: {num_blocks}")

    return True


def demo_bm25(test_queries: list = None, cleanup: bool = False):
    """Demonstrate BM25 ranking"""
    print("\n" + "="*80)
    print(" " * 20 + "BM25 RANKING DEMO")
    print("="*80)

    index_dir = "inverted_index_demo"
    storage = InvertedIndexStorage(index_dir)

    if not os.path.exists(os.path.join(index_dir, "postings.bin")):
        print(f"\n[ERROR] Index not found at {index_dir}")
        print("   Please run indexing demo first")
        return

    print(f"\nLoading index from {index_dir}...")
    inverted_index, doc_info = storage.load_final_index()

    print(f"Index loaded:")
    print(f"  - Documents: {len(doc_info)}")
    print(f"  - Unique terms: {len(inverted_index)}")

    # Create ranker
    ranker = BM25Ranker(inverted_index, doc_info)

    # Default test queries
    if test_queries is None:
        test_queries = [
            "công ty công nghệ",
            "doanh nghiệp hà nội",
            "dịch vụ tư vấn",
        ]

    preprocessor = TextPreprocessor()

    for query in test_queries:
        print(f"\n{'-'*80}")
        print(f"Query: {query}")

        query_terms = preprocessor.process(query, remove_stops=True)
        print(f"Terms: {query_terms}")

        start_time = time.time()
        results = ranker.rank_documents(query_terms, top_k=5)
        end_time = time.time()

        print(f"Time: {(end_time-start_time)*1000:.2f}ms")
        print(f"Results: {len(results)}")

        for rank, (doc_id, score, doc) in enumerate(results, 1):
            company = doc.get('Tên doanh nghiệp', 'N/A')[:50]
            print(f"\n  {rank}. Score: {score:.4f}")
            print(f"     {company}")

    # Optional cleanup
    if cleanup:
        print(f"\n{'-'*80}")
        print("Cleaning up demo index...")
        import shutil
        if os.path.exists(index_dir):
            shutil.rmtree(index_dir)
        print("[OK] Done!")


def main():
    print("\n" + "="*80)
    print(" " * 15 + "SEARCH ENGINE - TEST & DEMO SUITE")
    print("="*80)

    # Get data path
    data_path = Path("data_sample/sample_cleaned.jsonl")

    if not data_path.exists():
        print(f"\n[ERROR] Data file not found: {data_path}")
        print("\nPlease ensure the file exists or download it from the data source.")
        sys.exit(1)

    # Menu
    while True:
        print("\n" + "-"*80)
        print("SELECT TEST:")
        print("  1. Text Preprocessing Demo")
        print("  2. SPIMI Indexing Demo (100 docs)")
        print("  3. BM25 Ranking Demo")
        print("  4. Full Demo (all above)")
        print("  5. Build Full Index (all data)")
        print("  6. Clean up demo index")
        print("  7. Exit")
        print("-"*80)

        choice = input("\nEnter choice (1-7): ").strip()

        if choice == '1':
            demo_preprocessing()

        elif choice == '2':
            demo_indexing(str(data_path), sample_size=100)

        elif choice == '3':
            # First do indexing (if not exists)
            index_demo_dir = Path("inverted_index_demo")
            if not (index_demo_dir / "postings.bin").exists():
                demo_indexing(str(data_path), sample_size=100)
            demo_bm25()

        elif choice == '4':
            demo_preprocessing()
            demo_indexing(str(data_path), sample_size=100)
            demo_bm25(cleanup=True)

        elif choice == '5':
            print("\n" + "="*80)
            print("[WARNING] This will index all data in the file.")
            print("[WARNING] This may take a while and use significant memory.")
            confirm = input("Continue? (y/n): ").strip().lower()

            if confirm == 'y':
                indexer = SPIMIIndexer(memory_limit_mb=500, index_dir="inverted_index")
                total_docs, num_blocks = indexer.index_documents(str(data_path))
                merged_index = indexer.merge_blocks()
                doc_info = indexer.finalize(merged_index)

                print("\n[OK] Full index built successfully!")
                print("   Run: python -m src.indexer")
                print("   To start searching")

        elif choice == '6':
            print("\n" + "="*80)
            print("Cleaning up demo index...")
            import shutil
            index_demo_dir = Path("inverted_index_demo")
            if index_demo_dir.exists():
                shutil.rmtree(index_demo_dir)
                print("[OK] Demo index cleaned up")
            else:
                print("[INFO] No demo index found")

        elif choice == '7':
            print("\n[OK] Goodbye!")
            break

        else:
            print("[ERROR] Invalid choice")


if __name__ == "__main__":
    main()
