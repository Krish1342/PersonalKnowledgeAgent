from typing import Dict, Any
from datetime import datetime

from app.agents.state import AgentState
from app.memory.vector_store import VectorStore
from app.memory.episodic_store import EpisodicStore
from app.utils.chunking import TextChunker, ChunkingConfig


def ingestion_agent(state: AgentState) -> Dict[str, Any]:
    """
    Ingestion agent node.

    Processes raw text input into:
    1. Vector store (semantic chunks with embeddings)
    2. Episodic store (memory log with metadata)

    Args:
        state: Current agent state containing 'raw_input' and optional 'source'.

    Returns:
        State updates with 'chunks_ingested' count or 'error'.
    """
    raw_input = state.get("raw_input")
    source = state.get("source", "user_input")

    # Validate input
    if not raw_input or not raw_input.strip():
        return {
            "error": "No input provided for ingestion",
            "chunks_ingested": 0,
        }

    try:
        # Initialize stores
        vector_store = VectorStore()
        episodic_store = EpisodicStore()

        # Initialize chunker with overlap
        chunker = TextChunker(
            config=ChunkingConfig(
                chunk_size=1000,
                chunk_overlap=200,
                min_chunk_size=100,
            )
        )

        # Chunk the input
        chunks = chunker.chunk(
            text=raw_input,
            metadata={"source": source},
            auto_detect_type=True,
        )

        if not chunks:
            return {
                "error": "No chunks generated from input",
                "chunks_ingested": 0,
            }

        # Prepare documents and metadata for vector store
        documents = [chunk.content for chunk in chunks]
        timestamp = datetime.utcnow().isoformat()

        metadatas = [
            {
                "source": source,
                "chunk_index": chunk.index,
                "start_char": chunk.start_char,
                "end_char": chunk.end_char,
                "ingested_at": timestamp,
            }
            for chunk in chunks
        ]

        # Add to vector store
        doc_ids = vector_store.add_documents(
            documents=documents,
            metadatas=metadatas,
        )

        # Log to episodic store (append-only)
        for i, chunk in enumerate(chunks):
            episodic_store.append_memory(
                source=source,
                content=chunk.content,
                version=1,
                confidence=1.0,
            )

        return {
            "chunks_ingested": len(chunks),
            "error": None,
        }

    except Exception as e:
        return {
            "error": f"Ingestion failed: {str(e)}",
            "chunks_ingested": 0,
        }
