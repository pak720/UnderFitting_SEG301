"""Storage module for inverted index — compact numpy-based format."""
import os
import json
import pickle
import struct
from datetime import datetime
from typing import Dict, List, Tuple

import numpy as np


class InvertedIndexStorage:
    """Manages storage and retrieval of the inverted index."""

    def __init__(self, index_dir: str = "inverted_index"):
        self.index_dir = index_dir
        os.makedirs(index_dir, exist_ok=True)

        self.metadata_file    = os.path.join(index_dir, "metadata.json")
        self.postings_file    = os.path.join(index_dir, "postings.bin")
        self.terms_file       = os.path.join(index_dir, "terms.pkl")
        self.doc_lengths_file = os.path.join(index_dir, "doc_lengths.npy")
        self.doc_offsets_file = os.path.join(index_dir, "doc_offsets.npy")

    # ------------------------------------------------------------------
    # Block helpers (used during SPIMI build)
    # ------------------------------------------------------------------

    def save_block(self, block_index: int,
                   inverted_index: Dict[str, List[Tuple[int, int]]]) -> str:
        block_file = os.path.join(self.index_dir, f"block_{block_index}.pkl")
        with open(block_file, 'wb') as f:
            pickle.dump(inverted_index, f)
        return block_file

    def load_block(self, block_index: int) -> Dict[str, List[Tuple[int, int]]]:
        block_file = os.path.join(self.index_dir, f"block_{block_index}.pkl")
        if not os.path.exists(block_file):
            return {}
        with open(block_file, 'rb') as f:
            return pickle.load(f)

    def cleanup_blocks(self, num_blocks: int) -> None:
        for i in range(num_blocks):
            p = os.path.join(self.index_dir, f"block_{i}.pkl")
            if os.path.exists(p):
                os.remove(p)

    # ------------------------------------------------------------------
    # Final index — save
    # ------------------------------------------------------------------

    def save_final_index(self,
                         inverted_index: Dict[str, List[Tuple[int, int]]],
                         doc_lengths: np.ndarray,
                         doc_offsets: np.ndarray,
                         jsonl_path: str) -> None:
        """
        Persist the merged index.

        doc_lengths : int32 array — doc_lengths[doc_id]  = token count
        doc_offsets : int64 array — doc_offsets[doc_id]  = byte offset in JSONL
        jsonl_path  : path to source JSONL (stored in metadata for DocStore)
        """
        # --- postings binary (term → [(doc_id, freq), …]) ---
        terms_mapping: Dict[str, int] = {}
        with open(self.postings_file, 'wb') as f:
            for term in sorted(inverted_index.keys()):
                terms_mapping[term] = f.tell()
                postings = inverted_index[term]
                f.write(struct.pack('I', len(postings)))
                for doc_id, freq in postings:
                    f.write(struct.pack('II', doc_id, freq))

        with open(self.terms_file, 'wb') as f:
            pickle.dump(terms_mapping, f)

        # --- compact numpy arrays (replaces bulky doc_info.pkl) ---
        np.save(self.doc_lengths_file, doc_lengths.astype(np.int32))
        np.save(self.doc_offsets_file, doc_offsets.astype(np.int64))

        # --- metadata ---
        metadata = {
            'total_terms': len(inverted_index),
            'total_docs': int(len(doc_lengths)),
            'jsonl_path': str(jsonl_path),
            'creation_time': datetime.now().isoformat(),
        }
        with open(self.metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)

    # ------------------------------------------------------------------
    # Final index — load
    # ------------------------------------------------------------------

    def load_final_index(
        self,
    ) -> Tuple[Dict[str, List[Tuple[int, int]]], np.ndarray, np.ndarray, str]:
        """
        Returns
        -------
        inverted_index : dict  term → [(doc_id, freq), …]
        doc_lengths    : int32 numpy array
        doc_offsets    : int64 numpy array
        jsonl_path     : str (path to source JSONL)
        """
        if not os.path.exists(self.postings_file):
            return {}, np.array([], np.int32), np.array([], np.int64), ''

        with open(self.terms_file, 'rb') as f:
            terms_mapping = pickle.load(f)

        inverted_index: Dict[str, List[Tuple[int, int]]] = {}
        with open(self.postings_file, 'rb') as f:
            for term, offset in terms_mapping.items():
                f.seek(offset)
                n = struct.unpack('I', f.read(4))[0]
                postings = [struct.unpack('II', f.read(8)) for _ in range(n)]
                inverted_index[term] = postings

        doc_lengths = np.load(self.doc_lengths_file)
        doc_offsets = np.load(self.doc_offsets_file)

        with open(self.metadata_file, encoding='utf-8') as f:
            metadata = json.load(f)
        jsonl_path = metadata.get('jsonl_path', '')

        return inverted_index, doc_lengths, doc_offsets, jsonl_path
