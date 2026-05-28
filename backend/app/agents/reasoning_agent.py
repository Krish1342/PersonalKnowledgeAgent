from typing import Dict, Any

from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq

from app.agents.state import AgentState
from app.config import settings
from app.utils.response_formatting import detect_query_intent, format_response


BASE_SYSTEM_PROMPT = """You are [User]'s personal knowledge agent. You have access to their notes, PDFs, and documents. When they ask about something, answer from their materials directly and naturally -- like a study partner who has read everything they've saved. Be concise, warm, and format your response to match what they actually asked for. Never say 'based on the provided context'. Just answer."""

FORMAT_SYSTEM_PROMPT = """You are a personal knowledge assistant. Respond naturally and conversationally. Never use robotic preambles. Match your format to what was asked: prose paragraphs for summaries and explanations, direct sentences for definitions, tables only for comparisons with many attributes, numbered lists only when explicitly asked to list things. Write like a knowledgeable friend, not a database."""

RAG_SYSTEM_RULES = """STRICT RULES:
1. ONLY use information from the provided context to answer.
2. If the context doesn't contain enough information, say "I don't have enough information in my knowledge base to answer this."
3. NEVER make up information or use external knowledge.
4. Cite the source when providing information.
5. Be concise and direct."""


# System prompt enforcing RAG-only behavior with formatting guidance
REASONING_SYSTEM_PROMPT = (
    BASE_SYSTEM_PROMPT
    + "\n\n"
    + FORMAT_SYSTEM_PROMPT
    + "\n\n"
    + RAG_SYSTEM_RULES
    + "\n\nCONTEXT:\n{context}\n\n"
    + "Answer the user's question based ONLY on the context above."
)


REASONING_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", REASONING_SYSTEM_PROMPT),
        ("human", "{question}"),
    ]
)


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
        formatted_context = "\n\n".join(
            [
                f"[Source: {c.get('source', 'unknown')}]\n{c.get('content', '')}"
                for c in context
            ]
        )

        # Initialize LLM
        if not settings.GROQ_API_KEY:
            # Fallback: construct answer from context without LLM
            fallback_answer = _construct_fallback_answer(context, question)
            intent = detect_query_intent(question)
            fallback_answer = format_response(fallback_answer, intent)
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
        response = chain.invoke(
            {
                "context": formatted_context,
                "question": question,
            }
        )

        answer = response.content
        intent = detect_query_intent(question)
        answer = format_response(answer, intent)

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

    if len(content) > 500:
        return f"From {source}:\n\n{content[:500]}..."

    return f"From {source}:\n\n{content}"
