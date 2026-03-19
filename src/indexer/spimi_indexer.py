"""SPIMI (Single-Pass In-Memory Indexing) implementation"""
import json
import os
import psutil
from collections import defaultdict
from typing import Dict, List, Tuple, Any
import gc

import numpy as np

from .preprocessor import TextPreprocessor, extract_searchable_text
from .storage import InvertedIndexStorage
from .doc_store import DocStore


class SPIMIIndexer:
    """Single-Pass In-Memory Indexing algorithm implementation"""

    def __init__(self, memory_limit_mb: int = 500, index_dir: str = "inverted_index"):
        self.memory_limit_bytes = memory_limit_mb * 1024 * 1024
        self.memory_limit_mb = memory_limit_mb
        self.preprocessor = TextPreprocessor()
        self.storage = InvertedIndexStorage(index_dir)

        self.doc_counter = 0
        self.doc_lengths: Dict[int, int] = {}   # doc_id → token count
        self.doc_offsets: Dict[int, int] = {}   # doc_id → byte offset in JSONL

    def _get_memory_usage(self) -> int:
        process = psutil.Process(os.getpid())
        return process.memory_info().rss

    def index_documents(self, jsonl_path: str) -> Tuple[int, int]:
        """
        Index documents using SPIMI algorithm.

        Reads the JSONL file line by line, recording the byte offset of each
        valid document so we can rebuild a DocStore without keeping full doc
        content in memory.
        """
        print(f"Starting SPIMI indexing from {jsonl_path}")
        print(f"Memory limit: {self.memory_limit_mb} MB")

        inverted_index: Dict[str, List[Tuple[int, int]]] = defaultdict(list)
        block_index = 0
        total_docs_indexed = 0

        batch_docs: List[Tuple[Dict[str, Any], int]] = []  # (doc, byte_offset)

        with open(jsonl_path, 'r', encoding='utf-8') as f:
            while True:
                offset = f.tell()
                line = f.readline()
                if not line:
                    break
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    doc = json.loads(stripped)
                    if not doc:
                        continue
                    batch_docs.append((doc, offset))
                except json.JSONDecodeError:
                    continue

                if len(batch_docs) >= 1000:
                    processed = self._process_batch(batch_docs, inverted_index)
                    total_docs_indexed += processed
                    batch_docs = []

                    if self._get_memory_usage() > self.memory_limit_bytes:
                        print(f"\nBlock {block_index}: Writing to disk "
                              f"({total_docs_indexed} docs, "
                              f"{len(inverted_index)} terms) …")
                        self.storage.save_block(block_index, dict(inverted_index))
                        block_index += 1
                        inverted_index = defaultdict(list)
                        gc.collect()

                if total_docs_indexed % 100_000 == 0 and total_docs_indexed > 0:
                    print(f"Indexed {total_docs_indexed:,} documents …")

        # flush remaining batch
        if batch_docs:
            total_docs_indexed += self._process_batch(batch_docs, inverted_index)

        if inverted_index:
            print(f"\nBlock {block_index}: Writing final block "
                  f"({total_docs_indexed} docs) …")
            self.storage.save_block(block_index, dict(inverted_index))
            block_index += 1

        print(f"\nIndexing complete — {total_docs_indexed:,} docs, "
              f"{block_index} block(s)")
        return total_docs_indexed, block_index

    def _process_batch(self,
                       batch: List[Tuple[Dict[str, Any], int]],
                       inverted_index: Dict[str, List[Tuple[int, int]]]) -> int:
        """Process one batch of (doc, byte_offset) pairs."""
        processed = 0
        for doc, offset in batch:
            text = extract_searchable_text(doc)
            tokens = self.preprocessor.process(text)

            self.doc_lengths[self.doc_counter] = len(tokens)
            self.doc_offsets[self.doc_counter] = offset

            term_freq: Dict[str, int] = defaultdict(int)
            for token in tokens:
                term_freq[token] += 1
            for term, freq in term_freq.items():
                inverted_index[term].append((self.doc_counter, freq))

            self.doc_counter += 1
            processed += 1
        return processed

    def merge_blocks(self) -> Dict[str, List[Tuple[int, int]]]:
        """Merge all SPIMI blocks into a single inverted index."""
        print("\nMerging blocks …")
        merged_index: Dict[str, List[Tuple[int, int]]] = defaultdict(list)

        num_blocks = 0
        while os.path.exists(
                os.path.join(self.storage.index_dir, f"block_{num_blocks}.pkl")):
            num_blocks += 1

        print(f"Found {num_blocks} block(s) to merge")
        for block_idx in range(num_blocks):
            print(f"  Merging block {block_idx} …")
            block = self.storage.load_block(block_idx)
            for term, postings in block.items():
                merged_index[term].extend(postings)

        for term in merged_index:
            merged_index[term].sort(key=lambda x: x[0])

        print(f"Merge complete — {len(merged_index):,} unique terms")
        return dict(merged_index)

    def finalize(self,
                 merged_index: Dict[str, List[Tuple[int, int]]],
                 jsonl_path: str) -> None:
        """
        Save the final index using compact numpy arrays instead of bulky
        pickle dicts, and persist a DocStore for on-demand doc retrieval.
        """
        print("\nFinalizing index …")

        N = len(self.doc_lengths)
        doc_lengths_arr = np.array(
            [self.doc_lengths[i] for i in range(N)], dtype=np.int32)
        doc_offsets_arr = np.array(
            [self.doc_offsets[i] for i in range(N)], dtype=np.int64)

        self.storage.save_final_index(
            merged_index, doc_lengths_arr, doc_offsets_arr, jsonl_path)

        num_blocks = 0
        while os.path.exists(
                os.path.join(self.storage.index_dir, f"block_{num_blocks}.pkl")):
            num_blocks += 1
        self.storage.cleanup_blocks(num_blocks)

        avg_len = float(doc_lengths_arr.mean()) if N else 0.0
        print(f"Index saved — {N:,} docs, avg {avg_len:.1f} tokens/doc")

    def build_index(self, jsonl_path: str) -> None:
        """Complete indexing pipeline: index → merge → finalize."""
        self.index_documents(jsonl_path)
        merged_index = self.merge_blocks()
        self.finalize(merged_index, jsonl_path)
