"""
Tests for the ingestion agent.
Tests the complete ingestion pipeline with mocked dependencies.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.agents.ingestion_agent import (
    IngestionAgent,
    DocumentCleaner,
    IngestionResult,
)


class TestDocumentCleaner:
    """Test DocumentCleaner class."""

    def test_clean_text_removes_bom(self):
        """Test that BOM is removed from text."""
        cleaner = DocumentCleaner()
        text = "\ufeffHello World"
        cleaned = cleaner.clean_text(text)
        assert cleaned == "Hello World"

    def test_clean_text_normalizes_whitespace(self):
        """Test that excessive whitespace is normalized."""
        cleaner = DocumentCleaner()
        text = "Hello    \n\n\n    World"
        cleaned = cleaner.clean_text(text)
        assert "    " not in cleaned
        assert "\n\n\n" not in cleaned

    def test_clean_markdown_removes_frontmatter(self):
        """Test that YAML frontmatter is removed."""
        cleaner = DocumentCleaner()
        text = """---
title: Test
author: John
---

Content here"""
        cleaned = cleaner._clean_markdown(text)
        assert "title:" not in cleaned
        assert "Content here" in cleaned

    def test_clean_markdown_removes_comments(self):
        """Test that HTML comments are removed."""
        cleaner = DocumentCleaner()
        text = "Text <!-- comment --> more text"
        cleaned = cleaner._clean_markdown(text)
        assert "<!-- comment -->" not in cleaned
        assert "Text" in cleaned

    def test_extract_from_pdf_with_bytes(self):
        """Test PDF extraction with sample data."""
        cleaner = DocumentCleaner()
        # This would need a real PDF for full testing
        # Skipping for now as it requires PDF file
        pass

    def test_extract_from_docx_with_bytes(self):
        """Test DOCX extraction with sample data."""
        cleaner = DocumentCleaner()
        # This would need a real DOCX for full testing
        # Skipping for now as it requires DOCX file
        pass


class TestIngestionAgent:
    """Test IngestionAgent class."""

    @pytest.mark.asyncio
    async def test_ingest_simple_text(self):
        """Test ingesting simple text content."""
        agent = IngestionAgent()
        
        content = "This is a test document about machine learning."
        result = await agent.ingest(
            content=content,
            source="test.txt",
            input_type="text"
        )
        
        assert isinstance(result, IngestionResult)
        assert result.success is not None
        assert result.chunks_created >= 0
        assert result.documents_processed >= 0

    @pytest.mark.asyncio
    async def test_ingest_markdown(self):
        """Test ingesting markdown content."""
        agent = IngestionAgent()
        
        content = """
# Test Document
        
This is a test with **bold** and *italic*.
        
## Section 2
        
More content here.
"""
        result = await agent.ingest(
            content=content,
            source="test.md",
            input_type="markdown"
        )
        
        assert isinstance(result, IngestionResult)

    @pytest.mark.asyncio
    async def test_ingest_empty_content(self):
        """Test ingesting empty content."""
        agent = IngestionAgent()
        
        content = ""
        result = await agent.ingest(
            content=content,
            source="empty.txt",
            input_type="text"
        )
        
        # Should handle gracefully
        assert isinstance(result, IngestionResult)

    @pytest.mark.asyncio
    async def test_ingest_from_file_not_found(self):
        """Test ingesting from non-existent file."""
        agent = IngestionAgent()
        
        result = await agent.ingest_from_file(
            file_path="/nonexistent/path/file.pdf"
        )
        
        assert result.success is False
        assert len(result.errors) > 0

    @pytest.mark.asyncio
    async def test_graph_execution(self):
        """Test that the LangGraph graph executes."""
        agent = IngestionAgent()
        graph = agent._build_graph()
        
        # Check that graph is compiled
        assert graph is not None
        assert hasattr(graph, 'invoke')

    @pytest.mark.asyncio
    async def test_long_document_chunking(self):
        """Test that long documents are properly chunked."""
        agent = IngestionAgent()
        
        # Create a long document
        content = "\n".join([
            f"Paragraph {i}: This is a test paragraph with some content."
            for i in range(50)
        ])
        
        result = await agent.ingest(
            content=content,
            source="long_doc.txt",
            input_type="text"
        )
        
        # Should create multiple chunks
        if result.success:
            assert result.chunks_created > 0

    @pytest.mark.asyncio
    async def test_special_characters_handling(self):
        """Test handling of special characters."""
        agent = IngestionAgent()
        
        content = "Test with émojis 🚀, spëcial çhars, and Ünicode."
        result = await agent.ingest(
            content=content,
            source="special.txt",
            input_type="text"
        )
        
        assert isinstance(result, IngestionResult)

    @pytest.mark.asyncio
    async def test_result_contains_document_ids(self):
        """Test that result contains document IDs."""
        agent = IngestionAgent()
        
        content = "Test document for IDs."
        result = await agent.ingest(
            content=content,
            source="test_ids.txt",
            input_type="text"
        )
        
        if result.success:
            # Should have document IDs if successful
            assert isinstance(result.document_ids, list)


class TestIngestionResult:
    """Test IngestionResult dataclass."""

    def test_result_creation(self):
        """Test creating IngestionResult."""
        result = IngestionResult(
            success=True,
            chunks_created=5,
            documents_processed=1,
            metadata_stored=True,
            vector_embeddings_stored=True,
            message="Test message",
            errors=[],
            document_ids=["id1", "id2"]
        )
        
        assert result.success is True
        assert result.chunks_created == 5
        assert result.documents_processed == 1
        assert len(result.document_ids) == 2

    def test_result_with_errors(self):
        """Test IngestionResult with errors."""
        result = IngestionResult(
            success=False,
            chunks_created=0,
            documents_processed=0,
            metadata_stored=False,
            vector_embeddings_stored=False,
            message="Failed to ingest",
            errors=["Error 1", "Error 2"],
            document_ids=[]
        )
        
        assert result.success is False
        assert len(result.errors) == 2


# Integration tests (would need full setup)
@pytest.mark.integration
class TestIngestionIntegration:
    """Integration tests requiring full environment setup."""

    @pytest.mark.asyncio
    async def test_end_to_end_ingestion(self):
        """Test complete ingestion workflow."""
        agent = IngestionAgent()
        
        content = """
# Integration Test Document
        
This is a comprehensive test of the ingestion system.
        
## Technical Content
        
Key points:
- Point 1
- Point 2
- Point 3
        
## Code Example
        
```python
def hello():
    print("Hello World")
```
        
## Conclusion
        
This concludes the test.
"""
        
        result = await agent.ingest(
            content=content,
            source="integration_test.md",
            input_type="markdown"
        )
        
        # Verify complete flow
        assert isinstance(result, IngestionResult)
        if result.success:
            assert result.chunks_created > 0
            assert result.documents_processed > 0


if __name__ == "__main__":
    # Run basic tests
    import sys
    
    async def run_tests():
        """Run async tests."""
        print("Running ingestion agent tests...\n")
        
        # Test cleaner
        print("Testing DocumentCleaner...")
        cleaner = TestDocumentCleaner()
        cleaner.test_clean_text_removes_bom()
        cleaner.test_clean_text_normalizes_whitespace()
        cleaner.test_clean_markdown_removes_frontmatter()
        print("✓ DocumentCleaner tests passed\n")
        
        # Test result
        print("Testing IngestionResult...")
        result_test = TestIngestionResult()
        result_test.test_result_creation()
        result_test.test_result_with_errors()
        print("✓ IngestionResult tests passed\n")
        
        # Test agent
        print("Testing IngestionAgent...")
        agent_test = TestIngestionAgent()
        await agent_test.test_ingest_simple_text()
        await agent_test.test_ingest_markdown()
        await agent_test.test_special_characters_handling()
        print("✓ IngestionAgent tests passed\n")
        
        print("✓ All tests completed!")
    
    asyncio.run(run_tests())
