"""
Critic Agent for Personal Knowledge Agent

Validates reasoning outputs against source documents, detects unsupported claims,
assigns confidence scores, and determines when re-reasoning is needed.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Set
from datetime import datetime
from enum import Enum
import re
from groq import AsyncGroq
import os


class ConfidenceLevel(Enum):
    """Confidence levels for validation"""

    VERY_HIGH = "very_high"  # 90-100% claims supported
    HIGH = "high"  # 75-89% claims supported
    MEDIUM = "medium"  # 60-74% claims supported
    LOW = "low"  # 40-59% claims supported
    VERY_LOW = "very_low"  # <40% claims supported


class ClaimStatus(Enum):
    """Status of individual claims"""

    SUPPORTED = "supported"  # Claim is supported by sources
    PARTIALLY_SUPPORTED = "partially_supported"  # Claim is partially supported
    UNSUPPORTED = "unsupported"  # Claim has no support in sources
    CONTRADICTED = "contradicted"  # Claim contradicts sources


@dataclass
class Claim:
    """Represents an extracted claim from reasoning output"""

    text: str
    status: ClaimStatus
    supporting_chunks: List[str] = field(default_factory=list)
    citation_ids: List[str] = field(default_factory=list)
    confidence: float = 0.0
    explanation: str = ""


@dataclass
class ValidationIssue:
    """Represents a validation issue found during criticism"""

    severity: str  # "critical", "major", "minor"
    issue_type: str  # "unsupported_claim", "missing_citation", "weak_evidence", etc.
    description: str
    claim: Optional[str] = None
    suggestion: str = ""


@dataclass
class ValidationResult:
    """Result of validation process"""

    is_valid: bool
    confidence: ConfidenceLevel
    confidence_score: float  # 0-100

    # Claims analysis
    total_claims: int
    supported_claims: int
    partially_supported_claims: int
    unsupported_claims: int
    contradicted_claims: int

    # Detailed findings
    claims: List[Claim] = field(default_factory=list)
    issues: List[ValidationIssue] = field(default_factory=list)

    # Re-reasoning recommendation
    should_re_reason: bool = False
    re_reasoning_reason: str = ""
    improvement_suggestions: List[str] = field(default_factory=list)

    # Metadata
    validation_timestamp: datetime = field(default_factory=datetime.utcnow)
    validation_duration_ms: float = 0.0

    def get_support_percentage(self) -> float:
        """Get percentage of supported claims"""
        if self.total_claims == 0:
            return 0.0
        return (self.supported_claims / self.total_claims) * 100

    def get_summary(self) -> str:
        """Get human-readable validation summary"""
        return (
            f"Validation Result: {'PASS' if self.is_valid else 'FAIL'}\n"
            f"Confidence: {self.confidence.value} ({self.confidence_score:.1f}%)\n"
            f"Claims: {self.supported_claims}/{self.total_claims} supported "
            f"({self.get_support_percentage():.1f}%)\n"
            f"Issues: {len(self.issues)} found "
            f"({sum(1 for i in self.issues if i.severity == 'critical')} critical)\n"
            f"Re-reasoning needed: {'Yes' if self.should_re_reason else 'No'}"
        )


class CriticAgent:
    """
    Agent that validates reasoning outputs against source documents.

    Responsibilities:
    - Extract claims from reasoning output
    - Validate each claim against source chunks
    - Detect unsupported claims and hallucinations
    - Assign confidence scores
    - Determine if re-reasoning is needed
    - Provide improvement suggestions
    """

    def __init__(
        self,
        groq_api_key: Optional[str] = None,
        model: str = "llama-3.3-70b-versatile",
        re_reason_threshold: float = 60.0,
        use_llm_validation: bool = True,
    ):
        """
        Initialize Critic Agent.

        Args:
            groq_api_key: Groq API key (uses GROQ_API_KEY env var if not provided)
            model: Groq model to use for intelligent validation
            re_reason_threshold: Confidence threshold below which re-reasoning is recommended
            use_llm_validation: Whether to use LLM for claim validation (fallback to heuristics)
        """
        self.groq_api_key = groq_api_key or os.getenv("GROQ_API_KEY")
        self.model = model
        self.re_reason_threshold = re_reason_threshold
        self.use_llm_validation = use_llm_validation

        if self.groq_api_key and self.use_llm_validation:
            self.client = AsyncGroq(api_key=self.groq_api_key)
        else:
            self.client = None

    async def validate(
        self,
        reasoning_output: str,
        source_chunks: List[Dict],
        citations: Optional[List[Dict]] = None,
        reasoning_steps: Optional[List[str]] = None,
    ) -> ValidationResult:
        """
        Validate reasoning output against source documents.

        Args:
            reasoning_output: Final answer/reasoning to validate
            source_chunks: Source chunks used for reasoning
            citations: List of citations (if available)
            reasoning_steps: Intermediate reasoning steps (if available)

        Returns:
            ValidationResult with findings and recommendations
        """
        start_time = datetime.utcnow()

        # Extract claims from reasoning output
        claims = await self._extract_claims(reasoning_output, reasoning_steps)

        # Validate each claim against sources
        validated_claims = await self._validate_claims(claims, source_chunks, citations)

        # Calculate confidence score
        confidence_score, confidence_level = self._calculate_confidence(
            validated_claims
        )

        # Detect validation issues
        issues = self._detect_issues(validated_claims, citations, source_chunks)

        # Determine if re-reasoning is needed
        should_re_reason, re_reasoning_reason = self._should_re_reason(
            confidence_score, validated_claims, issues
        )

        # Generate improvement suggestions
        suggestions = self._generate_suggestions(validated_claims, issues)

        # Calculate statistics
        supported = sum(
            1 for c in validated_claims if c.status == ClaimStatus.SUPPORTED
        )
        partially_supported = sum(
            1 for c in validated_claims if c.status == ClaimStatus.PARTIALLY_SUPPORTED
        )
        unsupported = sum(
            1 for c in validated_claims if c.status == ClaimStatus.UNSUPPORTED
        )
        contradicted = sum(
            1 for c in validated_claims if c.status == ClaimStatus.CONTRADICTED
        )

        duration = (datetime.utcnow() - start_time).total_seconds() * 1000

        return ValidationResult(
            is_valid=confidence_score >= self.re_reason_threshold,
            confidence=confidence_level,
            confidence_score=confidence_score,
            total_claims=len(validated_claims),
            supported_claims=supported,
            partially_supported_claims=partially_supported,
            unsupported_claims=unsupported,
            contradicted_claims=contradicted,
            claims=validated_claims,
            issues=issues,
            should_re_reason=should_re_reason,
            re_reasoning_reason=re_reasoning_reason,
            improvement_suggestions=suggestions,
            validation_duration_ms=duration,
        )

    async def _extract_claims(
        self, reasoning_output: str, reasoning_steps: Optional[List[str]] = None
    ) -> List[str]:
        """Extract individual claims from reasoning output"""
        if self.client and self.use_llm_validation:
            try:
                return await self._extract_claims_with_llm(
                    reasoning_output, reasoning_steps
                )
            except Exception as e:
                print(f"LLM claim extraction failed: {e}, using fallback")

        return self._extract_claims_heuristic(reasoning_output, reasoning_steps)

    async def _extract_claims_with_llm(
        self, reasoning_output: str, reasoning_steps: Optional[List[str]] = None
    ) -> List[str]:
        """Extract claims using LLM"""
        steps_text = ""
        if reasoning_steps:
            steps_text = "\n\nReasoning Steps:\n" + "\n".join(
                f"{i+1}. {step}" for i, step in enumerate(reasoning_steps)
            )

        prompt = f"""Extract all factual claims from the following reasoning output. 
A claim is a specific statement that can be verified against source documents.

Reasoning Output:
{reasoning_output}
{steps_text}

Return ONLY a JSON array of claim strings, one per line. Example:
["The sky is blue", "Water boils at 100°C", "Python was created in 1991"]

Claims:"""

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=1000,
        )

        content = response.choices[0].message.content.strip()

        # Parse JSON array
        import json

        try:
            claims = json.loads(content)
            return claims if isinstance(claims, list) else []
        except json.JSONDecodeError:
            # Fallback: extract lines that look like claims
            lines = [line.strip().strip("\"',-") for line in content.split("\n")]
            return [line for line in lines if line and len(line) > 10]

    def _extract_claims_heuristic(
        self, reasoning_output: str, reasoning_steps: Optional[List[str]] = None
    ) -> List[str]:
        """Extract claims using heuristic rules"""
        claims = []

        # Split into sentences
        sentences = re.split(r"[.!?]+", reasoning_output)

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            # Skip meta-statements
            skip_patterns = [
                r"^(therefore|thus|hence|in conclusion|to summarize)",
                r"^(first|second|third|finally|lastly)",
                r"^(let me|let\'s|we can|we should)",
                r"^(based on|according to|the sources)",
            ]

            if any(re.match(pattern, sentence.lower()) for pattern in skip_patterns):
                continue

            # Must be substantial (more than 5 words)
            if len(sentence.split()) < 5:
                continue

            claims.append(sentence)

        # Also extract from reasoning steps if provided
        if reasoning_steps:
            for step in reasoning_steps:
                step_sentences = re.split(r"[.!?]+", step)
                for sentence in step_sentences:
                    sentence = sentence.strip()
                    if sentence and len(sentence.split()) >= 5:
                        if sentence not in claims:
                            claims.append(sentence)

        return claims

    async def _validate_claims(
        self,
        claims: List[str],
        source_chunks: List[Dict],
        citations: Optional[List[Dict]] = None,
    ) -> List[Claim]:
        """Validate each claim against source chunks"""
        validated_claims = []

        for claim_text in claims:
            if self.client and self.use_llm_validation:
                try:
                    claim = await self._validate_claim_with_llm(
                        claim_text, source_chunks, citations
                    )
                    validated_claims.append(claim)
                    continue
                except Exception as e:
                    print(f"LLM claim validation failed: {e}, using fallback")

            # Fallback: heuristic validation
            claim = self._validate_claim_heuristic(claim_text, source_chunks, citations)
            validated_claims.append(claim)

        return validated_claims

    async def _validate_claim_with_llm(
        self,
        claim: str,
        source_chunks: List[Dict],
        citations: Optional[List[Dict]] = None,
    ) -> Claim:
        """Validate a single claim using LLM"""
        # Prepare source context
        sources_text = "\n\n".join(
            [
                f"Source {i+1} (ID: {chunk.get('id', 'N/A')}):\n{chunk.get('content', chunk.get('text', ''))}"
                for i, chunk in enumerate(source_chunks[:10])  # Limit to top 10
            ]
        )

        prompt = f"""Validate the following claim against the provided source documents.

Claim: "{claim}"

Source Documents:
{sources_text}

Determine:
1. Status: supported/partially_supported/unsupported/contradicted
2. Confidence: 0-100 (how confident you are in the status)
3. Supporting source IDs (if any)
4. Brief explanation

Return ONLY a JSON object in this exact format:
{{
    "status": "supported",
    "confidence": 85,
    "supporting_source_ids": ["source_1", "source_3"],
    "explanation": "Brief explanation here"
}}

Response:"""

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=300,
        )

        content = response.choices[0].message.content.strip()

        # Parse response
        import json

        try:
            result = json.loads(content)
            status_map = {
                "supported": ClaimStatus.SUPPORTED,
                "partially_supported": ClaimStatus.PARTIALLY_SUPPORTED,
                "unsupported": ClaimStatus.UNSUPPORTED,
                "contradicted": ClaimStatus.CONTRADICTED,
            }

            status = status_map.get(
                result.get("status", "unsupported"), ClaimStatus.UNSUPPORTED
            )
            confidence = float(result.get("confidence", 0))
            supporting_ids = result.get("supporting_source_ids", [])
            explanation = result.get("explanation", "")

            # Find supporting chunks
            supporting_chunks = [
                chunk.get("content", chunk.get("text", ""))
                for chunk in source_chunks
                if chunk.get("id") in supporting_ids
            ]

            return Claim(
                text=claim,
                status=status,
                supporting_chunks=supporting_chunks,
                citation_ids=supporting_ids,
                confidence=confidence,
                explanation=explanation,
            )
        except Exception as e:
            print(f"Failed to parse LLM validation response: {e}")
            return self._validate_claim_heuristic(claim, source_chunks, citations)

    def _validate_claim_heuristic(
        self,
        claim: str,
        source_chunks: List[Dict],
        citations: Optional[List[Dict]] = None,
    ) -> Claim:
        """Validate a single claim using heuristic keyword matching"""
        claim_lower = claim.lower()
        claim_keywords = set(re.findall(r"\b\w+\b", claim_lower))

        # Remove common stop words
        stop_words = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
            "is",
            "are",
            "was",
            "were",
            "be",
            "been",
            "being",
            "have",
            "has",
            "had",
        }
        claim_keywords = claim_keywords - stop_words

        best_matches = []

        for chunk in source_chunks:
            content = chunk.get("content", chunk.get("text", "")).lower()
            content_keywords = set(re.findall(r"\b\w+\b", content))

            # Calculate keyword overlap
            overlap = claim_keywords & content_keywords
            if overlap:
                overlap_ratio = (
                    len(overlap) / len(claim_keywords) if claim_keywords else 0
                )

                if overlap_ratio > 0.3:  # At least 30% overlap
                    best_matches.append(
                        {
                            "chunk": chunk,
                            "overlap_ratio": overlap_ratio,
                            "content": chunk.get("content", chunk.get("text", "")),
                        }
                    )

        # Sort by overlap
        best_matches.sort(key=lambda x: x["overlap_ratio"], reverse=True)

        # Determine status based on matches
        if not best_matches:
            status = ClaimStatus.UNSUPPORTED
            confidence = 20.0
            explanation = "No supporting evidence found in sources"
        elif best_matches[0]["overlap_ratio"] >= 0.7:
            status = ClaimStatus.SUPPORTED
            confidence = min(90.0, best_matches[0]["overlap_ratio"] * 100)
            explanation = f"Strong keyword overlap ({best_matches[0]['overlap_ratio']:.1%}) with sources"
        elif best_matches[0]["overlap_ratio"] >= 0.4:
            status = ClaimStatus.PARTIALLY_SUPPORTED
            confidence = min(70.0, best_matches[0]["overlap_ratio"] * 100)
            explanation = f"Partial keyword overlap ({best_matches[0]['overlap_ratio']:.1%}) with sources"
        else:
            status = ClaimStatus.UNSUPPORTED
            confidence = 40.0
            explanation = f"Weak keyword overlap ({best_matches[0]['overlap_ratio']:.1%}) with sources"

        supporting_chunks = [m["content"] for m in best_matches[:3]]
        citation_ids = [m["chunk"].get("id", "") for m in best_matches[:3]]

        return Claim(
            text=claim,
            status=status,
            supporting_chunks=supporting_chunks,
            citation_ids=citation_ids,
            confidence=confidence,
            explanation=explanation,
        )

    def _calculate_confidence(
        self, validated_claims: List[Claim]
    ) -> Tuple[float, ConfidenceLevel]:
        """Calculate overall confidence score and level"""
        if not validated_claims:
            return 0.0, ConfidenceLevel.VERY_LOW

        # Weight by claim status
        status_weights = {
            ClaimStatus.SUPPORTED: 1.0,
            ClaimStatus.PARTIALLY_SUPPORTED: 0.6,
            ClaimStatus.UNSUPPORTED: 0.0,
            ClaimStatus.CONTRADICTED: -0.5,
        }

        # Calculate weighted score
        weighted_sum = sum(
            status_weights[claim.status] * (claim.confidence / 100)
            for claim in validated_claims
        )

        # Normalize to 0-100
        max_possible = len(validated_claims)
        confidence_score = max(0, min(100, (weighted_sum / max_possible) * 100))

        # Determine confidence level
        if confidence_score >= 90:
            level = ConfidenceLevel.VERY_HIGH
        elif confidence_score >= 75:
            level = ConfidenceLevel.HIGH
        elif confidence_score >= 60:
            level = ConfidenceLevel.MEDIUM
        elif confidence_score >= 40:
            level = ConfidenceLevel.LOW
        else:
            level = ConfidenceLevel.VERY_LOW

        return confidence_score, level

    def _detect_issues(
        self,
        validated_claims: List[Claim],
        citations: Optional[List[Dict]],
        source_chunks: List[Dict],
    ) -> List[ValidationIssue]:
        """Detect validation issues"""
        issues = []

        # Check for unsupported claims
        for claim in validated_claims:
            if claim.status == ClaimStatus.UNSUPPORTED:
                issues.append(
                    ValidationIssue(
                        severity="major",
                        issue_type="unsupported_claim",
                        description="Claim has no supporting evidence in sources",
                        claim=claim.text,
                        suggestion="Remove claim or provide supporting sources",
                    )
                )
            elif claim.status == ClaimStatus.CONTRADICTED:
                issues.append(
                    ValidationIssue(
                        severity="critical",
                        issue_type="contradicted_claim",
                        description="Claim contradicts source documents",
                        claim=claim.text,
                        suggestion="Revise claim to align with sources or remove it",
                    )
                )
            elif (
                claim.status == ClaimStatus.PARTIALLY_SUPPORTED
                and claim.confidence < 50
            ):
                issues.append(
                    ValidationIssue(
                        severity="minor",
                        issue_type="weak_evidence",
                        description="Claim has weak supporting evidence",
                        claim=claim.text,
                        suggestion="Strengthen claim with more specific evidence or qualify it",
                    )
                )

        # Check for missing citations
        unsupported_count = sum(
            1
            for c in validated_claims
            if c.status in [ClaimStatus.UNSUPPORTED, ClaimStatus.CONTRADICTED]
        )

        if unsupported_count > len(validated_claims) * 0.3:
            issues.append(
                ValidationIssue(
                    severity="critical",
                    issue_type="excessive_unsupported_claims",
                    description=f"{unsupported_count}/{len(validated_claims)} claims are unsupported",
                    suggestion="Re-reason with more focus on grounding in sources",
                )
            )

        # Check citation coverage
        if citations is not None:
            cited_sources = set(
                c.get("chunk_id") or c.get("id") for c in citations if c
            )
            available_sources = set(c.get("id") for c in source_chunks if c.get("id"))

            if len(cited_sources) < len(available_sources) * 0.3:
                issues.append(
                    ValidationIssue(
                        severity="minor",
                        issue_type="low_citation_coverage",
                        description=f"Only {len(cited_sources)}/{len(available_sources)} sources cited",
                        suggestion="Consider citing more relevant sources",
                    )
                )

        return issues

    def _should_re_reason(
        self,
        confidence_score: float,
        validated_claims: List[Claim],
        issues: List[ValidationIssue],
    ) -> Tuple[bool, str]:
        """Determine if re-reasoning is needed"""
        reasons = []

        # Check confidence threshold
        if confidence_score < self.re_reason_threshold:
            reasons.append(
                f"Confidence score ({confidence_score:.1f}%) below threshold ({self.re_reason_threshold}%)"
            )

        # Check for critical issues
        critical_issues = [i for i in issues if i.severity == "critical"]
        if critical_issues:
            reasons.append(
                f"{len(critical_issues)} critical issues found: "
                + ", ".join(i.issue_type for i in critical_issues)
            )

        # Check for contradicted claims
        contradicted = sum(
            1 for c in validated_claims if c.status == ClaimStatus.CONTRADICTED
        )
        if contradicted > 0:
            reasons.append(f"{contradicted} claims contradict source documents")

        # Check unsupported ratio
        unsupported_ratio = (
            sum(1 for c in validated_claims if c.status == ClaimStatus.UNSUPPORTED)
            / len(validated_claims)
            if validated_claims
            else 0
        )

        if unsupported_ratio > 0.4:
            reasons.append(f"{unsupported_ratio:.1%} of claims are unsupported")

        should_re_reason = len(reasons) > 0
        re_reasoning_reason = "; ".join(reasons) if reasons else ""

        return should_re_reason, re_reasoning_reason

    def _generate_suggestions(
        self, validated_claims: List[Claim], issues: List[ValidationIssue]
    ) -> List[str]:
        """Generate improvement suggestions"""
        suggestions = []

        # Add issue-specific suggestions
        for issue in issues:
            if issue.suggestion and issue.suggestion not in suggestions:
                suggestions.append(issue.suggestion)

        # Add general suggestions based on claim analysis
        unsupported_claims = [
            c
            for c in validated_claims
            if c.status in [ClaimStatus.UNSUPPORTED, ClaimStatus.CONTRADICTED]
        ]

        if unsupported_claims:
            suggestions.append(
                "Focus reasoning on information explicitly stated in source documents"
            )

        weak_claims = [
            c
            for c in validated_claims
            if c.status == ClaimStatus.PARTIALLY_SUPPORTED and c.confidence < 60
        ]

        if weak_claims:
            suggestions.append(
                "Use more specific evidence and direct quotes from sources"
            )

        if len(validated_claims) > 0:
            avg_confidence = sum(c.confidence for c in validated_claims) / len(
                validated_claims
            )
            if avg_confidence < 70:
                suggestions.append(
                    "Re-retrieve with different query or filters to get more relevant sources"
                )

        return suggestions[:5]  # Limit to top 5 suggestions

    def get_stats(self, validation_result: ValidationResult) -> Dict:
        """Get validation statistics"""
        return {
            "is_valid": validation_result.is_valid,
            "confidence": validation_result.confidence.value,
            "confidence_score": validation_result.confidence_score,
            "support_percentage": validation_result.get_support_percentage(),
            "total_claims": validation_result.total_claims,
            "supported_claims": validation_result.supported_claims,
            "unsupported_claims": validation_result.unsupported_claims,
            "total_issues": len(validation_result.issues),
            "critical_issues": sum(
                1 for i in validation_result.issues if i.severity == "critical"
            ),
            "should_re_reason": validation_result.should_re_reason,
            "validation_duration_ms": validation_result.validation_duration_ms,
        }


# Convenience function for quick validation
async def quick_validate(
    reasoning_output: str,
    source_chunks: List[Dict],
    citations: Optional[List[Dict]] = None,
    re_reason_threshold: float = 60.0,
) -> ValidationResult:
    """
    Quick validation without creating a CriticAgent instance.

    Args:
        reasoning_output: Final answer to validate
        source_chunks: Source documents used for reasoning
        citations: Optional list of citations
        re_reason_threshold: Confidence threshold for re-reasoning recommendation

    Returns:
        ValidationResult with validation findings
    """
    agent = CriticAgent(re_reason_threshold=re_reason_threshold)
    return await agent.validate(reasoning_output, source_chunks, citations)


# Example usage
if __name__ == "__main__":
    import asyncio

    async def main():
        # Initialize critic agent
        critic = CriticAgent(re_reason_threshold=65.0, use_llm_validation=True)

        # Example reasoning output
        reasoning_output = """
        Based on the sources, Python was created by Guido van Rossum in 1991.
        It is a high-level, interpreted programming language known for its readability.
        Python is widely used in data science, web development, and automation.
        The language was designed with simplicity and code readability in mind.
        """

        # Example source chunks
        source_chunks = [
            {
                "id": "chunk_1",
                "content": "Python was created by Guido van Rossum and first released in 1991. It emphasizes code readability and simplicity.",
                "metadata": {"source": "Python History"},
            },
            {
                "id": "chunk_2",
                "content": "Python is an interpreted, high-level programming language used extensively in data science and web development.",
                "metadata": {"source": "Python Overview"},
            },
        ]

        # Example citations
        citations = [
            {"chunk_id": "chunk_1", "text": "Python was created by Guido van Rossum"},
            {
                "chunk_id": "chunk_2",
                "text": "interpreted, high-level programming language",
            },
        ]

        # Validate
        result = await critic.validate(
            reasoning_output=reasoning_output,
            source_chunks=source_chunks,
            citations=citations,
        )

        # Print results
        print("=" * 60)
        print("VALIDATION RESULT")
        print("=" * 60)
        print(result.get_summary())
        print()

        print("Claims Analysis:")
        for i, claim in enumerate(result.claims, 1):
            print(f"\n{i}. {claim.text}")
            print(f"   Status: {claim.status.value}")
            print(f"   Confidence: {claim.confidence:.1f}%")
            print(f"   Explanation: {claim.explanation}")

        if result.issues:
            print("\n" + "=" * 60)
            print("ISSUES FOUND")
            print("=" * 60)
            for i, issue in enumerate(result.issues, 1):
                print(f"\n{i}. [{issue.severity.upper()}] {issue.issue_type}")
                print(f"   {issue.description}")
                if issue.suggestion:
                    print(f"   Suggestion: {issue.suggestion}")

        if result.improvement_suggestions:
            print("\n" + "=" * 60)
            print("IMPROVEMENT SUGGESTIONS")
            print("=" * 60)
            for i, suggestion in enumerate(result.improvement_suggestions, 1):
                print(f"{i}. {suggestion}")

        print("\n" + "=" * 60)
        print("STATISTICS")
        print("=" * 60)
        stats = critic.get_stats(result)
        for key, value in stats.items():
            print(f"{key}: {value}")

    asyncio.run(main())
