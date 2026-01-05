"""
Vector store using FAISS for efficient similarity search.
Manages embeddings using Sentence-Transformers.
"""

import os
import pickle
import hashlib
from typing import List, Tuple, Dict, Any, Optional
from pathlib import Path

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

from app.config import get_settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


class VectorStore:
    """
    Vector store for managing embeddings.
    Uses FAISS for efficient similarity search with persistent storage.
    """

    def __init__(
        self,
        model_name: Optional[str] = None,
        vector_store_path: Optional[str] = None,
    ):
        """
        Initialize vector store.

        Args:
            model_name: Sentence-Transformers model name. If None, uses config.
            vector_store_path: Path to store FAISS index and metadata.
                               If None, uses config.

        Raises:
            ValueError: If vector store path is invalid
        """
        settings = get_settings()
        self.model_name = model_name or settings.EMBEDDING_MODEL
        self.vector_store_path = Path(vector_store_path or settings.VECTOR_STORE_PATH)

        # Create directory if it doesn't exist
        self.vector_store_path.mkdir(parents=True, exist_ok=True)

        # Index paths
        self.index_path = self.vector_store_path / "faiss.index"
        self.id_map_path = self.vector_store_path / "id_map.pkl"

        # Load or initialize embedding model
        logger.info(f"Loading embedding model: {self.model_name}")
        self.model = SentenceTransformer(self.model_name)
        self.embedding_dim = self.model.get_sentence_embedding_dimension()

        # Load or initialize FAISS index
        self.index = self._load_or_create_index()
        self.id_map: Dict[int, str] = self._load_id_map()

        logger.info(
            f"Vector store initialized with {len(self.id_map)} documents, "
            f"embedding dim: {self.embedding_dim}"
        )

    def _load_or_create_index(self) -> faiss.IndexIDMap:
        """
        Load existing FAISS index or create new one.

        Returns:
            FAISS IndexIDMap instance
        """
        if self.index_path.exists():
            try:
                logger.info(f"Loading FAISS index from {self.index_path}")
                index = faiss.read_index(str(self.index_path))
                return index
            except Exception as e:
                logger.error(f"Failed to load index, creating new one: {e}")

        logger.info("Creating new FAISS index")
        base_index = faiss.IndexFlatL2(self.embedding_dim)
        index = faiss.IndexIDMap(base_index)
        return index

    def _load_id_map(self) -> Dict[int, str]:
        """
        Load ID mapping from disk or create empty one.

        Returns:
            Dictionary mapping embedding IDs to document hashes
        """
        if self.id_map_path.exists():
            try:
                logger.info(f"Loading ID map from {self.id_map_path}")
                with open(self.id_map_path, "rb") as f:
                    return pickle.load(f)
            except Exception as e:
                logger.error(f"Failed to load ID map: {e}")

        return {}

    def _save_index(self) -> None:
        """Save FAISS index to disk."""
        try:
            faiss.write_index(self.index, str(self.index_path))
            logger.debug(f"Saved FAISS index to {self.index_path}")
        except Exception as e:
            logger.error(f"Failed to save index: {e}")
            raise

    def _save_id_map(self) -> None:
        """Save ID mapping to disk."""
        try:
            with open(self.id_map_path, "wb") as f:
                pickle.dump(self.id_map, f)
            logger.debug(f"Saved ID map to {self.id_map_path}")
        except Exception as e:
            logger.error(f"Failed to save ID map: {e}")
            raise

    @staticmethod
    def _compute_hash(text: str) -> str:
        """
        Compute SHA-256 hash of text.

        Args:
            text: Text to hash

        Returns:
            Hex hash string
        """
        return hashlib.sha256(text.encode()).hexdigest()

    def add_documents(
        self, documents: List[str], metadatas: Optional[List[Dict[str, Any]]] = None
    ) -> List[Tuple[int, str]]:
        """
        Add documents to vector store.

        Args:
            documents: List of document texts
            metadatas: Optional list of metadata dicts (must match documents length)

        Returns:
            List of (embedding_id, content_hash) tuples

        Raises:
            ValueError: If documents list is empty or metadata length mismatch
        """
        if not documents:
            raise ValueError("Documents list cannot be empty")

        if metadatas and len(metadatas) != len(documents):
            raise ValueError(
                f"Metadata count ({len(metadatas)}) must match documents count "
                f"({len(documents)})"
            )

        logger.info(f"Adding {len(documents)} documents to vector store")

        # Compute hashes and embeddings
        hashes = [self._compute_hash(doc) for doc in documents]
        embeddings = self.model.encode(documents, convert_to_numpy=True)

        # Get next ID
        start_id = len(self.id_map)

        # Add to FAISS index
        embedding_ids = []
        for i, embedding in enumerate(embeddings):
            embedding_id = start_id + i
            self.index.add_with_ids(
                np.array([embedding], dtype=np.float32), np.array([embedding_id])
            )
            self.id_map[embedding_id] = hashes[i]
            embedding_ids.append(embedding_id)

        # Save index and mapping
        self._save_index()
        self._save_id_map()

        results = list(zip(embedding_ids, hashes))
        logger.info(f"Successfully added {len(results)} documents")

        return results

    def similarity_search(
        self, query: str, k: int = 5, threshold: Optional[float] = None
    ) -> List[Tuple[str, float]]:
        """
        Search for similar documents.

        Args:
            query: Query text
            k: Number of results to return
            threshold: Optional similarity threshold (lower is more similar)

        Returns:
            List of (content_hash, distance) tuples, sorted by similarity

        Raises:
            ValueError: If k is invalid or index is empty
        """
        if k < 1:
            raise ValueError("k must be at least 1")

        if len(self.id_map) == 0:
            logger.warning("Vector store is empty, returning empty results")
            return []

        logger.debug(f"Searching for: {query}")

        # Encode query
        query_embedding = self.model.encode([query], convert_to_numpy=True)

        # Search
        distances, indices = self.index.search(
            query_embedding.astype(np.float32), min(k, len(self.id_map))
        )

        # Convert results
        results = []
        for distance, idx in zip(distances[0], indices[0]):
            if idx == -1:  # Invalid index
                continue

            content_hash = self.id_map.get(int(idx))
            if content_hash is None:
                logger.warning(f"Index {idx} not found in ID map")
                continue

            # Apply threshold if specified
            if threshold is not None and distance > threshold:
                continue

            results.append((content_hash, float(distance)))

        logger.debug(f"Found {len(results)} similar documents")
        return results

    def delete_by_embedding_ids(self, embedding_ids: List[int]) -> None:
        """
        Delete documents by embedding IDs.

        Args:
            embedding_ids: List of embedding IDs to delete

        Raises:
            ValueError: If any ID not found
        """
        if not embedding_ids:
            logger.warning("No embedding IDs provided for deletion")
            return

        logger.info(f"Deleting {len(embedding_ids)} embeddings")

        missing_ids = [eid for eid in embedding_ids if eid not in self.id_map]
        if missing_ids:
            logger.warning(f"Embedding IDs not found: {missing_ids}")
            raise ValueError(f"Embedding IDs not found: {missing_ids}")

        # Remove from FAISS index
        ids_array = np.array(embedding_ids, dtype=np.int64)
        self.index.remove_ids(ids_array)

        # Remove from ID map
        for eid in embedding_ids:
            del self.id_map[eid]

        # Save changes
        self._save_index()
        self._save_id_map()

        logger.info(f"Successfully deleted {len(embedding_ids)} embeddings")

    def get_stats(self) -> Dict[str, Any]:
        """
        Get vector store statistics.

        Returns:
            Dictionary with store information
        """
        return {
            "document_count": len(self.id_map),
            "embedding_dim": self.embedding_dim,
            "model": self.model_name,
            "storage_path": str(self.vector_store_path),
            "index_size_mb": (
                self.index_path.stat().st_size / 1024 / 1024
                if self.index_path.exists()
                else 0
            ),
        }

    def clear(self) -> None:
        """
        Clear all data from vector store.
        WARNING: This deletes all embeddings and cannot be undone.
        """
        logger.warning("Clearing vector store")

        # Create new index
        self.index = faiss.IndexIDMap(faiss.IndexFlatL2(self.embedding_dim))
        self.id_map.clear()

        # Save empty state
        self._save_index()
        self._save_id_map()

        logger.info("Vector store cleared")
