# Ingestion System - Personal Knowledge Agent

Complete document ingestion pipeline using LangGraph and Groq API.

## Overview

The ingestion system is a sophisticated orchestration layer that transforms raw documents (PDF, DOCX, Markdown, plain text) into richly indexed, searchable knowledge in the vector and metadata stores.

### Key Features

- **Multi-Format Support**: PDF, DOCX, Markdown, and plain text documents
- **Intelligent Chunking**: Semantic splitting with boundary preservation
- **Groq-Powered Enrichment**: Uses Groq API for content analysis
- **Vector Indexing**: FAISS-based similarity search
- **Metadata Management**: PostgreSQL/Supabase for comprehensive indexing
- **Error Resilience**: Graceful fallbacks and comprehensive error tracking
- **Async Pipeline**: Non-blocking document processing
- **REST API**: FastAPI endpoints for easy integration

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    REST API Endpoints                        │
│  (Text Ingest | File Upload | Batch Processing | Status)   │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│               LangGraph Ingestion Agent                      │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ Orchestration Graph (5 Nodes):                         │ │
│  │  1. CLEAN: Text extraction and normalization          │ │
│  │  2. SPLIT: Semantic chunking with boundaries          │ │
│  │  3. ENRICH: Groq-based content analysis               │ │
│  │  4. STORE: Vector and metadata persistence            │ │
│  │  5. FINALIZE: Result summarization                    │ │
│  └────────────────────────────────────────────────────────┘ │
└────────────────────────┬────────────────────────────────────┘
                         │
         ┌───────────────┼───────────────┐
         ▼               ▼               ▼
    ┌─────────┐    ┌──────────┐    ┌──────────────┐
    │  FAISS  │    │PostgreSQL│    │ Groq API     │
    │ Vector  │    │ Metadata │    │ (Enrichment) │
    │ Store   │    │  Store   │    │              │
    └─────────┘    └──────────┘    └──────────────┘
```

## Installation

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

Key packages:

- langgraph==0.0.29
- groq==0.4.2
- PyPDF2==3.0.1
- python-docx==0.8.11

### 2. Configure Environment

Create `.env` file:

```bash
# Groq API
GROQ_API_KEY=gsk_your_api_key_here
GROQ_MODEL=mixtral-8x7b-32768

# Vector Store
VECTOR_STORE_PATH=./data/vector_store

# Chunking
CHUNK_SIZE=512
CHUNK_OVERLAP=50

# Metadata Store (Supabase)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key

# Application
APP_NAME=Personal Knowledge Agent
APP_VERSION=1.0.0
ENVIRONMENT=development
DEBUG=true
```

### 3. Initialize Database

```bash
python scripts/init_db.py
```

## Usage

### REST API

Start the server:

```bash
uvicorn app.main:app --reload
```

#### Example: Ingest Text

```bash
curl -X POST http://localhost:8000/documents/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "content": "# My Document\n\nContent here...",
    "source": "my_document.md",
    "input_type": "markdown"
  }'
```

#### Example: Upload File

```bash
curl -X POST http://localhost:8000/documents/ingest/upload \
  -F "file=@document.pdf" \
  -F "source=research_paper"
```

#### Example: Batch Processing

```bash
curl -X POST http://localhost:8000/documents/ingest/batch \
  -H "Content-Type: application/json" \
  -d '{
    "documents": [
      {
        "content": "Content 1",
        "source": "doc1.md",
        "input_type": "markdown"
      },
      {
        "content": "Content 2",
        "source": "doc2.md",
        "input_type": "markdown"
      }
    ]
  }'
```

### Python API

```python
from app.agents.ingestion_agent import IngestionAgent
import asyncio

async def main():
    agent = IngestionAgent()

    # Ingest text
    result = await agent.ingest(
        content="Your document content",
        source="document.md",
        input_type="markdown"
    )

    print(f"Success: {result.success}")
    print(f"Chunks: {result.chunks_created}")
    print(f"IDs: {result.document_ids}")

    # Ingest file
    result = await agent.ingest_from_file(
        file_path="/path/to/document.pdf"
    )

asyncio.run(main())
```

## Pipeline Details

### 1. Clean Stage

**Input**: Raw document (any format)
**Output**: Cleaned, normalized text

Processing:

- PDF: Extracts text using PyPDF2
- DOCX: Extracts text using python-docx
- Markdown: Removes YAML frontmatter and HTML comments
- Text: Direct processing with BOM removal
- All: Normalizes whitespace and line endings

### 2. Split Stage

**Input**: Cleaned text
**Output**: Semantic chunks with metadata

Processing:

- Uses SemanticChunker from preprocessing module
- Chunk size: 512 tokens (configurable)
- Overlap: 50 tokens for continuity
- Preserves section headings and context

### 3. Enrich Stage

**Input**: Chunks
**Output**: Enriched chunks with tags and analysis

Processing:

- Calls Groq API for intelligent analysis
- Analyzes each chunk for:
  - **Topics**: code, api, database, security, performance, configuration, mathematics, best-practices
  - **Domains**: machine-learning, data-science, backend-development, frontend-development, devops, cloud
  - **Difficulty**: beginner, intermediate, advanced
  - **Key Terms**: Top 10 terms per chunk
- Falls back to local tagging if API unavailable

### 4. Store Stage

**Input**: Enriched chunks
**Output**: Stored embeddings and metadata

Processing:

- Generates 384-dimensional embeddings (all-MiniLM-L6-v2)
- Stores embeddings in FAISS vector index
- Stores metadata in Supabase PostgreSQL:
  - Document ID, source, content hash
  - Embedding ID, tags, topics, domain
  - Difficulty level, key terms
  - Timestamps and additional metadata

### 5. Finalize Stage

**Input**: Storage results
**Output**: Ingestion summary

Processing:

- Aggregates statistics
- Collects all document IDs
- Creates IngestionResult with:
  - Success status
  - Chunk count
  - Document count
  - Error messages
  - Created document IDs

## Response Format

All endpoints return `IngestionResponse`:

```json
{
  "success": true,
  "chunks_created": 5,
  "documents_processed": 1,
  "metadata_stored": true,
  "vector_embeddings_stored": true,
  "message": "Successfully ingested 1 document with 5 chunks",
  "errors": [],
  "document_ids": ["doc_123", "doc_124", "doc_125"]
}
```

## Configuration Options

### Chunking

```bash
CHUNK_SIZE=512        # Tokens per chunk
CHUNK_OVERLAP=50      # Token overlap between chunks
```

### Groq API

```bash
GROQ_API_KEY=...              # API key (required)
GROQ_MODEL=mixtral-8x7b-32768 # Model selection
```

Available models:

- `mixtral-8x7b-32768` (default)
- `llama2-70b-4096`
- `llama3-8b-8192`

### Storage

```bash
VECTOR_STORE_PATH=./data/vector_store  # FAISS index location
SUPABASE_URL=...                       # PostgreSQL connection
SUPABASE_KEY=...                       # Authentication
```

## Error Handling

The system includes comprehensive error handling:

### Recoverable Errors

- Groq API timeout → Falls back to local tagging
- Single chunk failure → Continues with other chunks
- File format detection → Tries multiple parsers

### Unrecoverable Errors

- Empty document → Returns error in result
- Invalid file format → Returns 400 Bad Request
- Storage failure → Returns error in result

All errors are:

- Logged with full context
- Returned in response `errors` field
- Tracked for monitoring

## Performance

### Typical Processing Times

- **Text extraction**: 100-500 tokens/sec
- **Chunking**: < 100ms for 10KB documents
- **Embeddings**: ~10-50ms per chunk
- **Groq enrichment**: 1-3 sec per chunk (API dependent)
- **Storage**: < 100ms per chunk

### Optimization Tips

1. **Batch Processing**: Use `/documents/ingest/batch` for multiple documents
2. **Parallel Upload**: Process multiple files simultaneously
3. **Groq Model Selection**: Use smaller models for speed
4. **Vector Store**: Keep index size reasonable (< 1M chunks recommended)

## File Size Limits

Recommended limits (configurable):

- PDF: < 50MB
- DOCX: < 10MB
- Text/Markdown: < 100MB
- Batch: 100 documents per request

## Examples

### Example 1: Ingest Technical Documentation

```python
import asyncio
from app.agents.ingestion_agent import IngestionAgent

async def ingest_docs():
    agent = IngestionAgent()

    # Read markdown file
    with open('technical_guide.md', 'r') as f:
        content = f.read()

    result = await agent.ingest(
        content=content,
        source="technical_guide.md",
        input_type="markdown"
    )

    if result.success:
        print(f"✓ Ingested {result.chunks_created} chunks")
        for doc_id in result.document_ids:
            print(f"  - {doc_id}")
    else:
        print(f"✗ Failed: {result.message}")

asyncio.run(ingest_docs())
```

### Example 2: Batch Process Multiple PDFs

```python
import asyncio
import glob
from app.agents.ingestion_agent import IngestionAgent

async def batch_ingest():
    agent = IngestionAgent()

    pdf_files = glob.glob("documents/*.pdf")

    for pdf_file in pdf_files:
        print(f"Processing {pdf_file}...")
        result = await agent.ingest_from_file(pdf_file)

        if result.success:
            print(f"  ✓ {result.chunks_created} chunks")
        else:
            print(f"  ✗ {result.message}")

asyncio.run(batch_ingest())
```

### Example 3: REST API with Error Handling

```python
import requests
import time

def ingest_with_retry(content, source, max_retries=3):
    """Ingest with exponential backoff retry."""

    for attempt in range(max_retries):
        try:
            response = requests.post(
                'http://localhost:8000/documents/ingest',
                json={
                    'content': content,
                    'source': source,
                    'input_type': 'markdown'
                },
                timeout=30
            )

            if response.status_code == 200:
                return response.json()
            elif attempt < max_retries - 1:
                wait = 2 ** attempt
                print(f"Retrying after {wait}s...")
                time.sleep(wait)

        except requests.ConnectionError:
            if attempt < max_retries - 1:
                wait = 2 ** attempt
                time.sleep(wait)

    raise Exception("Ingestion failed after retries")

result = ingest_with_retry("# My Content", "source.md")
print(f"Chunks: {result['chunks_created']}")
```

## Troubleshooting

### Issue: Groq API fails silently

**Solution**: Check API key and ensure quota available

```bash
export GROQ_API_KEY=gsk_your_key
# Test: curl https://api.groq.com/v1/models
```

### Issue: PDF extraction produces garbled text

**Solution**: Try alternative PDF parser or manually convert

```python
# Some PDFs need preprocessing
from PyPDF2 import PdfReader
pdf = PdfReader("file.pdf")
# Check if text is extractable
```

### Issue: Vector store grows too large

**Solution**: Implement cleanup or use smaller embedding models

```bash
# Clear old embeddings
rm -rf ./data/vector_store/
# Or use lighter embeddings in config
EMBEDDING_MODEL=all-MiniLM-L6-v2
```

### Issue: Metadata queries slow

**Solution**: Add database indexes or partition tables

```sql
-- Check Supabase performance
SELECT * FROM pg_stat_statements
ORDER BY mean_exec_time DESC;
```

## Testing

Run tests:

```bash
# Unit tests
pytest tests/test_ingestion_agent.py -v

# Integration tests (requires full environment)
pytest tests/test_ingestion_agent.py -v -m integration

# Example tests
python examples/ingestion_example.py
```

## API Documentation

Full API reference available at [API.md](./API.md)

Key endpoints:

- `POST /documents/ingest` - Ingest text
- `POST /documents/ingest/upload` - Upload file
- `POST /documents/ingest/batch` - Batch processing
- `GET /documents/ingest/status` - Agent status

## See Also

- [Ingestion Agent Documentation](./INGESTION_AGENT.md)
- [API Reference](./API.md)
- [Memory System](./MEMORY.md)
- [Content Preprocessing](./PREPROCESSING.md)
- [Configuration](./SETUP.md)

## Support

For issues or questions:

1. Check logs: `logs/app.log`
2. Review error responses
3. Test with simple content first
4. Verify all environment variables
5. Check Groq API status

---

**Last Updated**: 2024
**Version**: 1.0.0
