"""
LangGraph-based document ingestion agent.
Orchestrates text cleaning, chunking, embedding, and storage.
"""

import io
import re
from typing import TypedDict, List, Dict, Any, Optional, Literal
from dataclasses import dataclass
from enum import Enum

from langgraph.graph import StateGraph, START, END
from groq import Groq

from app.config import get_settings
from app.memory import MemoryManager
from app.utils.logging import get_logger

logger = get_logger(__name__)


class InputType(str, Enum):
    """Supported input document types."""
    TEXT = "text"
    MARKDOWN = "markdown"
    PDF = "pdf"
    DOCX = "docx"


@dataclass
class IngestionResult:
    """Result of document ingestion."""
    success: bool
    chunks_created: int
    documents_processed: int
    metadata_stored: bool
    vector_embeddings_stored: bool
    message: str
    errors: List[str]
    document_ids: List[str]


class IngestionState(TypedDict):
    """State for ingestion workflow."""
    raw_input: str
    input_type: str
    source: str
    cleaned_text: str
    document_count: int
    chunks: List[Dict[str, Any]]
    doc_ids: List[str]
    errors: List[str]
    result: Optional[IngestionResult]


class DocumentCleaner:
    """Clean and normalize document text."""

    @staticmethod
    def clean_text(text: str, input_type: str = "text") -> str:
        """
        Clean and normalize text from various sources.

        Args:
            text: Raw text to clean
            input_type: Type of input (text, markdown, pdf, docx)

        Returns:
            Cleaned text
        """
        logger.debug(f"Cleaning {input_type} text ({len(text)} chars)")

        # Remove BOM characters
        text = text.replace("\ufeff", "")

        # Normalize line endings
        text = text.replace("\r\n", "\n").replace("\r", "\n")

        # Remove extra whitespace (but preserve structure)
        lines = text.split("\n")
        lines = [line.rstrip() for line in lines]

        # Remove excessive blank lines
        cleaned_lines = []
        blank_count = 0
        for line in lines:
            if not line.strip():
                blank_count += 1
                if blank_count <= 2:  # Keep max 2 consecutive blank lines
                    cleaned_lines.append(line)
            else:
                blank_count = 0
                cleaned_lines.append(line)

        text = "\n".join(cleaned_lines).strip()

        # Handle markdown-specific cleaning
        if input_type == "markdown":
            text = DocumentCleaner._clean_markdown(text)

        # Remove control characters
        text = "".join(
            char for char in text if ord(char) >= 32 or char in "\n\t"
        )

        logger.debug(f"Cleaned text: {len(text)} chars")
        return text

    @staticmethod
    def _clean_markdown(text: str) -> str:
        """Clean markdown-specific elements."""
        # Remove HTML comments
        text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)

        # Clean up frontmatter (YAML)
        if text.startswith("---"):
            try:
                parts = text.split("---", 2)
                if len(parts) >= 3:
                    text = parts[2]
            except Exception:
                pass

        # Remove trailing whitespace from code blocks
        lines = text.split("\n")
        result = []
        in_code = False
        for line in lines:
            if line.strip().startswith("```"):
                in_code = not in_code
            result.append(line.rstrip() if in_code else line)
        text = "\n".join(result)

        return text

    @staticmethod
    def extract_from_pdf(pdf_bytes: bytes) -> str:
        """
        Extract text from PDF bytes.

        Args:
            pdf_bytes: PDF file content

        Returns:
            Extracted text
        """
        try:
            from PyPDF2 import PdfReader

            pdf_reader = PdfReader(io.BytesIO(pdf_bytes))
            text_parts = []

            for page_num, page in enumerate(pdf_reader.pages):
                try:
                    text = page.extract_text()
                    if text:
                        text_parts.append(text)
                except Exception as e:
                    logger.warning(f"Failed to extract page {page_num}: {e}")

            text = "\n\n".join(text_parts)
            logger.info(f"Extracted {len(text)} chars from PDF")
            return text
        except ImportError:
            raise ValueError("PyPDF2 not installed. Install with: pip install PyPDF2")
        except Exception as e:
            raise ValueError(f"Failed to extract PDF: {e}")

    @staticmethod
    def extract_from_docx(docx_bytes: bytes) -> str:
        """
        Extract text from DOCX bytes.

        Args:
            docx_bytes: DOCX file content

        Returns:
            Extracted text
        """
        try:
            from docx import Document

            doc = Document(io.BytesIO(docx_bytes))
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            text = "\n".join(paragraphs)

            logger.info(f"Extracted {len(text)} chars from DOCX")
            return text
        except ImportError:
            raise ValueError(
                "python-docx not installed. Install with: pip install python-docx"
            )
        except Exception as e:
            raise ValueError(f"Failed to extract DOCX: {e}")


class IngestionAgent:
    """
    LangGraph-based document ingestion agent.
    Orchestrates the complete ingestion pipeline.
    """

    def __init__(self, memory_manager: Optional[MemoryManager] = None):
        """
        Initialize ingestion agent.

        Args:
            memory_manager: Memory manager instance. Creates default if None.
        """
        self.memory_manager = memory_manager or MemoryManager()
        self.settings = get_settings()
        self.cleaner = DocumentCleaner()
        self.groq_client = Groq(api_key=self.settings.GROQ_API_KEY)
        self.graph = self._build_graph()

        logger.info("IngestionAgent initialized")

    def _build_graph(self) -> StateGraph:
        """
        Build LangGraph workflow.

        Returns:
            Compiled state graph
        """
        workflow = StateGraph(IngestionState)

        # Add nodes
        workflow.add_node("clean", self._clean_step)
        workflow.add_node("split", self._split_step)
        workflow.add_node("enrich", self._enrich_step)
        workflow.add_node("store", self._store_step)
        workflow.add_node("finalize", self._finalize_step)

        # Add edges
        workflow.add_edge(START, "clean")
        workflow.add_edge("clean", "split")
        workflow.add_edge("split", "enrich")
        workflow.add_edge("enrich", "store")
        workflow.add_edge("store", "finalize")
        workflow.add_edge("finalize", END)

        return workflow.compile()

    def _clean_step(self, state: IngestionState) -> IngestionState:
        """
        Clean and normalize input text.

        Args:
            state: Current ingestion state

        Returns:
            Updated state with cleaned text
        """
        logger.info(
            f"Clean step: {state['input_type']} from {state['source']}"
        )

        try:
            cleaned = self.cleaner.clean_text(
                state["raw_input"], state["input_type"]
            )
            state["cleaned_text"] = cleaned
            logger.info(f"Cleaned text: {len(cleaned)} chars")
            return state
        except Exception as e:
            state["errors"].append(f"Cleaning failed: {str(e)}")
            logger.error(f"Cleaning error: {e}")
            raise

    def _split_step(self, state: IngestionState) -> IngestionState:
        """
        Split text into semantic chunks.

        Args:
            state: Current ingestion state

        Returns:
            Updated state with chunks
        """
        logger.info("Split step: chunking text")

        try:
            chunks = self.memory_manager.chunker.chunk(
                state["cleaned_text"], source=state["source"]
            )

            state["chunks"] = [chunk.to_dict() for chunk in chunks]
            logger.info(f"Created {len(chunks)} chunks")
            return state
        except Exception as e:
            state["errors"].append(f"Chunking failed: {str(e)}")
            logger.error(f"Chunking error: {e}")
            raise

    def _enrich_step(self, state: IngestionState) -> IngestionState:
        """
        Enrich chunks with metadata using Groq.

        Args:
            state: Current ingestion state

        Returns:
            Updated state with enriched chunks
        """
        logger.info(f"Enrich step: analyzing {len(state['chunks'])} chunks")

        try:
            enriched_chunks = []
            for i, chunk in enumerate(state["chunks"]):
                try:
                    # Use Groq for content analysis
                    enriched = self._analyze_chunk_with_groq(chunk, i)
                    enriched_chunks.append(enriched)
                except Exception as e:
                    logger.warning(f"Groq analysis failed for chunk {i}: {e}")
                    # Fallback to local tagging
                    enriched = self._analyze_chunk_local(chunk)
                    enriched_chunks.append(enriched)

            state["chunks"] = enriched_chunks
            logger.info(f"Enriched {len(enriched_chunks)} chunks")
            return state
        except Exception as e:
            state["errors"].append(f"Enrichment failed: {str(e)}")
            logger.error(f"Enrichment error: {e}")
            raise

    def _analyze_chunk_with_groq(self, chunk: Dict[str, Any], index: int) -> Dict[str, Any]:
        """
        Analyze chunk using Groq API for additional insights.

        Args:
            chunk: Chunk to analyze
            index: Chunk index

        Returns:
            Enriched chunk
        """
        text_sample = chunk["text"][:500]  # First 500 chars

        prompt = f"""Analyze this text chunk and provide a JSON response with:
{{"key_concepts": ["concept1", "concept2"], "summary": "brief summary", "technical_level": "beginner|intermediate|advanced"}}

Text: {text_sample}"""

        try:
            message = self.groq_client.messages.create(
                model=self.settings.GROQ_MODEL,
                max_tokens=200,
                messages=[{"role": "user", "content": prompt}],
            )

            response_text = message.content[0].text
            # Parse response (simple JSON extraction)
            chunk["groq_analysis"] = response_text
            logger.debug(f"Groq analysis for chunk {index}: success")
        except Exception as e:
            logger.warning(f"Groq API call failed: {e}")
            chunk["groq_analysis"] = None

        return chunk

    def _analyze_chunk_local(self, chunk: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze chunk locally using tagging.

        Args:
            chunk: Chunk to analyze

        Returns:
            Enriched chunk
        """
        metadata = self.memory_manager.tagger.tag_content(chunk["text"])
        chunk["local_metadata"] = {
            "topics": metadata.topics,
            "domain": metadata.domain,
            "difficulty_level": metadata.difficulty_level,
            "key_terms": metadata.key_terms,
        }
        return chunk

    def _store_step(self, state: IngestionState) -> IngestionState:
        """
        Store chunks in vector and metadata stores.

        Args:
            state: Current ingestion state

        Returns:
            Updated state with stored doc IDs
        """
        logger.info(f"Store step: saving {len(state['chunks'])} chunks")

        try:
            chunk_texts = [chunk["text"] for chunk in state["chunks"]]

            # Add to memory manager
            doc_ids = self.memory_manager.add_documents(
                documents=chunk_texts,
                source=state["source"],
                auto_chunk=False,  # Already chunked
                auto_tag=True,
                tags=["ingestion-agent"],
            )

            state["doc_ids"] = doc_ids
            state["document_count"] = len(doc_ids)
            logger.info(f"Stored {len(doc_ids)} documents")
            return state
        except Exception as e:
            state["errors"].append(f"Storage failed: {str(e)}")
            logger.error(f"Storage error: {e}")
            raise

    def _finalize_step(self, state: IngestionState) -> IngestionState:
        """
        Finalize ingestion and create summary.

        Args:
            state: Current ingestion state

        Returns:
            Updated state with result
        """
        logger.info("Finalize step: creating summary")

        result = IngestionResult(
            success=len(state["errors"]) == 0,
            chunks_created=len(state["chunks"]),
            documents_processed=state["document_count"],
            metadata_stored=True,
            vector_embeddings_stored=True,
            message=(
                f"Successfully ingested {state['document_count']} documents "
                f"from {state['source']}"
                if len(state["errors"]) == 0
                else f"Ingestion completed with {len(state['errors'])} errors"
            ),
            errors=state["errors"],
            document_ids=state["doc_ids"],
        )

        state["result"] = result
        logger.info(f"Ingestion complete: {result.message}")
        return state

    async def ingest(
        self,
        content: str,
        source: str,
        input_type: str = "text",
    ) -> IngestionResult:
        """
        Execute ingestion workflow.

        Args:
            content: Document content to ingest
            source: Source identifier
            input_type: Type of input (text, markdown, pdf, docx)

        Returns:
            Ingestion result with summary

        Raises:
            ValueError: If input is invalid
        """
        if not content:
            raise ValueError("Content cannot be empty")

        if not source:
            raise ValueError("Source cannot be empty")

        logger.info(
            f"Starting ingestion: {input_type} from {source} "
            f"({len(content)} bytes)"
        )

        # Initialize state
        initial_state: IngestionState = {
            "raw_input": content,
            "input_type": input_type,
            "source": source,
            "cleaned_text": "",
            "document_count": 0,
            "chunks": [],
            "doc_ids": [],
            "errors": [],
            "result": None,
        }

        try:
            # Execute workflow
            final_state = self.graph.invoke(initial_state)
            result = final_state.get("result")

            if not result:
                raise ValueError("Workflow did not produce result")

            logger.info(f"Ingestion completed: {result.message}")
            return result

        except Exception as e:
            logger.error(f"Ingestion workflow failed: {e}")
            return IngestionResult(
                success=False,
                chunks_created=0,
                documents_processed=0,
                metadata_stored=False,
                vector_embeddings_stored=False,
                message=f"Ingestion failed: {str(e)}",
                errors=[str(e)],
                document_ids=[],
            )

    async def ingest_from_file(
        self,
        file_path: str,
        source: Optional[str] = None,
    ) -> IngestionResult:
        """
        Ingest document from file.

        Args:
            file_path: Path to file
            source: Optional source identifier (defaults to file_path)

        Returns:
            Ingestion result

        Raises:
            ValueError: If file not found or unsupported format
        """
        import os

        if not os.path.exists(file_path):
            raise ValueError(f"File not found: {file_path}")

        source = source or file_path
        _, ext = os.path.splitext(file_path)
        ext = ext.lower().lstrip(".")

        logger.info(f"Ingesting file: {file_path} (type: {ext})")

        try:
            with open(file_path, "rb") as f:
                content_bytes = f.read()

            # Determine input type and extract text
            if ext == "pdf":
                content = self.cleaner.extract_from_pdf(content_bytes)
                input_type = "pdf"
            elif ext == "docx":
                content = self.cleaner.extract_from_docx(content_bytes)
                input_type = "docx"
            elif ext in ("md", "markdown"):
                content = content_bytes.decode("utf-8")
                input_type = "markdown"
            elif ext == "txt":
                content = content_bytes.decode("utf-8")
                input_type = "text"
            else:
                raise ValueError(f"Unsupported file type: {ext}")

            return await self.ingest(content, source, input_type)

        except Exception as e:
            logger.error(f"File ingestion failed: {e}")
            return IngestionResult(
                success=False,
                chunks_created=0,
                documents_processed=0,
                metadata_stored=False,
                vector_embeddings_stored=False,
                message=f"File ingestion failed: {str(e)}",
                errors=[str(e)],
                document_ids=[],
            )
