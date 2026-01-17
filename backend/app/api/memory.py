from typing import Optional, List

from fastapi import APIRouter, HTTPException, status, Query
from pydantic import BaseModel, Field

from app.memory.episodic_store import EpisodicStore


router = APIRouter(prefix="/memory", tags=["memory"])


class MemoryItem(BaseModel):
    """A single memory log entry."""

    id: int
    source: str
    content: str
    created_at: str
    version: int
    confidence: float


class MemoryResponse(BaseModel):
    """Response body for memory endpoint."""

    total: int
    items: List[MemoryItem]
    sources: List[str] = Field(
        default_factory=list,
        description="List of unique source types in the memory store",
    )


class MemoryStatsResponse(BaseModel):
    """Response body for memory stats endpoint."""

    total_memories: int
    sources: List[str]
    source_counts: dict


@router.get(
    "",
    response_model=MemoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get episodic memory history",
    description="Retrieve memory logs from the episodic store with optional filtering.",
)
async def get_memory(
    source: Optional[str] = Query(
        default=None,
        description="Filter by source type",
    ),
    limit: int = Query(
        default=50,
        ge=1,
        le=500,
        description="Maximum number of records to return",
    ),
    offset: int = Query(
        default=0,
        ge=0,
        description="Number of records to skip",
    ),
    min_confidence: Optional[float] = Query(
        default=None,
        ge=0.0,
        le=1.0,
        description="Minimum confidence threshold",
    ),
) -> MemoryResponse:
    """
    Retrieve episodic memory history.
    
    Returns memory logs with metadata about when and why knowledge was learned.
    """
    try:
        store = EpisodicStore()

        # Get memory entries
        memories = store.get_history(
            source=source,
            limit=limit,
            offset=offset,
            min_confidence=min_confidence,
        )

        # Get total count and sources
        total = store.count(source=source)
        sources = store.get_sources()

        # Format items
        items = [
            MemoryItem(
                id=m.id,
                source=m.source,
                content=m.content,
                created_at=m.created_at.isoformat() if m.created_at else "",
                version=m.version,
                confidence=m.confidence,
            )
            for m in memories
        ]

        return MemoryResponse(
            total=total,
            items=items,
            sources=sources,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve memory: {str(e)}",
        )


@router.get(
    "/stats",
    response_model=MemoryStatsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get memory statistics",
    description="Get aggregate statistics about the episodic memory store.",
)
async def get_memory_stats() -> MemoryStatsResponse:
    """
    Get statistics about the episodic memory store.
    """
    try:
        store = EpisodicStore()

        sources = store.get_sources()
        total = store.count()

        # Get count per source
        source_counts = {
            source: store.count(source=source)
            for source in sources
        }

        return MemoryStatsResponse(
            total_memories=total,
            sources=sources,
            source_counts=source_counts,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve stats: {str(e)}",
        )


@router.get(
    "/{memory_id}",
    response_model=MemoryItem,
    status_code=status.HTTP_200_OK,
    summary="Get a specific memory by ID",
)
async def get_memory_by_id(memory_id: int) -> MemoryItem:
    """
    Retrieve a specific memory entry by its ID.
    """
    try:
        store = EpisodicStore()
        memory = store.get_by_id(memory_id)

        if not memory:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Memory with ID {memory_id} not found",
            )

        return MemoryItem(
            id=memory.id,
            source=memory.source,
            content=memory.content,
            created_at=memory.created_at.isoformat() if memory.created_at else "",
            version=memory.version,
            confidence=memory.confidence,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve memory: {str(e)}",
        )
