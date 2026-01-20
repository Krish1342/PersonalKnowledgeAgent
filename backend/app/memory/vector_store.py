from typing import List, Dict, Any, Optional
from pathlib import Path
import os

from app.config import settings


class VectorStore:
    """ChromaDB vector store with sentence-transformers embeddings.

    Uses lazy loading to reduce memory usage on startup.
    """

    def __init__(
        self,
        collection_name: str = "knowledge_base",
        persist_directory: Optional[str] = None,
        model_name: Optional[str] = None,
    ) -> None:
        """
        Initialize the vector store.

        Args:
            collection_name: Name of the ChromaDB collection.
            persist_directory: Path to persist the database.
            model_name: Sentence-transformers model name.
        """
        self._persist_directory = persist_directory or settings.VECTOR_DB_PATH
        self._model_name = model_name or settings.MODEL_NAME
        self._collection_name = collection_name

        # Ensure directory exists
        Path(self._persist_directory).mkdir(parents=True, exist_ok=True)

        # Lazy-loaded components (initialized on first use)
        self._embedding_model = None
        self._client = None
        self._collection = None

    def _get_embedding_model(self):
        """Lazy load the embedding model."""
        if self._embedding_model is None:
            # Import here to avoid loading at startup
            from sentence_transformers import SentenceTransformer

            self._embedding_model = SentenceTransformer(self._model_name)
        return self._embedding_model

    def _get_client(self):
        """Lazy load the ChromaDB client."""
        if self._client is None:
            import chromadb
            from chromadb.config import Settings as ChromaSettings

            self._client = chromadb.PersistentClient(
                path=self._persist_directory,
                settings=ChromaSettings(
                    anonymized_telemetry=False,
                    allow_reset=True,
                ),
            )
        return self._client

    def _get_collection(self):
        """Lazy load the ChromaDB collection."""
        if self._collection is None:
            self._collection = self._get_client().get_or_create_collection(
                name=self._collection_name,
                metadata={"hnsw:space": "cosine"},
            )
        return self._collection

    def _generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a list of texts.

        Args:
            texts: List of text strings to embed.

        Returns:
            List of embedding vectors.
        """
        embeddings = self._get_embedding_model().encode(texts, convert_to_numpy=True)
        return embeddings.tolist()

    def add_documents(
        self,
        documents: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None,
    ) -> List[str]:
        """
        Add documents to the vector store.

        Args:
            documents: List of document texts to add.
            metadatas: Optional list of metadata dicts for each document.
            ids: Optional list of unique IDs. Auto-generated if not provided.

        Returns:
            List of document IDs that were added.
        """
        if not documents:
            return []

        # Generate IDs if not provided
        if ids is None:
            existing_count = self._get_collection().count()
            ids = [f"doc_{existing_count + i}" for i in range(len(documents))]

        # Generate embeddings
        embeddings = self._generate_embeddings(documents)

        # Prepare metadatas
        if metadatas is None:
            metadatas = [{} for _ in documents]

        # Add to collection
        self._get_collection().add(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )

        return ids

    def similarity_search(
        self,
        query: str,
        k: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search for similar documents.

        Args:
            query: Query text to search for.
            k: Number of results to return.
            filter_metadata: Optional metadata filter.

        Returns:
            List of results with 'id', 'document', 'metadata', 'distance'.
        """
        # Generate query embedding
        query_embedding = self._generate_embeddings([query])[0]

        # Perform search
        results = self._get_collection().query(
            query_embeddings=[query_embedding],
            n_results=k,
            where=filter_metadata,
            include=["documents", "metadatas", "distances"],
        )

        # Format results
        formatted_results: List[Dict[str, Any]] = []
        if results["ids"] and results["ids"][0]:
            for i, doc_id in enumerate(results["ids"][0]):
                formatted_results.append(
                    {
                        "id": doc_id,
                        "document": (
                            results["documents"][0][i] if results["documents"] else None
                        ),
                        "metadata": (
                            results["metadatas"][0][i] if results["metadatas"] else {}
                        ),
                        "distance": (
                            results["distances"][0][i] if results["distances"] else None
                        ),
                    }
                )

        return formatted_results

    def delete_documents(self, ids: List[str]) -> None:
        """
        Delete documents by their IDs.

        Args:
            ids: List of document IDs to delete.
        """
        if ids:
            self._get_collection().delete(ids=ids)

    def count(self) -> int:
        """
        Get the total number of documents in the store.

        Returns:
            Document count.
        """
        return self._get_collection().count()

    def reset(self) -> None:
        """Delete all documents from the collection."""
        self._get_client().delete_collection(self._collection_name)
        self._collection = self._get_client().get_or_create_collection(
            name=self._collection_name,
            metadata={"hnsw:space": "cosine"},
        )
