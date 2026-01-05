"""
Example script demonstrating the ingestion agent workflow.
Shows how to use the agent directly and via the REST API.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.agents.ingestion_agent import IngestionAgent
from app.utils.logging import get_logger

logger = get_logger(__name__)


async def example_text_ingestion():
    """Example: Ingest plain text."""
    logger.info("=== Text Ingestion Example ===")

    agent = IngestionAgent()

    text_content = """
    # Machine Learning Fundamentals
    
    Machine learning is a subset of artificial intelligence that enables systems to learn from data.
    
    ## Key Concepts
    
    **Supervised Learning**: Learning from labeled data
    - Classification: Predicting discrete categories
    - Regression: Predicting continuous values
    
    **Unsupervised Learning**: Finding patterns in unlabeled data
    - Clustering: Grouping similar items
    - Dimensionality Reduction: Reducing feature space
    
    ## Best Practices
    
    1. Start with simple models before complex ones
    2. Always split data into train/test sets
    3. Monitor for overfitting and underfitting
    4. Use cross-validation for robust evaluation
    """

    result = await agent.ingest(
        content=text_content,
        source="ml_guide.md",
        input_type="markdown",
    )

    logger.info(f"Ingestion result: {result}")
    print(f"\n✓ Success: {result.success}")
    print(f"✓ Chunks created: {result.chunks_created}")
    print(f"✓ Documents processed: {result.documents_processed}")
    print(f"✓ Message: {result.message}")
    if result.errors:
        print(f"✗ Errors: {result.errors}")
    return result


async def example_batch_ingestion():
    """Example: Ingest multiple documents."""
    logger.info("\n=== Batch Ingestion Example ===")

    agent = IngestionAgent()

    documents = [
        {
            "content": """
            # Python Best Practices
            
            Python is a versatile language with several best practices:
            - Use type hints for clarity
            - Write docstrings for documentation
            - Follow PEP 8 style guidelines
            - Use virtual environments for project isolation
            """,
            "source": "python_best_practices.md",
            "input_type": "markdown",
        },
        {
            "content": """
            # API Design
            
            RESTful APIs should follow these principles:
            - Use standard HTTP methods (GET, POST, PUT, DELETE)
            - Return appropriate status codes
            - Use consistent naming conventions
            - Version your APIs
            - Implement proper error handling
            """,
            "source": "api_design.md",
            "input_type": "markdown",
        },
    ]

    results = []
    for doc in documents:
        result = await agent.ingest(
            content=doc["content"],
            source=doc["source"],
            input_type=doc["input_type"],
        )
        results.append(result)
        print(f"\n✓ Ingested: {doc['source']}")
        print(f"  Chunks: {result.chunks_created}, Docs: {result.documents_processed}")

    return results


async def example_agent_workflow():
    """Example: Complete workflow with memory integration."""
    logger.info("\n=== Complete Agent Workflow ===")

    agent = IngestionAgent()

    content = """
    # Cloud Architecture Patterns
    
    ## Microservices
    Decompose applications into small, independent services.
    
    ## Serverless Computing
    Run code without managing servers.
    
    ## Container Orchestration
    Manage containerized applications at scale using Kubernetes.
    
    ## Load Balancing
    Distribute traffic across multiple instances.
    """

    result = await agent.ingest(
        content=content,
        source="cloud_patterns.md",
        input_type="markdown",
    )

    print(f"\n=== Ingestion Summary ===")
    print(f"Status: {'✓ SUCCESS' if result.success else '✗ FAILED'}")
    print(f"Chunks created: {result.chunks_created}")
    print(f"Documents processed: {result.documents_processed}")
    print(f"Metadata stored: {result.metadata_stored}")
    print(f"Embeddings stored: {result.vector_embeddings_stored}")
    print(f"Document IDs: {result.document_ids}")
    print(f"Message: {result.message}")

    if result.errors:
        print(f"Errors: {result.errors}")

    return result


async def main():
    """Run examples."""
    logger.info("Starting ingestion agent examples\n")

    try:
        # Example 1: Text ingestion
        await example_text_ingestion()

        # Example 2: Batch ingestion
        await example_batch_ingestion()

        # Example 3: Full workflow
        await example_agent_workflow()

        logger.info("\n✓ All examples completed successfully!")

    except Exception as e:
        logger.error(f"Example failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
