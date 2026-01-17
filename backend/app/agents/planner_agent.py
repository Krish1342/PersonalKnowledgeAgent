from typing import Dict, Any

from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq

from app.agents.state import AgentState
from app.config import settings


PLANNER_SYSTEM_PROMPT = """You are a query planner for a knowledge base system.

Your job is to analyze the user's question and create a clear, focused search query
that will help retrieve the most relevant information from the knowledge base.

RULES:
1. Extract the core intent of the question
2. Identify key concepts and entities
3. Reformulate into a clear search query
4. Keep the query concise but comprehensive

USER QUESTION: {question}

Respond with ONLY the optimized search query, nothing else."""


PLANNER_PROMPT = ChatPromptTemplate.from_messages([
    ("system", PLANNER_SYSTEM_PROMPT),
])


def planner_agent(state: AgentState) -> Dict[str, Any]:
    """
    Planner agent node.
    
    Analyzes user question and creates an optimized retrieval query.
    
    Args:
        state: Current agent state containing 'messages'.
        
    Returns:
        State updates with 'plan'.
    """
    messages = state.get("messages", [])

    # Extract user question
    question: str = ""
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            question = msg.content
            break

    if not question:
        return {
            "plan": None,
            "error": "No question found in messages",
        }

    try:
        # Use LLM if available
        if settings.GROQ_API_KEY:
            llm = ChatGroq(
                api_key=settings.GROQ_API_KEY,
                model_name=settings.GROQ_MODEL_NAME,
                temperature=0.0,
            )

            chain = PLANNER_PROMPT | llm
            response = chain.invoke({"question": question})
            plan = response.content.strip()
        else:
            # Fallback: use question directly as plan
            plan = question

        return {
            "plan": plan,
            "error": None,
        }

    except Exception as e:
        # Fallback to original question on error
        return {
            "plan": question,
            "error": f"Planning failed, using original query: {str(e)}",
        }
