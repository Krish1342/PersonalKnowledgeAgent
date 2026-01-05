"""
Planner Agent for query analysis and retrieval planning.

This agent provides intelligent query planning with:
- User query analysis and classification
- Complex query decomposition into sub-questions
- Retrieval strategy determination per subtask
- Structured plan generation with priorities
- Integration with Groq API for intelligent planning
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


class QueryComplexity(Enum):
    """Query complexity levels."""

    SIMPLE = "simple"  # Single concept, direct answer
    MODERATE = "moderate"  # Multiple related concepts
    COMPLEX = "complex"  # Multiple unrelated concepts, requires reasoning
    MULTI_STEP = "multi_step"  # Sequential steps, dependency chain


class RetrievalStrategy(Enum):
    """Retrieval strategies for different query types."""

    DIRECT_SEARCH = "direct_search"  # Simple semantic search
    TOPIC_FILTERED = "topic_filtered"  # Search with topic filters
    DOMAIN_SPECIFIC = "domain_specific"  # Search within specific domain
    MULTI_DOMAIN = "multi_domain"  # Search across domains
    TEMPORAL = "temporal"  # Time-based search
    COMPARATIVE = "comparative"  # Compare multiple concepts
    AGGREGATIVE = "aggregative"  # Aggregate multiple searches


@dataclass
class SubTask:
    """
    A subtask in the execution plan.

    Attributes:
        id: Unique subtask identifier
        question: The sub-question to answer
        strategy: Retrieval strategy to use
        topics: Relevant topics for filtering
        domains: Relevant domains for filtering
        difficulty: Expected difficulty level
        priority: Execution priority (1=highest)
        depends_on: List of subtask IDs this depends on
        estimated_chunks: Expected number of chunks needed
        metadata: Additional metadata for retrieval
    """

    id: str
    question: str
    strategy: RetrievalStrategy
    topics: List[str] = field(default_factory=list)
    domains: List[str] = field(default_factory=list)
    difficulty: Optional[str] = None
    priority: int = 1
    depends_on: List[str] = field(default_factory=list)
    estimated_chunks: int = 5
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionPlan:
    """
    Complete execution plan for a query.

    Attributes:
        original_query: The original user query
        complexity: Query complexity level
        subtasks: List of subtasks to execute
        total_subtasks: Number of subtasks
        estimated_total_chunks: Estimated total chunks needed
        reasoning: Explanation of the plan
        requires_aggregation: Whether results need aggregation
        execution_order: Recommended execution order
    """

    original_query: str
    complexity: QueryComplexity
    subtasks: List[SubTask]
    total_subtasks: int
    estimated_total_chunks: int
    reasoning: str
    requires_aggregation: bool = False
    execution_order: List[str] = field(default_factory=list)


class PlannerAgent:
    """
    Agent for intelligent query planning and decomposition.

    Features:
    - Query complexity analysis
    - Sub-question generation
    - Retrieval strategy determination
    - Dependency resolution
    - Priority assignment
    """

    def __init__(
        self,
        groq_api_key: Optional[str] = None,
        groq_model: Optional[str] = None,
        max_subtasks: int = 10,
    ):
        """
        Initialize planner agent.

        Args:
            groq_api_key: Groq API key (uses config default if None)
            groq_model: Groq model to use (uses config default if None)
            max_subtasks: Maximum number of subtasks to generate
        """
        self.api_key = groq_api_key or settings.GROQ_API_KEY
        self.model = groq_model or settings.GROQ_MODEL
        self.max_subtasks = max_subtasks

        # Initialize Groq client if API key available
        self.groq_client = None
        if self.api_key:
            try:
                self.groq_client = AsyncGroq(api_key=self.api_key)
                logger.info("PlannerAgent initialized with Groq API")
            except Exception as e:
                logger.warning(f"Failed to initialize Groq client: {e}")
        else:
            logger.info("PlannerAgent initialized without Groq API (fallback mode)")

        logger.info(
            "PlannerAgent initialized",
            extra={
                "max_subtasks": max_subtasks,
                "has_groq": self.groq_client is not None,
            },
        )

    async def create_plan(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> ExecutionPlan:
        """
        Create an execution plan for a user query.

        Args:
            query: User query to plan for
            context: Optional context (user preferences, history, etc.)

        Returns:
            ExecutionPlan with subtasks and strategies

        Raises:
            ValueError: If query is empty
        """
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")

        logger.info(f"Creating plan for query: {query[:100]}...")

        # Analyze query complexity
        complexity = await self._analyze_complexity(query)
        logger.debug(f"Query complexity: {complexity.value}")

        # Generate subtasks based on complexity
        if complexity == QueryComplexity.SIMPLE:
            subtasks = [self._create_simple_subtask(query)]
        else:
            if self.groq_client:
                subtasks = await self._generate_subtasks_with_groq(
                    query, complexity, context
                )
            else:
                subtasks = self._generate_subtasks_fallback(query, complexity)

        # Determine execution order
        execution_order = self._determine_execution_order(subtasks)

        # Calculate statistics
        total_chunks = sum(st.estimated_chunks for st in subtasks)
        requires_aggregation = len(subtasks) > 1

        # Generate reasoning
        reasoning = self._generate_reasoning(query, complexity, subtasks)

        plan = ExecutionPlan(
            original_query=query,
            complexity=complexity,
            subtasks=subtasks,
            total_subtasks=len(subtasks),
            estimated_total_chunks=total_chunks,
            reasoning=reasoning,
            requires_aggregation=requires_aggregation,
            execution_order=execution_order,
        )

        logger.info(
            f"Plan created: {len(subtasks)} subtasks, complexity={complexity.value}",
            extra={
                "total_subtasks": len(subtasks),
                "estimated_chunks": total_chunks,
            },
        )

        return plan

    async def _analyze_complexity(self, query: str) -> QueryComplexity:
        """
        Analyze query complexity.

        Args:
            query: User query

        Returns:
            QueryComplexity level
        """
        # Simple heuristics for complexity analysis
        query_lower = query.lower()

        # Check for multi-step indicators
        multi_step_keywords = [
            "first",
            "then",
            "after",
            "before",
            "step by step",
            "how do i",
            "explain how",
            "walk me through",
        ]
        if any(kw in query_lower for kw in multi_step_keywords):
            return QueryComplexity.MULTI_STEP

        # Check for complex indicators
        complex_keywords = [
            "compare",
            "difference between",
            "versus",
            "vs",
            "both",
            "multiple",
            "various",
            "different ways",
            "pros and cons",
            "advantages and disadvantages",
        ]
        if any(kw in query_lower for kw in complex_keywords):
            return QueryComplexity.COMPLEX

        # Check for moderate indicators (multiple concepts with "and")
        if " and " in query_lower or query.count("?") > 1:
            return QueryComplexity.MODERATE

        # Check word count and question marks
        word_count = len(query.split())
        if word_count > 20:
            return QueryComplexity.COMPLEX
        elif word_count > 10:
            return QueryComplexity.MODERATE

        return QueryComplexity.SIMPLE

    def _create_simple_subtask(self, query: str) -> SubTask:
        """
        Create a single subtask for simple queries.

        Args:
            query: User query

        Returns:
            SubTask
        """
        # Infer topics and domains from keywords
        topics, domains = self._infer_metadata(query)

        return SubTask(
            id="task_1",
            question=query,
            strategy=RetrievalStrategy.DIRECT_SEARCH,
            topics=topics,
            domains=domains,
            priority=1,
            estimated_chunks=5,
        )

    async def _generate_subtasks_with_groq(
        self,
        query: str,
        complexity: QueryComplexity,
        context: Optional[Dict[str, Any]],
    ) -> List[SubTask]:
        """
        Generate subtasks using Groq API.

        Args:
            query: User query
            complexity: Query complexity level
            context: Optional context

        Returns:
            List of SubTask objects
        """
        try:
            prompt = self._build_groq_prompt(query, complexity, context)

            response = await self.groq_client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a query planning expert. Break down complex queries into logical subtasks with retrieval strategies.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=2000,
            )

            content = response.choices[0].message.content
            logger.debug(f"Groq response: {content[:200]}...")

            # Parse Groq response
            subtasks = self._parse_groq_response(content)

            if not subtasks:
                logger.warning("Failed to parse Groq response, using fallback")
                return self._generate_subtasks_fallback(query, complexity)

            return subtasks[: self.max_subtasks]

        except Exception as e:
            logger.error(f"Groq API error: {e}", exc_info=True)
            return self._generate_subtasks_fallback(query, complexity)

    def _build_groq_prompt(
        self,
        query: str,
        complexity: QueryComplexity,
        context: Optional[Dict[str, Any]],
    ) -> str:
        """
        Build prompt for Groq API.

        Args:
            query: User query
            complexity: Query complexity
            context: Optional context

        Returns:
            Formatted prompt
        """
        prompt = f"""Analyze this query and break it into subtasks:

Query: "{query}"
Complexity: {complexity.value}

Generate a JSON response with subtasks. Each subtask should have:
- id: unique identifier (task_1, task_2, etc.)
- question: the specific sub-question
- strategy: one of [direct_search, topic_filtered, domain_specific, multi_domain, temporal, comparative, aggregative]
- topics: list of relevant topics from [code, api, database, security, performance, configuration, mathematics, best-practices]
- domains: list of domains from [machine-learning, data-science, backend-development, frontend-development, devops, cloud]
- difficulty: one of [beginner, intermediate, advanced]
- priority: 1 (highest) to 5 (lowest)
- depends_on: list of task IDs this depends on
- estimated_chunks: estimated number of document chunks needed (1-20)

Format as JSON:
{{
  "subtasks": [
    {{
      "id": "task_1",
      "question": "...",
      "strategy": "direct_search",
      "topics": ["code"],
      "domains": ["backend-development"],
      "difficulty": "intermediate",
      "priority": 1,
      "depends_on": [],
      "estimated_chunks": 5
    }}
  ],
  "reasoning": "Brief explanation of the decomposition"
}}

Keep subtasks focused and actionable. Max {self.max_subtasks} subtasks."""

        if context:
            prompt += f"\n\nContext: {json.dumps(context, indent=2)}"

        return prompt

    def _parse_groq_response(self, content: str) -> List[SubTask]:
        """
        Parse Groq API response into SubTask objects.

        Args:
            content: Groq response content

        Returns:
            List of SubTask objects
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
            subtasks_data = data.get("subtasks", [])

            subtasks = []
            for st_data in subtasks_data:
                try:
                    # Parse strategy enum
                    strategy_str = st_data.get("strategy", "direct_search")
                    strategy = RetrievalStrategy(strategy_str)

                    subtask = SubTask(
                        id=st_data.get("id", f"task_{len(subtasks) + 1}"),
                        question=st_data.get("question", ""),
                        strategy=strategy,
                        topics=st_data.get("topics", []),
                        domains=st_data.get("domains", []),
                        difficulty=st_data.get("difficulty"),
                        priority=st_data.get("priority", 1),
                        depends_on=st_data.get("depends_on", []),
                        estimated_chunks=st_data.get("estimated_chunks", 5),
                    )
                    subtasks.append(subtask)
                except Exception as e:
                    logger.warning(f"Failed to parse subtask: {e}")
                    continue

            return subtasks

        except Exception as e:
            logger.error(f"Failed to parse Groq response: {e}")
            return []

    def _generate_subtasks_fallback(
        self,
        query: str,
        complexity: QueryComplexity,
    ) -> List[SubTask]:
        """
        Generate subtasks using fallback heuristics (no Groq API).

        Args:
            query: User query
            complexity: Query complexity

        Returns:
            List of SubTask objects
        """
        query_lower = query.lower()
        subtasks = []

        if complexity == QueryComplexity.MODERATE:
            # Split on "and" or multiple questions
            if " and " in query_lower:
                parts = query.split(" and ")
                for i, part in enumerate(parts[:3]):  # Max 3 parts
                    topics, domains = self._infer_metadata(part)
                    subtasks.append(
                        SubTask(
                            id=f"task_{i + 1}",
                            question=part.strip(),
                            strategy=(
                                RetrievalStrategy.TOPIC_FILTERED
                                if topics
                                else RetrievalStrategy.DIRECT_SEARCH
                            ),
                            topics=topics,
                            domains=domains,
                            priority=i + 1,
                            estimated_chunks=5,
                        )
                    )
            else:
                # Single moderate query
                topics, domains = self._infer_metadata(query)
                subtasks.append(
                    SubTask(
                        id="task_1",
                        question=query,
                        strategy=RetrievalStrategy.TOPIC_FILTERED,
                        topics=topics,
                        domains=domains,
                        priority=1,
                        estimated_chunks=8,
                    )
                )

        elif complexity == QueryComplexity.COMPLEX:
            # Handle comparison queries
            if any(
                kw in query_lower for kw in ["compare", "difference", "versus", "vs"]
            ):
                topics, domains = self._infer_metadata(query)
                subtasks.append(
                    SubTask(
                        id="task_1",
                        question=query,
                        strategy=RetrievalStrategy.COMPARATIVE,
                        topics=topics,
                        domains=domains,
                        priority=1,
                        estimated_chunks=10,
                    )
                )
            else:
                # Generic complex query
                topics, domains = self._infer_metadata(query)
                subtasks.append(
                    SubTask(
                        id="task_1",
                        question=query,
                        strategy=RetrievalStrategy.MULTI_DOMAIN,
                        topics=topics,
                        domains=domains,
                        priority=1,
                        estimated_chunks=15,
                    )
                )

        elif complexity == QueryComplexity.MULTI_STEP:
            # Break into sequential steps
            step_keywords = ["first", "then", "after", "next", "finally"]
            has_explicit_steps = any(kw in query_lower for kw in step_keywords)

            if has_explicit_steps:
                # Try to extract explicit steps
                sentences = query.replace("?", ".").split(".")
                for i, sentence in enumerate(sentences[:3]):
                    if sentence.strip():
                        topics, domains = self._infer_metadata(sentence)
                        depends_on = [f"task_{i}"] if i > 0 else []
                        subtasks.append(
                            SubTask(
                                id=f"task_{i + 1}",
                                question=sentence.strip(),
                                strategy=RetrievalStrategy.DIRECT_SEARCH,
                                topics=topics,
                                domains=domains,
                                priority=i + 1,
                                depends_on=depends_on,
                                estimated_chunks=5,
                            )
                        )
            else:
                # Generic multi-step approach
                topics, domains = self._infer_metadata(query)
                subtasks.append(
                    SubTask(
                        id="task_1",
                        question=query,
                        strategy=RetrievalStrategy.AGGREGATIVE,
                        topics=topics,
                        domains=domains,
                        priority=1,
                        estimated_chunks=12,
                    )
                )

        # Ensure at least one subtask
        if not subtasks:
            topics, domains = self._infer_metadata(query)
            subtasks.append(
                SubTask(
                    id="task_1",
                    question=query,
                    strategy=RetrievalStrategy.DIRECT_SEARCH,
                    topics=topics,
                    domains=domains,
                    priority=1,
                    estimated_chunks=5,
                )
            )

        return subtasks

    def _infer_metadata(self, text: str) -> tuple[List[str], List[str]]:
        """
        Infer topics and domains from text using keywords.

        Args:
            text: Text to analyze

        Returns:
            Tuple of (topics, domains)
        """
        text_lower = text.lower()

        # Topic inference
        topic_keywords = {
            "code": ["code", "programming", "function", "class", "method"],
            "api": ["api", "endpoint", "rest", "http", "request"],
            "database": ["database", "sql", "query", "table", "schema"],
            "security": ["security", "authentication", "authorization", "encrypt"],
            "performance": ["performance", "optimization", "speed", "fast", "slow"],
            "configuration": ["config", "setup", "install", "environment"],
            "mathematics": ["math", "algorithm", "formula", "calculate"],
            "best-practices": ["best practice", "pattern", "convention", "standard"],
        }

        topics = []
        for topic, keywords in topic_keywords.items():
            if any(kw in text_lower for kw in keywords):
                topics.append(topic)

        # Domain inference
        domain_keywords = {
            "machine-learning": [
                "machine learning",
                "ml",
                "model",
                "training",
                "neural",
            ],
            "data-science": ["data science", "analysis", "visualization", "pandas"],
            "backend-development": ["backend", "server", "api", "database"],
            "frontend-development": ["frontend", "ui", "react", "vue", "angular"],
            "devops": ["devops", "docker", "kubernetes", "ci/cd", "deploy"],
            "cloud": ["cloud", "aws", "azure", "gcp", "serverless"],
        }

        domains = []
        for domain, keywords in domain_keywords.items():
            if any(kw in text_lower for kw in keywords):
                domains.append(domain)

        return topics, domains

    def _determine_execution_order(self, subtasks: List[SubTask]) -> List[str]:
        """
        Determine optimal execution order based on dependencies and priorities.

        Args:
            subtasks: List of subtasks

        Returns:
            Ordered list of task IDs
        """
        # Sort by priority first
        sorted_tasks = sorted(subtasks, key=lambda t: (t.priority, t.id))

        # Resolve dependencies using topological sort
        execution_order = []
        completed = set()

        max_iterations = len(sorted_tasks) * 2
        iterations = 0

        while sorted_tasks and iterations < max_iterations:
            iterations += 1
            for task in sorted_tasks[:]:
                # Check if all dependencies are met
                deps_met = all(dep in completed for dep in task.depends_on)

                if deps_met:
                    execution_order.append(task.id)
                    completed.add(task.id)
                    sorted_tasks.remove(task)

        # Add any remaining tasks (circular dependencies or errors)
        for task in sorted_tasks:
            execution_order.append(task.id)

        return execution_order

    def _generate_reasoning(
        self,
        query: str,
        complexity: QueryComplexity,
        subtasks: List[SubTask],
    ) -> str:
        """
        Generate reasoning explanation for the plan.

        Args:
            query: Original query
            complexity: Query complexity
            subtasks: Generated subtasks

        Returns:
            Reasoning explanation
        """
        if complexity == QueryComplexity.SIMPLE:
            return f"Simple query requiring direct semantic search. Single subtask will retrieve relevant chunks."

        elif complexity == QueryComplexity.MODERATE:
            return f"Moderate query with multiple concepts. Decomposed into {len(subtasks)} subtasks for targeted retrieval."

        elif complexity == QueryComplexity.COMPLEX:
            strategies = set(st.strategy.value for st in subtasks)
            return f"Complex query requiring {len(subtasks)} subtasks with {len(strategies)} retrieval strategies. Results will be aggregated for comprehensive answer."

        else:  # MULTI_STEP
            return f"Multi-step query with dependencies. {len(subtasks)} subtasks will be executed sequentially, with each step building on previous results."

    async def analyze_query(self, query: str) -> Dict[str, Any]:
        """
        Analyze query without creating full plan.

        Args:
            query: User query

        Returns:
            Analysis results
        """
        complexity = await self._analyze_complexity(query)
        topics, domains = self._infer_metadata(query)

        return {
            "query": query,
            "complexity": complexity.value,
            "inferred_topics": topics,
            "inferred_domains": domains,
            "word_count": len(query.split()),
            "has_groq": self.groq_client is not None,
        }

    def get_stats(self) -> Dict[str, Any]:
        """
        Get planner agent statistics.

        Returns:
            Dictionary with agent statistics
        """
        return {
            "max_subtasks": self.max_subtasks,
            "has_groq": self.groq_client is not None,
            "model": self.model,
        }


# Convenience function for quick planning
async def quick_plan(query: str) -> ExecutionPlan:
    """
    Quick planning without creating agent instance.

    Args:
        query: User query

    Returns:
        ExecutionPlan
    """
    agent = PlannerAgent()
    return await agent.create_plan(query)
