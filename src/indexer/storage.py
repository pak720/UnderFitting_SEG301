"""Storage module for inverted index management"""
import os
import json
import pickle
from typing import Dict, List, Tuple, Any
from collections import defaultdict
import struct
from datetime import datetime


class InvertedIndexStorage:
    """Manages storage and retrieval of inverted index"""

    def __init__(self, index_dir: str = "inverted_index"):
        self.index_dir = index_dir
        os.makedirs(index_dir, exist_ok=True)

        self.metadata_file = os.path.join(index_dir, "metadata.json")
        self.postings_file = os.path.join(index_dir, "postings.bin")
        self.terms_file = os.path.join(index_dir, "terms.pkl")
        self.doc_info_file = os.path.join(index_dir, "doc_info.pkl")

        self.terms_data = {}  # term -> offset in postings file
        self.doc_info = {}    # doc_id -> {length, doc_freq}
        self.metadata = {}

    def save_block(self, block_index: int, inverted_index: Dict[str, List[Tuple[int, int]]]):
        """Save a single block of inverted index to disk"""
        block_file = os.path.join(self.index_dir, f"block_{block_index}.pkl")
        with open(block_file, 'wb') as f:
            pickle.dump(inverted_index, f)
        return block_file

    def load_block(self, block_index: int) -> Dict[str, List[Tuple[int, int]]]:
        """Load a block from disk"""
        block_file = os.path.join(self.index_dir, f"block_{block_index}.pkl")
        if not os.path.exists(block_file):
            return {}
        with open(block_file, 'rb') as f:
            return pickle.load(f)

    def merge_blocks(self, num_blocks: int) -> Dict[str, List[Tuple[int, int]]]:
        """Merge all blocks into final inverted index"""
        merged_index = defaultdict(list)

        for block_idx in range(num_blocks):
            block = self.load_block(block_idx)
            for term, postings in block.items():
                merged_index[term].extend(postings)

        # Sort postings for each term
        for term in merged_index:
            merged_index[term].sort(key=lambda x: x[0])

        return dict(merged_index)

    def save_final_index(self, inverted_index: Dict[str, List[Tuple[int, int]]],
                        doc_info: Dict[int, Dict[str, Any]]):
        """Save final merged inverted index"""
        # Save terms and postings using binary format for efficiency
        term_offset = 0
        terms_mapping = {}

        with open(self.postings_file, 'wb') as f:
            for term in sorted(inverted_index.keys()):
                terms_mapping[term] = f.tell()
                postings = inverted_index[term]

                # Store number of postings and then each posting
                f.write(struct.pack('I', len(postings)))
                for doc_id, freq in postings:
                    f.write(struct.pack('II', doc_id, freq))

        # Save terms mapping
        with open(self.terms_file, 'wb') as f:
            pickle.dump(terms_mapping, f)

        # Save doc info
        with open(self.doc_info_file, 'wb') as f:
            pickle.dump(doc_info, f)

        # Save metadata
        self.metadata = {
            'total_terms': len(inverted_index),
            'total_docs': len(doc_info),
            'creation_time': datetime.now().isoformat()
        }

        with open(self.metadata_file, 'w', encoding='utf-8') as f:
            json.dump(self.metadata, f, ensure_ascii=False, indent=2)

    def load_final_index(self) -> Tuple[Dict[str, List[Tuple[int, int]]], Dict[int, Dict[str, Any]]]:
        """Load final inverted index from disk"""
        if not os.path.exists(self.postings_file):
            return {}, {}

        # Load terms mapping
        with open(self.terms_file, 'rb') as f:
            terms_mapping = pickle.load(f)

        # Load inverted index from postings file
        inverted_index = {}
        with open(self.postings_file, 'rb') as f:
            for term, offset in terms_mapping.items():
                f.seek(offset)
                num_postings = struct.unpack('I', f.read(4))[0]
                postings = []
                for _ in range(num_postings):
                    doc_id, freq = struct.unpack('II', f.read(8))
                    postings.append((doc_id, freq))
                inverted_index[term] = postings

        # Load doc info
        with open(self.doc_info_file, 'rb') as f:
            doc_info = pickle.load(f)

        return inverted_index, doc_info

    def cleanup_blocks(self, num_blocks: int):
        """Remove block files after merging"""
        for block_idx in range(num_blocks):
            block_file = os.path.join(self.index_dir, f"block_{block_idx}.pkl")
            if os.path.exists(block_file):
                os.remove(block_file)

    def get_postings(self, term: str) -> List[Tuple[int, int]]:
        """Get postings for a term from loaded index"""
        if not self.terms_data:
            self.load_final_index()
        return self.terms_data.get(term, [])

    def get_doc_info(self) -> Dict[int, Dict[str, Any]]:
        """Get document information"""
        if not self.doc_info:
            _, self.doc_info = self.load_final_index()
        return self.doc_info
