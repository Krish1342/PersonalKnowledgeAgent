from typing import Dict, Any

from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq

from app.agents.state import AgentState
from app.config import settings


# System prompt enforcing RAG-only behavior
REASONING_SYSTEM_PROMPT = """You are a knowledge assistant that answers questions based ONLY on the provided context.

STRICT RULES:
1. ONLY use information from the provided context to answer.
2. If the context doesn't contain enough information, say "I don't have enough information in my knowledge base to answer this."
3. NEVER make up information or use external knowledge.
4. Cite the source when providing information.
5. Be concise and direct.

CONTEXT:
{context}

Answer the user's question based ONLY on the context above."""


REASONING_PROMPT = ChatPromptTemplate.from_messages([
    ("system", REASONING_SYSTEM_PROMPT),
    ("human", "{question}"),
])


def reasoning_agent(state: AgentState) -> Dict[str, Any]:
    """
    Reasoning agent node.
    
    Uses LLM to synthesize an answer based ONLY on retrieved context.
    Enforces RAG-only behavior (no hallucination).
    
    Args:
        state: Current agent state containing 'context' and 'messages'.
        
    Returns:
        State updates with 'answer' and updated 'messages'.
    """
    context = state.get("context", [])
    messages = state.get("messages", [])

    # Extract user question from messages
    question: str = ""
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            question = msg.content
            break

    if not question:
        return {
            "answer": None,
            "error": "No question found in messages",
        }

    # Handle empty context
    if not context:
        no_context_answer = (
            "I don't have any relevant information in my knowledge base to answer this question. "
            "Please ingest relevant documents first."
        )
        return {
            "answer": no_context_answer,
            "messages": messages + [AIMessage(content=no_context_answer)],
            "error": None,
        }

    try:
        # Format context for prompt
        formatted_context = "\n\n".join([
            f"[Source: {c.get('source', 'unknown')}]\n{c.get('content', '')}"
            for c in context
        ])

        # Initialize LLM
        if not settings.GROQ_API_KEY:
            # Fallback: construct answer from context without LLM
            fallback_answer = _construct_fallback_answer(context, question)
            return {
                "answer": fallback_answer,
                "messages": messages + [AIMessage(content=fallback_answer)],
                "error": "GROQ_API_KEY not configured, using fallback response",
            }

        llm = ChatGroq(
            api_key=settings.GROQ_API_KEY,
            model_name=settings.GROQ_MODEL_NAME,
            temperature=0.1,  # Low temperature for factual responses
        )

        # Generate response
        chain = REASONING_PROMPT | llm
        response = chain.invoke({
            "context": formatted_context,
            "question": question,
        })

        answer = response.content

        return {
            "answer": answer,
            "messages": messages + [AIMessage(content=answer)],
            "error": None,
        }

    except Exception as e:
        error_msg = f"Reasoning failed: {str(e)}"
        return {
            "answer": None,
            "messages": messages,
            "error": error_msg,
        }


def _construct_fallback_answer(context: list, question: str) -> str:
    """
    Construct a basic answer from context when LLM is unavailable.
    
    Args:
        context: Retrieved context chunks.
        question: User question.
        
    Returns:
        Fallback answer string.
    """
    if not context:
        return "No relevant information found in the knowledge base."

    # Return top context with source attribution
    top_context = context[0]
    content = top_context.get("content", "")
    source = top_context.get("source", "unknown")

    return (
        f"Based on my knowledge base (source: {source}):\n\n"
        f"{content[:500]}..."
        if len(content) > 500
        else f"Based on my knowledge base (source: {source}):\n\n{content}"
    )
