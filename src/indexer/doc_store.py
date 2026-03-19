"""
DocStore — on-demand document lookup via byte-offset index into a JSONL file.

Instead of loading all documents into memory, we record the byte position of
each document in the original JSONL file.  At retrieval time we seek directly
to that position and read only the documents we actually need (top-k results).

Memory cost: 8 bytes × N docs (int64 offset array)  ≈ 12 MB for 1.5 M docs.
"""

import json
from pathlib import Path
from typing import Dict, List, Any

import numpy as np


class DocStore:
    """Random-access into a JSONL file using pre-built byte offsets."""

    def __init__(self, jsonl_path: str, offsets: np.ndarray) -> None:
        """
        Args:
            jsonl_path: Absolute path to the source JSONL file.
            offsets:    int64 numpy array where offsets[doc_id] = byte offset
                        of that document's line in the JSONL file.
        """
        self.jsonl_path = str(jsonl_path)
        self.offsets = offsets      # shape (N,), dtype int64
        self._fh = None             # lazy file handle

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self, store_dir: str) -> None:
        """Save offset array and metadata to *store_dir*."""
        store_dir = Path(store_dir)
        store_dir.mkdir(exist_ok=True, parents=True)
        np.save(str(store_dir / 'doc_offsets.npy'), self.offsets)
        with open(store_dir / 'doc_store_meta.json', 'w', encoding='utf-8') as f:
            json.dump({'jsonl_path': self.jsonl_path,
                       'num_docs': int(len(self.offsets))}, f, indent=2)

    @staticmethod
    def load(store_dir: str) -> 'DocStore':
        """Load a previously saved DocStore from *store_dir*."""
        store_dir = Path(store_dir)
        with open(store_dir / 'doc_store_meta.json', encoding='utf-8') as f:
            meta = json.load(f)
        offsets = np.load(str(store_dir / 'doc_offsets.npy'))
        return DocStore(meta['jsonl_path'], offsets)

    # ------------------------------------------------------------------
    # Building
    # ------------------------------------------------------------------

    @staticmethod
    def build(jsonl_path: str) -> 'DocStore':
        """
        Scan *jsonl_path* once, recording the byte offset of every valid
        JSON line. Returns a DocStore ready to use (not yet saved to disk).

        The doc_id assigned to each document is its 0-based index among
        *valid* JSON lines, matching the convention used by SPIMIIndexer.
        """
        offsets: List[int] = []
        with open(jsonl_path, 'r', encoding='utf-8') as f:
            while True:
                pos = f.tell()
                line = f.readline()
                if not line:
                    break
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    json.loads(stripped)    # validate JSON
                    offsets.append(pos)
                except json.JSONDecodeError:
                    pass
        return DocStore(jsonl_path, np.array(offsets, dtype=np.int64))

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def _open(self) -> None:
        if self._fh is None or self._fh.closed:
            self._fh = open(self.jsonl_path, 'r', encoding='utf-8')

    def get(self, doc_id: int) -> Dict[str, Any]:
        """Fetch one document by its doc_id (O(1) disk seek)."""
        self._open()
        self._fh.seek(int(self.offsets[doc_id]))
        return json.loads(self._fh.readline())

    def get_many(self, doc_ids: List[int]) -> Dict[int, Dict[str, Any]]:
        """
        Fetch several documents efficiently.
        Reads in ascending offset order to minimise seek distance.
        """
        sorted_ids = sorted(doc_ids, key=lambda d: self.offsets[d])
        self._open()
        result: Dict[int, Dict[str, Any]] = {}
        for doc_id in sorted_ids:
            self._fh.seek(int(self.offsets[doc_id]))
            result[doc_id] = json.loads(self._fh.readline())
        return result

    def __len__(self) -> int:
        return len(self.offsets)

    def __del__(self) -> None:
        if self._fh and not self._fh.closed:
            self._fh.close()
