from typing import Optional, List, Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage

from app.graph.agent_graph import get_query_graph


router = APIRouter(prefix="/query", tags=["query"])


class QueryRequest(BaseModel):
    """Request body for query endpoint."""

    question: str = Field(
        ...,
        min_length=1,
        description="The question to ask the knowledge base.",
    )


class ContextItem(BaseModel):
    """A single context item from retrieval."""

    content: str
    source: str
    relevance_score: Optional[float] = None


class QueryResponse(BaseModel):
    """Response body for query endpoint."""

    answer: str
    context: List[ContextItem]
    score: Optional[float] = Field(
        default=None,
        description="Groundedness score (0.0-1.0)",
    )
    critique: Optional[str] = Field(
        default=None,
        description="Critic feedback on answer quality",
    )


@router.post(
    "",
    response_model=QueryResponse,
    status_code=status.HTTP_200_OK,
    summary="Query the knowledge base",
    description="Ask a question and get a RAG-grounded answer from the knowledge base.",
)
async def query_knowledge_base(request: QueryRequest) -> QueryResponse:
    """
    Query the knowledge base with a question.

    Triggers the full LangGraph workflow:
    1. Plan: Optimize the query for retrieval
    2. Retrieve: Find relevant context from vector store
    3. Reason: Synthesize answer from context (RAG-only)
    4. Critique: Verify groundedness, retry if score < 0.7
    """
    try:
        # Get the query graph
        graph = get_query_graph()

        # Prepare initial state with user message
        initial_state = {
            "messages": [HumanMessage(content=request.question)],
            "context": [],
            "plan": None,
            "critique": None,
            "score": None,
            "answer": None,
        }

        # Execute the query workflow
        result = graph.invoke(initial_state)

        # Extract results
        answer = result.get("answer")
        context = result.get("context", [])
        score = result.get("score")
        critique = result.get("critique")
        error = result.get("error")

        # Handle missing answer
        if not answer:
            if error:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=error,
                )
            answer = (
                "Unable to generate an answer. Please try rephrasing your question."
            )

        # Format context items
        context_items = [
            ContextItem(
                content=c.get("content", ""),
                source=c.get("source", "unknown"),
                relevance_score=c.get("relevance_score"),
            )
            for c in context
        ]

        return QueryResponse(
            answer=answer,
            context=context_items,
            score=score,
            critique=critique,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Query failed: {str(e)}",
        )
