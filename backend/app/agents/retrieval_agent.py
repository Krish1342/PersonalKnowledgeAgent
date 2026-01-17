from typing import Dict, Any, List

from langchain_core.messages import HumanMessage

from app.agents.state import AgentState
from app.memory.vector_store import VectorStore


def retrieval_agent(state: AgentState) -> Dict[str, Any]:
    """
    Retrieval agent node.

    Queries the vector store based on the plan or latest user message.
    Returns relevant context chunks for the reasoning agent.

    Args:
        state: Current agent state containing 'plan' or 'messages'.

    Returns:
        State updates with 'context' list or 'error'.
    """
    # Determine query: use plan if available, otherwise last user message
    plan = state.get("plan")
    messages = state.get("messages", [])

    query: str = ""

    if plan:
        query = plan
    elif messages:
        # Find the last human message
        for msg in reversed(messages):
            if isinstance(msg, HumanMessage):
                query = msg.content
                break

    if not query:
        return {
            "context": [],
            "error": "No query found for retrieval",
        }

    try:
        # Initialize vector store
        vector_store = VectorStore()

        # Check if store has documents
        if vector_store.count() == 0:
            return {
                "context": [],
                "error": "Knowledge base is empty. Please ingest documents first.",
            }

        # Perform similarity search
        results: List[Dict[str, Any]] = vector_store.similarity_search(
            query=query,
            k=5,  # Top 5 relevant chunks
        )

        # Format context for downstream agents
        context = [
            {
                "id": result["id"],
                "content": result["document"],
                "source": result["metadata"].get("source", "unknown"),
                "chunk_index": result["metadata"].get("chunk_index", 0),
                "relevance_score": (
                    1.0 - result["distance"] if result["distance"] else 1.0
                ),
            }
            for result in results
        ]

        return {
            "context": context,
            "error": None,
        }

    except Exception as e:
        return {
            "context": [],
            "error": f"Retrieval failed: {str(e)}",
        }
