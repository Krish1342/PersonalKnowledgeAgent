from typing import Optional, Dict, Any
from concurrent.futures import ThreadPoolExecutor
from tempfile import NamedTemporaryFile
from uuid import uuid4
import os
import threading

from fastapi import APIRouter, HTTPException, status, UploadFile, File, Form
from pydantic import BaseModel, Field

from app.graph.agent_graph import get_ingestion_graph
from app.utils.pdf_ingestion import ingest_pdf_file


router = APIRouter(prefix="/ingest", tags=["ingestion"])

_pdf_jobs: Dict[str, Dict[str, Any]] = {}
_pdf_jobs_lock = threading.Lock()
_pdf_executor = ThreadPoolExecutor(max_workers=2)


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


class PdfIngestStartResponse(BaseModel):
    job_id: str
    status: str
    message: str
    source: str


class PdfIngestStatusResponse(BaseModel):
    job_id: str
    status: str
    message: str
    source: str
    current_page: int
    total_pages: int
    chunks_ingested: int


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


@router.post(
    "/pdf",
    response_model=PdfIngestStartResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Ingest a PDF into knowledge base",
    description="Upload a PDF, extract text per page, chunk, and store in the vector store.",
)
async def ingest_pdf(
    file: UploadFile = File(...),
    source: Optional[str] = Form(default=None),
) -> PdfIngestStartResponse:
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are supported",
        )

    job_id = str(uuid4())
    filename = os.path.basename(file.filename)
    source_label = source or filename

    with _pdf_jobs_lock:
        _pdf_jobs[job_id] = {
            "job_id": job_id,
            "status": "queued",
            "message": "Queued for processing",
            "source": filename,
            "current_page": 0,
            "total_pages": 0,
            "chunks_ingested": 0,
        }

    tmp = NamedTemporaryFile(delete=False, suffix=".pdf")
    try:
        content = await file.read()
        tmp.write(content)
        tmp.flush()
    finally:
        tmp.close()

    _pdf_executor.submit(
        _process_pdf_job,
        job_id,
        tmp.name,
        filename,
        source_label,
    )

    return PdfIngestStartResponse(
        job_id=job_id,
        status="queued",
        message="Queued for processing",
        source=filename,
    )


@router.get(
    "/pdf/{job_id}",
    response_model=PdfIngestStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Get PDF ingestion status",
)
async def get_pdf_status(job_id: str) -> PdfIngestStatusResponse:
    with _pdf_jobs_lock:
        job = _pdf_jobs.get(job_id)

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PDF ingestion job not found",
        )

    return PdfIngestStatusResponse(**job)


def _process_pdf_job(
    job_id: str,
    file_path: str,
    filename: str,
    source_label: str,
) -> None:
    try:
        _update_pdf_job(job_id, status="processing", message="Starting PDF processing")

        def _progress(page_number: int, total_pages: int, stage: str) -> None:
            message = f"Processing page {page_number} of {total_pages}..."
            _update_pdf_job(
                job_id,
                status="processing",
                message=message,
                current_page=page_number,
                total_pages=total_pages,
            )

        result = ingest_pdf_file(
            file_path=file_path,
            filename=filename,
            source_label=source_label,
            progress_callback=_progress,
        )

        _update_pdf_job(
            job_id,
            status="completed",
            message=f"Successfully ingested {result['chunks_ingested']} chunks",
            current_page=result["total_pages"],
            total_pages=result["total_pages"],
            chunks_ingested=result["chunks_ingested"],
        )
    except Exception as e:
        _update_pdf_job(
            job_id,
            status="error",
            message=f"PDF ingestion failed: {str(e)}",
        )
    finally:
        try:
            os.unlink(file_path)
        except Exception:
            pass


def _update_pdf_job(job_id: str, **updates: Any) -> None:
    with _pdf_jobs_lock:
        job = _pdf_jobs.get(job_id)
        if not job:
            return
        job.update(updates)
