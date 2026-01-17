"""
Enhanced episodic memory store with compression, tags, bookmarks, and user isolation.
"""

from typing import List, Optional, Set
from datetime import datetime
from pathlib import Path
import json

from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Text,
    DateTime,
    Float,
    Boolean,
    ForeignKey,
    Table,
    LargeBinary,
    Index,
)
from sqlalchemy.orm import sessionmaker, declarative_base, Session, relationship

from app.config import settings
from app.utils.compression import ContentCompressor, get_deduplicator


Base = declarative_base()


# Association table for many-to-many relationship between memories and tags
memory_tags = Table(
    "memory_tags",
    Base.metadata,
    Column("memory_id", Integer, ForeignKey("memory_logs_v2.id"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id"), primary_key=True),
)


class Tag(Base):
    """Tag model for categorizing memories."""

    __tablename__ = "tags"

    id: int = Column(Integer, primary_key=True, autoincrement=True)
    name: str = Column(String(100), unique=True, nullable=False, index=True)
    color: str = Column(String(7), default="#6366f1")  # Hex color
    user_id: str = Column(String(255), nullable=True, index=True)  # For user isolation
    created_at: datetime = Column(DateTime, default=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "color": self.color,
            "user_id": self.user_id,
        }


class MemoryLogV2(Base):
    """Enhanced SQLAlchemy model for episodic memory with compression."""

    __tablename__ = "memory_logs_v2"

    id: int = Column(Integer, primary_key=True, autoincrement=True)
    user_id: str = Column(String(255), nullable=True, index=True)  # Clerk user ID
    source: str = Column(String(255), nullable=False, index=True)

    # Compressed content storage
    content_compressed: bytes = Column(LargeBinary, nullable=False)
    content_hash: str = Column(String(64), nullable=False, index=True)  # SHA-256
    original_size: int = Column(Integer, nullable=False)
    compressed_size: int = Column(Integer, nullable=False)

    # Metadata
    title: str = Column(String(500), nullable=True)  # Auto-generated or user-provided
    summary: str = Column(Text, nullable=True)  # AI-generated summary

    # Timestamps and versioning
    created_at: datetime = Column(
        DateTime, default=datetime.utcnow, nullable=False, index=True
    )
    updated_at: datetime = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    version: int = Column(Integer, default=1, nullable=False)

    # Quality metrics
    confidence: float = Column(Float, default=1.0, nullable=False)

    # User interaction
    is_bookmarked: bool = Column(Boolean, default=False, index=True)
    view_count: int = Column(Integer, default=0)

    # Relationships
    tags = relationship("Tag", secondary=memory_tags, backref="memories")

    # Indexes for common queries
    __table_args__ = (
        Index("idx_user_created", "user_id", "created_at"),
        Index("idx_user_bookmarked", "user_id", "is_bookmarked"),
        Index("idx_user_source", "user_id", "source"),
    )

    def __repr__(self) -> str:
        return (
            f"<MemoryLogV2(id={self.id}, user_id='{self.user_id}', "
            f"source='{self.source}', bookmarked={self.is_bookmarked})>"
        )

    @property
    def content(self) -> str:
        """Decompress and return content."""
        return ContentCompressor.decompress(self.content_compressed)

    @property
    def compression_ratio(self) -> float:
        """Calculate compression ratio."""
        return (
            self.original_size / self.compressed_size
            if self.compressed_size > 0
            else 1.0
        )

    def to_dict(self, include_content: bool = True) -> dict:
        """Convert model to dictionary."""
        data = {
            "id": self.id,
            "user_id": self.user_id,
            "source": self.source,
            "title": self.title,
            "summary": self.summary,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "version": self.version,
            "confidence": self.confidence,
            "is_bookmarked": self.is_bookmarked,
            "view_count": self.view_count,
            "original_size": self.original_size,
            "compressed_size": self.compressed_size,
            "compression_ratio": round(self.compression_ratio, 2),
            "tags": [tag.to_dict() for tag in self.tags] if self.tags else [],
        }
        if include_content:
            data["content"] = self.content
        return data


class SearchHistory(Base):
    """Track user search queries."""

    __tablename__ = "search_history"

    id: int = Column(Integer, primary_key=True, autoincrement=True)
    user_id: str = Column(String(255), nullable=True, index=True)
    query: str = Column(Text, nullable=False)
    results_count: int = Column(Integer, default=0)
    created_at: datetime = Column(DateTime, default=datetime.utcnow, index=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "query": self.query,
            "results_count": self.results_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class EpisodicStoreV2:
    """Enhanced SQLite-based episodic memory store with compression and user isolation."""

    def __init__(self, db_path: Optional[str] = None) -> None:
        self._db_path = db_path or settings.SQLITE_DB_PATH.replace(".db", "_v2.db")

        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)

        self._engine = create_engine(
            f"sqlite:///{self._db_path}",
            echo=False,
            connect_args={"check_same_thread": False},
        )
        self._session_factory = sessionmaker(
            bind=self._engine,
            autocommit=False,
            autoflush=False,
        )

        Base.metadata.create_all(self._engine)
        self._deduplicator = get_deduplicator()

    def _get_session(self) -> Session:
        return self._session_factory()

    def append_memory(
        self,
        source: str,
        content: str,
        user_id: Optional[str] = None,
        title: Optional[str] = None,
        summary: Optional[str] = None,
        tags: Optional[List[str]] = None,
        version: int = 1,
        confidence: float = 1.0,
        skip_duplicates: bool = True,
    ) -> Optional[MemoryLogV2]:
        """
        Append a new memory with compression.

        Args:
            source: Origin of the memory
            content: The content to store
            user_id: Clerk user ID for isolation
            title: Optional title
            summary: Optional AI summary
            tags: List of tag names
            version: Version number
            confidence: Confidence score
            skip_duplicates: Skip if content already exists

        Returns:
            Created MemoryLogV2 or None if duplicate
        """
        # Check for duplicates
        content_hash = ContentCompressor.compute_hash(content)

        session = self._get_session()
        try:
            if skip_duplicates:
                existing = (
                    session.query(MemoryLogV2)
                    .filter(
                        MemoryLogV2.content_hash == content_hash,
                        MemoryLogV2.user_id == user_id,
                    )
                    .first()
                )
                if existing:
                    return None  # Skip duplicate

            # Compress content
            compressed = ContentCompressor.compress(content)
            original_size = len(content.encode("utf-8"))

            # Auto-generate title if not provided
            if not title:
                title = (
                    content[:100].strip() + "..."
                    if len(content) > 100
                    else content.strip()
                )

            memory = MemoryLogV2(
                user_id=user_id,
                source=source,
                content_compressed=compressed,
                content_hash=content_hash,
                original_size=original_size,
                compressed_size=len(compressed),
                title=title,
                summary=summary,
                version=version,
                confidence=confidence,
            )

            # Handle tags
            if tags:
                for tag_name in tags:
                    tag = (
                        session.query(Tag)
                        .filter(Tag.name == tag_name, Tag.user_id == user_id)
                        .first()
                    )
                    if not tag:
                        tag = Tag(name=tag_name, user_id=user_id)
                        session.add(tag)
                    memory.tags.append(tag)

            session.add(memory)
            session.commit()
            session.refresh(memory)
            return memory
        finally:
            session.close()

    def get_history(
        self,
        user_id: Optional[str] = None,
        source: Optional[str] = None,
        tag: Optional[str] = None,
        bookmarked_only: bool = False,
        search_query: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        min_confidence: Optional[float] = None,
    ) -> List[MemoryLogV2]:
        """Retrieve memory history with filtering."""
        session = self._get_session()
        try:
            query = session.query(MemoryLogV2)

            if user_id is not None:
                query = query.filter(MemoryLogV2.user_id == user_id)

            if source is not None:
                query = query.filter(MemoryLogV2.source == source)

            if bookmarked_only:
                query = query.filter(MemoryLogV2.is_bookmarked == True)

            if tag is not None:
                query = query.join(MemoryLogV2.tags).filter(Tag.name == tag)

            if min_confidence is not None:
                query = query.filter(MemoryLogV2.confidence >= min_confidence)

            if search_query:
                # For SQLite, we need to decompress to search
                # This is a limitation - consider full-text search for production
                pass

            query = query.order_by(MemoryLogV2.created_at.desc())
            query = query.limit(limit).offset(offset)

            return query.all()
        finally:
            session.close()

    def get_by_id(
        self, memory_id: int, user_id: Optional[str] = None
    ) -> Optional[MemoryLogV2]:
        """Retrieve memory by ID with user isolation."""
        session = self._get_session()
        try:
            query = session.query(MemoryLogV2).filter(MemoryLogV2.id == memory_id)
            if user_id:
                query = query.filter(MemoryLogV2.user_id == user_id)

            memory = query.first()
            if memory:
                # Increment view count
                memory.view_count += 1
                session.commit()
            return memory
        finally:
            session.close()

    def toggle_bookmark(
        self, memory_id: int, user_id: Optional[str] = None
    ) -> Optional[bool]:
        """Toggle bookmark status. Returns new status or None if not found."""
        session = self._get_session()
        try:
            query = session.query(MemoryLogV2).filter(MemoryLogV2.id == memory_id)
            if user_id:
                query = query.filter(MemoryLogV2.user_id == user_id)

            memory = query.first()
            if memory:
                memory.is_bookmarked = not memory.is_bookmarked
                session.commit()
                return memory.is_bookmarked
            return None
        finally:
            session.close()

    def add_tags(
        self, memory_id: int, tags: List[str], user_id: Optional[str] = None
    ) -> bool:
        """Add tags to a memory."""
        session = self._get_session()
        try:
            query = session.query(MemoryLogV2).filter(MemoryLogV2.id == memory_id)
            if user_id:
                query = query.filter(MemoryLogV2.user_id == user_id)

            memory = query.first()
            if not memory:
                return False

            for tag_name in tags:
                tag = (
                    session.query(Tag)
                    .filter(Tag.name == tag_name, Tag.user_id == user_id)
                    .first()
                )
                if not tag:
                    tag = Tag(name=tag_name, user_id=user_id)
                    session.add(tag)
                if tag not in memory.tags:
                    memory.tags.append(tag)

            session.commit()
            return True
        finally:
            session.close()

    def get_tags(self, user_id: Optional[str] = None) -> List[Tag]:
        """Get all tags for a user."""
        session = self._get_session()
        try:
            query = session.query(Tag)
            if user_id:
                query = query.filter(Tag.user_id == user_id)
            return query.all()
        finally:
            session.close()

    def get_stats(self, user_id: Optional[str] = None) -> dict:
        """Get storage statistics."""
        session = self._get_session()
        try:
            query = session.query(MemoryLogV2)
            if user_id:
                query = query.filter(MemoryLogV2.user_id == user_id)

            memories = query.all()

            total_original = sum(m.original_size for m in memories)
            total_compressed = sum(m.compressed_size for m in memories)
            bookmarked_count = sum(1 for m in memories if m.is_bookmarked)

            sources = {}
            for m in memories:
                sources[m.source] = sources.get(m.source, 0) + 1

            return {
                "total_memories": len(memories),
                "bookmarked_count": bookmarked_count,
                "total_original_bytes": total_original,
                "total_compressed_bytes": total_compressed,
                "storage_saved_bytes": total_original - total_compressed,
                "storage_saved_percent": (
                    round((1 - total_compressed / total_original) * 100, 2)
                    if total_original > 0
                    else 0
                ),
                "average_compression_ratio": (
                    round(total_original / total_compressed, 2)
                    if total_compressed > 0
                    else 1
                ),
                "sources": sources,
            }
        finally:
            session.close()

    def log_search(
        self, query: str, results_count: int, user_id: Optional[str] = None
    ) -> None:
        """Log a search query."""
        session = self._get_session()
        try:
            search = SearchHistory(
                user_id=user_id,
                query=query,
                results_count=results_count,
            )
            session.add(search)
            session.commit()
        finally:
            session.close()

    def get_search_history(
        self, user_id: Optional[str] = None, limit: int = 20
    ) -> List[SearchHistory]:
        """Get recent search history."""
        session = self._get_session()
        try:
            query = session.query(SearchHistory)
            if user_id:
                query = query.filter(SearchHistory.user_id == user_id)
            return query.order_by(SearchHistory.created_at.desc()).limit(limit).all()
        finally:
            session.close()

    def export_data(self, user_id: Optional[str] = None) -> dict:
        """Export all user data for backup."""
        session = self._get_session()
        try:
            query = session.query(MemoryLogV2)
            if user_id:
                query = query.filter(MemoryLogV2.user_id == user_id)

            memories = query.all()
            tags = self.get_tags(user_id)

            return {
                "exported_at": datetime.utcnow().isoformat(),
                "user_id": user_id,
                "memories": [m.to_dict(include_content=True) for m in memories],
                "tags": [t.to_dict() for t in tags],
                "stats": self.get_stats(user_id),
            }
        finally:
            session.close()

    def import_data(self, data: dict, user_id: Optional[str] = None) -> dict:
        """Import data from backup."""
        imported_count = 0
        skipped_count = 0

        for memory_data in data.get("memories", []):
            result = self.append_memory(
                source=memory_data.get("source", "import"),
                content=memory_data.get("content", ""),
                user_id=user_id,
                title=memory_data.get("title"),
                summary=memory_data.get("summary"),
                tags=[t["name"] for t in memory_data.get("tags", [])],
                confidence=memory_data.get("confidence", 1.0),
            )
            if result:
                imported_count += 1
            else:
                skipped_count += 1

        return {
            "imported": imported_count,
            "skipped_duplicates": skipped_count,
        }

    def count(self, user_id: Optional[str] = None, source: Optional[str] = None) -> int:
        """Count memories."""
        session = self._get_session()
        try:
            query = session.query(MemoryLogV2)
            if user_id:
                query = query.filter(MemoryLogV2.user_id == user_id)
            if source:
                query = query.filter(MemoryLogV2.source == source)
            return query.count()
        finally:
            session.close()

    def get_sources(self, user_id: Optional[str] = None) -> List[str]:
        """Get unique sources."""
        session = self._get_session()
        try:
            query = session.query(MemoryLogV2.source).distinct()
            if user_id:
                query = query.filter(MemoryLogV2.user_id == user_id)
            return [r[0] for r in query.all()]
        finally:
            session.close()


# Singleton
_store_v2: Optional[EpisodicStoreV2] = None


def get_episodic_store_v2() -> EpisodicStoreV2:
    """Get singleton EpisodicStoreV2 instance."""
    global _store_v2
    if _store_v2 is None:
        _store_v2 = EpisodicStoreV2()
    return _store_v2
