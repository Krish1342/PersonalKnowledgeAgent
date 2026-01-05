"""
Reflection Agent for Personal Knowledge Agent

Analyzes user feedback and queries, detects weak knowledge areas,
improves future retrieval and tagging, and logs learning insights.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Tuple
from datetime import datetime, timedelta
from enum import Enum
from collections import defaultdict, Counter
import json
import re
from groq import AsyncGroq
import os


class FeedbackType(Enum):
    """Types of user feedback"""

    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    INCORRECT = "incorrect"
    INCOMPLETE = "incomplete"
    HELPFUL = "helpful"


class WeaknessType(Enum):
    """Types of knowledge weaknesses"""

    COVERAGE_GAP = "coverage_gap"  # Missing information
    LOW_QUALITY = "low_quality"  # Poor quality sources
    OUTDATED = "outdated"  # Old information
    AMBIGUOUS = "ambiguous"  # Unclear/conflicting info
    POOR_RETRIEVAL = "poor_retrieval"  # Good info exists but not retrieved
    MISSING_CONTEXT = "missing_context"  # Lacks necessary context


class InsightType(Enum):
    """Types of learning insights"""

    QUERY_PATTERN = "query_pattern"
    KNOWLEDGE_GAP = "knowledge_gap"
    RETRIEVAL_ISSUE = "retrieval_issue"
    TAGGING_IMPROVEMENT = "tagging_improvement"
    USER_BEHAVIOR = "user_behavior"
    SYSTEM_PERFORMANCE = "system_performance"


@dataclass
class UserFeedback:
    """Represents user feedback on a response"""

    feedback_id: str
    query: str
    response: str
    feedback_type: FeedbackType
    rating: Optional[float]  # 1-5 stars
    comment: Optional[str]
    timestamp: datetime
    context: Dict = field(default_factory=dict)  # Additional context

    # Associated data
    retrieved_chunks: List[str] = field(default_factory=list)
    reasoning_confidence: Optional[float] = None
    validation_passed: Optional[bool] = None


@dataclass
class QueryAnalysis:
    """Analysis of a user query"""

    query: str
    topics: List[str]
    intent: str  # "factual", "how-to", "comparison", "explanation", etc.
    complexity: str  # "simple", "moderate", "complex"
    keywords: List[str]
    entities: List[str]
    timestamp: datetime

    # Performance metrics
    retrieval_success: bool = False
    response_quality: Optional[float] = None
    user_satisfaction: Optional[float] = None


@dataclass
class KnowledgeWeakness:
    """Identified weakness in knowledge base"""

    weakness_id: str
    weakness_type: WeaknessType
    topic: str
    description: str
    severity: str  # "critical", "high", "medium", "low"

    # Evidence
    related_queries: List[str] = field(default_factory=list)
    failure_count: int = 0
    avg_confidence: float = 0.0

    # Recommendations
    recommendations: List[str] = field(default_factory=list)
    suggested_sources: List[str] = field(default_factory=list)

    detected_at: datetime = field(default_factory=datetime.utcnow)
    last_seen: datetime = field(default_factory=datetime.utcnow)


@dataclass
class TaggingImprovement:
    """Suggestion for improving tagging"""

    chunk_ids: List[str]
    current_tags: List[str]
    suggested_tags: List[str]
    reason: str
    confidence: float
    impact_score: float  # Expected improvement


@dataclass
class LearningInsight:
    """A learned insight from analysis"""

    insight_id: str
    insight_type: InsightType
    title: str
    description: str
    evidence: Dict

    # Impact & priority
    impact_score: float  # 0-100
    priority: str  # "critical", "high", "medium", "low"

    # Actions
    actionable: bool
    recommended_actions: List[str] = field(default_factory=list)

    timestamp: datetime = field(default_factory=datetime.utcnow)
    applied: bool = False


@dataclass
class ReflectionReport:
    """Comprehensive reflection report"""

    period_start: datetime
    period_end: datetime

    # Query analytics
    total_queries: int
    unique_topics: Set[str]
    common_query_patterns: List[Tuple[str, int]]

    # Feedback summary
    total_feedback: int
    positive_feedback_ratio: float
    avg_rating: Optional[float]

    # Weaknesses
    identified_weaknesses: List[KnowledgeWeakness]
    critical_gaps: List[str]

    # Improvements
    tagging_improvements: List[TaggingImprovement]
    retrieval_improvements: List[str]

    # Insights
    insights: List[LearningInsight]

    # Metrics
    metrics: Dict = field(default_factory=dict)


class ReflectionAgent:
    """
    Agent that analyzes system performance and learns from interactions.

    Responsibilities:
    - Analyze user feedback and queries to identify patterns
    - Detect weak knowledge areas and coverage gaps
    - Suggest improvements for retrieval and tagging
    - Log and report learning insights
    - Provide recommendations for system improvement
    """

    def __init__(
        self,
        groq_api_key: Optional[str] = None,
        model: str = "llama-3.3-70b-versatile",
        log_file: str = "reflection_log.jsonl",
        use_llm: bool = True,
    ):
        """
        Initialize Reflection Agent.

        Args:
            groq_api_key: Groq API key for intelligent analysis
            model: Groq model to use
            log_file: File to log insights
            use_llm: Whether to use LLM for analysis
        """
        self.groq_api_key = groq_api_key or os.getenv("GROQ_API_KEY")
        self.model = model
        self.log_file = log_file
        self.use_llm = use_llm

        if self.groq_api_key and self.use_llm:
            self.client = AsyncGroq(api_key=self.groq_api_key)
        else:
            self.client = None

        # In-memory storage (would be persisted in production)
        self.feedback_history: List[UserFeedback] = []
        self.query_history: List[QueryAnalysis] = []
        self.identified_weaknesses: List[KnowledgeWeakness] = []
        self.insights: List[LearningInsight] = []

    async def analyze_feedback(self, feedback: UserFeedback) -> Dict:
        """
        Analyze user feedback to extract insights.

        Args:
            feedback: User feedback to analyze

        Returns:
            Dict with analysis results
        """
        # Store feedback
        self.feedback_history.append(feedback)

        # Analyze query
        query_analysis = await self._analyze_query(
            feedback.query,
            feedback.retrieved_chunks,
            feedback.reasoning_confidence,
            feedback.rating,
        )

        self.query_history.append(query_analysis)

        # Detect issues based on feedback
        issues = await self._detect_issues_from_feedback(feedback, query_analysis)

        # Generate insights
        insights = await self._generate_insights_from_feedback(
            feedback, query_analysis, issues
        )

        # Log insights
        for insight in insights:
            await self._log_insight(insight)
            self.insights.append(insight)

        return {
            "feedback_processed": True,
            "query_analysis": query_analysis,
            "issues_detected": len(issues),
            "insights_generated": len(insights),
            "issues": issues,
            "insights": insights,
        }

    async def _analyze_query(
        self,
        query: str,
        retrieved_chunks: List[str],
        confidence: Optional[float],
        satisfaction: Optional[float],
    ) -> QueryAnalysis:
        """Analyze a user query"""
        if self.client and self.use_llm:
            try:
                return await self._analyze_query_with_llm(
                    query, retrieved_chunks, confidence, satisfaction
                )
            except Exception as e:
                print(f"LLM query analysis failed: {e}, using fallback")

        return self._analyze_query_heuristic(
            query, retrieved_chunks, confidence, satisfaction
        )

    async def _analyze_query_with_llm(
        self,
        query: str,
        retrieved_chunks: List[str],
        confidence: Optional[float],
        satisfaction: Optional[float],
    ) -> QueryAnalysis:
        """Analyze query using LLM"""
        prompt = f"""Analyze this user query and extract key information.

Query: "{query}"

Extract:
1. Topics: Main topics/subjects (list)
2. Intent: User's intent (factual/how-to/comparison/explanation/other)
3. Complexity: Query complexity (simple/moderate/complex)
4. Keywords: Important keywords (list)
5. Entities: Named entities mentioned (list)

Return ONLY a JSON object:
{{
    "topics": ["topic1", "topic2"],
    "intent": "factual",
    "complexity": "simple",
    "keywords": ["key1", "key2"],
    "entities": ["entity1"]
}}

Response:"""

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=500,
        )

        content = response.choices[0].message.content.strip()

        # Parse response
        import json

        try:
            result = json.loads(content)

            return QueryAnalysis(
                query=query,
                topics=result.get("topics", []),
                intent=result.get("intent", "unknown"),
                complexity=result.get("complexity", "moderate"),
                keywords=result.get("keywords", []),
                entities=result.get("entities", []),
                timestamp=datetime.utcnow(),
                retrieval_success=len(retrieved_chunks) > 0,
                response_quality=confidence,
                user_satisfaction=satisfaction,
            )
        except Exception as e:
            print(f"Failed to parse LLM query analysis: {e}")
            return self._analyze_query_heuristic(
                query, retrieved_chunks, confidence, satisfaction
            )

    def _analyze_query_heuristic(
        self,
        query: str,
        retrieved_chunks: List[str],
        confidence: Optional[float],
        satisfaction: Optional[float],
    ) -> QueryAnalysis:
        """Analyze query using heuristics"""
        query_lower = query.lower()

        # Extract keywords (words longer than 3 chars, not stop words)
        stop_words = {
            "what",
            "when",
            "where",
            "who",
            "why",
            "how",
            "the",
            "is",
            "are",
            "was",
            "were",
            "do",
            "does",
            "did",
            "can",
            "could",
            "would",
            "should",
        }
        words = re.findall(r"\b\w+\b", query_lower)
        keywords = [w for w in words if len(w) > 3 and w not in stop_words]

        # Determine intent
        if any(word in query_lower for word in ["how to", "how do", "how can"]):
            intent = "how-to"
        elif any(
            word in query_lower for word in ["what is", "what are", "define", "explain"]
        ):
            intent = "explanation"
        elif any(
            word in query_lower for word in ["compare", "difference", "vs", "versus"]
        ):
            intent = "comparison"
        elif any(word in query_lower for word in ["why", "reason", "because"]):
            intent = "reasoning"
        else:
            intent = "factual"

        # Determine complexity
        word_count = len(words)
        question_marks = query.count("?")

        if word_count < 5 or question_marks == 1:
            complexity = "simple"
        elif word_count > 15 or question_marks > 1:
            complexity = "complex"
        else:
            complexity = "moderate"

        # Extract topics (use keywords as proxy)
        topics = keywords[:3]  # Top 3 keywords as topics

        # Extract entities (capitalized words)
        entities = re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b", query)

        return QueryAnalysis(
            query=query,
            topics=topics,
            intent=intent,
            complexity=complexity,
            keywords=keywords,
            entities=entities,
            timestamp=datetime.utcnow(),
            retrieval_success=len(retrieved_chunks) > 0,
            response_quality=confidence,
            user_satisfaction=satisfaction,
        )

    async def _detect_issues_from_feedback(
        self, feedback: UserFeedback, query_analysis: QueryAnalysis
    ) -> List[str]:
        """Detect issues from feedback"""
        issues = []

        # Negative feedback
        if feedback.feedback_type in [FeedbackType.NEGATIVE, FeedbackType.INCORRECT]:
            issues.append("negative_feedback")

        # Low rating
        if feedback.rating and feedback.rating < 3.0:
            issues.append("low_rating")

        # No retrieval success
        if not query_analysis.retrieval_success:
            issues.append("retrieval_failure")

        # Low confidence
        if feedback.reasoning_confidence and feedback.reasoning_confidence < 60:
            issues.append("low_confidence_response")

        # Validation failure
        if feedback.validation_passed is False:
            issues.append("validation_failure")

        # Incomplete response
        if feedback.feedback_type == FeedbackType.INCOMPLETE:
            issues.append("incomplete_response")

        return issues

    async def _generate_insights_from_feedback(
        self, feedback: UserFeedback, query_analysis: QueryAnalysis, issues: List[str]
    ) -> List[LearningInsight]:
        """Generate insights from feedback"""
        insights = []

        # Knowledge gap insight
        if "retrieval_failure" in issues or "incomplete_response" in issues:
            for topic in query_analysis.topics:
                insight = LearningInsight(
                    insight_id=f"gap_{topic}_{datetime.utcnow().timestamp()}",
                    insight_type=InsightType.KNOWLEDGE_GAP,
                    title=f"Knowledge gap detected in topic: {topic}",
                    description=f"Query '{feedback.query}' revealed missing or insufficient knowledge about {topic}",
                    evidence={
                        "query": feedback.query,
                        "topics": query_analysis.topics,
                        "retrieval_success": query_analysis.retrieval_success,
                        "feedback_type": feedback.feedback_type.value,
                    },
                    impact_score=80 if "retrieval_failure" in issues else 60,
                    priority="high" if "retrieval_failure" in issues else "medium",
                    actionable=True,
                    recommended_actions=[
                        f"Acquire more content about {topic}",
                        f"Improve indexing for {topic}-related queries",
                        f"Review existing {topic} content for quality",
                    ],
                )
                insights.append(insight)

        # Retrieval improvement insight
        if "low_confidence_response" in issues and query_analysis.retrieval_success:
            insight = LearningInsight(
                insight_id=f"retrieval_{datetime.utcnow().timestamp()}",
                insight_type=InsightType.RETRIEVAL_ISSUE,
                title="Retrieved content may not be optimal",
                description=f"Query '{feedback.query}' retrieved content but resulted in low confidence",
                evidence={
                    "query": feedback.query,
                    "retrieved_chunks": len(feedback.retrieved_chunks),
                    "confidence": feedback.reasoning_confidence,
                    "feedback_type": feedback.feedback_type.value,
                },
                impact_score=70,
                priority="medium",
                actionable=True,
                recommended_actions=[
                    "Review retrieval ranking algorithm",
                    f"Improve embeddings for queries like: {query_analysis.intent}",
                    "Consider query expansion or reformulation",
                ],
            )
            insights.append(insight)

        # Query pattern insight (track common patterns)
        if query_analysis.intent and query_analysis.complexity:
            insight = LearningInsight(
                insight_id=f"pattern_{datetime.utcnow().timestamp()}",
                insight_type=InsightType.QUERY_PATTERN,
                title=f"Query pattern: {query_analysis.intent} ({query_analysis.complexity})",
                description=f"User asked {query_analysis.intent} question with {query_analysis.complexity} complexity",
                evidence={
                    "query": feedback.query,
                    "intent": query_analysis.intent,
                    "complexity": query_analysis.complexity,
                    "topics": query_analysis.topics,
                },
                impact_score=40,
                priority="low",
                actionable=False,
            )
            insights.append(insight)

        return insights

    async def detect_weak_areas(
        self, lookback_days: int = 30
    ) -> List[KnowledgeWeakness]:
        """
        Detect weak knowledge areas based on feedback history.

        Args:
            lookback_days: Number of days to look back

        Returns:
            List of identified weaknesses
        """
        cutoff = datetime.utcnow() - timedelta(days=lookback_days)

        # Get recent feedback
        recent_feedback = [f for f in self.feedback_history if f.timestamp >= cutoff]

        recent_queries = [q for q in self.query_history if q.timestamp >= cutoff]

        # Analyze by topic
        topic_issues = defaultdict(
            lambda: {
                "queries": [],
                "failures": 0,
                "low_confidence": 0,
                "negative_feedback": 0,
                "confidences": [],
            }
        )

        for query_analysis in recent_queries:
            for topic in query_analysis.topics:
                topic_issues[topic]["queries"].append(query_analysis.query)

                if not query_analysis.retrieval_success:
                    topic_issues[topic]["failures"] += 1

                if (
                    query_analysis.response_quality
                    and query_analysis.response_quality < 60
                ):
                    topic_issues[topic]["low_confidence"] += 1
                    topic_issues[topic]["confidences"].append(
                        query_analysis.response_quality
                    )

                if (
                    query_analysis.user_satisfaction
                    and query_analysis.user_satisfaction < 3
                ):
                    topic_issues[topic]["negative_feedback"] += 1

        # Identify weaknesses
        weaknesses = []

        for topic, issues in topic_issues.items():
            total_queries = len(issues["queries"])

            if total_queries < 2:  # Need at least 2 queries to identify weakness
                continue

            # Calculate severity metrics
            failure_rate = issues["failures"] / total_queries
            low_confidence_rate = issues["low_confidence"] / total_queries
            negative_rate = issues["negative_feedback"] / total_queries
            avg_confidence = (
                sum(issues["confidences"]) / len(issues["confidences"])
                if issues["confidences"]
                else 70
            )

            # Determine weakness type
            weakness_type = None
            severity = "low"
            recommendations = []

            if failure_rate >= 0.5:
                weakness_type = WeaknessType.COVERAGE_GAP
                severity = "critical" if failure_rate >= 0.75 else "high"
                recommendations = [
                    f"Add content covering {topic}",
                    f"Review indexing for {topic} queries",
                ]
            elif low_confidence_rate >= 0.5:
                weakness_type = WeaknessType.LOW_QUALITY
                severity = "high" if avg_confidence < 50 else "medium"
                recommendations = [
                    f"Improve quality of {topic} content",
                    f"Add more authoritative sources on {topic}",
                ]
            elif negative_rate >= 0.4:
                weakness_type = WeaknessType.POOR_RETRIEVAL
                severity = "medium"
                recommendations = [
                    f"Optimize retrieval for {topic} queries",
                    f"Review ranking algorithm for {topic} content",
                ]

            if weakness_type:
                weakness = KnowledgeWeakness(
                    weakness_id=f"weak_{topic}_{datetime.utcnow().timestamp()}",
                    weakness_type=weakness_type,
                    topic=topic,
                    description=f"{weakness_type.value} in {topic}: {failure_rate:.1%} failure rate, {avg_confidence:.1f} avg confidence",
                    severity=severity,
                    related_queries=issues["queries"][:5],  # Top 5
                    failure_count=issues["failures"],
                    avg_confidence=avg_confidence,
                    recommendations=recommendations,
                )

                weaknesses.append(weakness)

                # Store for tracking
                if weakness not in self.identified_weaknesses:
                    self.identified_weaknesses.append(weakness)

        return weaknesses

    async def suggest_tagging_improvements(
        self, chunks_metadata: List[Dict]
    ) -> List[TaggingImprovement]:
        """
        Suggest improvements to chunk tagging based on analysis.

        Args:
            chunks_metadata: List of chunk metadata dicts

        Returns:
            List of tagging improvement suggestions
        """
        improvements = []

        # Analyze query patterns to understand what tags would help
        topic_queries = defaultdict(list)
        for query_analysis in self.query_history:
            for topic in query_analysis.topics:
                topic_queries[topic].append(query_analysis)

        # Group chunks by similarity
        for chunk_meta in chunks_metadata:
            chunk_id = chunk_meta.get("id", "")
            current_tags = chunk_meta.get("tags", [])
            content = chunk_meta.get("content", "")

            # Suggest tags based on frequent query topics
            suggested_tags = set(current_tags)
            reasons = []

            for topic, queries in topic_queries.items():
                # If queries about this topic had poor results, suggest tag
                poor_results = [
                    q
                    for q in queries
                    if not q.retrieval_success
                    or (q.response_quality and q.response_quality < 60)
                ]

                if poor_results and topic.lower() in content.lower():
                    suggested_tags.add(topic)
                    reasons.append(f"Queries about '{topic}' had poor results")

            # Check if improvement needed
            if suggested_tags != set(current_tags):
                improvement = TaggingImprovement(
                    chunk_ids=[chunk_id],
                    current_tags=current_tags,
                    suggested_tags=list(suggested_tags),
                    reason="; ".join(reasons),
                    confidence=0.7,
                    impact_score=(
                        len(
                            topic_queries.get(
                                list(suggested_tags - set(current_tags))[0], []
                            )
                        )
                        if suggested_tags - set(current_tags)
                        else 0
                    ),
                )
                improvements.append(improvement)

        return improvements[:20]  # Return top 20

    async def generate_reflection_report(self, days: int = 7) -> ReflectionReport:
        """
        Generate comprehensive reflection report.

        Args:
            days: Number of days to analyze

        Returns:
            ReflectionReport with analysis and recommendations
        """
        end = datetime.utcnow()
        start = end - timedelta(days=days)

        # Filter data for period
        period_feedback = [
            f for f in self.feedback_history if start <= f.timestamp <= end
        ]
        period_queries = [q for q in self.query_history if start <= q.timestamp <= end]

        # Query analytics
        total_queries = len(period_queries)
        unique_topics = set()
        for q in period_queries:
            unique_topics.update(q.topics)

        # Count query patterns
        intent_counter = Counter(q.intent for q in period_queries)
        common_patterns = intent_counter.most_common(5)

        # Feedback summary
        total_feedback = len(period_feedback)
        positive_count = sum(
            1
            for f in period_feedback
            if f.feedback_type in [FeedbackType.POSITIVE, FeedbackType.HELPFUL]
        )
        positive_ratio = positive_count / total_feedback if total_feedback > 0 else 0

        ratings = [f.rating for f in period_feedback if f.rating]
        avg_rating = sum(ratings) / len(ratings) if ratings else None

        # Detect weaknesses
        weaknesses = await self.detect_weak_areas(lookback_days=days)
        critical_gaps = [w.topic for w in weaknesses if w.severity == "critical"]

        # Tagging improvements (would need chunk data)
        tagging_improvements = []

        # Retrieval improvements
        retrieval_insights = [
            i
            for i in self.insights
            if i.insight_type == InsightType.RETRIEVAL_ISSUE
            and start <= i.timestamp <= end
        ]
        retrieval_improvements = []
        for insight in retrieval_insights:
            retrieval_improvements.extend(insight.recommended_actions)

        # Filter insights for period
        period_insights = [i for i in self.insights if start <= i.timestamp <= end]

        # Calculate metrics
        metrics = {
            "avg_queries_per_day": total_queries / days if days > 0 else 0,
            "retrieval_success_rate": (
                sum(1 for q in period_queries if q.retrieval_success) / total_queries
                if total_queries > 0
                else 0
            ),
            "avg_response_quality": (
                sum(q.response_quality for q in period_queries if q.response_quality)
                / len([q for q in period_queries if q.response_quality])
                if [q for q in period_queries if q.response_quality]
                else 0
            ),
            "feedback_rate": total_feedback / total_queries if total_queries > 0 else 0,
            "critical_issues": len(critical_gaps),
            "total_insights": len(period_insights),
        }

        return ReflectionReport(
            period_start=start,
            period_end=end,
            total_queries=total_queries,
            unique_topics=unique_topics,
            common_query_patterns=common_patterns,
            total_feedback=total_feedback,
            positive_feedback_ratio=positive_ratio,
            avg_rating=avg_rating,
            identified_weaknesses=weaknesses,
            critical_gaps=critical_gaps,
            tagging_improvements=tagging_improvements,
            retrieval_improvements=retrieval_improvements,
            insights=period_insights,
            metrics=metrics,
        )

    async def _log_insight(self, insight: LearningInsight):
        """Log insight to file"""
        try:
            with open(self.log_file, "a") as f:
                log_entry = {
                    "timestamp": insight.timestamp.isoformat(),
                    "insight_id": insight.insight_id,
                    "type": insight.insight_type.value,
                    "title": insight.title,
                    "description": insight.description,
                    "impact_score": insight.impact_score,
                    "priority": insight.priority,
                    "evidence": insight.evidence,
                }
                f.write(json.dumps(log_entry) + "\n")
        except Exception as e:
            print(f"Failed to log insight: {e}")

    def get_stats(self) -> Dict:
        """Get reflection statistics"""
        return {
            "total_feedback": len(self.feedback_history),
            "total_queries": len(self.query_history),
            "identified_weaknesses": len(self.identified_weaknesses),
            "total_insights": len(self.insights),
            "positive_feedback": sum(
                1
                for f in self.feedback_history
                if f.feedback_type in [FeedbackType.POSITIVE, FeedbackType.HELPFUL]
            ),
            "negative_feedback": sum(
                1
                for f in self.feedback_history
                if f.feedback_type in [FeedbackType.NEGATIVE, FeedbackType.INCORRECT]
            ),
            "critical_weaknesses": sum(
                1 for w in self.identified_weaknesses if w.severity == "critical"
            ),
            "high_impact_insights": sum(
                1 for i in self.insights if i.impact_score >= 70
            ),
        }


# Example usage
if __name__ == "__main__":
    import asyncio

    async def main():
        # Initialize reflection agent
        agent = ReflectionAgent(use_llm=True)

        # Example feedback
        feedback1 = UserFeedback(
            feedback_id="fb_1",
            query="What is Python?",
            response="Python is a programming language...",
            feedback_type=FeedbackType.POSITIVE,
            rating=4.5,
            comment="Very helpful!",
            timestamp=datetime.utcnow(),
            retrieved_chunks=["chunk_1", "chunk_2"],
            reasoning_confidence=85.0,
            validation_passed=True,
        )

        feedback2 = UserFeedback(
            feedback_id="fb_2",
            query="How does quantum computing work?",
            response="I don't have enough information...",
            feedback_type=FeedbackType.INCOMPLETE,
            rating=2.0,
            comment="Not enough detail",
            timestamp=datetime.utcnow(),
            retrieved_chunks=[],
            reasoning_confidence=30.0,
            validation_passed=False,
        )

        # Analyze feedback
        print("=" * 60)
        print("ANALYZING FEEDBACK 1")
        print("=" * 60)
        result1 = await agent.analyze_feedback(feedback1)
        print(f"Issues detected: {result1['issues_detected']}")
        print(f"Insights generated: {result1['insights_generated']}")
        if result1["insights"]:
            for insight in result1["insights"]:
                print(f"\n  - {insight.title}")
                print(f"    Type: {insight.insight_type.value}")
                print(f"    Priority: {insight.priority}")

        print("\n" + "=" * 60)
        print("ANALYZING FEEDBACK 2")
        print("=" * 60)
        result2 = await agent.analyze_feedback(feedback2)
        print(f"Issues detected: {result2['issues_detected']}")
        print(f"Insights generated: {result2['insights_generated']}")
        if result2["insights"]:
            for insight in result2["insights"]:
                print(f"\n  - {insight.title}")
                print(f"    Type: {insight.insight_type.value}")
                print(f"    Priority: {insight.priority}")
                print(f"    Impact: {insight.impact_score:.1f}")
                if insight.recommended_actions:
                    print(f"    Actions:")
                    for action in insight.recommended_actions:
                        print(f"      • {action}")

        # Detect weak areas
        print("\n" + "=" * 60)
        print("WEAK KNOWLEDGE AREAS")
        print("=" * 60)
        weaknesses = await agent.detect_weak_areas(lookback_days=30)
        if weaknesses:
            for weakness in weaknesses:
                print(f"\n{weakness.topic} - {weakness.severity.upper()}")
                print(f"  Type: {weakness.weakness_type.value}")
                print(f"  Description: {weakness.description}")
                print(f"  Recommendations:")
                for rec in weakness.recommendations:
                    print(f"    • {rec}")
        else:
            print("No significant weaknesses detected")

        # Generate report
        print("\n" + "=" * 60)
        print("REFLECTION REPORT (7 DAYS)")
        print("=" * 60)
        report = await agent.generate_reflection_report(days=7)
        print(f"Period: {report.period_start.date()} to {report.period_end.date()}")
        print(f"\nQuery Analytics:")
        print(f"  Total queries: {report.total_queries}")
        print(f"  Unique topics: {len(report.unique_topics)}")
        print(f"  Common patterns: {report.common_query_patterns}")
        print(f"\nFeedback Summary:")
        print(f"  Total feedback: {report.total_feedback}")
        print(f"  Positive ratio: {report.positive_feedback_ratio:.1%}")
        print(
            f"  Avg rating: {report.avg_rating:.1f}"
            if report.avg_rating
            else "  Avg rating: N/A"
        )
        print(f"\nWeaknesses:")
        print(f"  Total identified: {len(report.identified_weaknesses)}")
        print(f"  Critical gaps: {report.critical_gaps}")
        print(f"\nMetrics:")
        for key, value in report.metrics.items():
            print(
                f"  {key}: {value:.2f}"
                if isinstance(value, float)
                else f"  {key}: {value}"
            )

        # Get stats
        print("\n" + "=" * 60)
        print("AGENT STATISTICS")
        print("=" * 60)
        stats = agent.get_stats()
        for key, value in stats.items():
            print(f"{key}: {value}")

    asyncio.run(main())
