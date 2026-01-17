from typing import Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.graph.agent_graph import get_ingestion_graph


router = APIRouter(prefix="/ingest", tags=["ingestion"])


class IngestRequest(BaseModel):
    """Request body for ingestion endpoint."""

    content: str = Field(
        ...,
        min_length=1,
        description="The text content to ingest into the knowledge base.",
    )
    source: Optional[str] = Field(
        default="user_input",
        description="Source identifier for the content (e.g., 'user_input', 'document', 'web').",
    )


class IngestResponse(BaseModel):
    """Response body for ingestion endpoint."""

    success: bool
    message: str
    chunks_ingested: int
    source: str


@router.post(
    "",
    response_model=IngestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest content into knowledge base",
    description="Process and store text content in the vector store and episodic memory.",
)
async def ingest_content(request: IngestRequest) -> IngestResponse:
    """
    Ingest content into the knowledge base.

    Triggers the ingestion agent workflow which:
    1. Chunks the content with semantic overlap
    2. Generates embeddings and stores in vector DB
    3. Logs to episodic memory for history tracking
    """
    try:
        # Get the ingestion graph
        graph = get_ingestion_graph()

        # Prepare initial state
        initial_state = {
            "raw_input": request.content,
            "source": request.source,
        }

        # Execute the ingestion workflow
        result = graph.invoke(initial_state)

        # Check for errors
        error = result.get("error")
        chunks_ingested = result.get("chunks_ingested", 0)

        if error and chunks_ingested == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error,
            )

        return IngestResponse(
            success=True,
            message=f"Successfully ingested {chunks_ingested} chunks",
            chunks_ingested=chunks_ingested,
            source=request.source or "user_input",
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ingestion failed: {str(e)}",
        )
