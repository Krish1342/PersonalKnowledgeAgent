"""
Practical Examples for Content Preprocessing Pipeline
======================================================

Real-world usage patterns for chunking, tagging, and memory management.
"""

# EXAMPLE 1: Basic Text Chunking
# ===============================

from app.utils.chunking import create_chunker


def example_basic_chunking():
    """Simple document chunking with default settings."""

    chunker = create_chunker()

    document = """
    # Authentication Guide
    
    ## Introduction
    Authentication is the process of verifying user identity. This guide covers
    common authentication patterns and best practices.
    
    ## Overview
    The system supports multiple authentication methods:
    - JWT tokens
    - OAuth 2.0
    - API keys
    
    ### JWT Tokens
    JSON Web Tokens provide a stateless authentication mechanism. They consist
    of three parts: header, payload, and signature. The header contains the token
    type and algorithm used. The payload contains claims about the entity.
    
    ### Security Best Practices
    Always validate token signatures to prevent tampering. Use HTTPS for all
    authentication requests. Never expose secrets in client-side code.
    """

    chunks = chunker.chunk(document, source="auth_guide")

    for chunk in chunks:
        print(f"\nChunk {chunk.chunk_index + 1}/{chunk.total_chunks}")
        print(f"Heading: {chunk.heading or 'N/A'}")
        print(f"Position: {chunk.start_char}-{chunk.end_char}")
        print(f"Text: {chunk.text[:100]}...")


# EXAMPLE 2: Content Tagging
# ===========================

from app.utils.tagging import create_tagger


def example_content_tagging():
    """Automatic metadata extraction from content."""

    tagger = create_tagger()

    texts = {
        "ml_paper": """
        Deep Learning for NLP: Transformers have revolutionized natural language
        processing. Attention mechanisms enable parallel processing of sequences.
        We propose a novel architecture combining CNN and LSTM layers for
        improved feature extraction. Mathematical proofs of convergence are provided.
        """,
        "api_guide": """
        REST API Endpoints
        
        GET /api/users - Fetch all users
        POST /api/users - Create new user
        Request headers: Authorization, Content-Type
        Response: JSON with status code 200
        """,
        "tutorial": """
        Getting Started with Python
        
        This tutorial covers the basics of Python programming. We'll learn:
        1. Variables and types
        2. Control flow (if/else)
        3. Functions and loops
        
        Simple example code:
        ```python
        def hello(name):
            print(f"Hello, {name}!")
        ```
        """,
    }

    for name, text in texts.items():
        metadata = tagger.tag_content(text)
        print(f"\n{name.upper()}")
        print(f"  Domain: {metadata.domain}")
        print(f"  Difficulty: {metadata.difficulty_level}")
        print(f"  Topics: {', '.join(metadata.topics)}")
        print(f"  Key Terms: {', '.join(metadata.key_terms[:5])}")


# EXAMPLE 3: Full Pipeline Integration
# =====================================

from app.memory import MemoryManager


async def example_full_pipeline():
    """Complete document ingestion and search workflow."""

    # Initialize memory manager
    manager = MemoryManager()
    manager.init_db()

    # Sample documents
    documents = [
        """
        # FastAPI for Beginners
        
        FastAPI is a modern Python web framework. Getting started is simple.
        Install with: pip install fastapi uvicorn
        
        ## Your First Application
        
        ```python
        from fastapi import FastAPI
        
        app = FastAPI()
        
        @app.get("/")
        def read_root():
            return {"Hello": "World"}
        ```
        
        Run with: uvicorn main:app --reload
        """,
        """
        # Production Deployment Strategies
        
        ## Architecture Patterns
        
        Consider multi-tier deployment architecture:
        - Load balancers for traffic distribution
        - Container orchestration with Kubernetes
        - Database replication for redundancy
        - CDN for static assets
        
        ## Performance Optimization
        
        Measure latency with APM tools. Cache frequently accessed data.
        Implement database indexing strategies. Use async operations.
        """,
    ]

    # 1. Ingest documents with auto-processing
    print("Ingesting documents...")
    doc_ids = manager.add_documents(
        documents=documents,
        source="fastapi_docs",
        tags=["official", "tutorial"],
        auto_chunk=True,  # Enable chunking
        auto_tag=True,  # Enable tagging
    )
    print(f"✓ Added {len(doc_ids)} document chunks")

    # 2. Get statistics
    stats = manager.get_memory_stats()
    print(f"\nMemory Stats:")
    print(f"  Total documents: {stats['total_documents']}")
    print(f"  Embedding model: {stats['model']}")
    print(f"  Storage size: {stats['index_size_mb']:.2f} MB")

    # 3. Perform searches with various queries
    queries = [
        "How to install FastAPI?",
        "Database performance optimization",
        "Kubernetes deployment strategies",
    ]

    print(f"\n{'='*60}")
    print("SEMANTIC SEARCH RESULTS")
    print(f"{'='*60}")

    for query in queries:
        print(f"\nQuery: '{query}'")
        results = manager.similarity_search(
            query=query, k=3, filter_source="fastapi_docs"
        )

        for i, result in enumerate(results, 1):
            print(f"\n  {i}. Match (Similarity: {result['similarity_score']:.1%})")
            print(f"     Domain: {result['domain']}")
            print(f"     Difficulty: {result['difficulty_level']}")
            print(f"     Topics: {', '.join(result['topics'][:3])}")
            print(f"     Text: {result['id'][:8]}...")


# EXAMPLE 4: Filtering by Metadata
# ================================


def example_metadata_filtering():
    """Advanced filtering using auto-generated metadata."""

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.memory.metadata_store import DocumentMetadata
    from app.config import get_settings

    settings = get_settings()
    engine = create_engine(settings.DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Find beginner-level documents
    beginner_docs = (
        session.query(DocumentMetadata).filter_by(difficulty_level="beginner").all()
    )
    print(f"Beginner-level documents: {len(beginner_docs)}")

    # Find documents about APIs
    api_docs = (
        session.query(DocumentMetadata)
        .filter(DocumentMetadata.topics.contains(["api"]))
        .all()
    )
    print(f"Documents about APIs: {len(api_docs)}")

    # Find backend-related content
    backend_docs = (
        session.query(DocumentMetadata).filter_by(domain="backend-development").all()
    )
    print(f"Backend development docs: {len(backend_docs)}")

    # Find documents from specific source with difficulty filter
    tutorial_docs = (
        session.query(DocumentMetadata)
        .filter(
            DocumentMetadata.source == "fastapi_docs",
            DocumentMetadata.difficulty_level.in_(["beginner", "intermediate"]),
        )
        .all()
    )
    print(f"Tutorial docs (beginner/intermediate): {len(tutorial_docs)}")

    session.close()


# EXAMPLE 5: Chunking Custom Content
# ===================================


def example_custom_chunking():
    """Chunk with custom size and overlap settings."""

    from app.utils.chunking import SemanticChunker

    # Custom chunker with larger chunks
    chunker = SemanticChunker(
        chunk_size=1000, chunk_overlap=100  # Larger chunks  # More overlap for context
    )

    long_document = """
    # Advanced Topics in Machine Learning
    
    ## Part 1: Deep Learning Architectures
    
    Transformers have become the dominant architecture in modern NLP.
    They employ self-attention mechanisms to capture long-range dependencies.
    The multi-head attention pattern allows the model to focus on different
    aspects of the input simultaneously...
    
    [Many more paragraphs...]
    """

    chunks = chunker.chunk(long_document, source="ml_course")

    print(f"Created {len(chunks)} chunks")
    for chunk in chunks:
        print(f"  Chunk {chunk.chunk_index}: {len(chunk.text)} chars")


# EXAMPLE 6: Batch Processing Documents
# ======================================


def example_batch_processing():
    """Process multiple documents efficiently."""

    from app.memory import MemoryManager
    import glob

    manager = MemoryManager()
    manager.init_db()

    # Load multiple markdown files
    doc_files = glob.glob("./knowledge_base/*.md")

    for file_path in doc_files:
        print(f"Processing: {file_path}")

        with open(file_path, "r") as f:
            content = f.read()

        # Process with auto-chunking and tagging
        doc_ids = manager.add_documents(
            documents=[content],
            source=file_path,
            tags=["markdown", "imported"],
            auto_chunk=True,
            auto_tag=True,
        )
        print(f"  ✓ Created {len(doc_ids)} chunks")

    # Show final statistics
    stats = manager.get_memory_stats()
    print(f"\nTotal documents in memory: {stats['total_documents']}")


# EXAMPLE 7: Searching by Topic and Domain
# =========================================


def example_topic_domain_search():
    """Demonstrate filtering and searching by metadata."""

    from app.memory import MemoryManager

    manager = MemoryManager()

    # Search in specific domain
    results = manager.similarity_search(
        query="How do I scale a backend service?",
        k=5,
        filter_source="backend_docs",  # Optional source filter
    )

    print("Backend Service Scaling Results:")
    for result in results:
        print(f"\n  Domain: {result['domain']}")
        print(f"  Difficulty: {result['difficulty_level']}")
        print(f"  Topics: {result['topics']}")
        print(f"  Similarity: {result['similarity_score']:.1%}")

        # Use metadata to decide if relevant
        if "performance" in result["topics"]:
            print("  ✓ Includes performance content")
        if result["difficulty_level"] in ["intermediate", "advanced"]:
            print("  ✓ Suitable for experienced developers")


# EXAMPLE 8: Memory Statistics and Cleanup
# =========================================


def example_memory_management():
    """Monitor and manage memory store."""

    from app.memory import MemoryManager

    manager = MemoryManager()

    # Get comprehensive statistics
    stats = manager.get_memory_stats()

    print("Memory Store Statistics:")
    print(f"  Total documents: {stats['total_documents']}")
    print(f"  Embedding dimension: {stats['embedding_dim']}")
    print(f"  Model: {stats['model']}")
    print(f"  Storage path: {stats['storage_path']}")
    print(f"  Index size: {stats['index_size_mb']:.2f} MB")
    print(f"  Sources tracked: {len(stats['sources'])}")

    # Delete documents from a source
    if "old_source" in stats["sources"]:
        result = manager.delete_by_source("old_source")
        print(f"\nDeleted {result['documents_deleted']} documents")
        print(f"Freed {result['embeddings_deleted']} embeddings")


if __name__ == "__main__":
    print("Content Preprocessing Examples")
    print("=" * 60)

    print("\n1. Basic Chunking")
    example_basic_chunking()

    print("\n" + "=" * 60)
    print("2. Content Tagging")
    example_content_tagging()

    print("\n" + "=" * 60)
    print("3. Custom Chunking")
    example_custom_chunking()
