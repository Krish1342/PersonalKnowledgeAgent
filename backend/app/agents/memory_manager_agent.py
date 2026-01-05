"""
Memory Manager Agent for Personal Knowledge Agent

Intelligently manages the knowledge base lifecycle: deciding what to store,
merging duplicates, updating confidence scores, handling versioning, and pruning
low-value memory.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Tuple
from datetime import datetime, timedelta
from enum import Enum
import re
from groq import AsyncGroq
import os
import hashlib


class StorageDecision(Enum):
    """Decision on whether to store new knowledge"""

    STORE = "store"  # Store as new knowledge
    MERGE = "merge"  # Merge with existing knowledge
    UPDATE = "update"  # Update existing knowledge
    REJECT = "reject"  # Reject (low quality/duplicate)
    VERSION = "version"  # Create new version


class QualityLevel(Enum):
    """Quality assessment levels"""

    EXCELLENT = "excellent"  # 90-100
    GOOD = "good"  # 75-89
    ACCEPTABLE = "acceptable"  # 60-74
    POOR = "poor"  # 40-59
    UNACCEPTABLE = "unacceptable"  # <40


class PruneReason(Enum):
    """Reasons for pruning memory"""

    LOW_QUALITY = "low_quality"
    NEVER_ACCESSED = "never_accessed"
    OUTDATED = "outdated"
    DUPLICATE = "duplicate"
    LOW_CONFIDENCE = "low_confidence"
    SUPERSEDED = "superseded"


@dataclass
class QualityAssessment:
    """Assessment of knowledge quality"""

    score: float  # 0-100
    level: QualityLevel
    factors: Dict[str, float]  # Individual quality factors
    issues: List[str] = field(default_factory=list)
    strengths: List[str] = field(default_factory=list)


@dataclass
class DuplicateMatch:
    """Represents a potential duplicate"""

    existing_id: str
    similarity_score: float  # 0-1
    match_type: str  # "exact", "near", "semantic"
    existing_content: str
    recommendation: str  # "merge", "keep_both", "prefer_existing", "prefer_new"


@dataclass
class StorageRecommendation:
    """Recommendation for storing new knowledge"""

    decision: StorageDecision
    reason: str
    quality: QualityAssessment
    duplicates: List[DuplicateMatch] = field(default_factory=list)
    merge_target_id: Optional[str] = None
    confidence_adjustment: float = 0.0  # +/- adjustment to confidence
    metadata_updates: Dict = field(default_factory=dict)


@dataclass
class VersionInfo:
    """Version information for knowledge"""

    version_id: str
    parent_version: Optional[str]
    created_at: datetime
    changes: str
    reason: str


@dataclass
class PruneCandidate:
    """Candidate for pruning"""

    chunk_id: str
    reason: PruneReason
    score: float  # Higher = more likely to prune
    details: Dict
    recommendation: str  # "prune", "keep", "archive"


@dataclass
class MemoryStats:
    """Memory management statistics"""

    total_chunks: int
    high_quality_chunks: int
    low_quality_chunks: int
    never_accessed: int
    outdated: int
    duplicates: int
    avg_confidence: float
    avg_access_count: float
    storage_size_estimate: int  # In bytes


class MemoryManagerAgent:
    """
    Agent that intelligently manages knowledge base lifecycle.

    Responsibilities:
    - Evaluate quality of new knowledge before storing
    - Detect and merge duplicate knowledge
    - Update confidence scores based on usage and validation
    - Handle versioning for knowledge updates
    - Prune low-value memory to maintain quality
    """

    def __init__(
        self,
        memory_manager,  # Reference to storage MemoryManager
        groq_api_key: Optional[str] = None,
        model: str = "llama-3.3-70b-versatile",
        quality_threshold: float = 60.0,
        similarity_threshold: float = 0.85,
        use_llm: bool = True,
    ):
        """
        Initialize Memory Manager Agent.

        Args:
            memory_manager: Storage MemoryManager instance for data access
            groq_api_key: Groq API key for intelligent decisions
            model: Groq model to use
            quality_threshold: Minimum quality score to store (0-100)
            similarity_threshold: Similarity threshold for duplicate detection (0-1)
            use_llm: Whether to use LLM for intelligent decisions
        """
        self.memory_manager = memory_manager
        self.groq_api_key = groq_api_key or os.getenv("GROQ_API_KEY")
        self.model = model
        self.quality_threshold = quality_threshold
        self.similarity_threshold = similarity_threshold
        self.use_llm = use_llm

        if self.groq_api_key and self.use_llm:
            self.client = AsyncGroq(api_key=self.groq_api_key)
        else:
            self.client = None

    async def evaluate_for_storage(
        self,
        content: str,
        metadata: Optional[Dict] = None,
        source: Optional[str] = None,
    ) -> StorageRecommendation:
        """
        Evaluate whether new knowledge should be stored.

        Args:
            content: Content to evaluate
            metadata: Optional metadata
            source: Optional source information

        Returns:
            StorageRecommendation with decision and details
        """
        # Assess quality
        quality = await self._assess_quality(content, metadata, source)

        # Check for duplicates
        duplicates = await self._find_duplicates(content, metadata)

        # Make storage decision
        decision, reason, merge_target = self._make_storage_decision(
            quality, duplicates
        )

        # Calculate confidence adjustment
        confidence_adj = self._calculate_confidence_adjustment(quality, duplicates)

        # Prepare metadata updates
        metadata_updates = {
            "quality_score": quality.score,
            "quality_level": quality.level.value,
            "ingestion_timestamp": datetime.utcnow().isoformat(),
            "last_accessed": datetime.utcnow().isoformat(),
            "access_count": 0,
            "confidence": min(100, max(0, 50 + confidence_adj)),  # Base 50 + adjustment
        }

        if source:
            metadata_updates["source"] = source

        return StorageRecommendation(
            decision=decision,
            reason=reason,
            quality=quality,
            duplicates=duplicates,
            merge_target_id=merge_target,
            confidence_adjustment=confidence_adj,
            metadata_updates=metadata_updates,
        )

    async def _assess_quality(
        self,
        content: str,
        metadata: Optional[Dict] = None,
        source: Optional[str] = None,
    ) -> QualityAssessment:
        """Assess quality of content"""
        if self.client and self.use_llm:
            try:
                return await self._assess_quality_with_llm(content, metadata, source)
            except Exception as e:
                print(f"LLM quality assessment failed: {e}, using fallback")

        return self._assess_quality_heuristic(content, metadata, source)

    async def _assess_quality_with_llm(
        self,
        content: str,
        metadata: Optional[Dict] = None,
        source: Optional[str] = None,
    ) -> QualityAssessment:
        """Assess quality using LLM"""
        meta_text = ""
        if metadata:
            meta_text = f"\n\nMetadata: {metadata}"
        if source:
            meta_text += f"\nSource: {source}"

        prompt = f"""Assess the quality of the following content for a knowledge base.

Content:
{content[:2000]}  # Limit length
{meta_text}

Evaluate these factors (score 0-100 for each):
1. Informativeness: How much useful information does it contain?
2. Clarity: How clear and understandable is it?
3. Accuracy: How accurate does it appear (look for claims that need verification)?
4. Completeness: How complete is the information?
5. Relevance: How relevant is it for a knowledge base?

Return ONLY a JSON object:
{{
    "overall_score": 75,
    "informativeness": 80,
    "clarity": 85,
    "accuracy": 70,
    "completeness": 65,
    "relevance": 75,
    "issues": ["List of issues"],
    "strengths": ["List of strengths"]
}}

Response:"""

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=500,
        )

        content_text = response.choices[0].message.content.strip()

        # Parse response
        import json

        try:
            result = json.loads(content_text)

            score = float(result.get("overall_score", 50))
            factors = {
                "informativeness": float(result.get("informativeness", 50)),
                "clarity": float(result.get("clarity", 50)),
                "accuracy": float(result.get("accuracy", 50)),
                "completeness": float(result.get("completeness", 50)),
                "relevance": float(result.get("relevance", 50)),
            }

            level = self._score_to_level(score)

            return QualityAssessment(
                score=score,
                level=level,
                factors=factors,
                issues=result.get("issues", []),
                strengths=result.get("strengths", []),
            )
        except Exception as e:
            print(f"Failed to parse LLM quality assessment: {e}")
            return self._assess_quality_heuristic(content, metadata, source)

    def _assess_quality_heuristic(
        self,
        content: str,
        metadata: Optional[Dict] = None,
        source: Optional[str] = None,
    ) -> QualityAssessment:
        """Assess quality using heuristic rules"""
        factors = {}
        issues = []
        strengths = []

        # Informativeness: based on length and word diversity
        word_count = len(content.split())
        unique_words = len(set(content.lower().split()))

        if word_count < 10:
            factors["informativeness"] = 20
            issues.append("Content is too short")
        elif word_count < 50:
            factors["informativeness"] = 50
        elif word_count < 200:
            factors["informativeness"] = 75
        else:
            factors["informativeness"] = 90
            strengths.append("Comprehensive content")

        # Clarity: based on sentence structure
        sentences = re.split(r"[.!?]+", content)
        avg_sentence_length = word_count / max(
            1, len([s for s in sentences if s.strip()])
        )

        if avg_sentence_length > 40:
            factors["clarity"] = 50
            issues.append("Sentences are too long")
        elif avg_sentence_length < 5:
            factors["clarity"] = 60
            issues.append("Sentences are too short")
        else:
            factors["clarity"] = 85
            strengths.append("Well-structured sentences")

        # Accuracy: check for uncertainty markers
        uncertainty_markers = [
            "maybe",
            "perhaps",
            "possibly",
            "might",
            "could be",
            "unclear",
        ]
        uncertainty_count = sum(
            1 for marker in uncertainty_markers if marker in content.lower()
        )

        if uncertainty_count > 3:
            factors["accuracy"] = 50
            issues.append("High uncertainty in content")
        elif uncertainty_count > 1:
            factors["accuracy"] = 70
        else:
            factors["accuracy"] = 85
            strengths.append("Definitive statements")

        # Completeness: check for incomplete sentences/thoughts
        incomplete_markers = ["...", "etc", "and so on", "to be continued"]
        incomplete_count = sum(
            1 for marker in incomplete_markers if marker in content.lower()
        )

        if incomplete_count > 2:
            factors["completeness"] = 50
            issues.append("Content appears incomplete")
        elif incomplete_count > 0:
            factors["completeness"] = 70
        else:
            factors["completeness"] = 85

        # Relevance: check for metadata and source
        if metadata and len(metadata) > 2:
            factors["relevance"] = 85
            strengths.append("Rich metadata provided")
        elif metadata:
            factors["relevance"] = 70
        else:
            factors["relevance"] = 60
            issues.append("Limited metadata")

        # Calculate overall score (weighted average)
        overall_score = (
            factors["informativeness"] * 0.25
            + factors["clarity"] * 0.20
            + factors["accuracy"] * 0.25
            + factors["completeness"] * 0.15
            + factors["relevance"] * 0.15
        )

        level = self._score_to_level(overall_score)

        return QualityAssessment(
            score=overall_score,
            level=level,
            factors=factors,
            issues=issues,
            strengths=strengths,
        )

    def _score_to_level(self, score: float) -> QualityLevel:
        """Convert score to quality level"""
        if score >= 90:
            return QualityLevel.EXCELLENT
        elif score >= 75:
            return QualityLevel.GOOD
        elif score >= 60:
            return QualityLevel.ACCEPTABLE
        elif score >= 40:
            return QualityLevel.POOR
        else:
            return QualityLevel.UNACCEPTABLE

    async def _find_duplicates(
        self, content: str, metadata: Optional[Dict] = None
    ) -> List[DuplicateMatch]:
        """Find potential duplicates in existing knowledge base"""
        duplicates = []

        try:
            # Search for similar content
            results = await self.memory_manager.search(
                query=content[:500], top_k=5  # Use first 500 chars
            )

            for result in results:
                existing_content = result.get("content", result.get("text", ""))

                # Calculate similarity
                similarity = self._calculate_similarity(content, existing_content)

                if similarity >= self.similarity_threshold:
                    match_type = "exact" if similarity >= 0.95 else "near"

                    # Determine recommendation
                    if similarity >= 0.98:
                        recommendation = "merge"
                    elif similarity >= 0.90:
                        recommendation = "prefer_existing"
                    else:
                        recommendation = "keep_both"

                    duplicates.append(
                        DuplicateMatch(
                            existing_id=result.get("id", ""),
                            similarity_score=similarity,
                            match_type=match_type,
                            existing_content=existing_content,
                            recommendation=recommendation,
                        )
                    )

        except Exception as e:
            print(f"Duplicate search failed: {e}")

        return duplicates

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two texts (simple implementation)"""
        # Normalize texts
        text1 = text1.lower().strip()
        text2 = text2.lower().strip()

        # Exact match
        if text1 == text2:
            return 1.0

        # Character-level similarity (Jaccard)
        set1 = set(text1.split())
        set2 = set(text2.split())

        if not set1 or not set2:
            return 0.0

        intersection = len(set1 & set2)
        union = len(set1 | set2)

        jaccard = intersection / union if union > 0 else 0.0

        # Also consider length similarity
        len_ratio = min(len(text1), len(text2)) / max(len(text1), len(text2))

        # Combined score
        return jaccard * 0.7 + len_ratio * 0.3

    def _make_storage_decision(
        self, quality: QualityAssessment, duplicates: List[DuplicateMatch]
    ) -> Tuple[StorageDecision, str, Optional[str]]:
        """Make decision on how to store content"""
        merge_target = None

        # Check quality threshold
        if quality.score < self.quality_threshold:
            return (
                StorageDecision.REJECT,
                f"Quality score ({quality.score:.1f}) below threshold ({self.quality_threshold})",
                None,
            )

        # Check for exact duplicates
        exact_duplicates = [d for d in duplicates if d.similarity_score >= 0.95]

        if exact_duplicates:
            merge_target = exact_duplicates[0].existing_id
            return (
                StorageDecision.MERGE,
                f"Near-exact duplicate found (similarity: {exact_duplicates[0].similarity_score:.2%})",
                merge_target,
            )

        # Check for near duplicates
        near_duplicates = [d for d in duplicates if 0.85 <= d.similarity_score < 0.95]

        if near_duplicates:
            merge_target = near_duplicates[0].existing_id
            return (
                StorageDecision.VERSION,
                f"Similar content found, creating new version (similarity: {near_duplicates[0].similarity_score:.2%})",
                merge_target,
            )

        # Store as new knowledge
        return (
            StorageDecision.STORE,
            f"Quality acceptable ({quality.level.value}), no significant duplicates",
            None,
        )

    def _calculate_confidence_adjustment(
        self, quality: QualityAssessment, duplicates: List[DuplicateMatch]
    ) -> float:
        """Calculate confidence score adjustment"""
        adjustment = 0.0

        # Quality-based adjustment
        if quality.level == QualityLevel.EXCELLENT:
            adjustment += 30
        elif quality.level == QualityLevel.GOOD:
            adjustment += 15
        elif quality.level == QualityLevel.ACCEPTABLE:
            adjustment += 0
        elif quality.level == QualityLevel.POOR:
            adjustment -= 15

        # Duplicate-based adjustment (having similar content increases confidence)
        if duplicates:
            avg_similarity = sum(d.similarity_score for d in duplicates) / len(
                duplicates
            )
            if avg_similarity >= 0.7:
                adjustment += 10

        return adjustment

    async def merge_duplicates(
        self, chunk_ids: List[str], strategy: str = "keep_best"
    ) -> Dict:
        """
        Merge duplicate chunks.

        Args:
            chunk_ids: List of chunk IDs to merge
            strategy: Merge strategy ("keep_best", "combine", "newest")

        Returns:
            Dict with merge results
        """
        if len(chunk_ids) < 2:
            return {"error": "Need at least 2 chunks to merge"}

        try:
            # Fetch chunks
            chunks = []
            for chunk_id in chunk_ids:
                chunk = await self._get_chunk_by_id(chunk_id)
                if chunk:
                    chunks.append(chunk)

            if len(chunks) < 2:
                return {"error": "Could not fetch chunks"}

            # Apply merge strategy
            if strategy == "keep_best":
                merged = self._merge_keep_best(chunks)
            elif strategy == "combine":
                merged = self._merge_combine(chunks)
            elif strategy == "newest":
                merged = self._merge_newest(chunks)
            else:
                return {"error": f"Unknown strategy: {strategy}"}

            # Delete old chunks and store merged
            deleted_ids = [c["id"] for c in chunks]
            # Note: actual deletion would happen here via memory_manager

            return {
                "success": True,
                "merged_content": merged,
                "deleted_ids": deleted_ids,
                "strategy": strategy,
            }

        except Exception as e:
            return {"error": str(e)}

    async def _get_chunk_by_id(self, chunk_id: str) -> Optional[Dict]:
        """Get chunk by ID (placeholder - would use memory_manager)"""
        # This would fetch from memory_manager
        return None

    def _merge_keep_best(self, chunks: List[Dict]) -> Dict:
        """Keep the highest quality chunk"""
        best_chunk = max(
            chunks, key=lambda c: c.get("metadata", {}).get("quality_score", 0)
        )

        # Update metadata to reflect merge
        merged = best_chunk.copy()
        merged["metadata"]["merged_from"] = [
            c["id"] for c in chunks if c["id"] != best_chunk["id"]
        ]
        merged["metadata"]["merge_date"] = datetime.utcnow().isoformat()

        return merged

    def _merge_combine(self, chunks: List[Dict]) -> Dict:
        """Combine content from all chunks"""
        combined_content = "\n\n---\n\n".join(
            [c.get("content", c.get("text", "")) for c in chunks]
        )

        # Use metadata from highest quality chunk
        best_chunk = max(
            chunks, key=lambda c: c.get("metadata", {}).get("quality_score", 0)
        )

        merged = best_chunk.copy()
        merged["content"] = combined_content
        merged["metadata"]["merged_from"] = [c["id"] for c in chunks]
        merged["metadata"]["merge_date"] = datetime.utcnow().isoformat()
        merged["metadata"]["merge_strategy"] = "combine"

        return merged

    def _merge_newest(self, chunks: List[Dict]) -> Dict:
        """Keep the newest chunk"""
        newest_chunk = max(
            chunks, key=lambda c: c.get("metadata", {}).get("created_at", "1970-01-01")
        )

        merged = newest_chunk.copy()
        merged["metadata"]["merged_from"] = [
            c["id"] for c in chunks if c["id"] != newest_chunk["id"]
        ]
        merged["metadata"]["merge_date"] = datetime.utcnow().isoformat()

        return merged

    async def update_confidence(
        self,
        chunk_id: str,
        validation_passed: bool,
        access_count_delta: int = 1,
        feedback_score: Optional[float] = None,
    ) -> float:
        """
        Update confidence score for a chunk.

        Args:
            chunk_id: Chunk ID
            validation_passed: Whether validation passed
            access_count_delta: How much to increment access count
            feedback_score: Optional user feedback (0-100)

        Returns:
            New confidence score
        """
        # Get current chunk metadata
        chunk = await self._get_chunk_by_id(chunk_id)
        if not chunk:
            return 0.0

        current_confidence = chunk.get("metadata", {}).get("confidence", 50.0)
        current_access = chunk.get("metadata", {}).get("access_count", 0)

        # Calculate adjustment
        adjustment = 0.0

        # Validation impact
        if validation_passed:
            adjustment += 5.0
        else:
            adjustment -= 10.0

        # Access frequency impact (diminishing returns)
        access_boost = min(10, (current_access + access_count_delta) * 0.5)
        adjustment += access_boost

        # Feedback impact
        if feedback_score is not None:
            feedback_impact = (feedback_score - 50) * 0.2
            adjustment += feedback_impact

        # Calculate new confidence (bounded 0-100)
        new_confidence = max(0, min(100, current_confidence + adjustment))

        # Update metadata (would use memory_manager)
        # await self.memory_manager.update_metadata(chunk_id, {
        #     'confidence': new_confidence,
        #     'access_count': current_access + access_count_delta,
        #     'last_accessed': datetime.utcnow().isoformat()
        # })

        return new_confidence

    async def create_version(
        self, parent_id: str, new_content: str, changes: str, reason: str
    ) -> Dict:
        """
        Create a new version of existing knowledge.

        Args:
            parent_id: ID of parent chunk
            new_content: Updated content
            changes: Description of changes
            reason: Reason for new version

        Returns:
            Dict with new version info
        """
        parent = await self._get_chunk_by_id(parent_id)
        if not parent:
            return {"error": "Parent chunk not found"}

        # Generate version ID
        version_id = hashlib.sha256(
            f"{parent_id}:{datetime.utcnow().isoformat()}".encode()
        ).hexdigest()[:16]

        # Create version metadata
        version_info = VersionInfo(
            version_id=version_id,
            parent_version=parent_id,
            created_at=datetime.utcnow(),
            changes=changes,
            reason=reason,
        )

        # Create new chunk with version info
        new_chunk = {
            "content": new_content,
            "metadata": {
                **parent.get("metadata", {}),
                "version_id": version_id,
                "parent_version": parent_id,
                "version_created_at": version_info.created_at.isoformat(),
                "version_changes": changes,
                "version_reason": reason,
                "version_number": parent.get("metadata", {}).get("version_number", 0)
                + 1,
            },
        }

        return {"success": True, "version_info": version_info, "new_chunk": new_chunk}

    async def prune_memory(
        self,
        max_chunks: Optional[int] = None,
        min_quality: float = 40.0,
        min_confidence: float = 30.0,
        inactive_days: int = 180,
    ) -> Dict:
        """
        Prune low-value memory from knowledge base.

        Args:
            max_chunks: Maximum chunks to keep (None = no limit)
            min_quality: Minimum quality score to keep
            min_confidence: Minimum confidence score to keep
            inactive_days: Days of inactivity before considering for pruning

        Returns:
            Dict with pruning results
        """
        # Get all chunks (would use memory_manager)
        # all_chunks = await self.memory_manager.get_all_chunks()
        all_chunks = []  # Placeholder

        # Identify prune candidates
        candidates = await self._identify_prune_candidates(
            all_chunks, min_quality, min_confidence, inactive_days
        )

        # Sort by prune score (highest = most likely to prune)
        candidates.sort(key=lambda c: c.score, reverse=True)

        # Determine what to prune
        to_prune = []
        to_archive = []

        for candidate in candidates:
            if candidate.recommendation == "prune":
                to_prune.append(candidate.chunk_id)
            elif candidate.recommendation == "archive":
                to_archive.append(candidate.chunk_id)

        # If max_chunks specified, prune additional if needed
        if max_chunks and len(all_chunks) - len(to_prune) > max_chunks:
            additional_prune = len(all_chunks) - len(to_prune) - max_chunks
            # Take lowest confidence chunks
            remaining = [c for c in all_chunks if c["id"] not in to_prune]
            remaining.sort(key=lambda c: c.get("metadata", {}).get("confidence", 0))
            to_prune.extend([c["id"] for c in remaining[:additional_prune]])

        # Execute pruning (would use memory_manager)
        # for chunk_id in to_prune:
        #     await self.memory_manager.delete_chunk(chunk_id)

        return {
            "success": True,
            "pruned_count": len(to_prune),
            "archived_count": len(to_archive),
            "pruned_ids": to_prune,
            "archived_ids": to_archive,
            "candidates_evaluated": len(candidates),
        }

    async def _identify_prune_candidates(
        self,
        chunks: List[Dict],
        min_quality: float,
        min_confidence: float,
        inactive_days: int,
    ) -> List[PruneCandidate]:
        """Identify candidates for pruning"""
        candidates = []
        cutoff_date = datetime.utcnow() - timedelta(days=inactive_days)

        for chunk in chunks:
            metadata = chunk.get("metadata", {})
            chunk_id = chunk.get("id", "")

            quality = metadata.get("quality_score", 50)
            confidence = metadata.get("confidence", 50)
            access_count = metadata.get("access_count", 0)
            last_accessed = metadata.get("last_accessed")

            prune_score = 0.0
            reasons = []

            # Quality check
            if quality < min_quality:
                prune_score += 30
                reasons.append(PruneReason.LOW_QUALITY)

            # Confidence check
            if confidence < min_confidence:
                prune_score += 25
                reasons.append(PruneReason.LOW_CONFIDENCE)

            # Access check
            if access_count == 0:
                prune_score += 20
                reasons.append(PruneReason.NEVER_ACCESSED)

            # Inactivity check
            if last_accessed:
                try:
                    last_access_date = datetime.fromisoformat(last_accessed)
                    if last_access_date < cutoff_date:
                        prune_score += 15
                        reasons.append(PruneReason.OUTDATED)
                except:
                    pass

            if prune_score > 0:
                # Determine recommendation
                if prune_score >= 50:
                    recommendation = "prune"
                elif prune_score >= 30:
                    recommendation = "archive"
                else:
                    recommendation = "keep"

                candidates.append(
                    PruneCandidate(
                        chunk_id=chunk_id,
                        reason=reasons[0] if reasons else PruneReason.LOW_QUALITY,
                        score=prune_score,
                        details={
                            "quality": quality,
                            "confidence": confidence,
                            "access_count": access_count,
                            "last_accessed": last_accessed,
                            "all_reasons": [r.value for r in reasons],
                        },
                        recommendation=recommendation,
                    )
                )

        return candidates

    async def get_memory_stats(self) -> MemoryStats:
        """Get current memory statistics"""
        # Would fetch from memory_manager
        # all_chunks = await self.memory_manager.get_all_chunks()
        all_chunks = []  # Placeholder

        if not all_chunks:
            return MemoryStats(
                total_chunks=0,
                high_quality_chunks=0,
                low_quality_chunks=0,
                never_accessed=0,
                outdated=0,
                duplicates=0,
                avg_confidence=0.0,
                avg_access_count=0.0,
                storage_size_estimate=0,
            )

        high_quality = sum(
            1 for c in all_chunks if c.get("metadata", {}).get("quality_score", 0) >= 75
        )

        low_quality = sum(
            1 for c in all_chunks if c.get("metadata", {}).get("quality_score", 0) < 60
        )

        never_accessed = sum(
            1 for c in all_chunks if c.get("metadata", {}).get("access_count", 0) == 0
        )

        # Calculate averages
        confidences = [c.get("metadata", {}).get("confidence", 0) for c in all_chunks]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0

        access_counts = [
            c.get("metadata", {}).get("access_count", 0) for c in all_chunks
        ]
        avg_access = sum(access_counts) / len(access_counts) if access_counts else 0

        # Estimate storage size (rough estimate)
        total_size = sum(
            len(c.get("content", c.get("text", "")).encode("utf-8")) for c in all_chunks
        )

        return MemoryStats(
            total_chunks=len(all_chunks),
            high_quality_chunks=high_quality,
            low_quality_chunks=low_quality,
            never_accessed=never_accessed,
            outdated=0,  # Would calculate based on timestamps
            duplicates=0,  # Would calculate based on similarity
            avg_confidence=avg_confidence,
            avg_access_count=avg_access,
            storage_size_estimate=total_size,
        )


# Example usage
if __name__ == "__main__":
    import asyncio

    async def main():
        # Mock memory manager
        class MockMemoryManager:
            async def search(self, query, top_k=5):
                return []

        # Initialize agent
        agent = MemoryManagerAgent(
            memory_manager=MockMemoryManager(),
            quality_threshold=60.0,
            similarity_threshold=0.85,
        )

        # Example: Evaluate content for storage
        content = """
        Python is a high-level, interpreted programming language created by 
        Guido van Rossum and first released in 1991. It emphasizes code 
        readability with its notable use of significant whitespace. Python 
        supports multiple programming paradigms including procedural, 
        object-oriented, and functional programming.
        """

        recommendation = await agent.evaluate_for_storage(
            content=content,
            metadata={"topic": "programming", "difficulty": "beginner"},
            source="Python Documentation",
        )

        print("=" * 60)
        print("STORAGE RECOMMENDATION")
        print("=" * 60)
        print(f"Decision: {recommendation.decision.value}")
        print(f"Reason: {recommendation.reason}")
        print(f"\nQuality Assessment:")
        print(f"  Score: {recommendation.quality.score:.1f}/100")
        print(f"  Level: {recommendation.quality.level.value}")
        print(f"\nQuality Factors:")
        for factor, score in recommendation.quality.factors.items():
            print(f"  {factor}: {score:.1f}")

        if recommendation.quality.issues:
            print(f"\nIssues:")
            for issue in recommendation.quality.issues:
                print(f"  - {issue}")

        if recommendation.quality.strengths:
            print(f"\nStrengths:")
            for strength in recommendation.quality.strengths:
                print(f"  - {strength}")

        if recommendation.duplicates:
            print(f"\nDuplicates Found: {len(recommendation.duplicates)}")
            for dup in recommendation.duplicates:
                print(f"  - Similarity: {dup.similarity_score:.2%}")
                print(f"    Recommendation: {dup.recommendation}")

        print(f"\nMetadata Updates:")
        for key, value in recommendation.metadata_updates.items():
            print(f"  {key}: {value}")

        # Example: Memory statistics
        print("\n" + "=" * 60)
        print("MEMORY STATISTICS")
        print("=" * 60)
        stats = await agent.get_memory_stats()
        print(f"Total Chunks: {stats.total_chunks}")
        print(f"High Quality: {stats.high_quality_chunks}")
        print(f"Low Quality: {stats.low_quality_chunks}")
        print(f"Never Accessed: {stats.never_accessed}")
        print(f"Avg Confidence: {stats.avg_confidence:.1f}")
        print(f"Avg Access Count: {stats.avg_access_count:.1f}")
        print(f"Storage Size: {stats.storage_size_estimate:,} bytes")

    asyncio.run(main())
