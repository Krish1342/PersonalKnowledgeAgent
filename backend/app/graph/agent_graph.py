from typing import Literal, TypeAlias

from langgraph.graph import StateGraph, END

from app.agents.state import AgentState
from app.agents.planner_agent import planner_agent
from app.agents.retrieval_agent import retrieval_agent
from app.agents.reasoning_agent import reasoning_agent
from app.agents.critic_agent import critic_agent
from app.agents.ingestion_agent import ingestion_agent


# Type aliases for compiled graphs
QueryGraph: TypeAlias = StateGraph
IngestionGraph: TypeAlias = StateGraph

# Groundedness threshold for retry logic
GROUNDEDNESS_THRESHOLD = 0.7

# Maximum retry attempts to prevent infinite loops
MAX_RETRIES = 2


def _should_retry(state: AgentState) -> Literal["retrieve", "end"]:
    """
    Conditional edge function: determine if retrieval should be retried.

    Args:
        state: Current agent state.

    Returns:
        "retrieve" if score < threshold and retries remain, else "end".
    """
    score = state.get("score", 1.0)
    retries = state.get("_retry_count", 0)

    if score < GROUNDEDNESS_THRESHOLD and retries < MAX_RETRIES:
        return "retrieve"
    return "end"


def _increment_retry(state: AgentState) -> dict:
    """Helper node to track retry count."""
    current = state.get("_retry_count", 0)
    return {"_retry_count": current + 1}


def create_query_graph() -> StateGraph:
    """
    Create and compile the query workflow graph.

    Workflow: Plan -> Retrieve -> Reason -> Critique -> (conditional retry or End)

    Returns:
        Compiled LangGraph StateGraph.
    """
    # Initialize graph with state schema
    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("plan", planner_agent)
    graph.add_node("retrieve", retrieval_agent)
    graph.add_node("reason", reasoning_agent)
    graph.add_node("critique", critic_agent)
    graph.add_node("increment_retry", _increment_retry)

    # Set entry point
    graph.set_entry_point("plan")

    # Define edges: Plan -> Retrieve -> Reason -> Critique
    graph.add_edge("plan", "retrieve")
    graph.add_edge("retrieve", "reason")
    graph.add_edge("reason", "critique")

    # Conditional edge after critique: retry or end
    graph.add_conditional_edges(
        "critique",
        _should_retry,
        {
            "retrieve": "increment_retry",
            "end": END,
        },
    )

    # After incrementing retry, go back to retrieve
    graph.add_edge("increment_retry", "retrieve")

    # Compile the graph
    compiled = graph.compile()

    return compiled


def create_ingestion_graph() -> StateGraph:
    """
    Create and compile the ingestion workflow graph.

    Workflow: Ingest -> End

    Returns:
        Compiled LangGraph StateGraph.
    """
    # Initialize graph with state schema
    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("ingest", ingestion_agent)

    # Set entry point
    graph.set_entry_point("ingest")

    # Edge to end
    graph.add_edge("ingest", END)

    # Compile the graph
    compiled = graph.compile()

    return compiled


# Pre-compiled graph instances for reuse
_query_graph = None
_ingestion_graph = None


def get_query_graph() -> StateGraph:
    """
    Get the singleton query graph instance.

    Returns:
        Compiled query graph.
    """
    global _query_graph
    if _query_graph is None:
        _query_graph = create_query_graph()
    return _query_graph


def get_ingestion_graph() -> StateGraph:
    """
    Get the singleton ingestion graph instance.

    Returns:
        Compiled ingestion graph.
    """
    global _ingestion_graph
    if _ingestion_graph is None:
        _ingestion_graph = create_ingestion_graph()
    return _ingestion_graph
