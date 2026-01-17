from typing import Dict, Any, List
import re

from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq

from app.agents.state import AgentState
from app.config import settings


# Critic prompt for groundedness check
CRITIC_SYSTEM_PROMPT = """You are a fact-checking critic. Your job is to verify if an answer is grounded in the provided source context.

EVALUATION CRITERIA:
1. Is every claim in the answer supported by the context?
2. Does the answer contain any information NOT in the context?
3. Are there any hallucinations or fabricated details?

CONTEXT (Source of Truth):
{context}

ANSWER TO EVALUATE:
{answer}

Respond in this EXACT format:
SCORE: [0.0 to 1.0]
GROUNDED: [YES/NO]
CRITIQUE: [Your detailed feedback]

Where:
- 1.0 = Perfectly grounded, all claims supported
- 0.7-0.9 = Mostly grounded, minor unsupported details
- 0.4-0.6 = Partially grounded, some hallucinations
- 0.0-0.3 = Mostly hallucinated, not grounded"""


CRITIC_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", CRITIC_SYSTEM_PROMPT),
    ]
)


def critic_agent(state: AgentState) -> Dict[str, Any]:
    """
    Critic agent node.

    Evaluates if the reasoning agent's answer is grounded in the source context.
    Returns a groundedness score and critique.

    Args:
        state: Current agent state containing 'answer' and 'context'.

    Returns:
        State updates with 'score' and 'critique'.
    """
    answer = state.get("answer")
    context = state.get("context", [])

    # Validate inputs
    if not answer:
        return {
            "score": 0.0,
            "critique": "No answer provided to evaluate.",
        }

    if not context:
        return {
            "score": 0.0,
            "critique": "No context available to verify answer against.",
        }

    try:
        # Format context
        formatted_context = "\n\n".join(
            [f"[{c.get('source', 'unknown')}]: {c.get('content', '')}" for c in context]
        )

        # Check for "no information" answers (these are grounded by design)
        no_info_patterns = [
            r"don't have.*information",
            r"no relevant information",
            r"knowledge base.*empty",
            r"please ingest",
        ]

        for pattern in no_info_patterns:
            if re.search(pattern, answer.lower()):
                return {
                    "score": 1.0,
                    "critique": "Answer correctly indicates lack of information. Fully grounded.",
                }

        # Use LLM for evaluation if available
        if not settings.GROQ_API_KEY:
            # Fallback: simple keyword overlap check
            score, critique = _fallback_groundedness_check(answer, context)
            return {
                "score": score,
                "critique": critique,
            }

        llm = ChatGroq(
            api_key=settings.GROQ_API_KEY,
            model_name=settings.GROQ_MODEL_NAME,
            temperature=0.0,  # Deterministic for evaluation
        )

        # Generate critique
        chain = CRITIC_PROMPT | llm
        response = chain.invoke(
            {
                "context": formatted_context,
                "answer": answer,
            }
        )

        # Parse response
        score, critique = _parse_critic_response(response.content)

        return {
            "score": score,
            "critique": critique,
        }

    except Exception as e:
        return {
            "score": 0.5,  # Uncertain score on error
            "critique": f"Evaluation failed: {str(e)}",
        }


def _parse_critic_response(response: str) -> tuple[float, str]:
    """
    Parse the critic LLM response to extract score and critique.

    Args:
        response: Raw LLM response.

    Returns:
        Tuple of (score, critique).
    """
    score = 0.5  # Default
    critique = response

    # Extract score
    score_match = re.search(r"SCORE:\s*([\d.]+)", response, re.IGNORECASE)
    if score_match:
        try:
            score = float(score_match.group(1))
            score = max(0.0, min(1.0, score))  # Clamp to [0, 1]
        except ValueError:
            pass

    # Extract critique
    critique_match = re.search(r"CRITIQUE:\s*(.+)", response, re.IGNORECASE | re.DOTALL)
    if critique_match:
        critique = critique_match.group(1).strip()

    return score, critique


def _fallback_groundedness_check(
    answer: str,
    context: List[Dict[str, Any]],
) -> tuple[float, str]:
    """
    Simple fallback groundedness check using keyword overlap.

    Args:
        answer: Generated answer.
        context: Retrieved context chunks.

    Returns:
        Tuple of (score, critique).
    """
    # Extract content from context
    context_text = " ".join([c.get("content", "").lower() for c in context])

    # Tokenize (simple word split)
    answer_words = set(re.findall(r"\b\w{4,}\b", answer.lower()))
    context_words = set(re.findall(r"\b\w{4,}\b", context_text))

    if not answer_words:
        return 1.0, "Answer is too short to evaluate."

    # Calculate overlap
    overlap = answer_words & context_words
    overlap_ratio = len(overlap) / len(answer_words)

    # Map to score
    if overlap_ratio >= 0.7:
        score = 0.9
        critique = "High keyword overlap with context. Likely grounded."
    elif overlap_ratio >= 0.4:
        score = 0.6
        critique = "Moderate keyword overlap. Some claims may be unsupported."
    else:
        score = 0.3
        critique = "Low keyword overlap. Answer may contain hallucinations."

    return score, critique
