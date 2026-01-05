"""
Long-term memory layer combining vector store and metadata.
Provides unified interface for document management with semantic search.
Integrates intelligent chunking and content tagging.
"""

from typing import List, Dict, Any, Optional, Tuple
from app.memory.vector_store import VectorStore
from app.memory.metadata_store import MetadataStore
from app.utils.chunking import SemanticChunker, Chunk
from app.utils.tagging import ContentTagger, ContentMetadata
from app.utils.logging import get_logger

logger = get_logger(__name__)


class MemoryManager:
    """
    Unified memory manager combining vector, metadata, chunking, and tagging.
    """

    def __init__(
        self,
        vector_store: Optional[VectorStore] = None,
        metadata_store: Optional[MetadataStore] = None,
        chunker: Optional[SemanticChunker] = None,
        tagger: Optional[ContentTagger] = None,
    ):
        """
        Initialize memory manager.

        Args:
            vector_store: Vector store instance. Creates default if None.
            metadata_store: Metadata store instance. Creates default if None.
            chunker: Text chunker instance. Creates default if None.
            tagger: Content tagger instance. Creates default if None.
        """
        self.vector_store = vector_store or VectorStore()
        self.metadata_store = metadata_store or MetadataStore()
        self.chunker = chunker or SemanticChunker()
        self.tagger = tagger or ContentTagger()

    def process_documents(
        self,
        documents: List[str],
        source: str,
        auto_chunk: bool = True,
        auto_tag: bool = True,
    ) -> Dict[str, Any]:
        """
        Process raw documents through chunking and tagging pipeline.

        Args:
            documents: Raw document texts
            source: Source identifier
            auto_chunk: Whether to chunk documents
            auto_tag: Whether to auto-tag chunks

        Returns:
            Dictionary with processing results

        Raises:
            ValueError: If documents list is empty
        """
        if not documents:
            raise ValueError("Documents list cannot be empty")

        logger.info(
            f"Processing {len(documents)} documents from {source} "
            f"(chunk={auto_chunk}, tag={auto_tag})"
        )

        all_chunks: List[Tuple[Chunk, Optional[ContentMetadata]]] = []

        # Chunk documents
        for i, doc in enumerate(documents):
            doc_source = f"{source}[doc_{i}]"
            chunks = self.chunker.chunk(doc, source=doc_source)
            logger.debug(f"Created {len(chunks)} chunks from document {i}")

            # Tag chunks if enabled
            for chunk in chunks:
                metadata = None
                if auto_tag:
                    metadata = self.tagger.tag_content(chunk.text)
                all_chunks.append((chunk, metadata))

        logger.info(f"Processing complete: {len(all_chunks)} chunks created")

        return {
            "source": source,
            "document_count": len(documents),
            "chunk_count": len(all_chunks),
            "chunks": all_chunks,
        }

    def add_documents(
        self,
        documents: List[str],
        source: str,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        auto_chunk: bool = True,
        auto_tag: bool = True,
    ) -> List[str]:
        """
        Add documents with embeddings and metadata.
        Optionally processes through chunking and tagging pipeline.

        Args:
            documents: List of document texts
            source: Source identifier (file path, URL, etc.)
            tags: Optional additional tags for documents
            metadata: Optional metadata for documents
            auto_chunk: Whether to chunk documents first
            auto_tag: Whether to auto-tag content

        Returns:
            List of document IDs

        Raises:
            ValueError: If documents list is empty or other validation fails
        """
        if not documents:
            raise ValueError("Documents list cannot be empty")

        logger.info(f"Adding {len(documents)} documents from source: {source}")

        # Process through pipeline if auto_chunk is enabled
        if auto_chunk:
            processed = self.process_documents(
                documents, source, auto_chunk=True, auto_tag=auto_tag
            )
            chunks = [chunk for chunk, _ in processed["chunks"]]
            chunk_texts = [chunk.text for chunk in chunks]
            chunk_metadata_list = [metadata for _, metadata in processed["chunks"]]
        else:
            chunk_texts = documents
            chunk_metadata_list = [None] * len(documents)

        # Add to vector store
        embedding_results = self.vector_store.add_documents(chunk_texts)

        # Add to metadata store
        doc_ids = []
        for (embedding_id, content_hash), doc_text, chunk_meta in zip(
            embedding_results, chunk_texts, chunk_metadata_list
        ):
            try:
                # Prepare metadata from chunk
                doc_meta = {
                    **(metadata or {}),
                }

                # Add auto-generated metadata
                if chunk_meta:
                    doc_meta.update(
                        {
                            "auto_topics": chunk_meta.topics,
                            "auto_domain": chunk_meta.domain,
                            "auto_difficulty": chunk_meta.difficulty_level,
                        }
                    )

                doc_id = self.metadata_store.add_document(
                    source=source,
                    content_hash=content_hash,
                    embedding_id=embedding_id,
                    tags=tags,
                    topics=chunk_meta.topics if chunk_meta else None,
                    domain=chunk_meta.domain if chunk_meta else None,
                    difficulty_level=chunk_meta.difficulty_level if chunk_meta else None,
                    key_terms=chunk_meta.key_terms if chunk_meta else None,
                    metadata=doc_meta,
                )
                doc_ids.append(doc_id)
            except ValueError as e:
                logger.warning(f"Document already exists: {content_hash}")
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
        results = self.vector_store.similarity_search(
            query, k=k * 2, threshold=threshold
        )

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
                    "similarity_score": 1.0
                    / (1.0 + distance),  # Convert distance to score
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
