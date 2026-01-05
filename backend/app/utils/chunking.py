"""
Semantic-aware text chunking for document processing.
Preserves context and structure while creating meaningful chunks.
"""

import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

from app.config import get_settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class Chunk:
    """Represents a text chunk with metadata."""

    text: str
    start_char: int
    end_char: int
    heading: Optional[str] = None
    section: Optional[str] = None
    chunk_index: int = 0
    total_chunks: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "text": self.text,
            "start_char": self.start_char,
            "end_char": self.end_char,
            "heading": self.heading,
            "section": self.section,
            "chunk_index": self.chunk_index,
            "total_chunks": self.total_chunks,
        }


class SemanticChunker:
    """
    Text chunker that preserves semantic boundaries.
    Respects paragraph, sentence, and heading structure.
    """

    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 50):
        """
        Initialize chunker.

        Args:
            chunk_size: Target size for chunks (in characters)
            chunk_overlap: Number of overlapping characters between chunks
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        logger.debug(f"Chunker initialized: size={chunk_size}, overlap={chunk_overlap}")

    @staticmethod
    def _extract_heading(text: str) -> Tuple[Optional[str], str]:
        """
        Extract heading from text if present.

        Args:
            text: Text to process

        Returns:
            Tuple of (heading, text_without_heading)
        """
        # Match markdown or text headings
        heading_pattern = r"^#+\s+(.+?)$|^(.+?)\n={3,}$|^(.+?)\n-{3,}$"
        match = re.match(heading_pattern, text, re.MULTILINE)

        if match:
            heading = match.group(1) or match.group(2) or match.group(3)
            # Remove heading from text
            text = re.sub(heading_pattern, "", text, count=1, flags=re.MULTILINE).lstrip()
            return heading.strip(), text
        return None, text

    @staticmethod
    def _is_sentence_end(text: str, pos: int) -> bool:
        """
        Check if position is at a sentence boundary.

        Args:
            text: Full text
            pos: Position to check

        Returns:
            True if at sentence boundary
        """
        if pos >= len(text):
            return True

        # Look for sentence-ending punctuation followed by space/newline
        if text[pos] in ".!?" and pos + 1 < len(text):
            next_char = text[pos + 1]
            return next_char in (" ", "\n", "\t")

        return False

    @staticmethod
    def _is_paragraph_end(text: str, pos: int) -> bool:
        """
        Check if position is at a paragraph boundary.

        Args:
            text: Full text
            pos: Position to check

        Returns:
            True if at paragraph boundary
        """
        if pos >= len(text) - 1:
            return True

        # Check for double newline
        return text[pos : pos + 2] == "\n\n"

    def _find_split_point(self, text: str, max_size: int) -> int:
        """
        Find optimal split point for chunk.
        Prioritizes paragraph, then sentence, then word boundaries.

        Args:
            text: Text to split
            max_size: Maximum size to consider

        Returns:
            Position to split at
        """
        if len(text) <= max_size:
            return len(text)

        # Try to find paragraph boundary
        for pos in range(max_size, 0, -1):
            if self._is_paragraph_end(text, pos):
                return pos

        # Try to find sentence boundary
        for pos in range(max_size, 0, -1):
            if self._is_sentence_end(text, pos):
                return pos + 1

        # Fall back to word boundary
        split_pos = max_size
        while split_pos > 0 and text[split_pos] not in (" ", "\n", "\t"):
            split_pos -= 1

        return split_pos if split_pos > 0 else max_size

    def chunk(self, text: str, source: str = "unknown") -> List[Chunk]:
        """
        Chunk text into semantic units.

        Args:
            text: Text to chunk
            source: Source identifier for tracking

        Returns:
            List of Chunk objects

        Raises:
            ValueError: If text is empty
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")

        logger.info(f"Chunking text from {source} ({len(text)} chars)")

        # Extract document-level heading
        doc_heading, text = self._extract_heading(text)

        chunks: List[Chunk] = []
        char_pos = 0

        # Split by major sections if they exist
        sections = re.split(r"\n(?=#{1,3}\s+)", text)

        for section_text in sections:
            if not section_text.strip():
                continue

            section_heading, section_body = self._extract_heading(section_text)
            section_name = section_heading or doc_heading

            # Process section into chunks
            pos = 0
            while pos < len(section_body):
                # Determine chunk boundaries
                chunk_end = min(pos + self.chunk_size, len(section_body))
                split_point = self._find_split_point(section_body[pos:chunk_end], self.chunk_size)

                chunk_text = section_body[pos : pos + split_point].strip()

                if chunk_text:
                    chunk = Chunk(
                        text=chunk_text,
                        start_char=char_pos,
                        end_char=char_pos + len(chunk_text),
                        heading=section_heading,
                        section=section_name,
                    )
                    chunks.append(chunk)
                    char_pos += len(chunk_text)

                # Move position with overlap
                pos += split_point
                if pos < len(section_body) and self.chunk_overlap > 0:
                    pos = max(pos - self.chunk_overlap, 0)

        # Set chunk indices
        for idx, chunk in enumerate(chunks):
            chunk.chunk_index = idx
            chunk.total_chunks = len(chunks)

        logger.info(f"Created {len(chunks)} chunks from {source}")
        return chunks

    def chunk_documents(
        self, documents: List[str], source: str = "batch"
    ) -> List[Chunk]:
        """
        Chunk multiple documents.

        Args:
            documents: List of document texts
            source: Source identifier

        Returns:
            List of Chunk objects
        """
        all_chunks = []
        for i, doc in enumerate(documents):
            doc_source = f"{source}[doc_{i}]"
            chunks = self.chunk(doc, source=doc_source)
            all_chunks.extend(chunks)

        logger.info(f"Chunked {len(documents)} documents into {len(all_chunks)} chunks")
        return all_chunks


def create_chunker(
    chunk_size: Optional[int] = None,
    chunk_overlap: Optional[int] = None,
) -> SemanticChunker:
    """
    Factory function to create chunker with default settings.

    Args:
        chunk_size: Optional override for chunk size
        chunk_overlap: Optional override for chunk overlap

    Returns:
        SemanticChunker instance
    """
    settings = get_settings()
    return SemanticChunker(
        chunk_size=chunk_size or settings.CHUNK_SIZE,
        chunk_overlap=chunk_overlap or settings.CHUNK_OVERLAP,
    )
