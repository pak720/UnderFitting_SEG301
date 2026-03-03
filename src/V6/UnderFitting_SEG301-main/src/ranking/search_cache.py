"""
Persistent search cache for SearchEngine.
Stores search results on disk to speed up repeated queries.
"""

import json
import os
import hashlib
from pathlib import Path


class SearchCache:
    def __init__(self, cache_file="search_cache.json"):
        self.cache_file = cache_file
        self.cache = {}
        self._load()

    def _load(self):
        """Load cache from disk if exists"""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    self.cache = json.load(f)
            except Exception:
                self.cache = {}

    def _save(self):
        """Save cache to disk"""
        with open(self.cache_file, "w", encoding="utf-8") as f:
            json.dump(self.cache, f, ensure_ascii=False)

    def _make_key(self, query, top_k, mode="search"):
        """
        Create unique key for search query.
        mode: search or search2
        """
        raw = f"{mode}:{query}:{top_k}"
        return hashlib.md5(raw.encode()).hexdigest()

    def get(self, query, top_k, mode="search"):
        key = self._make_key(query, top_k, mode)
        return self.cache.get(key)

    def set(self, query, top_k, results, mode="search"):
        key = self._make_key(query, top_k, mode)

        # Make results JSON serializable
        serializable = []
        for doc_id, score, doc in results:
            serializable.append({
                "doc_id": doc_id,
                "score": score,
                "doc": doc
            })

        self.cache[key] = serializable
        self._save()