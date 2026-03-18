"""Indexer module for search engine using SPIMI algorithm and Vector Indexing"""

# Import VectorIndexer lazily to avoid heavy TensorFlow/Transformers load when not needed
def __getattr__(name):
    if name == 'VectorIndexer':
        from .vector_indexer import VectorIndexer
        return VectorIndexer
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

__all__ = ['VectorIndexer']
