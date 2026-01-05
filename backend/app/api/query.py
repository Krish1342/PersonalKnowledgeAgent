"""
Query API for Personal Knowledge Agent

Exposes the agent graph workflow via REST API.
Handles natural language queries and returns grounded answers with sources.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
import json
import asyncio
import traceback

# Import agent graph
from app.graph.agent_graph import (
    PersonalKnowledgeAgentGraph,
    create_agent_graph,
    AgentState,
)
from app.agents.reasoning_agent import ReasoningMode


# ============================================================================
# Request/Response Models
# ============================================================================


class ReasoningModeEnum(str, Enum):
    """Available reasoning modes"""

    ELI5 = "eli5"
    EXAM = "exam"
    RESEARCH = "research"
    COMPARISON = "comparison"


class QueryRequest(BaseModel):
    """Request model for query endpoint"""

    query: str = Field(
        ..., description="Natural language query", min_length=1, max_length=2000
    )
    mode: ReasoningModeEnum = Field(
        default=ReasoningModeEnum.RESEARCH,
        description="Reasoning mode (eli5/exam/research/comparison)",
    )
    user_id: Optional[str] = Field(None, description="Optional user identifier")
    session_id: Optional[str] = Field(None, description="Optional session identifier")
    context: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Optional additional context"
    )
    stream: bool = Field(default=False, description="Enable streaming response")

    class Config:
        schema_extra = {
            "example": {
                "query": "What are the key principles of machine learning?",
                "mode": "research",
                "user_id": "user_123",
                "session_id": "session_456",
                "context": {"domain": "AI"},
                "stream": False,
            }
        }


class Citation(BaseModel):
    """Citation/source model"""

    chunk_id: str = Field(..., description="Chunk identifier")
    text: str = Field(..., description="Cited text excerpt")
    source: Optional[str] = Field(None, description="Source document/URL")
    confidence: Optional[float] = Field(None, description="Citation confidence (0-100)")


class ReasoningStep(BaseModel):
    """Reasoning step model"""

    step_number: int = Field(..., description="Step number in reasoning chain")
    content: str = Field(..., description="Step content")


class QueryResponse(BaseModel):
    """Response model for query endpoint"""

    query: str = Field(..., description="Original query")
    answer: str = Field(..., description="Generated answer")
    confidence: float = Field(..., description="Overall confidence score (0-100)")

    # Sources and citations
    citations: List[Citation] = Field(
        default_factory=list, description="Source citations"
    )
    sources_count: int = Field(..., description="Number of sources used")

    # Reasoning details
    mode: str = Field(..., description="Reasoning mode used")
    reasoning_steps: Optional[List[ReasoningStep]] = Field(
        None, description="Reasoning chain (if available)"
    )

    # Validation
    validation_passed: bool = Field(..., description="Whether validation passed")
    validation_confidence: Optional[str] = Field(
        None, description="Validation confidence level"
    )

    # Metadata
    query_id: str = Field(..., description="Unique query identifier")
    session_id: Optional[str] = Field(None, description="Session identifier")
    processing_time_ms: float = Field(
        ..., description="Processing time in milliseconds"
    )
    timestamp: str = Field(..., description="Response timestamp (ISO format)")

    # Insights
    knowledge_gaps: Optional[List[str]] = Field(
        None, description="Detected knowledge gaps"
    )
    suggestions: Optional[List[str]] = Field(
        None, description="Improvement suggestions"
    )

    class Config:
        schema_extra = {
            "example": {
                "query": "What is machine learning?",
                "answer": "Machine learning is a subset of artificial intelligence...",
                "confidence": 87.5,
                "citations": [
                    {
                        "chunk_id": "chunk_123",
                        "text": "Machine learning is a method of data analysis...",
                        "source": "ML Textbook Chapter 1",
                    }
                ],
                "sources_count": 3,
                "mode": "research",
                "validation_passed": True,
                "validation_confidence": "high",
                "query_id": "query_abc123",
                "processing_time_ms": 1234.5,
                "timestamp": "2026-01-05T12:00:00Z",
            }
        }


class ErrorResponse(BaseModel):
    """Error response model"""

    error: str = Field(..., description="Error message")
    error_type: str = Field(..., description="Error type")
    query: Optional[str] = Field(None, description="Original query")
    timestamp: str = Field(..., description="Error timestamp")
    details: Optional[Dict[str, Any]] = Field(
        None, description="Additional error details"
    )


class HealthResponse(BaseModel):
    """Health check response"""

    status: str = Field(..., description="Service status")
    timestamp: str = Field(..., description="Current timestamp")
    agents_loaded: bool = Field(..., description="Whether agents are loaded")


# ============================================================================
# API Router
# ============================================================================

router = APIRouter(prefix="/api/v1", tags=["query"])

# Global agent graph instance (initialized on startup)
_agent_graph: Optional[PersonalKnowledgeAgentGraph] = None


def get_agent_graph() -> PersonalKnowledgeAgentGraph:
    """Dependency to get agent graph instance"""
    if _agent_graph is None:
        raise HTTPException(
            status_code=503,
            detail="Agent graph not initialized. Please check service startup.",
        )
    return _agent_graph


async def initialize_agent_graph(memory_manager, groq_api_key: Optional[str] = None):
    """Initialize the agent graph (call this on app startup)"""
    global _agent_graph

    try:
        _agent_graph = await create_agent_graph(
            memory_manager=memory_manager,
            groq_api_key=groq_api_key,
            enable_checkpointing=True,
        )
        print("✓ Agent graph initialized successfully")
    except Exception as e:
        print(f"✗ Failed to initialize agent graph: {e}")
        traceback.print_exc()
        raise


# ============================================================================
# API Endpoints
# ============================================================================


@router.post(
    "/query",
    response_model=QueryResponse,
    summary="Process natural language query",
    description="""
    Process a natural language query using the full agent workflow:
    Observe → Plan → Retrieve → Reason → Critique → Act → Reflect → Update Memory
    
    Returns a grounded answer with source citations and confidence score.
    """,
)
async def query(
    request: QueryRequest,
    background_tasks: BackgroundTasks,
    graph: PersonalKnowledgeAgentGraph = Depends(get_agent_graph),
) -> QueryResponse:
    """
    Process a natural language query through the agent workflow.

    Args:
        request: Query request with query text and options
        background_tasks: FastAPI background tasks
        graph: Agent graph instance

    Returns:
        QueryResponse with answer, sources, and confidence
    """
    start_time = datetime.utcnow()
    query_id = f"query_{start_time.timestamp()}"

    try:
        # If streaming requested, use different endpoint
        if request.stream:
            raise HTTPException(
                status_code=400, detail="For streaming, use POST /query/stream endpoint"
            )

        # Prepare context
        context = request.context or {}
        context["mode"] = request.mode.value

        # Execute agent graph
        result: AgentState = await graph.execute(
            query=request.query,
            user_id=request.user_id,
            session_id=request.session_id or query_id,
            context=context,
        )

        # Check workflow status
        if result.get("workflow_status") == "failed":
            errors = result.get("errors", [])
            raise HTTPException(
                status_code=500,
                detail=f"Workflow failed: {errors[0] if errors else 'Unknown error'}",
            )

        # Extract response components
        answer = result.get("final_answer", "")
        if not answer:
            raise HTTPException(
                status_code=500,
                detail="No answer generated. Check agent configuration.",
            )

        # Extract citations
        citations = []
        for citation_dict in result.get("citations", []):
            citations.append(
                Citation(
                    chunk_id=citation_dict.get("chunk_id", "unknown"),
                    text=citation_dict.get("text", ""),
                    source=citation_dict.get("source"),
                    confidence=citation_dict.get("confidence"),
                )
            )

        # Extract reasoning steps
        reasoning_steps = None
        reasoning_result = result.get("reasoning_result")
        if reasoning_result and hasattr(reasoning_result, "reasoning_steps"):
            reasoning_steps = [
                ReasoningStep(
                    step_number=i + 1,
                    content=step.content if hasattr(step, "content") else str(step),
                )
                for i, step in enumerate(reasoning_result.reasoning_steps)
            ]

        # Extract validation info
        validation_result = result.get("validation_result")
        validation_passed = True
        validation_confidence = None

        if validation_result:
            validation_passed = validation_result.is_valid
            validation_confidence = validation_result.confidence.value

        # Get confidence score
        confidence = result.get("confidence_score", 0.0)

        # Extract insights for knowledge gaps and suggestions
        knowledge_gaps = []
        suggestions = []

        insights = result.get("insights", [])
        for insight in insights:
            if insight.get("type") == "knowledge_gap":
                knowledge_gaps.append(insight.get("title", ""))

            # Extract suggestions from validation
            if validation_result and validation_result.improvement_suggestions:
                suggestions = validation_result.improvement_suggestions[:3]

        # Calculate processing time
        processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000

        # Build response
        response = QueryResponse(
            query=request.query,
            answer=answer,
            confidence=confidence,
            citations=citations,
            sources_count=len(citations),
            mode=request.mode.value,
            reasoning_steps=reasoning_steps,
            validation_passed=validation_passed,
            validation_confidence=validation_confidence,
            query_id=query_id,
            session_id=request.session_id or query_id,
            processing_time_ms=processing_time,
            timestamp=datetime.utcnow().isoformat(),
            knowledge_gaps=knowledge_gaps if knowledge_gaps else None,
            suggestions=suggestions if suggestions else None,
        )

        # Log query in background (optional)
        background_tasks.add_task(
            log_query, query=request.query, response=response, result=result
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        # Log error
        error_msg = str(e)
        error_trace = traceback.format_exc()

        print(f"Query processing error: {error_msg}")
        print(error_trace)

        raise HTTPException(
            status_code=500,
            detail={
                "error": error_msg,
                "error_type": type(e).__name__,
                "query": request.query,
                "timestamp": datetime.utcnow().isoformat(),
            },
        )


@router.post(
    "/query/stream",
    summary="Stream query processing",
    description="Stream the agent workflow execution for real-time updates",
)
async def query_stream(
    request: QueryRequest, graph: PersonalKnowledgeAgentGraph = Depends(get_agent_graph)
):
    """
    Stream query processing for real-time updates.

    Returns Server-Sent Events (SSE) with workflow progress.
    """

    async def event_generator():
        try:
            # Prepare context
            context = request.context or {}
            context["mode"] = request.mode.value

            # Stream workflow execution
            async for event in graph.stream(
                query=request.query,
                user_id=request.user_id,
                session_id=request.session_id,
                context=context,
            ):
                # Format as SSE
                event_data = json.dumps(
                    {
                        "event": "update",
                        "data": str(event),  # Convert to string for safety
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                )
                yield f"data: {event_data}\n\n"

            # Send completion event
            completion_data = json.dumps(
                {"event": "complete", "timestamp": datetime.utcnow().isoformat()}
            )
            yield f"data: {completion_data}\n\n"

        except Exception as e:
            error_data = json.dumps(
                {
                    "event": "error",
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat(),
                }
            )
            yield f"data: {error_data}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    description="Check if the query API is healthy and ready",
)
async def health_check() -> HealthResponse:
    """Health check endpoint"""
    return HealthResponse(
        status="healthy" if _agent_graph is not None else "unhealthy",
        timestamp=datetime.utcnow().isoformat(),
        agents_loaded=_agent_graph is not None,
    )


@router.get(
    "/modes",
    summary="Get available reasoning modes",
    description="List all available reasoning modes with descriptions",
)
async def get_reasoning_modes() -> Dict[str, Any]:
    """Get available reasoning modes"""
    return {
        "modes": [
            {
                "id": "eli5",
                "name": "ELI5 (Explain Like I'm 5)",
                "description": "Simple, accessible explanations suitable for beginners",
            },
            {
                "id": "exam",
                "name": "Exam Mode",
                "description": "Structured, comprehensive answers for exam preparation",
            },
            {
                "id": "research",
                "name": "Research Mode",
                "description": "Detailed, well-cited answers for research purposes",
            },
            {
                "id": "comparison",
                "name": "Comparison Mode",
                "description": "Side-by-side analysis of concepts or alternatives",
            },
        ],
        "default": "research",
    }


# ============================================================================
# Background Tasks
# ============================================================================


async def log_query(query: str, response: QueryResponse, result: AgentState):
    """Log query for analytics (background task)"""
    try:
        # This would typically write to a database or logging service
        log_entry = {
            "query": query,
            "query_id": response.query_id,
            "session_id": response.session_id,
            "confidence": response.confidence,
            "validation_passed": response.validation_passed,
            "sources_count": response.sources_count,
            "processing_time_ms": response.processing_time_ms,
            "timestamp": response.timestamp,
            "workflow_status": result.get("workflow_status"),
            "errors": result.get("errors", []),
        }

        # TODO: Implement actual logging (database, file, etc.)
        print(f"Query logged: {log_entry['query_id']}")

    except Exception as e:
        print(f"Failed to log query: {e}")


# ============================================================================
# Utility Functions
# ============================================================================


def format_error_response(
    error: Exception, query: Optional[str] = None
) -> ErrorResponse:
    """Format error as ErrorResponse"""
    return ErrorResponse(
        error=str(error),
        error_type=type(error).__name__,
        query=query,
        timestamp=datetime.utcnow().isoformat(),
        details={"traceback": traceback.format_exc()},
    )


# ============================================================================
# Example Usage (for testing)
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    from fastapi import FastAPI

    app = FastAPI(
        title="Personal Knowledge Agent API",
        description="Natural language query API with grounded reasoning",
        version="1.0.0",
    )

    app.include_router(router)

    @app.on_event("startup")
    async def startup_event():
        """Initialize agent graph on startup"""

        # Mock memory manager for testing
        class MockMemoryManager:
            async def search(self, query, top_k=5):
                return []

        try:
            await initialize_agent_graph(
                memory_manager=MockMemoryManager(),
                groq_api_key=None,  # Will use env var
            )
        except Exception as e:
            print(f"Warning: Failed to initialize agent graph: {e}")

    print("Starting Personal Knowledge Agent API...")
    print("API Docs available at: http://localhost:8000/docs")

    uvicorn.run(app, host="0.0.0.0", port=8000)
