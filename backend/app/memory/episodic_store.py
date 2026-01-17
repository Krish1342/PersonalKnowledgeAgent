from typing import List, Optional
from datetime import datetime
from pathlib import Path

from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Float
from sqlalchemy.orm import sessionmaker, declarative_base, Session

from app.config import settings


Base = declarative_base()


class MemoryLog(Base):
    """SQLAlchemy model for episodic memory logs."""

    __tablename__ = "memory_logs"

    id: int = Column(Integer, primary_key=True, autoincrement=True)
    source: str = Column(String(255), nullable=False, index=True)
    content: str = Column(Text, nullable=False)
    created_at: datetime = Column(DateTime, default=datetime.utcnow, nullable=False)
    version: int = Column(Integer, default=1, nullable=False)
    confidence: float = Column(Float, default=1.0, nullable=False)

    def __repr__(self) -> str:
        return (
            f"<MemoryLog(id={self.id}, source='{self.source}', "
            f"version={self.version}, confidence={self.confidence})>"
        )

    def to_dict(self) -> dict:
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "source": self.source,
            "content": self.content,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "version": self.version,
            "confidence": self.confidence,
        }


class EpisodicStore:
    """SQLite-based episodic memory store with append-only semantics."""

    def __init__(self, db_path: Optional[str] = None) -> None:
        """
        Initialize the episodic store.

        Args:
            db_path: Path to the SQLite database file.
        """
        self._db_path = db_path or settings.SQLITE_DB_PATH

        # Ensure directory exists
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)

        # Create engine and session factory
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

        # Create tables
        Base.metadata.create_all(self._engine)

    def _get_session(self) -> Session:
        """Create a new database session."""
        return self._session_factory()

    def append_memory(
        self,
        source: str,
        content: str,
        version: int = 1,
        confidence: float = 1.0,
    ) -> MemoryLog:
        """
        Append a new memory log entry (append-only).

        Args:
            source: Origin of the memory (e.g., 'user_input', 'web_scrape').
            content: The actual content/knowledge being stored.
            version: Version number for tracking updates.
            confidence: Confidence score (0.0 to 1.0).

        Returns:
            The created MemoryLog instance.
        """
        session = self._get_session()
        try:
            memory = MemoryLog(
                source=source,
                content=content,
                version=version,
                confidence=confidence,
                created_at=datetime.utcnow(),
            )
            session.add(memory)
            session.commit()
            session.refresh(memory)
            return memory
        finally:
            session.close()

    def get_history(
        self,
        source: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        min_confidence: Optional[float] = None,
    ) -> List[MemoryLog]:
        """
        Retrieve memory history with optional filtering.

        Args:
            source: Filter by source type.
            limit: Maximum number of records to return.
            offset: Number of records to skip.
            min_confidence: Minimum confidence threshold.

        Returns:
            List of MemoryLog entries ordered by created_at descending.
        """
        session = self._get_session()
        try:
            query = session.query(MemoryLog)

            if source is not None:
                query = query.filter(MemoryLog.source == source)

            if min_confidence is not None:
                query = query.filter(MemoryLog.confidence >= min_confidence)

            query = query.order_by(MemoryLog.created_at.desc())
            query = query.limit(limit).offset(offset)

            return query.all()
        finally:
            session.close()

    def get_by_id(self, memory_id: int) -> Optional[MemoryLog]:
        """
        Retrieve a specific memory by ID.

        Args:
            memory_id: The ID of the memory to retrieve.

        Returns:
            MemoryLog if found, None otherwise.
        """
        session = self._get_session()
        try:
            return session.query(MemoryLog).filter(MemoryLog.id == memory_id).first()
        finally:
            session.close()

    def count(self, source: Optional[str] = None) -> int:
        """
        Count total memory entries.

        Args:
            source: Optional source filter.

        Returns:
            Total count of memories.
        """
        session = self._get_session()
        try:
            query = session.query(MemoryLog)
            if source is not None:
                query = query.filter(MemoryLog.source == source)
            return query.count()
        finally:
            session.close()

    def get_sources(self) -> List[str]:
        """
        Get all unique source types.

        Returns:
            List of unique source strings.
        """
        session = self._get_session()
        try:
            results = session.query(MemoryLog.source).distinct().all()
            return [r[0] for r in results]
        finally:
            session.close()
