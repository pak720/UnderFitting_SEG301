"""SPIMI (Single-Pass In-Memory Indexing) implementation"""
import json
import os
import psutil
from collections import defaultdict
from typing import Dict, List, Tuple, Generator, Any
import gc

from .preprocessor import TextPreprocessor, extract_searchable_text
from .storage import InvertedIndexStorage


class SPIMIIndexer:
    """Single-Pass In-Memory Indexing algorithm implementation"""

    def __init__(self, memory_limit_mb: int = 500, index_dir: str = "inverted_index"):
        """
        Initialize SPIMI indexer

        Args:
            memory_limit_mb: Maximum memory to use before writing block to disk (in MB)
            index_dir: Directory to store index files
        """
        self.memory_limit_bytes = memory_limit_mb * 1024 * 1024
        self.memory_limit_mb = memory_limit_mb
        self.preprocessor = TextPreprocessor()
        self.storage = InvertedIndexStorage(index_dir)

        # Track document information
        self.doc_counter = 0
        self.doc_lengths = {}  # doc_id -> token count
        self.doc_contents = {}  # doc_id -> original doc for retrieval

    def _get_memory_usage(self) -> int:
        """Get current memory usage in bytes"""
        process = psutil.Process(os.getpid())
        return process.memory_info().rss

    def _estimate_memory(self, inverted_index: Dict[str, List[Tuple[int, int]]]) -> int:
        """Estimate memory usage of inverted index"""
        size = 0
        for term, postings in inverted_index.items():
            size += len(term) * 2  # term string
            size += len(postings) * 16  # each posting is (doc_id, freq)
        return size

    def index_documents(self, jsonl_path: str) -> Tuple[int, int]:
        """
        Index documents using SPIMI algorithm

        Args:
            jsonl_path: Path to JSONL file

        Returns:
            Tuple of (total_documents, total_blocks)
        """
        print(f"Starting SPIMI indexing from {jsonl_path}")
        print(f"Memory limit: {self.memory_limit_mb} MB")

        inverted_index = defaultdict(list)
        block_index = 0
        total_docs_indexed = 0

        # Read documents in batches
        batch_docs = []

        with open(jsonl_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                try:
                    doc = json.loads(line.strip())
                    if not doc:
                        continue

                    batch_docs.append(doc)

                    # Process batch when we reach a reasonable size
                    if len(batch_docs) >= 1000 or total_docs_indexed % 10000 == 0:
                        processed = self._process_batch(batch_docs, inverted_index)
                        total_docs_indexed += processed
                        batch_docs = []

                        # Check memory usage
                        current_memory = self._get_memory_usage()

                        if current_memory > self.memory_limit_bytes:
                            print(f"\nBlock {block_index}: Writing to disk...")
                            print(f"  - Documents indexed: {total_docs_indexed}")
                            print(f"  - Terms in index: {len(inverted_index)}")
                            print(f"  - Memory used: {current_memory / 1024 / 1024:.1f} MB")

                            # Save block to disk
                            self.storage.save_block(block_index, dict(inverted_index))
                            block_index += 1

                            # Reset for next block
                            inverted_index = defaultdict(list)
                            gc.collect()

                    # Progress indicator
                    if total_docs_indexed % 100000 == 0 and total_docs_indexed > 0:
                        print(f"Indexed {total_docs_indexed} documents...")

                except json.JSONDecodeError:
                    continue

        # Process remaining documents
        if batch_docs:
            processed = self._process_batch(batch_docs, inverted_index)
            total_docs_indexed += processed

        # Save final block if not empty
        if inverted_index:
            print(f"\nBlock {block_index}: Writing final block to disk...")
            print(f"  - Documents indexed: {total_docs_indexed}")
            print(f"  - Terms in index: {len(inverted_index)}")

            self.storage.save_block(block_index, dict(inverted_index))
            block_index += 1

        print(f"\nIndexing complete!")
        print(f"Total documents: {total_docs_indexed}")
        print(f"Total blocks: {block_index}")

        return total_docs_indexed, block_index

    def _process_batch(self, docs: List[Dict[str, Any]],
                       inverted_index: Dict[str, List[Tuple[int, int]]]) -> int:
        """Process a batch of documents and update inverted index"""
        processed = 0

        for doc in docs:
            # Extract searchable text
            text = extract_searchable_text(doc)

            # Preprocess
            tokens = self.preprocessor.process(text)

            # Store document info
            self.doc_lengths[self.doc_counter] = len(tokens)
            self.doc_contents[self.doc_counter] = doc

            # Count term frequencies
            term_freq = defaultdict(int)
            for token in tokens:
                term_freq[token] += 1

            # Add to inverted index
            for term, freq in term_freq.items():
                inverted_index[term].append((self.doc_counter, freq))

            self.doc_counter += 1
            processed += 1

        return processed

    def merge_blocks(self) -> Dict[str, List[Tuple[int, int]]]:
        """Merge all blocks into final inverted index"""
        print("\nMerging blocks...")

        # Load all blocks and merge
        merged_index = defaultdict(list)

        # Count blocks
        num_blocks = 0
        while os.path.exists(os.path.join(self.storage.index_dir, f"block_{num_blocks}.pkl")):
            num_blocks += 1

        print(f"Found {num_blocks} blocks to merge")

        for block_idx in range(num_blocks):
            print(f"Merging block {block_idx}...")
            block = self.storage.load_block(block_idx)

            for term, postings in block.items():
                merged_index[term].extend(postings)

        # Sort postings for each term by doc_id for faster retrieval
        for term in merged_index:
            merged_index[term].sort(key=lambda x: x[0])

        print(f"Merge complete: {len(merged_index)} unique terms")

        return dict(merged_index)

    def finalize(self, merged_index: Dict[str, List[Tuple[int, int]]]) -> Dict[int, Dict[str, Any]]:
        """Finalize indexing and save to persistent storage"""
        print("\nFinalizing index...")

        # Prepare document information
        doc_info = {}
        total_length = 0

        for doc_id, length in self.doc_lengths.items():
            doc_info[doc_id] = {
                'length': length,
                'original_doc': self.doc_contents[doc_id]
            }
            total_length += length

        # Calculate average document length
        avg_doc_length = total_length / len(doc_info) if doc_info else 0

        # Add metadata
        for doc_id in doc_info:
            doc_info[doc_id]['avg_length'] = avg_doc_length

        # Save final index
        self.storage.save_final_index(merged_index, doc_info)

        # Cleanup block files
        num_blocks = 0
        while os.path.exists(os.path.join(self.storage.index_dir, f"block_{num_blocks}.pkl")):
            num_blocks += 1

        self.storage.cleanup_blocks(num_blocks)

        print(f"Index saved successfully!")
        print(f"Total documents: {len(doc_info)}")
        print(f"Average document length: {avg_doc_length:.1f} tokens")

        return doc_info

    def build_index(self, jsonl_path: str) -> Tuple[Dict[str, List[Tuple[int, int]]], Dict[int, Dict[str, Any]]]:
        """Complete indexing pipeline"""
        # Step 1: Index documents with SPIMI
        total_docs, num_blocks = self.index_documents(jsonl_path)

        # Step 2: Merge blocks
        merged_index = self.merge_blocks()

        # Step 3: Finalize
        doc_info = self.finalize(merged_index)

        return merged_index, doc_info
