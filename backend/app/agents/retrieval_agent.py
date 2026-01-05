"""
Retrieval Agent for semantic search and metadata filtering.

This agent provides intelligent document retrieval with:
- Semantic vector search using FAISS
- Metadata filtering (topics, domains, difficulty, recency)
- Confidence thresholding
- Top-k result ranking
- Grounded chunk retrieval with context
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from app.memory import MemoryManager
from app.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class RetrievalResult:
    """
    Result from a retrieval operation.
    
    Attributes:
        chunks: List of retrieved chunks with metadata
        query: Original query string
        total_results: Total number of results found
        filtered_count: Number after filtering
        avg_confidence: Average confidence score
        execution_time_ms: Time taken for retrieval
    """
    chunks: List[Dict[str, Any]]
    query: str
    total_results: int
    filtered_count: int
    avg_confidence: float
    execution_time_ms: float


@dataclass
class RetrievalFilters:
    """
    Filters for retrieval operations.
    
    Attributes:
        topics: Filter by topics (e.g., ['code', 'api'])
        domains: Filter by domains (e.g., ['backend-development'])
        difficulty: Filter by difficulty levels (e.g., ['intermediate', 'advanced'])
        min_date: Minimum creation date (ISO format or datetime)
        max_date: Maximum creation date (ISO format or datetime)
        source: Filter by source identifier
        exclude_topics: Topics to exclude
        exclude_domains: Domains to exclude
    """
    topics: Optional[List[str]] = None
    domains: Optional[List[str]] = None
    difficulty: Optional[List[str]] = None
    min_date: Optional[datetime] = None
    max_date: Optional[datetime] = None
    source: Optional[str] = None
    exclude_topics: Optional[List[str]] = None
    exclude_domains: Optional[List[str]] = None


class RetrievalAgent:
    """
    Agent for intelligent document retrieval.
    
    Features:
    - Semantic vector search with FAISS
    - Metadata filtering and refinement
    - Confidence thresholding
    - Recency-based filtering
    - Top-k result ranking
    """
    
    def __init__(
        self,
        memory_manager: Optional[MemoryManager] = None,
        default_top_k: int = 10,
        default_confidence_threshold: float = 0.5,
    ):
        """
        Initialize retrieval agent.
        
        Args:
            memory_manager: MemoryManager instance (creates new if None)
            default_top_k: Default number of results to return
            default_confidence_threshold: Default minimum confidence score
        """
        self.memory = memory_manager or MemoryManager()
        self.default_top_k = default_top_k
        self.default_confidence_threshold = default_confidence_threshold
        
        logger.info(
            "RetrievalAgent initialized",
            extra={
                "default_top_k": default_top_k,
                "default_confidence_threshold": default_confidence_threshold,
            }
        )
    
    async def search(
        self,
        query: str,
        top_k: Optional[int] = None,
        confidence_threshold: Optional[float] = None,
        filters: Optional[RetrievalFilters] = None,
        include_metadata: bool = True,
        include_embeddings: bool = False,
    ) -> RetrievalResult:
        """
        Perform semantic search with optional filtering.
        
        Args:
            query: Search query string
            top_k: Number of results to return (defaults to default_top_k)
            confidence_threshold: Minimum similarity score (0.0 to 1.0)
            filters: Optional metadata filters
            include_metadata: Include full metadata in results
            include_embeddings: Include embedding vectors in results
            
        Returns:
            RetrievalResult with matched chunks and metadata
            
        Raises:
            ValueError: If query is empty or parameters are invalid
        """
        import time
        start_time = time.time()
        
        # Validate inputs
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")
        
        top_k = top_k or self.default_top_k
        confidence_threshold = confidence_threshold or self.default_confidence_threshold
        
        if top_k < 1:
            raise ValueError("top_k must be at least 1")
        if not 0.0 <= confidence_threshold <= 1.0:
            raise ValueError("confidence_threshold must be between 0.0 and 1.0")
        
        logger.info(
            f"Search query: {query[:100]}...",
            extra={
                "top_k": top_k,
                "confidence_threshold": confidence_threshold,
                "has_filters": filters is not None,
            }
        )
        
        try:
            # Perform vector similarity search
            # Retrieve more results initially for filtering
            initial_k = top_k * 3 if filters else top_k
            
            results = self.memory.similarity_search(
                query=query,
                k=initial_k,
            )
            
            total_results = len(results)
            logger.debug(f"Initial vector search returned {total_results} results")
            
            # Apply confidence threshold
            filtered_results = [
                r for r in results 
                if r.get("similarity_score", 0.0) >= confidence_threshold
            ]
            
            logger.debug(
                f"After confidence threshold: {len(filtered_results)} results"
            )
            
            # Apply metadata filters
            if filters:
                filtered_results = self._apply_filters(filtered_results, filters)
                logger.debug(f"After metadata filtering: {len(filtered_results)} results")
            
            # Limit to top_k
            filtered_results = filtered_results[:top_k]
            
            # Enrich results with context
            enriched_results = self._enrich_results(
                filtered_results,
                include_metadata=include_metadata,
                include_embeddings=include_embeddings,
            )
            
            # Calculate statistics
            avg_confidence = (
                sum(r.get("similarity_score", 0.0) for r in enriched_results) / len(enriched_results)
                if enriched_results else 0.0
            )
            
            execution_time_ms = (time.time() - start_time) * 1000
            
            result = RetrievalResult(
                chunks=enriched_results,
                query=query,
                total_results=total_results,
                filtered_count=len(enriched_results),
                avg_confidence=avg_confidence,
                execution_time_ms=execution_time_ms,
            )
            
            logger.info(
                f"Search complete: {len(enriched_results)} results in {execution_time_ms:.2f}ms",
                extra={
                    "avg_confidence": avg_confidence,
                    "total_results": total_results,
                }
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Search failed: {e}", exc_info=True)
            raise
    
    def _apply_filters(
        self,
        results: List[Dict[str, Any]],
        filters: RetrievalFilters,
    ) -> List[Dict[str, Any]]:
        """
        Apply metadata filters to results.
        
        Args:
            results: List of search results
            filters: Filter criteria
            
        Returns:
            Filtered results
        """
        filtered = results
        
        # Filter by topics
        if filters.topics:
            topics_set = set(filters.topics)
            filtered = [
                r for r in filtered
                if any(
                    topic in topics_set
                    for topic in r.get("metadata", {}).get("tags", [])
                )
            ]
        
        # Filter by domains
        if filters.domains:
            domains_set = set(filters.domains)
            filtered = [
                r for r in filtered
                if r.get("metadata", {}).get("domain") in domains_set
            ]
        
        # Filter by difficulty
        if filters.difficulty:
            difficulty_set = set(filters.difficulty)
            filtered = [
                r for r in filtered
                if r.get("metadata", {}).get("difficulty_level") in difficulty_set
            ]
        
        # Filter by date range
        if filters.min_date or filters.max_date:
            filtered = self._filter_by_date(filtered, filters.min_date, filters.max_date)
        
        # Filter by source
        if filters.source:
            filtered = [
                r for r in filtered
                if r.get("metadata", {}).get("source") == filters.source
            ]
        
        # Exclude topics
        if filters.exclude_topics:
            exclude_topics_set = set(filters.exclude_topics)
            filtered = [
                r for r in filtered
                if not any(
                    topic in exclude_topics_set
                    for topic in r.get("metadata", {}).get("tags", [])
                )
            ]
        
        # Exclude domains
        if filters.exclude_domains:
            exclude_domains_set = set(filters.exclude_domains)
            filtered = [
                r for r in filtered
                if r.get("metadata", {}).get("domain") not in exclude_domains_set
            ]
        
        return filtered
    
    def _filter_by_date(
        self,
        results: List[Dict[str, Any]],
        min_date: Optional[datetime],
        max_date: Optional[datetime],
    ) -> List[Dict[str, Any]]:
        """
        Filter results by creation date.
        
        Args:
            results: List of search results
            min_date: Minimum date (inclusive)
            max_date: Maximum date (inclusive)
            
        Returns:
            Date-filtered results
        """
        filtered = []
        
        for result in results:
            created_at_str = result.get("metadata", {}).get("created_at")
            if not created_at_str:
                continue
            
            try:
                # Parse ISO format date
                if isinstance(created_at_str, str):
                    created_at = datetime.fromisoformat(
                        created_at_str.replace("Z", "+00:00")
                    )
                elif isinstance(created_at_str, datetime):
                    created_at = created_at_str
                else:
                    continue
                
                # Check date range
                if min_date and created_at < min_date:
                    continue
                if max_date and created_at > max_date:
                    continue
                
                filtered.append(result)
                
            except (ValueError, AttributeError) as e:
                logger.warning(f"Failed to parse date: {created_at_str}, error: {e}")
                continue
        
        return filtered
    
    def _enrich_results(
        self,
        results: List[Dict[str, Any]],
        include_metadata: bool,
        include_embeddings: bool,
    ) -> List[Dict[str, Any]]:
        """
        Enrich results with additional context and formatting.
        
        Args:
            results: Raw search results
            include_metadata: Include full metadata
            include_embeddings: Include embedding vectors
            
        Returns:
            Enriched results
        """
        enriched = []
        
        for idx, result in enumerate(results):
            enriched_result = {
                "rank": idx + 1,
                "content": result.get("content", ""),
                "similarity_score": result.get("similarity_score", 0.0),
                "confidence": self._score_to_confidence(result.get("similarity_score", 0.0)),
            }
            
            # Add metadata if requested
            if include_metadata:
                metadata = result.get("metadata", {})
                enriched_result["metadata"] = {
                    "source": metadata.get("source"),
                    "topics": metadata.get("tags", []),
                    "domain": metadata.get("domain"),
                    "difficulty": metadata.get("difficulty_level"),
                    "created_at": metadata.get("created_at"),
                    "key_terms": metadata.get("key_terms", []),
                }
                
                # Add document ID for reference
                enriched_result["document_id"] = result.get("id")
            
            # Add embeddings if requested
            if include_embeddings:
                enriched_result["embedding"] = result.get("embedding")
            
            enriched.append(enriched_result)
        
        return enriched
    
    def _score_to_confidence(self, similarity_score: float) -> str:
        """
        Convert similarity score to confidence level.
        
        Args:
            similarity_score: Cosine similarity score (0.0 to 1.0)
            
        Returns:
            Confidence level: very_high, high, medium, low
        """
        if similarity_score >= 0.85:
            return "very_high"
        elif similarity_score >= 0.70:
            return "high"
        elif similarity_score >= 0.50:
            return "medium"
        else:
            return "low"
    
    async def search_by_topic(
        self,
        query: str,
        topics: List[str],
        top_k: Optional[int] = None,
        confidence_threshold: Optional[float] = None,
    ) -> RetrievalResult:
        """
        Search with topic filtering.
        
        Args:
            query: Search query
            topics: List of topics to filter by
            top_k: Number of results
            confidence_threshold: Minimum confidence
            
        Returns:
            RetrievalResult with topic-filtered chunks
        """
        filters = RetrievalFilters(topics=topics)
        return await self.search(
            query=query,
            top_k=top_k,
            confidence_threshold=confidence_threshold,
            filters=filters,
        )
    
    async def search_recent(
        self,
        query: str,
        days: int = 7,
        top_k: Optional[int] = None,
        confidence_threshold: Optional[float] = None,
    ) -> RetrievalResult:
        """
        Search recent documents (last N days).
        
        Args:
            query: Search query
            days: Number of days to look back
            top_k: Number of results
            confidence_threshold: Minimum confidence
            
        Returns:
            RetrievalResult with recent chunks
        """
        min_date = datetime.now() - timedelta(days=days)
        filters = RetrievalFilters(min_date=min_date)
        
        return await self.search(
            query=query,
            top_k=top_k,
            confidence_threshold=confidence_threshold,
            filters=filters,
        )
    
    async def search_by_domain(
        self,
        query: str,
        domains: List[str],
        top_k: Optional[int] = None,
        confidence_threshold: Optional[float] = None,
    ) -> RetrievalResult:
        """
        Search with domain filtering.
        
        Args:
            query: Search query
            domains: List of domains to filter by
            top_k: Number of results
            confidence_threshold: Minimum confidence
            
        Returns:
            RetrievalResult with domain-filtered chunks
        """
        filters = RetrievalFilters(domains=domains)
        return await self.search(
            query=query,
            top_k=top_k,
            confidence_threshold=confidence_threshold,
            filters=filters,
        )
    
    async def search_by_difficulty(
        self,
        query: str,
        difficulty: List[str],
        top_k: Optional[int] = None,
        confidence_threshold: Optional[float] = None,
    ) -> RetrievalResult:
        """
        Search with difficulty filtering.
        
        Args:
            query: Search query
            difficulty: List of difficulty levels (beginner, intermediate, advanced)
            top_k: Number of results
            confidence_threshold: Minimum confidence
            
        Returns:
            RetrievalResult with difficulty-filtered chunks
        """
        filters = RetrievalFilters(difficulty=difficulty)
        return await self.search(
            query=query,
            top_k=top_k,
            confidence_threshold=confidence_threshold,
            filters=filters,
        )
    
    async def advanced_search(
        self,
        query: str,
        topics: Optional[List[str]] = None,
        domains: Optional[List[str]] = None,
        difficulty: Optional[List[str]] = None,
        min_date: Optional[datetime] = None,
        max_date: Optional[datetime] = None,
        source: Optional[str] = None,
        exclude_topics: Optional[List[str]] = None,
        exclude_domains: Optional[List[str]] = None,
        top_k: Optional[int] = None,
        confidence_threshold: Optional[float] = None,
    ) -> RetrievalResult:
        """
        Advanced search with all available filters.
        
        Args:
            query: Search query
            topics: Filter by topics
            domains: Filter by domains
            difficulty: Filter by difficulty levels
            min_date: Minimum creation date
            max_date: Maximum creation date
            source: Filter by source
            exclude_topics: Topics to exclude
            exclude_domains: Domains to exclude
            top_k: Number of results
            confidence_threshold: Minimum confidence
            
        Returns:
            RetrievalResult with filtered chunks
        """
        filters = RetrievalFilters(
            topics=topics,
            domains=domains,
            difficulty=difficulty,
            min_date=min_date,
            max_date=max_date,
            source=source,
            exclude_topics=exclude_topics,
            exclude_domains=exclude_domains,
        )
        
        return await self.search(
            query=query,
            top_k=top_k,
            confidence_threshold=confidence_threshold,
            filters=filters,
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get retrieval agent statistics.
        
        Returns:
            Dictionary with agent statistics
        """
        return {
            "default_top_k": self.default_top_k,
            "default_confidence_threshold": self.default_confidence_threshold,
            "memory_initialized": self.memory is not None,
        }


# Convenience function for quick searches
async def quick_search(
    query: str,
    top_k: int = 5,
    confidence_threshold: float = 0.5,
) -> RetrievalResult:
    """
    Quick search without creating agent instance.
    
    Args:
        query: Search query
        top_k: Number of results
        confidence_threshold: Minimum confidence
        
    Returns:
        RetrievalResult
    """
    agent = RetrievalAgent()
    return await agent.search(
        query=query,
        top_k=top_k,
        confidence_threshold=confidence_threshold,
    )
