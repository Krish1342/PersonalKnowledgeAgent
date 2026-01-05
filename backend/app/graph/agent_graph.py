"""
LangGraph Agent Workflow for Personal Knowledge Agent

Orchestrates the complete agent workflow:
Observe → Plan → Retrieve → Reason → Critique → Act → Reflect → Update Memory
"""

from typing import TypedDict, Annotated, Sequence, Optional, Dict, List, Any
from typing_extensions import Literal
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from datetime import datetime
import operator
import traceback

# Import agents
from app.agents.planner_agent import (
    PlannerAgent,
    ExecutionPlan,
    SubTask,
    QueryComplexity,
)
from app.agents.retrieval_agent import RetrievalAgent, RetrievalResult, RetrievalFilters
from app.agents.reasoning_agent import ReasoningAgent, ReasoningResult, ReasoningMode
from app.agents.critic_agent import CriticAgent, ValidationResult, ConfidenceLevel
from app.agents.reflection_agent import ReflectionAgent, UserFeedback, FeedbackType
from app.agents.memory_manager_agent import MemoryManagerAgent, StorageRecommendation


# ============================================================================
# State Schema
# ============================================================================


class AgentState(TypedDict, total=False):
    """
    State schema for the agent workflow.

    Fields are accumulated across the workflow, allowing each node to
    read from and write to the state.
    """

    # Input
    query: str
    user_id: Optional[str]
    session_id: Optional[str]
    context: Dict[str, Any]

    # Observation
    observed_at: datetime
    query_metadata: Dict[str, Any]

    # Planning
    execution_plan: Optional[ExecutionPlan]
    current_subtask_index: int
    completed_subtasks: Annotated[List[str], operator.add]

    # Retrieval
    retrieval_results: List[RetrievalResult]
    retrieved_chunks: Annotated[List[Dict], operator.add]
    retrieval_stats: Dict[str, Any]

    # Reasoning
    reasoning_result: Optional[ReasoningResult]
    intermediate_answers: Annotated[List[str], operator.add]
    reasoning_trace: Annotated[List[str], operator.add]

    # Critique
    validation_result: Optional[ValidationResult]
    should_re_reason: bool
    re_reason_count: int

    # Action
    final_answer: Optional[str]
    citations: List[Dict]
    confidence_score: float

    # Reflection
    feedback: Optional[UserFeedback]
    insights: Annotated[List[Dict], operator.add]

    # Memory Update
    storage_decisions: Annotated[List[Dict], operator.add]
    memory_stats: Dict[str, Any]

    # Workflow Control
    current_node: str
    errors: Annotated[List[str], operator.add]
    retry_count: int
    max_retries: int
    workflow_status: str  # "running", "completed", "failed"

    # Timestamps
    started_at: datetime
    completed_at: Optional[datetime]


# ============================================================================
# Agent Graph Builder
# ============================================================================


class PersonalKnowledgeAgentGraph:
    """
    Orchestrates the complete agent workflow using LangGraph.

    Workflow:
    1. Observe: Parse and analyze user query
    2. Plan: Decompose into subtasks with strategies
    3. Retrieve: Get relevant knowledge chunks
    4. Reason: Generate grounded answer
    5. Critique: Validate reasoning
    6. Act: Prepare final response
    7. Reflect: Learn from interaction
    8. Update Memory: Store new knowledge
    """

    def __init__(
        self,
        planner_agent: PlannerAgent,
        retrieval_agent: RetrievalAgent,
        reasoning_agent: ReasoningAgent,
        critic_agent: CriticAgent,
        reflection_agent: ReflectionAgent,
        memory_manager_agent: MemoryManagerAgent,
        max_retries: int = 2,
        enable_checkpointing: bool = True,
    ):
        """
        Initialize the agent graph.

        Args:
            planner_agent: Agent for query planning
            retrieval_agent: Agent for knowledge retrieval
            reasoning_agent: Agent for reasoning
            critic_agent: Agent for validation
            reflection_agent: Agent for learning
            memory_manager_agent: Agent for memory management
            max_retries: Maximum retries for failed nodes
            enable_checkpointing: Enable state persistence
        """
        self.planner = planner_agent
        self.retrieval = retrieval_agent
        self.reasoning = reasoning_agent
        self.critic = critic_agent
        self.reflection = reflection_agent
        self.memory_manager = memory_manager_agent
        self.max_retries = max_retries
        self.enable_checkpointing = enable_checkpointing

        # Build the graph
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow"""
        # Create graph
        workflow = StateGraph(AgentState)

        # Add nodes
        workflow.add_node("observe", self._observe_node)
        workflow.add_node("plan", self._plan_node)
        workflow.add_node("retrieve", self._retrieve_node)
        workflow.add_node("reason", self._reason_node)
        workflow.add_node("critique", self._critique_node)
        workflow.add_node("act", self._act_node)
        workflow.add_node("reflect", self._reflect_node)
        workflow.add_node("update_memory", self._update_memory_node)
        workflow.add_node("handle_error", self._handle_error_node)

        # Set entry point
        workflow.set_entry_point("observe")

        # Add edges
        workflow.add_edge("observe", "plan")
        workflow.add_edge("plan", "retrieve")
        workflow.add_edge("retrieve", "reason")
        workflow.add_edge("reason", "critique")

        # Conditional edge from critique
        workflow.add_conditional_edges(
            "critique",
            self._should_re_reason,
            {"re_reason": "reason", "act": "act", "error": "handle_error"},
        )

        workflow.add_edge("act", "reflect")
        workflow.add_edge("reflect", "update_memory")

        # Conditional edge from update_memory
        workflow.add_conditional_edges(
            "update_memory",
            self._check_completion,
            {"end": END, "error": "handle_error"},
        )

        # Error handling
        workflow.add_conditional_edges(
            "handle_error", self._should_retry, {"retry": "observe", "end": END}
        )

        # Compile graph
        if self.enable_checkpointing:
            checkpointer = MemorySaver()
            return workflow.compile(checkpointer=checkpointer)
        else:
            return workflow.compile()

    # ========================================================================
    # Node Implementations
    # ========================================================================

    async def _observe_node(self, state: AgentState) -> AgentState:
        """
        Observe: Parse and analyze user query.

        Extracts metadata, intent, and context from the query.
        """
        try:
            query = state["query"]

            # Extract query metadata
            metadata = {
                "length": len(query),
                "word_count": len(query.split()),
                "has_question_mark": "?" in query,
                "timestamp": datetime.utcnow().isoformat(),
            }

            return {
                "observed_at": datetime.utcnow(),
                "query_metadata": metadata,
                "current_node": "observe",
                "started_at": state.get("started_at", datetime.utcnow()),
                "workflow_status": "running",
                "retry_count": state.get("retry_count", 0),
                "max_retries": state.get("max_retries", self.max_retries),
                "re_reason_count": state.get("re_reason_count", 0),
                "current_subtask_index": 0,
            }

        except Exception as e:
            error_msg = f"Observation failed: {str(e)}\n{traceback.format_exc()}"
            return {
                "errors": [error_msg],
                "current_node": "observe",
                "workflow_status": "error",
            }

    async def _plan_node(self, state: AgentState) -> AgentState:
        """
        Plan: Decompose query into subtasks with strategies.

        Uses PlannerAgent to create execution plan.
        """
        try:
            query = state["query"]
            context = state.get("context", {})

            # Create execution plan
            execution_plan = await self.planner.create_plan(query, context)

            return {
                "execution_plan": execution_plan,
                "current_node": "plan",
                "completed_subtasks": [],
            }

        except Exception as e:
            error_msg = f"Planning failed: {str(e)}\n{traceback.format_exc()}"
            return {
                "errors": [error_msg],
                "current_node": "plan",
                "workflow_status": "error",
            }

    async def _retrieve_node(self, state: AgentState) -> AgentState:
        """
        Retrieve: Get relevant knowledge chunks.

        Uses RetrievalAgent with strategies from execution plan.
        """
        try:
            query = state["query"]
            execution_plan = state.get("execution_plan")

            all_results = []
            all_chunks = []

            if execution_plan and execution_plan.subtasks:
                # Execute each subtask's retrieval
                for subtask in execution_plan.subtasks:
                    # Build filters from subtask metadata
                    filters = RetrievalFilters(
                        topics=subtask.metadata.get("topics", []),
                        domains=subtask.metadata.get("domains", []),
                    )

                    # Retrieve based on strategy
                    result = await self.retrieval.search(
                        query=subtask.query,
                        top_k=subtask.metadata.get("top_k", 5),
                        filters=filters,
                    )

                    all_results.append(result)

                    # Extract chunks
                    if hasattr(result, "chunks"):
                        all_chunks.extend(result.chunks)
            else:
                # Simple retrieval without plan
                result = await self.retrieval.search(query=query, top_k=10)
                all_results.append(result)
                if hasattr(result, "chunks"):
                    all_chunks.extend(result.chunks)

            # Calculate stats
            stats = {
                "total_results": len(all_results),
                "total_chunks": len(all_chunks),
                "avg_confidence": (
                    sum(
                        r.confidence_score
                        for r in all_results
                        if hasattr(r, "confidence_score")
                    )
                    / len(all_results)
                    if all_results
                    else 0
                ),
            }

            return {
                "retrieval_results": all_results,
                "retrieved_chunks": all_chunks,
                "retrieval_stats": stats,
                "current_node": "retrieve",
            }

        except Exception as e:
            error_msg = f"Retrieval failed: {str(e)}\n{traceback.format_exc()}"
            return {
                "errors": [error_msg],
                "current_node": "retrieve",
                "workflow_status": "error",
            }

    async def _reason_node(self, state: AgentState) -> AgentState:
        """
        Reason: Generate grounded answer using retrieved chunks.

        Uses ReasoningAgent with appropriate mode.
        """
        try:
            query = state["query"]
            chunks = state.get("retrieved_chunks", [])
            context = state.get("context", {})

            # Determine reasoning mode from context or default
            mode_str = context.get("mode", "research")
            mode_map = {
                "eli5": ReasoningMode.ELI5,
                "exam": ReasoningMode.EXAM,
                "research": ReasoningMode.RESEARCH,
                "comparison": ReasoningMode.COMPARISON,
            }
            mode = mode_map.get(mode_str, ReasoningMode.RESEARCH)

            # Reason with retrieved knowledge
            result = await self.reasoning.reason(
                query=query, retrieved_chunks=chunks, mode=mode
            )

            # Extract reasoning trace
            trace = []
            if hasattr(result, "reasoning_steps"):
                trace = [step.content for step in result.reasoning_steps]

            return {
                "reasoning_result": result,
                "reasoning_trace": trace,
                "current_node": "reason",
            }

        except Exception as e:
            error_msg = f"Reasoning failed: {str(e)}\n{traceback.format_exc()}"
            return {
                "errors": [error_msg],
                "current_node": "reason",
                "workflow_status": "error",
            }

    async def _critique_node(self, state: AgentState) -> AgentState:
        """
        Critique: Validate reasoning against sources.

        Uses CriticAgent to check quality and grounding.
        """
        try:
            reasoning_result = state.get("reasoning_result")
            chunks = state.get("retrieved_chunks", [])

            if not reasoning_result:
                return {
                    "errors": ["No reasoning result to critique"],
                    "current_node": "critique",
                    "workflow_status": "error",
                }

            # Extract components for validation
            answer = (
                reasoning_result.answer if hasattr(reasoning_result, "answer") else ""
            )
            citations = []
            if hasattr(reasoning_result, "citations"):
                citations = [
                    {"chunk_id": c.chunk_id, "text": c.text}
                    for c in reasoning_result.citations
                ]

            steps = []
            if hasattr(reasoning_result, "reasoning_steps"):
                steps = [step.content for step in reasoning_result.reasoning_steps]

            # Validate
            validation = await self.critic.validate(
                reasoning_output=answer,
                source_chunks=chunks,
                citations=citations,
                reasoning_steps=steps,
            )

            return {
                "validation_result": validation,
                "should_re_reason": validation.should_re_reason,
                "current_node": "critique",
            }

        except Exception as e:
            error_msg = f"Critique failed: {str(e)}\n{traceback.format_exc()}"
            return {
                "errors": [error_msg],
                "current_node": "critique",
                "workflow_status": "error",
            }

    async def _act_node(self, state: AgentState) -> AgentState:
        """
        Act: Prepare final response for user.

        Formats answer with citations and metadata.
        """
        try:
            reasoning_result = state.get("reasoning_result")
            validation_result = state.get("validation_result")

            if not reasoning_result:
                return {
                    "errors": ["No reasoning result to act on"],
                    "current_node": "act",
                    "workflow_status": "error",
                }

            # Extract final answer
            final_answer = (
                reasoning_result.answer if hasattr(reasoning_result, "answer") else ""
            )

            # Extract citations
            citations = []
            if hasattr(reasoning_result, "citations"):
                citations = [
                    {
                        "chunk_id": c.chunk_id,
                        "text": c.text,
                        "source": getattr(c, "source", "Unknown"),
                    }
                    for c in reasoning_result.citations
                ]

            # Get confidence score
            confidence = 0.0
            if validation_result:
                confidence = validation_result.confidence_score
            elif hasattr(reasoning_result, "confidence"):
                confidence = reasoning_result.confidence

            return {
                "final_answer": final_answer,
                "citations": citations,
                "confidence_score": confidence,
                "current_node": "act",
            }

        except Exception as e:
            error_msg = f"Action failed: {str(e)}\n{traceback.format_exc()}"
            return {
                "errors": [error_msg],
                "current_node": "act",
                "workflow_status": "error",
            }

    async def _reflect_node(self, state: AgentState) -> AgentState:
        """
        Reflect: Learn from interaction.

        Uses ReflectionAgent to analyze performance.
        """
        try:
            # Create feedback object (would come from user in production)
            query = state["query"]
            final_answer = state.get("final_answer", "")
            chunks = state.get("retrieved_chunks", [])
            confidence = state.get("confidence_score", 0.0)
            validation = state.get("validation_result")

            feedback = state.get("feedback")
            if not feedback:
                # Auto-generate feedback based on validation
                feedback_type = (
                    FeedbackType.POSITIVE if confidence >= 70 else FeedbackType.NEUTRAL
                )

                feedback = UserFeedback(
                    feedback_id=f"fb_{datetime.utcnow().timestamp()}",
                    query=query,
                    response=final_answer,
                    feedback_type=feedback_type,
                    rating=None,
                    comment=None,
                    timestamp=datetime.utcnow(),
                    retrieved_chunks=(
                        [c.get("id", "") for c in chunks] if chunks else []
                    ),
                    reasoning_confidence=confidence,
                    validation_passed=validation.is_valid if validation else None,
                )

            # Analyze feedback
            analysis = await self.reflection.analyze_feedback(feedback)

            # Extract insights
            insights = []
            if analysis.get("insights"):
                insights = [
                    {
                        "type": insight.insight_type.value,
                        "title": insight.title,
                        "description": insight.description,
                        "impact": insight.impact_score,
                    }
                    for insight in analysis["insights"]
                ]

            return {
                "feedback": feedback,
                "insights": insights,
                "current_node": "reflect",
            }

        except Exception as e:
            error_msg = f"Reflection failed: {str(e)}\n{traceback.format_exc()}"
            return {
                "errors": [error_msg],
                "current_node": "reflect",
                "workflow_status": "error",
            }

    async def _update_memory_node(self, state: AgentState) -> AgentState:
        """
        Update Memory: Store new knowledge and update scores.

        Uses MemoryManagerAgent to manage knowledge base.
        """
        try:
            query = state["query"]
            final_answer = state.get("final_answer", "")
            validation = state.get("validation_result")
            chunks = state.get("retrieved_chunks", [])

            storage_decisions = []

            # Evaluate if answer should be stored as new knowledge
            if final_answer and len(final_answer) > 50:
                recommendation = await self.memory_manager.evaluate_for_storage(
                    content=final_answer,
                    metadata={
                        "source": "generated_answer",
                        "query": query,
                        "confidence": state.get("confidence_score", 0.0),
                        "validated": validation.is_valid if validation else False,
                    },
                    source="reasoning_agent",
                )

                storage_decisions.append(
                    {
                        "content_type": "generated_answer",
                        "decision": recommendation.decision.value,
                        "reason": recommendation.reason,
                        "quality": recommendation.quality.score,
                    }
                )

            # Update confidence for retrieved chunks
            if validation:
                for chunk in chunks[:5]:  # Update top 5
                    chunk_id = chunk.get("id", "")
                    if chunk_id:
                        new_confidence = await self.memory_manager.update_confidence(
                            chunk_id=chunk_id,
                            validation_passed=validation.is_valid,
                            access_count_delta=1,
                        )

                        storage_decisions.append(
                            {
                                "content_type": "chunk_update",
                                "chunk_id": chunk_id,
                                "new_confidence": new_confidence,
                            }
                        )

            # Get memory stats
            stats = await self.memory_manager.get_memory_stats()
            memory_stats = {
                "total_chunks": stats.total_chunks,
                "avg_confidence": stats.avg_confidence,
                "high_quality_chunks": stats.high_quality_chunks,
            }

            return {
                "storage_decisions": storage_decisions,
                "memory_stats": memory_stats,
                "current_node": "update_memory",
                "workflow_status": "completed",
                "completed_at": datetime.utcnow(),
            }

        except Exception as e:
            error_msg = f"Memory update failed: {str(e)}\n{traceback.format_exc()}"
            return {
                "errors": [error_msg],
                "current_node": "update_memory",
                "workflow_status": "error",
            }

    async def _handle_error_node(self, state: AgentState) -> AgentState:
        """
        Handle errors with graceful degradation.
        """
        errors = state.get("errors", [])
        retry_count = state.get("retry_count", 0)

        return {
            "retry_count": retry_count + 1,
            "current_node": "handle_error",
            "workflow_status": "error_handling",
        }

    # ========================================================================
    # Conditional Edge Functions
    # ========================================================================

    def _should_re_reason(
        self, state: AgentState
    ) -> Literal["re_reason", "act", "error"]:
        """Determine if re-reasoning is needed"""
        # Check for errors first
        if state.get("workflow_status") == "error":
            return "error"

        validation = state.get("validation_result")
        re_reason_count = state.get("re_reason_count", 0)
        max_re_reasons = 2

        # Re-reason if validation suggests and haven't exceeded max attempts
        if (
            validation
            and validation.should_re_reason
            and re_reason_count < max_re_reasons
        ):
            state["re_reason_count"] = re_reason_count + 1
            return "re_reason"

        return "act"

    def _check_completion(self, state: AgentState) -> Literal["end", "error"]:
        """Check if workflow completed successfully"""
        if state.get("workflow_status") == "error":
            return "error"
        return "end"

    def _should_retry(self, state: AgentState) -> Literal["retry", "end"]:
        """Determine if should retry after error"""
        retry_count = state.get("retry_count", 0)
        max_retries = state.get("max_retries", self.max_retries)

        if retry_count < max_retries:
            return "retry"

        # Max retries exceeded, mark as failed
        state["workflow_status"] = "failed"
        return "end"

    # ========================================================================
    # Execution Methods
    # ========================================================================

    async def execute(
        self,
        query: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        context: Optional[Dict] = None,
    ) -> AgentState:
        """
        Execute the complete agent workflow.

        Args:
            query: User query
            user_id: Optional user ID
            session_id: Optional session ID
            context: Optional context dict

        Returns:
            Final agent state with results
        """
        # Initialize state
        initial_state: AgentState = {
            "query": query,
            "user_id": user_id,
            "session_id": session_id,
            "context": context or {},
            "started_at": datetime.utcnow(),
            "workflow_status": "running",
            "retry_count": 0,
            "max_retries": self.max_retries,
            "re_reason_count": 0,
            "current_subtask_index": 0,
            "completed_subtasks": [],
            "retrieved_chunks": [],
            "intermediate_answers": [],
            "reasoning_trace": [],
            "insights": [],
            "storage_decisions": [],
            "errors": [],
            "citations": [],
        }

        # Execute graph
        config = {"configurable": {"thread_id": session_id}} if session_id else {}

        final_state = await self.graph.ainvoke(initial_state, config)

        return final_state

    async def stream(
        self,
        query: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        context: Optional[Dict] = None,
    ):
        """
        Stream the workflow execution for real-time updates.

        Args:
            query: User query
            user_id: Optional user ID
            session_id: Optional session ID
            context: Optional context dict

        Yields:
            State updates as workflow progresses
        """
        # Initialize state
        initial_state: AgentState = {
            "query": query,
            "user_id": user_id,
            "session_id": session_id,
            "context": context or {},
            "started_at": datetime.utcnow(),
            "workflow_status": "running",
            "retry_count": 0,
            "max_retries": self.max_retries,
            "re_reason_count": 0,
            "current_subtask_index": 0,
            "completed_subtasks": [],
            "retrieved_chunks": [],
            "intermediate_answers": [],
            "reasoning_trace": [],
            "insights": [],
            "storage_decisions": [],
            "errors": [],
            "citations": [],
        }

        # Stream graph execution
        config = {"configurable": {"thread_id": session_id}} if session_id else {}

        async for event in self.graph.astream(initial_state, config):
            yield event

    def visualize(self, output_path: str = "agent_graph.png"):
        """
        Visualize the workflow graph.

        Args:
            output_path: Path to save visualization
        """
        try:
            from IPython.display import Image

            img = Image(self.graph.get_graph().draw_mermaid_png())

            with open(output_path, "wb") as f:
                f.write(img.data)

            print(f"Graph visualization saved to {output_path}")
        except Exception as e:
            print(f"Visualization failed: {e}")
            print("Make sure you have graphviz installed: pip install graphviz")


# ============================================================================
# Convenience Functions
# ============================================================================


async def create_agent_graph(
    memory_manager,
    groq_api_key: Optional[str] = None,
    enable_checkpointing: bool = True,
) -> PersonalKnowledgeAgentGraph:
    """
    Create a fully configured agent graph.

    Args:
        memory_manager: Storage MemoryManager instance
        groq_api_key: Groq API key for all agents
        enable_checkpointing: Enable state persistence

    Returns:
        Configured PersonalKnowledgeAgentGraph
    """
    # Initialize all agents
    planner = PlannerAgent(groq_api_key=groq_api_key)
    retrieval = RetrievalAgent(memory_manager=memory_manager)
    reasoning = ReasoningAgent(groq_api_key=groq_api_key)
    critic = CriticAgent(groq_api_key=groq_api_key)
    reflection = ReflectionAgent(groq_api_key=groq_api_key)
    memory_manager_agent = MemoryManagerAgent(
        memory_manager=memory_manager, groq_api_key=groq_api_key
    )

    # Create graph
    graph = PersonalKnowledgeAgentGraph(
        planner_agent=planner,
        retrieval_agent=retrieval,
        reasoning_agent=reasoning,
        critic_agent=critic,
        reflection_agent=reflection,
        memory_manager_agent=memory_manager_agent,
        enable_checkpointing=enable_checkpointing,
    )

    return graph


# Example usage
if __name__ == "__main__":
    import asyncio

    async def main():
        # Mock memory manager
        class MockMemoryManager:
            async def search(self, query, top_k=5):
                return []

        # Create graph
        graph = await create_agent_graph(
            memory_manager=MockMemoryManager(), enable_checkpointing=True
        )

        # Execute workflow
        query = "What are the key principles of machine learning?"

        print("=" * 60)
        print(f"EXECUTING WORKFLOW: {query}")
        print("=" * 60)

        result = await graph.execute(
            query=query, session_id="test_session_1", context={"mode": "research"}
        )

        # Print results
        print("\n" + "=" * 60)
        print("WORKFLOW RESULTS")
        print("=" * 60)
        print(f"Status: {result.get('workflow_status')}")
        print(f"Started: {result.get('started_at')}")
        print(f"Completed: {result.get('completed_at')}")

        if result.get("errors"):
            print(f"\nErrors: {len(result['errors'])}")
            for error in result["errors"]:
                print(f"  - {error}")

        print(f"\nRetrieval Stats:")
        stats = result.get("retrieval_stats", {})
        for key, value in stats.items():
            print(f"  {key}: {value}")

        if result.get("final_answer"):
            print(f"\nFinal Answer:")
            print(f"  {result['final_answer'][:200]}...")
            print(f"\nConfidence: {result.get('confidence_score', 0):.1f}%")

        if result.get("citations"):
            print(f"\nCitations: {len(result['citations'])}")

        if result.get("insights"):
            print(f"\nInsights Learned: {len(result['insights'])}")
            for insight in result["insights"]:
                print(f"  - {insight.get('title')}")

        # Visualize graph
        try:
            graph.visualize("workflow_graph.png")
        except Exception as e:
            print(f"\nVisualization skipped: {e}")

    asyncio.run(main())
