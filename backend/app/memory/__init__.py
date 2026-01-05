"""
Long-term memory layer combining vector store and metadata.
Provides unified interface for document management with semantic search.
"""

from typing import List, Dict, Any, Optional, Tuple
from app.memory.vector_store import VectorStore
from app.memory.metadata_store import MetadataStore
from app.utils.logging import get_logger

logger = get_logger(__name__)


class MemoryManager:
    """
    Unified memory manager combining vector and metadata stores.
    """

    def __init__(
        self,
        vector_store: Optional[VectorStore] = None,
        metadata_store: Optional[MetadataStore] = None,
    ):
        """
        Initialize memory manager.

        Args:
            vector_store: Vector store instance. Creates default if None.
            metadata_store: Metadata store instance. Creates default if None.
        """
        self.vector_store = vector_store or VectorStore()
        self.metadata_store = metadata_store or MetadataStore()

    def add_documents(
        self,
        documents: List[str],
        source: str,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        """
        Add documents with embeddings and metadata.

        Args:
            documents: List of document texts
            source: Source identifier (file path, URL, etc.)
            tags: Optional tags for documents
            metadata: Optional metadata for documents

        Returns:
            List of document IDs

        Raises:
            ValueError: If documents list is empty or other validation fails
        """
        if not documents:
            raise ValueError("Documents list cannot be empty")

        logger.info(f"Adding {len(documents)} documents from source: {source}")

        # Add to vector store
        embedding_results = self.vector_store.add_documents(documents)

        # Add to metadata store
        doc_ids = []
        for (embedding_id, content_hash), doc_text in zip(
            embedding_results, documents
        ):
            try:
                doc_id = self.metadata_store.add_document(
                    source=source,
                    content_hash=content_hash,
                    embedding_id=embedding_id,
                    tags=tags,
                    metadata=metadata,
                )
                doc_ids.append(doc_id)
            except ValueError as e:
                logger.warning(f"Document already exists: {content_hash}")
                # Still add to results list in case of duplicates
                doc_ids.append(content_hash)

        return doc_ids

    def similarity_search(
        self,
        query: str,
        k: int = 5,
        threshold: Optional[float] = None,
        filter_source: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search for similar documents.

        Args:
            query: Query text
            k: Number of results to return
            threshold: Optional distance threshold
            filter_source: Optional source to filter results

        Returns:
            List of documents with metadata and similarity scores

        Raises:
            ValueError: If k is invalid
        """
        if k < 1:
            raise ValueError("k must be at least 1")

        logger.debug(f"Similarity search: {query[:50]}...")

        # Search vector store
        results = self.vector_store.similarity_search(query, k=k * 2, threshold=threshold)

        # Enrich with metadata
        enriched_results = []
        for content_hash, distance in results:
            metadata = self.metadata_store.get_by_content_hash(content_hash)

            if metadata is None:
                logger.warning(f"Metadata not found for hash: {content_hash}")
                continue

            # Apply source filter if specified
            if filter_source and metadata.get("source") != filter_source:
                continue

            enriched_results.append(
                {
                    **metadata,
                    "similarity_score": 1.0 / (1.0 + distance),  # Convert distance to score
                    "distance": distance,
                }
            )

        return enriched_results[:k]

    def delete_by_source(self, source: str) -> Dict[str, Any]:
        """
        Delete all documents from a source.

        Args:
            source: Source identifier

        Returns:
            Dictionary with deletion statistics

        Raises:
            ValueError: If source not found
        """
        logger.info(f"Deleting all documents from source: {source}")

        # Get embedding IDs before deletion
        embedding_ids = self.metadata_store.get_embedding_ids_by_source(source)

        # Delete from metadata store
        count = self.metadata_store.delete_by_source(source)

        # Delete from vector store
        if embedding_ids:
            self.vector_store.delete_by_embedding_ids(embedding_ids)

        return {
            "source": source,
            "documents_deleted": count,
            "embeddings_deleted": len(embedding_ids),
        }

    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """
        Get document by ID.

        Args:
            doc_id: Document ID

        Returns:
            Document metadata or None if not found
        """
        return self.metadata_store.get_document(doc_id)

    def get_memory_stats(self) -> Dict[str, Any]:
        """
        Get memory statistics.

        Returns:
            Dictionary with memory information
        """
        vector_stats = self.vector_store.get_stats()
        return {
            **vector_stats,
            "total_documents": self.metadata_store.get_document_count(),
            "sources": self.metadata_store.list_sources(),
        }

    def init_db(self) -> None:
        """Initialize database tables."""
        self.metadata_store.init_db()


__all__ = ["MemoryManager", "VectorStore", "MetadataStore"]
