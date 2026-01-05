"""
Auto-generate metadata tags for text chunks.
Extracts topics, domain, and difficulty level using NLP and heuristics.
"""

import re
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass
from collections import Counter
import math

from app.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ContentMetadata:
    """Metadata extracted from content."""

    topics: List[str]
    domain: str
    difficulty_level: str  # "beginner", "intermediate", "advanced"
    key_terms: List[str]
    language: str = "en"
    content_length: int = 0


class ContentTagger:
    """
    Automatically extract and generate metadata tags for content.
    Uses heuristics and pattern matching for domain and difficulty analysis.
    """

    # Domain keywords mapping
    DOMAIN_KEYWORDS = {
        "machine-learning": [
            "neural network",
            "machine learning",
            "deep learning",
            "algorithm",
            "training",
            "model",
            "tensor",
            "classification",
            "regression",
        ],
        "data-science": [
            "data analysis",
            "statistics",
            "data visualization",
            "pandas",
            "numpy",
            "matplotlib",
            "hypothesis",
        ],
        "backend-development": [
            "api",
            "database",
            "server",
            "rest",
            "graphql",
            "microservice",
            "authentication",
            "sql",
            "postgresql",
        ],
        "frontend-development": [
            "react",
            "angular",
            "vue",
            "javascript",
            "html",
            "css",
            "component",
            "state",
            "dom",
        ],
        "devops": [
            "docker",
            "kubernetes",
            "deployment",
            "ci/cd",
            "pipeline",
            "container",
            "orchestration",
            "monitoring",
        ],
        "cloud": [
            "aws",
            "azure",
            "gcp",
            "cloud",
            "lambda",
            "serverless",
            "instance",
            "bucket",
        ],
    }

    # Difficulty indicators
    ADVANCED_INDICATORS = {
        "proof": 2,
        "theorem": 2,
        "mathematical": 2,
        "complex": 1.5,
        "optimization": 1.5,
        "architecture": 1,
        "design pattern": 1,
    }

    BEGINNER_INDICATORS = {
        "introduction": -2,
        "getting started": -2,
        "basics": -2,
        "simple": -1,
        "example": -0.5,
        "tutorial": -1,
    }

    def __init__(self):
        """Initialize content tagger."""
        self.topic_cache: Dict[str, Set[str]] = {}
        logger.debug("ContentTagger initialized")

    @staticmethod
    def _extract_key_terms(text: str, num_terms: int = 10) -> List[str]:
        """
        Extract key terms from text using TF-IDF-like heuristics.

        Args:
            text: Text to analyze
            num_terms: Number of terms to extract

        Returns:
            List of key terms
        """
        # Remove common words and split into terms
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
            "from",
            "is",
            "are",
            "be",
            "have",
            "has",
            "do",
            "does",
            "did",
            "can",
            "could",
            "will",
            "would",
            "should",
            "may",
            "this",
            "that",
            "these",
            "those",
            "i",
            "you",
            "he",
            "she",
            "it",
        }

        # Extract words (alphanumeric + hyphens)
        words = re.findall(r"\b[a-z\-]+\b", text.lower())

        # Filter and count
        filtered = [w for w in words if w not in stop_words and len(w) > 3]
        term_counts = Counter(filtered)

        return [term for term, _ in term_counts.most_common(num_terms)]

    def _detect_domain(self, text: str) -> str:
        """
        Detect content domain based on keywords.

        Args:
            text: Text to analyze

        Returns:
            Domain name
        """
        text_lower = text.lower()
        domain_scores: Dict[str, float] = {}

        for domain, keywords in self.DOMAIN_KEYWORDS.items():
            score = sum(text_lower.count(kw) for kw in keywords)
            if score > 0:
                domain_scores[domain] = score

        if domain_scores:
            return max(domain_scores, key=domain_scores.get)
        return "general"

    def _calculate_difficulty(self, text: str) -> str:
        """
        Calculate difficulty level based on content indicators.

        Args:
            text: Text to analyze

        Returns:
            Difficulty level ("beginner", "intermediate", "advanced")
        """
        text_lower = text.lower()
        score = 0

        # Count advanced indicators
        for indicator, weight in self.ADVANCED_INDICATORS.items():
            count = text_lower.count(indicator)
            score += count * weight

        # Count beginner indicators
        for indicator, weight in self.BEGINNER_INDICATORS.items():
            count = text_lower.count(indicator)
            score += count * weight

        # Consider text length and complexity
        words = text.split()
        avg_word_length = sum(len(w) for w in words) / len(words) if words else 0

        # Longer words suggest more advanced content
        if avg_word_length > 6:
            score += 0.5
        if avg_word_length > 8:
            score += 1

        # Check for technical density (ratio of technical terms)
        technical_words = sum(1 for w in words if len(w) > 4 and w.islower())
        technical_ratio = technical_words / len(words) if words else 0
        if technical_ratio > 0.3:
            score += 1

        # Classify based on score
        if score > 3:
            return "advanced"
        elif score > 0:
            return "intermediate"
        else:
            return "beginner"

    def _extract_topics(self, text: str) -> List[str]:
        """
        Extract topics from text.

        Args:
            text: Text to analyze

        Returns:
            List of topics
        """
        topics: Set[str] = set()
        text_lower = text.lower()

        # Look for common topic patterns
        # Numbered lists
        if re.search(r"^\d+\.\s+\w+", text, re.MULTILINE):
            topics.add("list")

        # Code blocks indicate programming content
        if "```" in text or re.search(r"^\s{4}\w+", text, re.MULTILINE):
            topics.add("code")

        # Math and equations
        if "$" in text or re.search(r"\\[a-z]+", text):
            topics.add("mathematics")

        # Configuration or settings
        if re.search(r"(config|setting|parameter|option)s?:", text, re.IGNORECASE):
            topics.add("configuration")

        # API related
        if re.search(
            r"(endpoint|request|response|header|payload)", text, re.IGNORECASE
        ):
            topics.add("api")

        # Database related
        if re.search(r"(query|database|schema|index|table)", text, re.IGNORECASE):
            topics.add("database")

        # Security related
        if re.search(
            r"(security|encryption|password|authentication|authorization)",
            text,
            re.IGNORECASE,
        ):
            topics.add("security")

        # Performance related
        if re.search(
            r"(performance|optimization|benchmark|latency|throughput)",
            text,
            re.IGNORECASE,
        ):
            topics.add("performance")

        # Best practices
        if re.search(r"(best practice|guideline|recommendation)", text, re.IGNORECASE):
            topics.add("best-practices")

        # Extract from headings
        headings = re.findall(r"^#+\s+(.+?)$", text, re.MULTILINE)
        for heading in headings:
            # Extract 1-2 word phrases from headings
            heading_words = heading.split()
            if len(heading_words) <= 3:
                topics.add(heading.lower().replace(" ", "-"))

        return list(topics) if topics else ["general"]

    def tag_content(self, text: str) -> ContentMetadata:
        """
        Generate comprehensive metadata tags for content.

        Args:
            text: Text to tag

        Returns:
            ContentMetadata object

        Raises:
            ValueError: If text is empty
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")

        logger.debug(f"Tagging content ({len(text)} chars)")

        metadata = ContentMetadata(
            topics=self._extract_topics(text),
            domain=self._detect_domain(text),
            difficulty_level=self._calculate_difficulty(text),
            key_terms=self._extract_key_terms(text),
            content_length=len(text),
        )

        logger.debug(
            f"Tagged content: domain={metadata.domain}, "
            f"difficulty={metadata.difficulty_level}, "
            f"topics={metadata.topics}"
        )

        return metadata

    def tag_batch(self, texts: List[str]) -> List[ContentMetadata]:
        """
        Tag multiple texts.

        Args:
            texts: List of texts to tag

        Returns:
            List of ContentMetadata objects
        """
        return [self.tag_content(text) for text in texts]


def create_tagger() -> ContentTagger:
    """
    Factory function to create content tagger.

    Returns:
        ContentTagger instance
    """
    return ContentTagger()
