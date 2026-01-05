"""
Metadata store using Supabase (PostgreSQL).
Manages document metadata including source, tags, domain, difficulty, and timestamps.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy import (
    create_engine,
    Column,
    String,
    DateTime,
    Integer,
    JSON,
    Index,
    Text,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import uuid

from app.config import get_settings
from app.utils.logging import get_logger

logger = get_logger(__name__)

Base = declarative_base()


class DocumentMetadata(Base):
    """SQLAlchemy model for document metadata."""

    __tablename__ = "documents"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    source = Column(String(255), nullable=False, index=True)
    content_hash = Column(String(64), nullable=False, unique=True, index=True)
    tags = Column(JSON, nullable=True)
    topics = Column(JSON, nullable=True)
    domain = Column(String(100), nullable=True, index=True)
    difficulty_level = Column(String(50), nullable=True)
    key_terms = Column(JSON, nullable=True)
    metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    embedding_id = Column(Integer, nullable=False, unique=True)

    __table_args__ = (
        Index("idx_source_created", "source", "created_at"),
        Index("idx_embedding_id", "embedding_id"),
        Index("idx_domain", "domain"),
        Index("idx_difficulty", "difficulty_level"),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "id": self.id,
            "source": self.source,
            "tags": self.tags or [],
            "topics": self.topics or [],
            "domain": self.domain,
            "difficulty_level": self.difficulty_level,
            "key_terms": self.key_terms or [],
            "metadata": self.metadata or {},
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "embedding_id": self.embedding_id,
        }


class MetadataStore:
    """
    Metadata store for managing document information.
    Persists metadata to Supabase (PostgreSQL).
    """

    def __init__(self, database_url: Optional[str] = None):
        """
        Initialize metadata store.

        Args:
            database_url: Supabase PostgreSQL connection URL. If None, uses config setting.
        """
        settings = get_settings()
        self.database_url = database_url or settings.DATABASE_URL
        self.engine = create_engine(self.database_url, pool_pre_ping=True)
        self.SessionLocal = sessionmaker(bind=self.engine)

        logger.info(
            f"Initializing metadata store (Supabase): {self.database_url[:50]}..."
        )

    def init_db(self) -> None:
        """
        Initialize database tables.
        Safe to call multiple times.
        """
        try:
            Base.metadata.create_all(self.engine)
            logger.info("Database tables initialized")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise

    def add_document(
        self,
        source: str,
        content_hash: str,
        embedding_id: int,
        tags: Optional[List[str]] = None,
        topics: Optional[List[str]] = None,
        domain: Optional[str] = None,
        difficulty_level: Optional[str] = None,
        key_terms: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Add document metadata.

        Args:
            source: Document source (file path, URL, etc.)
            content_hash: SHA-256 hash of document content
            embedding_id: ID of corresponding vector in store
            tags: Optional list of tags
            topics: Optional list of topics
            domain: Optional domain classification
            difficulty_level: Optional difficulty level
            key_terms: Optional extracted key terms
            metadata: Optional additional metadata

        Returns:
            Document ID

        Raises:
            ValueError: If document already exists
        """
        session = self.SessionLocal()
        try:
            # Check if document already exists
            existing = (
                session.query(DocumentMetadata)
                .filter_by(content_hash=content_hash)
                .first()
            )
            if existing:
                logger.warning(f"Document already exists: {content_hash}")
                raise ValueError(f"Document with hash {content_hash} already exists")

            doc = DocumentMetadata(
                source=source,
                content_hash=content_hash,
                embedding_id=embedding_id,
                tags=tags,
                topics=topics,
                domain=domain,
                difficulty_level=difficulty_level,
                key_terms=key_terms,
                metadata=metadata,
            )
            session.add(doc)
            session.commit()

            logger.info(f"Document added: {doc.id} from {source}")
            return doc.id

        except Exception as e:
            session.rollback()
            logger.error(f"Error adding document: {e}")
            raise
        finally:
            session.close()

    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """
        Get document metadata by ID.

        Args:
            doc_id: Document ID

        Returns:
            Document metadata or None if not found
        """
        session = self.SessionLocal()
        try:
            doc = session.query(DocumentMetadata).filter_by(id=doc_id).first()
            return doc.to_dict() if doc else None
        finally:
            session.close()

    def get_by_source(self, source: str) -> List[Dict[str, Any]]:
        """
        Get all documents from a specific source.

        Args:
            source: Document source

        Returns:
            List of document metadata
        """
        session = self.SessionLocal()
        try:
            docs = session.query(DocumentMetadata).filter_by(source=source).all()
            return [doc.to_dict() for doc in docs]
        finally:
            session.close()

    def get_by_content_hash(self, content_hash: str) -> Optional[Dict[str, Any]]:
        """
        Get document metadata by content hash.

        Args:
            content_hash: SHA-256 hash of content

        Returns:
            Document metadata or None if not found
        """
        session = self.SessionLocal()
        try:
            doc = (
                session.query(DocumentMetadata)
                .filter_by(content_hash=content_hash)
                .first()
            )
            return doc.to_dict() if doc else None
        finally:
            session.close()

    def update_tags(self, doc_id: str, tags: List[str]) -> None:
        """
        Update document tags.

        Args:
            doc_id: Document ID
            tags: New tags list
        """
        session = self.SessionLocal()
        try:
            doc = session.query(DocumentMetadata).filter_by(id=doc_id).first()
            if not doc:
                raise ValueError(f"Document {doc_id} not found")

            doc.tags = tags
            session.commit()
            logger.info(f"Updated tags for document: {doc_id}")

        except Exception as e:
            session.rollback()
            logger.error(f"Error updating tags: {e}")
            raise
        finally:
            session.close()

    def delete_by_source(self, source: str) -> int:
        """
        Delete all documents from a specific source.

        Args:
            source: Document source

        Returns:
            Number of documents deleted

        Raises:
            ValueError: If no documents found for source
        """
        session = self.SessionLocal()
        try:
            docs = session.query(DocumentMetadata).filter_by(source=source).all()

            if not docs:
                logger.warning(f"No documents found for source: {source}")
                raise ValueError(f"No documents found for source: {source}")

            embedding_ids = [doc.embedding_id for doc in docs]
            count = len(docs)

            # Delete from database
            session.query(DocumentMetadata).filter_by(source=source).delete()
            session.commit()

            logger.info(f"Deleted {count} documents from source: {source}")
            return count

        except Exception as e:
            session.rollback()
            logger.error(f"Error deleting by source: {e}")
            raise
        finally:
            session.close()

    def delete_document(self, doc_id: str) -> None:
        """
        Delete a specific document.

        Args:
            doc_id: Document ID

        Raises:
            ValueError: If document not found
        """
        session = self.SessionLocal()
        try:
            doc = session.query(DocumentMetadata).filter_by(id=doc_id).first()
            if not doc:
                raise ValueError(f"Document {doc_id} not found")

            session.delete(doc)
            session.commit()
            logger.info(f"Deleted document: {doc_id}")

        except Exception as e:
            session.rollback()
            logger.error(f"Error deleting document: {e}")
            raise
        finally:
            session.close()

    def get_embedding_ids_by_source(self, source: str) -> List[int]:
        """
        Get all embedding IDs for a source.

        Args:
            source: Document source

        Returns:
            List of embedding IDs
        """
        session = self.SessionLocal()
        try:
            docs = session.query(DocumentMetadata).filter_by(source=source).all()
            return [doc.embedding_id for doc in docs]
        finally:
            session.close()

    def list_sources(self) -> List[str]:
        """
        Get list of unique sources.

        Returns:
            List of source names
        """
        session = self.SessionLocal()
        try:
            sources = (
                session.query(DocumentMetadata.source)
                .distinct()
                .order_by(DocumentMetadata.source)
                .all()
            )
            return [source[0] for source in sources]
        finally:
            session.close()

    def get_document_count(self) -> int:
        """
        Get total number of documents.

        Returns:
            Document count
        """
        session = self.SessionLocal()
        try:
            return session.query(DocumentMetadata).count()
        finally:
            session.close()
