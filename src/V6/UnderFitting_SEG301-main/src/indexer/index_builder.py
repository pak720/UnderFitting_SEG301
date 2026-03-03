"""Index builder script for building the search index"""
import argparse
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from indexer.spimi_indexer import SPIMIIndexer


def main():
    parser = argparse.ArgumentParser(
        description='Build search index using SPIMI algorithm'
    )
    parser.add_argument(
        'jsonl_file',
        help='Path to JSONL file to index'
    )
    parser.add_argument(
        '--memory',
        type=int,
        default=500,
        help='Memory limit in MB for each block (default: 500)'
    )
    parser.add_argument(
        '--index-dir',
        default='inverted_index',
        help='Directory to store index (default: inverted_index)'
    )

    args = parser.parse_args()

    # Check if file exists
    if not Path(args.jsonl_file).exists():
        print(f"❌ File not found: {args.jsonl_file}")
        sys.exit(1)

    # Create indexer
    indexer = SPIMIIndexer(memory_limit_mb=args.memory, index_dir=args.index_dir)

    # Build index
    try:
        print("\n" + "="*80)
        print(" " * 25 + "🏗️  INDEX BUILDER")
        print("="*80 + "\n")

        merged_index, doc_info = indexer.build_index(args.jsonl_file)

        print("\n" + "="*80)
        print(" " * 20 + "✅ INDEX BUILDING COMPLETE!")
        print("="*80)
        print(f"\nIndex saved to: {args.index_dir}")
        print(f"Ready to search! Run: python -m src.indexer.console_app")
        print()

    except Exception as e:
        print(f"\n❌ Error during indexing: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
