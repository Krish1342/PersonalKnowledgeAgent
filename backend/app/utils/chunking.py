import re
from typing import List, Optional
from dataclasses import dataclass
from enum import Enum


class ContentType(Enum):
    """Supported content types for chunking."""

    TEXT = "text"
    MARKDOWN = "markdown"


@dataclass
class ChunkingConfig:
    """Configuration for text chunking."""

    chunk_size: int = 1000
    chunk_overlap: int = 200
    min_chunk_size: int = 100
    content_type: ContentType = ContentType.TEXT


@dataclass
class Chunk:
    """A text chunk with metadata."""

    content: str
    index: int
    start_char: int
    end_char: int
    metadata: dict


class TextChunker:
    """
    Semantic text chunker supporting plain text and Markdown.

    Handles normalization, whitespace cleanup, and overlap-based chunking.
    """

    # Markdown header patterns for semantic splitting
    _MD_HEADER_PATTERN = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)
    _MD_CODE_BLOCK_PATTERN = re.compile(r"```[\s\S]*?```", re.MULTILINE)
    _MD_HORIZONTAL_RULE = re.compile(r"^(-{3,}|\*{3,}|_{3,})$", re.MULTILINE)

    def __init__(self, config: Optional[ChunkingConfig] = None) -> None:
        """
        Initialize the chunker.

        Args:
            config: Chunking configuration. Uses defaults if not provided.
        """
        self.config = config or ChunkingConfig()

    def normalize_text(self, text: str) -> str:
        """
        Normalize text by cleaning whitespace and standardizing formatting.

        Args:
            text: Raw input text.

        Returns:
            Normalized text.
        """
        if not text:
            return ""

        # Replace tabs with spaces
        text = text.replace("\t", "    ")

        # Normalize line endings
        text = text.replace("\r\n", "\n").replace("\r", "\n")

        # Remove excessive blank lines (more than 2 consecutive)
        text = re.sub(r"\n{3,}", "\n\n", text)

        # Remove trailing whitespace from each line
        text = "\n".join(line.rstrip() for line in text.split("\n"))

        # Remove excessive spaces (more than 2 consecutive, preserve indentation)
        text = re.sub(r"(?<=\S)  +(?=\S)", " ", text)

        return text.strip()

    def _detect_content_type(self, text: str) -> ContentType:
        """
        Auto-detect if content is Markdown based on patterns.

        Args:
            text: Input text.

        Returns:
            Detected content type.
        """
        md_indicators = [
            self._MD_HEADER_PATTERN.search(text),
            self._MD_CODE_BLOCK_PATTERN.search(text),
            re.search(r"\[.+\]\(.+\)", text),  # Links
            re.search(r"^\s*[-*+]\s+", text, re.MULTILINE),  # Lists
            re.search(r"^\s*\d+\.\s+", text, re.MULTILINE),  # Numbered lists
        ]

        if sum(1 for indicator in md_indicators if indicator) >= 2:
            return ContentType.MARKDOWN

        return ContentType.TEXT

    def _find_semantic_breaks(self, text: str, content_type: ContentType) -> List[int]:
        """
        Find semantic break points in text.

        Args:
            text: Normalized text.
            content_type: Type of content.

        Returns:
            List of character positions for semantic breaks.
        """
        breaks: List[int] = []

        if content_type == ContentType.MARKDOWN:
            # Headers are strong break points
            for match in self._MD_HEADER_PATTERN.finditer(text):
                breaks.append(match.start())

            # Horizontal rules
            for match in self._MD_HORIZONTAL_RULE.finditer(text):
                breaks.append(match.start())

        # Paragraph breaks (double newlines) for all content types
        for match in re.finditer(r"\n\n+", text):
            breaks.append(match.start())

        return sorted(set(breaks))

    def _find_best_break(
        self,
        text: str,
        start: int,
        target_end: int,
        semantic_breaks: List[int],
    ) -> int:
        """
        Find the best break point near the target end position.

        Args:
            text: Full text.
            start: Start position of current chunk.
            target_end: Target end position based on chunk_size.
            semantic_breaks: List of semantic break positions.

        Returns:
            Best break position.
        """
        # Look for semantic breaks within range
        for break_pos in semantic_breaks:
            if start < break_pos <= target_end:
                # Prefer semantic break if it's reasonably close to target
                if break_pos >= target_end - self.config.chunk_overlap:
                    return break_pos

        # Fall back to sentence boundaries
        search_start = max(start, target_end - self.config.chunk_overlap)
        search_text = text[search_start : target_end + self.config.chunk_overlap]

        # Look for sentence endings
        sentence_ends = list(re.finditer(r"[.!?]\s+", search_text))
        if sentence_ends:
            last_sentence = sentence_ends[-1]
            return search_start + last_sentence.end()

        # Fall back to word boundaries
        word_breaks = list(re.finditer(r"\s+", search_text))
        if word_breaks:
            last_word = word_breaks[-1]
            return search_start + last_word.start()

        # Last resort: hard break at target
        return min(target_end, len(text))

    def chunk(
        self,
        text: str,
        metadata: Optional[dict] = None,
        auto_detect_type: bool = True,
    ) -> List[Chunk]:
        """
        Split text into semantic chunks with overlap.

        Args:
            text: Input text to chunk.
            metadata: Optional metadata to attach to all chunks.
            auto_detect_type: Whether to auto-detect Markdown content.

        Returns:
            List of Chunk objects.
        """
        if not text:
            return []

        # Normalize
        normalized = self.normalize_text(text)

        if len(normalized) <= self.config.chunk_size:
            return [
                Chunk(
                    content=normalized,
                    index=0,
                    start_char=0,
                    end_char=len(normalized),
                    metadata=metadata or {},
                )
            ]

        # Detect content type
        content_type = self.config.content_type
        if auto_detect_type:
            content_type = self._detect_content_type(normalized)

        # Find semantic break points
        semantic_breaks = self._find_semantic_breaks(normalized, content_type)

        # Generate chunks
        chunks: List[Chunk] = []
        start = 0
        chunk_index = 0

        while start < len(normalized):
            # Calculate target end
            target_end = start + self.config.chunk_size

            if target_end >= len(normalized):
                # Last chunk
                chunk_text = normalized[start:].strip()
                if len(chunk_text) >= self.config.min_chunk_size or not chunks:
                    chunks.append(
                        Chunk(
                            content=chunk_text,
                            index=chunk_index,
                            start_char=start,
                            end_char=len(normalized),
                            metadata=metadata or {},
                        )
                    )
                break

            # Find best break point
            end = self._find_best_break(normalized, start, target_end, semantic_breaks)

            chunk_text = normalized[start:end].strip()

            if len(chunk_text) >= self.config.min_chunk_size:
                chunks.append(
                    Chunk(
                        content=chunk_text,
                        index=chunk_index,
                        start_char=start,
                        end_char=end,
                        metadata=metadata or {},
                    )
                )
                chunk_index += 1

            # Move start with overlap
            start = max(start + 1, end - self.config.chunk_overlap)

        return chunks

    def chunk_to_strings(
        self,
        text: str,
        auto_detect_type: bool = True,
    ) -> List[str]:
        """
        Convenience method to get just the chunk content strings.

        Args:
            text: Input text.
            auto_detect_type: Whether to auto-detect Markdown content.

        Returns:
            List of chunk content strings.
        """
        chunks = self.chunk(text, auto_detect_type=auto_detect_type)
        return [c.content for c in chunks]
