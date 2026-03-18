"""Vector Searcher for semantic search."""

import json
from pathlib import Path
from typing import List, Tuple, Dict, Any
import numpy as np
import pickle
import logging

try:
    import faiss
except ImportError:
    faiss = None

from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


class VectorSearcher:
    """Search using semantic embeddings."""

    def __init__(self, index_dir: str = 'vector_index', device: str = 'cpu'):
        """Load vector index and searcher."""
        if faiss is None:
            raise ImportError("FAISS not installed. Run: pip install faiss-cpu or faiss-gpu")

        index_dir = Path(index_dir)

        # Load metadata
        with open(index_dir / 'metadata.json', 'r') as f:
            metadata = json.load(f)

        self.model_name = metadata['model_name']
        self.embedding_dim = metadata['embedding_dim']
        self.num_documents = metadata['num_documents']

        # Load model
        self.model = SentenceTransformer(self.model_name, device=device)

        # Load FAISS index
        self.index = faiss.read_index(str(index_dir / 'vector.index'))

        # Load mappings
        with open(index_dir / 'id_to_doc.pkl', 'rb') as f:
            self.id_to_doc = pickle.load(f)

        with open(index_dir / 'texts.pkl', 'rb') as f:
            self.texts = pickle.load(f)

        logger.info(f"Loaded vector index with {self.num_documents} documents")

    def search(self,
              query: str,
              top_k: int = 10) -> List[Tuple[int, float, Dict[str, Any]]]:
        """
        Search for semantically similar documents.

        Args:
            query: Search query
            top_k: Number of results to return

        Returns:
            List of (doc_id, score, document) tuples
        """
        # Convert query to embedding
        query_embedding = self.model.encode(
            [query],
            convert_to_numpy=True
        )[0].astype(np.float32)

        # Search FAISS index
        distances, indices = self.index.search(
            np.array([query_embedding]),
            k=min(top_k, self.num_documents)
        )

        # Process results
        results = []
        for idx, distance in zip(indices[0], distances[0]):
            if idx == -1:  # Invalid result
                continue

            # Convert L2 distance to similarity score (0-100)
            # FAISS uses L2 distance, smaller = more similar
            similarity_score = max(0, 100 - distance)

            doc = self.id_to_doc[int(idx)]
            results.append((int(idx), similarity_score, doc))

        return results

    def search_with_explanation(self,
                               query: str,
                               top_k: int = 10) -> Dict[str, Any]:
        """
        Search with detailed explanation.

        Returns:
            {
                'query': query,
                'model': model_name,
                'results': [(doc_id, score, doc), ...],
                'execution_time_ms': float
            }
        """
        import time
        start = time.time()

        results = self.search(query, top_k=top_k)

        execution_time = (time.time() - start) * 1000

        return {
            'query': query,
            'model': self.model_name,
            'num_results': len(results),
            'results': results,
            'execution_time_ms': execution_time
        }
