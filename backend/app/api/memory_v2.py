"""
Enhanced memory API routes with compression, bookmarks, tags, and user isolation.
"""

from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel

from app.memory.episodic_store_v2 import get_episodic_store_v2, MemoryLogV2
from app.utils.smart_tagger import get_smart_tagger
from app.auth.clerk import get_optional_user, get_required_user, ClerkUser, get_user_id


router = APIRouter(prefix="/memory", tags=["memory"])


# Request/Response models
class ToggleBookmarkRequest(BaseModel):
    memory_id: int


class AddTagsRequest(BaseModel):
    memory_id: int
    tags: List[str]


class CreateTagRequest(BaseModel):
    name: str
    color: Optional[str] = "#6366f1"


class ImportDataRequest(BaseModel):
    data: dict


class MemoryResponse(BaseModel):
    id: int
    source: str
    content: str
    title: Optional[str]
    summary: Optional[str]
    created_at: str
    confidence: float
    is_bookmarked: bool
    view_count: int
    original_size: int
    compressed_size: int
    compression_ratio: float
    tags: List[dict]


class MemoryListResponse(BaseModel):
    memories: List[dict]
    total: int
    page: int
    page_size: int


class StatsResponse(BaseModel):
    total_memories: int
    bookmarked_count: int
    total_original_bytes: int
    total_compressed_bytes: int
    storage_saved_bytes: int
    storage_saved_percent: float
    average_compression_ratio: float
    sources: dict


@router.get("")
async def get_memories(
    source: Optional[str] = Query(None),
    tag: Optional[str] = Query(None),
    bookmarked: bool = Query(False),
    search: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: Optional[ClerkUser] = Depends(get_optional_user),
) -> MemoryListResponse:
    """Get memories with filtering."""
    store = get_episodic_store_v2()
    user_id = get_user_id(user)

    memories = store.get_history(
        user_id=user_id,
        source=source,
        tag=tag,
        bookmarked_only=bookmarked,
        search_query=search,
        limit=limit,
        offset=offset,
    )

    total = store.count(user_id=user_id, source=source)

    return MemoryListResponse(
        memories=[m.to_dict(include_content=False) for m in memories],
        total=total,
        page=offset // limit + 1,
        page_size=limit,
    )


@router.get("/stats")
async def get_memory_stats(
    user: Optional[ClerkUser] = Depends(get_optional_user),
) -> StatsResponse:
    """Get memory statistics with storage savings."""
    store = get_episodic_store_v2()
    user_id = get_user_id(user)

    stats = store.get_stats(user_id=user_id)
    return StatsResponse(**stats)


@router.get("/sources")
async def get_sources(
    user: Optional[ClerkUser] = Depends(get_optional_user),
) -> List[str]:
    """Get all unique sources."""
    store = get_episodic_store_v2()
    user_id = get_user_id(user)
    return store.get_sources(user_id=user_id)


@router.get("/tags")
async def get_tags(
    user: Optional[ClerkUser] = Depends(get_optional_user),
) -> List[dict]:
    """Get all tags."""
    store = get_episodic_store_v2()
    user_id = get_user_id(user)
    tags = store.get_tags(user_id=user_id)
    return [t.to_dict() for t in tags]


@router.get("/search-history")
async def get_search_history(
    limit: int = Query(20, ge=1, le=100),
    user: Optional[ClerkUser] = Depends(get_optional_user),
) -> List[dict]:
    """Get recent search history."""
    store = get_episodic_store_v2()
    user_id = get_user_id(user)
    history = store.get_search_history(user_id=user_id, limit=limit)
    return [h.to_dict() for h in history]


@router.get("/{memory_id}")
async def get_memory_by_id(
    memory_id: int,
    user: Optional[ClerkUser] = Depends(get_optional_user),
) -> dict:
    """Get a specific memory by ID."""
    store = get_episodic_store_v2()
    user_id = get_user_id(user)

    memory = store.get_by_id(memory_id, user_id=user_id)
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")

    return memory.to_dict(include_content=True)


@router.post("/bookmark")
async def toggle_bookmark(
    request: ToggleBookmarkRequest,
    user: Optional[ClerkUser] = Depends(get_optional_user),
) -> dict:
    """Toggle bookmark status for a memory."""
    store = get_episodic_store_v2()
    user_id = get_user_id(user)

    result = store.toggle_bookmark(request.memory_id, user_id=user_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Memory not found")

    return {"memory_id": request.memory_id, "is_bookmarked": result}


@router.post("/tags")
async def add_tags_to_memory(
    request: AddTagsRequest,
    user: Optional[ClerkUser] = Depends(get_optional_user),
) -> dict:
    """Add tags to a memory."""
    store = get_episodic_store_v2()
    user_id = get_user_id(user)

    success = store.add_tags(request.memory_id, request.tags, user_id=user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Memory not found")

    return {"memory_id": request.memory_id, "tags_added": request.tags}


@router.post("/analyze")
async def analyze_content(
    content: str,
) -> dict:
    """Analyze content and suggest tags, title, and summary."""
    tagger = get_smart_tagger()
    return tagger.categorize_content(content)


@router.get("/export")
async def export_data(
    user: Optional[ClerkUser] = Depends(get_optional_user),
) -> dict:
    """Export all user data for backup."""
    store = get_episodic_store_v2()
    user_id = get_user_id(user)

    return store.export_data(user_id=user_id)


@router.post("/import")
async def import_data(
    request: ImportDataRequest,
    user: Optional[ClerkUser] = Depends(get_optional_user),
) -> dict:
    """Import data from backup."""
    store = get_episodic_store_v2()
    user_id = get_user_id(user)

    result = store.import_data(request.data, user_id=user_id)
    return {
        "success": True,
        "imported": result["imported"],
        "skipped_duplicates": result["skipped_duplicates"],
    }
