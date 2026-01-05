"""
Reasoning Agent for multi-step chain-of-thought reasoning.

This agent provides intelligent reasoning with:
- Multi-step chain-of-thought processing
- Grounded reasoning (uses only retrieved knowledge)
- Multiple reasoning modes (ELI5, Exam, Research, Comparison)
- Source citation and reference tracking
- Step-by-step reasoning traces
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum
import json

from groq import AsyncGroq

from app.config import get_settings
from app.utils.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


class ReasoningMode(Enum):
    """Reasoning mode for different use cases."""

    ELI5 = "eli5"  # Explain Like I'm 5 - simple, analogies
    EXAM = "exam"  # Academic, precise, structured
    RESEARCH = "research"  # In-depth, technical, comprehensive
    COMPARISON = "comparison"  # Compare and contrast concepts


@dataclass
class ReasoningStep:
    """
    A single step in the reasoning chain.

    Attributes:
        step_number: Step number in the chain
        thought: The reasoning thought at this step
        evidence: Evidence from retrieved chunks
        sources: Source IDs used in this step
        conclusion: Interim conclusion from this step
    """

    step_number: int
    thought: str
    evidence: List[str] = field(default_factory=list)
    sources: List[str] = field(default_factory=list)
    conclusion: str = ""


@dataclass
class Citation:
    """
    Source citation.

    Attributes:
        source_id: Unique source identifier
        content: Content snippet
        source_name: Source document name
        confidence: Confidence score
        relevance: How relevant to the answer
    """

    source_id: str
    content: str
    source_name: str
    confidence: str
    relevance: str = "high"


@dataclass
class ReasoningResult:
    """
    Complete reasoning result.

    Attributes:
        answer: Final synthesized answer
        reasoning_steps: Chain of thought steps
        citations: List of cited sources
        mode: Reasoning mode used
        grounded: Whether answer is fully grounded
        confidence: Overall confidence level
        total_steps: Number of reasoning steps
        sources_used: Number of unique sources used
    """

    answer: str
    reasoning_steps: List[ReasoningStep]
    citations: List[Citation]
    mode: ReasoningMode
    grounded: bool
    confidence: str
    total_steps: int
    sources_used: int


class ReasoningAgent:
    """
    Agent for multi-step chain-of-thought reasoning.

    Features:
    - Chain-of-thought reasoning with explicit steps
    - Multiple reasoning modes for different contexts
    - Grounded reasoning using only retrieved knowledge
    - Source citation and reference tracking
    - Confidence assessment
    """

    def __init__(
        self,
        groq_api_key: Optional[str] = None,
        groq_model: Optional[str] = None,
        max_reasoning_steps: int = 5,
    ):
        """
        Initialize reasoning agent.

        Args:
            groq_api_key: Groq API key (uses config default if None)
            groq_model: Groq model to use (uses config default if None)
            max_reasoning_steps: Maximum reasoning steps to perform
        """
        self.api_key = groq_api_key or settings.GROQ_API_KEY
        self.model = groq_model or settings.GROQ_MODEL
        self.max_reasoning_steps = max_reasoning_steps

        # Initialize Groq client if API key available
        self.groq_client = None
        if self.api_key:
            try:
                self.groq_client = AsyncGroq(api_key=self.api_key)
                logger.info("ReasoningAgent initialized with Groq API")
            except Exception as e:
                logger.warning(f"Failed to initialize Groq client: {e}")
        else:
            logger.info("ReasoningAgent initialized without Groq API (fallback mode)")

        logger.info(
            "ReasoningAgent initialized",
            extra={
                "max_reasoning_steps": max_reasoning_steps,
                "has_groq": self.groq_client is not None,
            },
        )

    async def reason(
        self,
        query: str,
        retrieved_chunks: List[Dict[str, Any]],
        mode: ReasoningMode = ReasoningMode.RESEARCH,
        require_grounding: bool = True,
    ) -> ReasoningResult:
        """
        Perform chain-of-thought reasoning on retrieved knowledge.

        Args:
            query: User query to answer
            retrieved_chunks: Retrieved knowledge chunks
            mode: Reasoning mode to use
            require_grounding: Require answer to be grounded in retrieved knowledge

        Returns:
            ReasoningResult with answer and reasoning trace

        Raises:
            ValueError: If query is empty or no chunks provided
        """
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")

        if not retrieved_chunks:
            raise ValueError("No retrieved chunks provided for reasoning")

        logger.info(
            f"Reasoning on query: {query[:100]}...",
            extra={
                "mode": mode.value,
                "num_chunks": len(retrieved_chunks),
            },
        )

        try:
            if self.groq_client:
                result = await self._reason_with_groq(
                    query, retrieved_chunks, mode, require_grounding
                )
            else:
                result = self._reason_fallback(query, retrieved_chunks, mode)

            logger.info(
                f"Reasoning complete: {result.total_steps} steps, {result.sources_used} sources",
                extra={
                    "grounded": result.grounded,
                    "confidence": result.confidence,
                },
            )

            return result

        except Exception as e:
            logger.error(f"Reasoning failed: {e}", exc_info=True)
            raise

    async def _reason_with_groq(
        self,
        query: str,
        retrieved_chunks: List[Dict[str, Any]],
        mode: ReasoningMode,
        require_grounding: bool,
    ) -> ReasoningResult:
        """
        Perform reasoning using Groq API.

        Args:
            query: User query
            retrieved_chunks: Retrieved knowledge
            mode: Reasoning mode
            require_grounding: Require grounding

        Returns:
            ReasoningResult
        """
        try:
            # Prepare context from retrieved chunks
            context = self._prepare_context(retrieved_chunks)

            # Build reasoning prompt
            prompt = self._build_reasoning_prompt(
                query, context, mode, require_grounding
            )

            # Call Groq API
            response = await self.groq_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self._get_system_prompt(mode)},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=3000,
            )

            content = response.choices[0].message.content
            logger.debug(f"Groq response: {content[:200]}...")

            # Parse reasoning response
            result = self._parse_reasoning_response(content, retrieved_chunks, mode)

            return result

        except Exception as e:
            logger.error(f"Groq reasoning error: {e}", exc_info=True)
            return self._reason_fallback(query, retrieved_chunks, mode)

    def _get_system_prompt(self, mode: ReasoningMode) -> str:
        """
        Get system prompt based on reasoning mode.

        Args:
            mode: Reasoning mode

        Returns:
            System prompt string
        """
        base = "You are an expert reasoning assistant. Provide step-by-step chain-of-thought reasoning."

        if mode == ReasoningMode.ELI5:
            return (
                f"{base} Explain concepts in simple terms using analogies and examples "
                "that a 5-year-old could understand. Avoid jargon and technical terms."
            )
        elif mode == ReasoningMode.EXAM:
            return (
                f"{base} Provide precise, academic answers suitable for an exam. "
                "Be structured, accurate, and include key definitions and concepts."
            )
        elif mode == ReasoningMode.RESEARCH:
            return (
                f"{base} Provide in-depth, technical analysis suitable for research. "
                "Include details, nuances, and comprehensive coverage of the topic."
            )
        elif mode == ReasoningMode.COMPARISON:
            return (
                f"{base} Compare and contrast the concepts systematically. "
                "Highlight similarities, differences, pros, cons, and use cases."
            )

        return base

    def _prepare_context(self, retrieved_chunks: List[Dict[str, Any]]) -> str:
        """
        Prepare context string from retrieved chunks.

        Args:
            retrieved_chunks: Retrieved knowledge chunks

        Returns:
            Formatted context string
        """
        context_parts = []

        for i, chunk in enumerate(retrieved_chunks[:10], 1):  # Limit to top 10
            content = chunk.get("content", "")
            source = chunk.get("metadata", {}).get("source", f"source_{i}")
            confidence = chunk.get("confidence", "medium")

            context_parts.append(
                f"[Source {i}: {source} | Confidence: {confidence}]\n{content}\n"
            )

        return "\n".join(context_parts)

    def _build_reasoning_prompt(
        self,
        query: str,
        context: str,
        mode: ReasoningMode,
        require_grounding: bool,
    ) -> str:
        """
        Build reasoning prompt for Groq API.

        Args:
            query: User query
            context: Prepared context
            mode: Reasoning mode
            require_grounding: Require grounding

        Returns:
            Formatted prompt
        """
        grounding_note = (
            "\n\nIMPORTANT: Use ONLY the information provided in the sources above. "
            "Do not add external knowledge. Cite sources for each claim."
            if require_grounding
            else ""
        )

        prompt = f"""Answer the following query using the provided sources.

Query: {query}

Available Sources:
{context}
{grounding_note}

Provide your answer in JSON format:
{{
  "reasoning_steps": [
    {{
      "step_number": 1,
      "thought": "First, I need to understand...",
      "evidence": ["Quote from source..."],
      "sources": ["Source 1"],
      "conclusion": "From this evidence, I conclude..."
    }}
  ],
  "final_answer": "The comprehensive answer to the query...",
  "citations": [
    {{
      "source_id": "Source 1",
      "content": "Relevant quote...",
      "source_name": "document.md",
      "relevance": "high"
    }}
  ],
  "grounded": true,
  "confidence": "high"
}}

Mode: {mode.value}
Max steps: {self.max_reasoning_steps}

Think step by step and cite your sources."""

        return prompt

    def _parse_reasoning_response(
        self,
        content: str,
        retrieved_chunks: List[Dict[str, Any]],
        mode: ReasoningMode,
    ) -> ReasoningResult:
        """
        Parse Groq API response into ReasoningResult.

        Args:
            content: Groq response content
            retrieved_chunks: Original retrieved chunks
            mode: Reasoning mode

        Returns:
            ReasoningResult
        """
        try:
            # Extract JSON from response
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                json_str = content.split("```")[1].split("```")[0].strip()
            else:
                json_str = content.strip()

            data = json.loads(json_str)

            # Parse reasoning steps
            reasoning_steps = []
            for step_data in data.get("reasoning_steps", []):
                step = ReasoningStep(
                    step_number=step_data.get("step_number", len(reasoning_steps) + 1),
                    thought=step_data.get("thought", ""),
                    evidence=step_data.get("evidence", []),
                    sources=step_data.get("sources", []),
                    conclusion=step_data.get("conclusion", ""),
                )
                reasoning_steps.append(step)

            # Parse citations
            citations = []
            for cit_data in data.get("citations", []):
                citation = Citation(
                    source_id=cit_data.get("source_id", ""),
                    content=cit_data.get("content", ""),
                    source_name=cit_data.get("source_name", ""),
                    confidence=cit_data.get("confidence", "medium"),
                    relevance=cit_data.get("relevance", "high"),
                )
                citations.append(citation)

            # Extract answer
            answer = data.get("final_answer", "")
            grounded = data.get("grounded", True)
            confidence = data.get("confidence", "medium")

            # Count unique sources
            all_sources = set()
            for step in reasoning_steps:
                all_sources.update(step.sources)

            result = ReasoningResult(
                answer=answer,
                reasoning_steps=reasoning_steps,
                citations=citations,
                mode=mode,
                grounded=grounded,
                confidence=confidence,
                total_steps=len(reasoning_steps),
                sources_used=len(all_sources),
            )

            return result

        except Exception as e:
            logger.error(f"Failed to parse reasoning response: {e}")
            return self._reason_fallback(
                query="",  # Not used in fallback
                retrieved_chunks=retrieved_chunks,
                mode=mode,
            )

    def _reason_fallback(
        self,
        query: str,
        retrieved_chunks: List[Dict[str, Any]],
        mode: ReasoningMode,
    ) -> ReasoningResult:
        """
        Fallback reasoning without Groq API.

        Args:
            query: User query
            retrieved_chunks: Retrieved chunks
            mode: Reasoning mode

        Returns:
            ReasoningResult with basic reasoning
        """
        logger.info("Using fallback reasoning (no Groq API)")

        # Create basic reasoning steps from top chunks
        reasoning_steps = []
        citations = []
        answer_parts = []

        for i, chunk in enumerate(retrieved_chunks[:3], 1):
            content = chunk.get("content", "")
            source_name = chunk.get("metadata", {}).get("source", f"source_{i}")
            confidence = chunk.get("confidence", "medium")

            # Create reasoning step
            step = ReasoningStep(
                step_number=i,
                thought=f"Analyzing relevant information from {source_name}",
                evidence=[content[:200] + "..."],
                sources=[f"Source {i}"],
                conclusion=f"This source provides relevant information about the topic.",
            )
            reasoning_steps.append(step)

            # Create citation
            citation = Citation(
                source_id=f"Source {i}",
                content=content[:300],
                source_name=source_name,
                confidence=confidence,
                relevance="high" if i == 1 else "medium",
            )
            citations.append(citation)

            # Add to answer
            answer_parts.append(content)

        # Synthesize answer based on mode
        if mode == ReasoningMode.ELI5:
            answer = self._synthesize_eli5(answer_parts)
        elif mode == ReasoningMode.EXAM:
            answer = self._synthesize_exam(answer_parts)
        elif mode == ReasoningMode.COMPARISON:
            answer = self._synthesize_comparison(answer_parts)
        else:
            answer = "\n\n".join(answer_parts[:2])

        result = ReasoningResult(
            answer=answer,
            reasoning_steps=reasoning_steps,
            citations=citations,
            mode=mode,
            grounded=True,
            confidence="medium",
            total_steps=len(reasoning_steps),
            sources_used=len(citations),
        )

        return result

    def _synthesize_eli5(self, parts: List[str]) -> str:
        """Synthesize ELI5 style answer."""
        if not parts:
            return "I don't have enough information to answer this question."

        return (
            f"Let me explain this in simple terms:\n\n"
            f"{parts[0][:300]}...\n\n"
            f"Think of it like this: the information above shows the main concept. "
            f"It's similar to how things work in everyday life."
        )

    def _synthesize_exam(self, parts: List[str]) -> str:
        """Synthesize exam-style answer."""
        if not parts:
            return "Insufficient information to provide a complete answer."

        return (
            f"Based on the available information:\n\n"
            f"{parts[0][:400]}...\n\n"
            f"Key points to remember:\n"
            f"- The primary concept is explained in the sources\n"
            f"- Multiple aspects are covered in the retrieved material\n"
            f"- The information provides a comprehensive overview"
        )

    def _synthesize_comparison(self, parts: List[str]) -> str:
        """Synthesize comparison-style answer."""
        if len(parts) < 2:
            return "Insufficient information for a comprehensive comparison."

        return (
            f"Comparing the concepts:\n\n"
            f"First aspect:\n{parts[0][:300]}...\n\n"
            f"Second aspect:\n{parts[1][:300]}...\n\n"
            f"The key differences and similarities are outlined in the sources above."
        )

    async def eli5(
        self,
        query: str,
        retrieved_chunks: List[Dict[str, Any]],
    ) -> ReasoningResult:
        """
        Reason in ELI5 (Explain Like I'm 5) mode.

        Args:
            query: User query
            retrieved_chunks: Retrieved knowledge

        Returns:
            ReasoningResult with simple explanation
        """
        return await self.reason(query, retrieved_chunks, ReasoningMode.ELI5)

    async def exam(
        self,
        query: str,
        retrieved_chunks: List[Dict[str, Any]],
    ) -> ReasoningResult:
        """
        Reason in Exam mode (academic, precise).

        Args:
            query: User query
            retrieved_chunks: Retrieved knowledge

        Returns:
            ReasoningResult with academic answer
        """
        return await self.reason(query, retrieved_chunks, ReasoningMode.EXAM)

    async def research(
        self,
        query: str,
        retrieved_chunks: List[Dict[str, Any]],
    ) -> ReasoningResult:
        """
        Reason in Research mode (in-depth, technical).

        Args:
            query: User query
            retrieved_chunks: Retrieved knowledge

        Returns:
            ReasoningResult with detailed analysis
        """
        return await self.reason(query, retrieved_chunks, ReasoningMode.RESEARCH)

    async def compare(
        self,
        query: str,
        retrieved_chunks: List[Dict[str, Any]],
    ) -> ReasoningResult:
        """
        Reason in Comparison mode.

        Args:
            query: User query
            retrieved_chunks: Retrieved knowledge

        Returns:
            ReasoningResult with comparison
        """
        return await self.reason(query, retrieved_chunks, ReasoningMode.COMPARISON)

    def format_answer(self, result: ReasoningResult) -> str:
        """
        Format reasoning result as human-readable text.

        Args:
            result: ReasoningResult to format

        Returns:
            Formatted answer string
        """
        output = []

        # Answer
        output.append("ANSWER:")
        output.append(result.answer)
        output.append("")

        # Reasoning trace
        if result.reasoning_steps:
            output.append("REASONING TRACE:")
            for step in result.reasoning_steps:
                output.append(f"\nStep {step.step_number}:")
                output.append(f"  Thought: {step.thought}")
                if step.evidence:
                    output.append(f"  Evidence: {step.evidence[0][:100]}...")
                output.append(f"  Conclusion: {step.conclusion}")
            output.append("")

        # Citations
        if result.citations:
            output.append("SOURCES:")
            for i, citation in enumerate(result.citations, 1):
                output.append(f"\n[{i}] {citation.source_name}")
                output.append(f"    {citation.content[:150]}...")
                output.append(
                    f"    Confidence: {citation.confidence} | Relevance: {citation.relevance}"
                )
            output.append("")

        # Metadata
        output.append("METADATA:")
        output.append(f"  Mode: {result.mode.value}")
        output.append(f"  Confidence: {result.confidence}")
        output.append(f"  Grounded: {result.grounded}")
        output.append(f"  Steps: {result.total_steps}")
        output.append(f"  Sources: {result.sources_used}")

        return "\n".join(output)

    def get_stats(self) -> Dict[str, Any]:
        """
        Get reasoning agent statistics.

        Returns:
            Dictionary with agent statistics
        """
        return {
            "max_reasoning_steps": self.max_reasoning_steps,
            "has_groq": self.groq_client is not None,
            "model": self.model,
            "supported_modes": [mode.value for mode in ReasoningMode],
        }


# Convenience function for quick reasoning
async def quick_reason(
    query: str,
    retrieved_chunks: List[Dict[str, Any]],
    mode: str = "research",
) -> ReasoningResult:
    """
    Quick reasoning without creating agent instance.

    Args:
        query: User query
        retrieved_chunks: Retrieved knowledge
        mode: Reasoning mode (eli5, exam, research, comparison)

    Returns:
        ReasoningResult
    """
    agent = ReasoningAgent()
    mode_enum = ReasoningMode(mode)
    return await agent.reason(query, retrieved_chunks, mode_enum)
