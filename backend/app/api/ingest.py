"""
FastAPI endpoints for document ingestion.
Exposes LangGraph ingestion agent through REST API.
"""

from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status
from pydantic import BaseModel, Field

from app.agents.ingestion_agent import IngestionAgent, IngestionResult
from app.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/documents", tags=["ingestion"])

# Initialize agent
_agent: Optional[IngestionAgent] = None


def get_agent() -> IngestionAgent:
    """Get or create ingestion agent."""
    global _agent
    if _agent is None:
        _agent = IngestionAgent()
    return _agent


class IngestRequest(BaseModel):
    """Request model for text ingestion."""

    content: str = Field(..., description="Document content to ingest")
    source: str = Field(..., description="Source identifier (file path, URL, etc.)")
    input_type: str = Field(
        default="text",
        description="Input type: text, markdown, pdf, docx",
    )


class IngestResponse(BaseModel):
    """Response model for ingestion."""

    success: bool
    chunks_created: int
    documents_processed: int
    metadata_stored: bool
    vector_embeddings_stored: bool
    message: str
    errors: list[str]
    document_ids: list[str]


@router.post("/ingest", response_model=IngestResponse, status_code=status.HTTP_200_OK)
async def ingest_text(request: IngestRequest) -> IngestResponse:
    """
    Ingest plain text or markdown document.

    Args:
        request: Ingestion request with content and metadata

    Returns:
        Ingestion summary

    Raises:
        HTTPException: If ingestion fails
    """
    logger.info(f"Ingestion request: {request.source} ({request.input_type})")

    try:
        agent = get_agent()
        result = await agent.ingest(
            content=request.content,
            source=request.source,
            input_type=request.input_type,
        )

        return IngestResponse(
            success=result.success,
            chunks_created=result.chunks_created,
            documents_processed=result.documents_processed,
            metadata_stored=result.metadata_stored,
            vector_embeddings_stored=result.vector_embeddings_stored,
            message=result.message,
            errors=result.errors,
            document_ids=result.document_ids,
        )

    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid request: {str(e)}",
        )
    except Exception as e:
        logger.error(f"Ingestion error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ingestion failed: {str(e)}",
        )


@router.post("/ingest/upload", response_model=IngestResponse)
async def ingest_file(
    file: UploadFile = File(...),
    source: Optional[str] = Form(None),
) -> IngestResponse:
    """
    Ingest document from file upload.

    Supports: PDF, DOCX, Markdown, Text files.

    Args:
        file: Uploaded file
        source: Optional source identifier (defaults to filename)

    Returns:
        Ingestion summary

    Raises:
        HTTPException: If file format not supported or ingestion fails
    """
    source = source or file.filename
    logger.info(f"File upload: {file.filename} ({file.content_type})")

    try:
        # Read file content
        content = await file.read()

        if not content:
            raise ValueError("File is empty")

        # Determine file type
        filename = file.filename or ""
        ext = filename.split(".")[-1].lower() if "." in filename else ""

        agent = get_agent()

        # Extract and process based on type
        from app.agents.ingestion_agent import DocumentCleaner

        cleaner = DocumentCleaner()

        if ext == "pdf":
            text_content = cleaner.extract_from_pdf(content)
            input_type = "pdf"
        elif ext == "docx":
            text_content = cleaner.extract_from_docx(content)
            input_type = "docx"
        elif ext in ("md", "markdown"):
            text_content = content.decode("utf-8")
            input_type = "markdown"
        elif ext == "txt":
            text_content = content.decode("utf-8")
            input_type = "text"
        else:
            raise ValueError(
                f"Unsupported file type: {ext}. "
                "Supported: pdf, docx, md, txt"
            )

        result = await agent.ingest(
            content=text_content,
            source=source,
            input_type=input_type,
        )

        return IngestResponse(
            success=result.success,
            chunks_created=result.chunks_created,
            documents_processed=result.documents_processed,
            metadata_stored=result.metadata_stored,
            vector_embeddings_stored=result.vector_embeddings_stored,
            message=result.message,
            errors=result.errors,
            document_ids=result.document_ids,
        )

    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid request: {str(e)}",
        )
    except Exception as e:
        logger.error(f"File ingestion error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"File ingestion failed: {str(e)}",
        )


@router.get("/ingest/status")
async def ingestion_status() -> dict[str, str]:
    """
    Get ingestion agent status.

    Returns:
        Status information
    """
    try:
        agent = get_agent()
        return {
            "status": "ready",
            "agent": "ingestion",
            "message": "Document ingestion agent is operational",
        }
    except Exception as e:
        logger.error(f"Status check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ingestion agent not available",
        )


class BatchIngestRequest(BaseModel):
    """Request for batch ingestion."""

    documents: list[IngestRequest] = Field(
        ..., description="List of documents to ingest"
    )


@router.post("/ingest/batch", response_model=list[IngestResponse])
async def ingest_batch(request: BatchIngestRequest) -> list[IngestResponse]:
    """
    Ingest multiple documents in batch.

    Args:
        request: Batch ingestion request

    Returns:
        List of ingestion results

    Raises:
        HTTPException: If batch ingestion fails
    """
    logger.info(f"Batch ingestion: {len(request.documents)} documents")

    try:
        agent = get_agent()
        results = []

        for doc_request in request.documents:
            try:
                result = await agent.ingest(
                    content=doc_request.content,
                    source=doc_request.source,
                    input_type=doc_request.input_type,
                )
                results.append(
                    IngestResponse(
                        success=result.success,
                        chunks_created=result.chunks_created,
                        documents_processed=result.documents_processed,
                        metadata_stored=result.metadata_stored,
                        vector_embeddings_stored=result.vector_embeddings_stored,
                        message=result.message,
                        errors=result.errors,
                        document_ids=result.document_ids,
                    )
                )
            except Exception as e:
                logger.error(f"Batch item failed: {e}")
                results.append(
                    IngestResponse(
                        success=False,
                        chunks_created=0,
                        documents_processed=0,
                        metadata_stored=False,
                        vector_embeddings_stored=False,
                        message=f"Ingestion failed: {str(e)}",
                        errors=[str(e)],
                        document_ids=[],
                    )
                )

        return results

    except Exception as e:
        logger.error(f"Batch ingestion error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch ingestion failed: {str(e)}",
        )
