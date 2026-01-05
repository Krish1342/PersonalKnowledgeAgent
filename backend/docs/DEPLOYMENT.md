# Complete Personal Knowledge Agent - Deployment Guide

End-to-end deployment and usage guide for the Personal Knowledge Agent with LangGraph ingestion pipeline.

## Quick Start

### 1. Prerequisites

- Python 3.11+
- Groq API key (get from https://console.groq.com)
- Supabase project (get from https://supabase.com)

### 2. Installation

```bash
# Clone/navigate to project
cd PersonalKnowledgeAgent/backend

# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configuration

Create `.env` file:

```bash
# Application
APP_NAME=Personal Knowledge Agent
APP_VERSION=1.0.0
ENVIRONMENT=development
DEBUG=true

# Groq API (required for enrichment)
GROQ_API_KEY=gsk_your_api_key_here
GROQ_MODEL=mixtral-8x7b-32768

# Supabase (required for metadata)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key

# Vector Store
VECTOR_STORE_PATH=./data/vector_store

# Chunking
CHUNK_SIZE=512
CHUNK_OVERLAP=50
```

### 4. Initialize Database

```bash
python scripts/init_db.py
```

This creates:

- Vector store directory
- FAISS index files
- PostgreSQL tables in Supabase

### 5. Start Server

```bash
uvicorn app.main:app --reload
```

Server available at: http://localhost:8000

API documentation: http://localhost:8000/docs

## Architecture Overview

### System Components

```
┌────────────────────────────────────────────────────────┐
│                   FastAPI Application                   │
├────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │         REST API Endpoints                        │  │
│  │  /documents/ingest (POST)     - Text ingestion   │  │
│  │  /documents/ingest/upload     - File upload      │  │
│  │  /documents/ingest/batch      - Batch processing │  │
│  │  /documents/ingest/status     - Status check     │  │
│  └──────────────────────────────────────────────────┘  │
│                      ▼                                   │
│  ┌──────────────────────────────────────────────────┐  │
│  │     LangGraph Ingestion Agent                     │  │
│  │  (5-node orchestration workflow)                 │  │
│  │                                                   │  │
│  │  1. CLEAN:    Text extraction & normalization    │  │
│  │  2. SPLIT:    Semantic chunking with boundaries  │  │
│  │  3. ENRICH:   Groq API content analysis          │  │
│  │  4. STORE:    Vector + metadata persistence      │  │
│  │  5. FINALIZE: Result summarization               │  │
│  └──────────────────────────────────────────────────┘  │
│          │              │              │                │
│          ▼              ▼              ▼                │
│  ┌───────────────┐  ┌─────────────┐  ┌──────────────┐ │
│  │ SemanticChunk │  │ContentTagger │  │ MemoryManager│ │
│  │     er        │  │   (local)    │  │             │ │
│  └───────────────┘  └─────────────┘  └──────────────┘ │
│          │              │              │                │
│          └──────────────┼──────────────┘                │
│                         ▼                               │
│         ┌────────────────────────────────┐            │
│         │   Storage Layer Integration     │            │
│         └────────────────────────────────┘            │
└────────────────────────────────────────────────────────┘
         │                     │                    │
         ▼                     ▼                    ▼
    ┌─────────────┐    ┌──────────────┐    ┌─────────────┐
    │   FAISS     │    │  Supabase    │    │  Groq API   │
    │ Vector Index│    │  PostgreSQL  │    │  (Enrichment)
    │             │    │  Metadata    │    │             │
    └─────────────┘    └──────────────┘    └─────────────┘
```

### Data Flow

```
Document Input
      ▼
┌──────────────────┐
│   CLEAN NODE     │  ▸ Extract text (PDF, DOCX, etc.)
│                  │  ▸ Normalize whitespace
│ Input: raw data  │  ▸ Remove BOM/formatting
│ Output: text     │
└──────────────────┘
      ▼
┌──────────────────┐
│   SPLIT NODE     │  ▸ Semantic chunking
│                  │  ▸ Preserve section context
│ Input: text      │  ▸ Add overlap for continuity
│ Output: chunks   │
└──────────────────┘
      ▼
┌──────────────────┐
│  ENRICH NODE     │  ▸ Groq API analysis
│                  │  ▸ Topic classification
│ Input: chunks    │  ▸ Domain categorization
│ Output: enriched │  ▸ Difficulty assessment
│         chunks   │  ▸ Key term extraction
└──────────────────┘
      ▼
┌──────────────────┐
│   STORE NODE     │  ▸ Generate embeddings
│                  │  ▸ Store in FAISS
│ Input: enriched  │  ▸ Store metadata in PostgreSQL
│ Output: IDs      │
└──────────────────┘
      ▼
┌──────────────────┐
│  FINALIZE NODE   │  ▸ Aggregate statistics
│                  │  ▸ Collect document IDs
│ Input: results   │  ▸ Create summary
│ Output: summary  │
└──────────────────┘
      ▼
   Result
```

## API Usage

### Endpoint 1: Ingest Text

Ingest plain text or markdown directly.

```bash
curl -X POST http://localhost:8000/documents/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "content": "# My Document\n\nContent here with **bold**.",
    "source": "my_document.md",
    "input_type": "markdown"
  }'
```

**Response:**

```json
{
  "success": true,
  "chunks_created": 2,
  "documents_processed": 1,
  "metadata_stored": true,
  "vector_embeddings_stored": true,
  "message": "Successfully ingested 1 document with 2 chunks",
  "errors": [],
  "document_ids": ["doc_abc123", "doc_abc124"]
}
```

### Endpoint 2: Upload File

Upload PDF, DOCX, Markdown, or text files.

```bash
# Upload PDF
curl -X POST http://localhost:8000/documents/ingest/upload \
  -F "file=@research_paper.pdf" \
  -F "source=research_2024"

# Upload Word document
curl -X POST http://localhost:8000/documents/ingest/upload \
  -F "file=@report.docx"

# Upload Markdown
curl -X POST http://localhost:8000/documents/ingest/upload \
  -F "file=@guide.md"
```

### Endpoint 3: Batch Ingest

Process multiple documents at once.

```bash
curl -X POST http://localhost:8000/documents/ingest/batch \
  -H "Content-Type: application/json" \
  -d '{
    "documents": [
      {
        "content": "First document content",
        "source": "doc1.md",
        "input_type": "markdown"
      },
      {
        "content": "Second document content",
        "source": "doc2.md",
        "input_type": "markdown"
      }
    ]
  }'
```

**Response:**

```json
[
  {
    "success": true,
    "chunks_created": 3,
    "documents_processed": 1,
    ...
  },
  {
    "success": true,
    "chunks_created": 2,
    "documents_processed": 1,
    ...
  }
]
```

### Endpoint 4: Check Status

```bash
curl http://localhost:8000/documents/ingest/status
```

**Response:**

```json
{
  "status": "ready",
  "agent": "ingestion",
  "message": "Document ingestion agent is operational"
}
```

## Python Usage

### Direct Agent Usage

```python
from app.agents.ingestion_agent import IngestionAgent
import asyncio

async def main():
    # Create agent
    agent = IngestionAgent()

    # Ingest text
    result = await agent.ingest(
        content="# My Document\n\nContent here",
        source="document.md",
        input_type="markdown"
    )

    print(f"Status: {'✓' if result.success else '✗'}")
    print(f"Chunks: {result.chunks_created}")
    print(f"Document IDs: {result.document_ids}")

asyncio.run(main())
```

### File Ingestion

```python
async def ingest_files():
    agent = IngestionAgent()

    # Ingest from file
    result = await agent.ingest_from_file(
        file_path="/path/to/document.pdf",
        source="research_paper"
    )

    if result.success:
        print(f"✓ Created {result.chunks_created} chunks")
    else:
        print(f"✗ Failed: {result.message}")

asyncio.run(ingest_files())
```

### Batch Processing

```python
async def batch_ingest():
    agent = IngestionAgent()

    documents = [
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

    for doc in documents:
        result = await agent.ingest(**doc)
        print(f"{'✓' if result.success else '✗'} {doc['source']}")

asyncio.run(batch_ingest())
```

## Supported Document Types

| Type       | Extension | Parser      |
| ---------- | --------- | ----------- |
| Plain Text | .txt      | Direct read |
| Markdown   | .md       | Direct read |
| PDF        | .pdf      | PyPDF2      |
| Word       | .docx     | python-docx |

## Configuration Reference

### Application Settings

```bash
APP_NAME=Personal Knowledge Agent     # Application name
APP_VERSION=1.0.0                     # Version
ENVIRONMENT=development               # development|staging|production
DEBUG=true                            # Debug mode
```

### Groq API Settings

```bash
GROQ_API_KEY=gsk_xxxxxxxxxxxx         # API key (required)
GROQ_MODEL=mixtral-8x7b-32768        # LLM model to use
```

Available models:

- `mixtral-8x7b-32768` (recommended)
- `llama2-70b-4096`
- `llama3-8b-8192`

### Storage Settings

```bash
VECTOR_STORE_PATH=./data/vector_store  # FAISS index location
SUPABASE_URL=https://xxx.supabase.co   # PostgreSQL connection
SUPABASE_KEY=xxx                       # Authentication key
```

### Chunking Settings

```bash
CHUNK_SIZE=512                        # Tokens per chunk
CHUNK_OVERLAP=50                      # Token overlap
```

## Monitoring & Logging

### View Logs

```bash
# All logs
tail -f logs/app.log

# Only errors
tail -f logs/app.log | grep ERROR

# JSON formatted
tail -f logs/app.log | jq
```

### Health Check

```bash
curl http://localhost:8000/health
```

## Troubleshooting

### Issue 1: Groq API Errors

**Error**: `groq.error.RateLimitError`

**Solution**:

```bash
# Check API key
echo $GROQ_API_KEY

# Verify quota at https://console.groq.com
# Agent has fallback to local tagging
```

### Issue 2: PDF Extraction Fails

**Error**: `Failed to extract text from PDF`

**Solution**:

```python
# Check if PDF is corrupted or scanned
from PyPDF2 import PdfReader
reader = PdfReader("file.pdf")
for page in reader.pages:
    text = page.extract_text()
    if not text:
        print("Cannot extract text from this page")
```

### Issue 3: Vector Store Issues

**Error**: `No such file or directory: ./data/vector_store`

**Solution**:

```bash
# Run initialization script
python scripts/init_db.py

# Or manually create directory
mkdir -p ./data/vector_store
```

### Issue 4: Database Connection

**Error**: `Failed to connect to Supabase`

**Solution**:

```bash
# Verify credentials
echo "SUPABASE_URL=$SUPABASE_URL"
echo "SUPABASE_KEY=$SUPABASE_KEY"

# Test connection
python -c "from app.memory import MetadataStore; m = MetadataStore()"
```

## Performance Tips

### 1. Optimize Chunk Size

```bash
# Smaller chunks = faster processing but more storage
CHUNK_SIZE=256  # Faster

# Larger chunks = slower but fewer embeddings
CHUNK_SIZE=1024 # More comprehensive
```

### 2. Batch Processing

```bash
# Process multiple documents at once
POST /documents/ingest/batch

# More efficient than individual requests
```

### 3. Use Streaming

For very large files, process in chunks:

```python
async def stream_process(file_path):
    chunk_size = 10000  # bytes
    with open(file_path, 'rb') as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            # Process chunk
```

### 4. Groq Model Selection

```bash
# Faster models
GROQ_MODEL=llama3-8b-8192

# More capable but slower
GROQ_MODEL=mixtral-8x7b-32768
```

## Deployment

### Local Development

```bash
uvicorn app.main:app --reload
```

### Production

```bash
# With Gunicorn
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 app.main:app

# With Docker
docker build -t knowledge-agent .
docker run -p 8000:8000 knowledge-agent
```

### Environment-Specific Settings

Create separate `.env` files:

```bash
.env.development
.env.staging
.env.production
```

Load based on ENVIRONMENT:

```bash
ENVIRONMENT=production
# App loads .env.production
```

## Monitoring & Metrics

### Key Metrics

```bash
# Check ingestion success rate
grep "ingestion" logs/app.log | grep -c "success"

# Average chunks per document
grep "chunks_created" logs/app.log | jq '.chunks_created' | stats
```

### Performance Benchmarks

Expected performance on standard hardware:

| Operation                    | Time              |
| ---------------------------- | ----------------- |
| Text extraction (1KB)        | < 10ms            |
| Semantic chunking            | < 100ms per 10KB  |
| Embedding generation         | 10-50ms per chunk |
| Groq enrichment              | 1-3 sec per chunk |
| Storage (FAISS + PostgreSQL) | < 100ms per chunk |

## Advanced Usage

### Custom Preprocessing

```python
from app.agents.ingestion_agent import DocumentCleaner

cleaner = DocumentCleaner()

# Custom cleaning
text = "Raw text with ###BOM###"
clean = cleaner.clean_text(text)

# Custom extraction
with open("file.pdf", "rb") as f:
    text = cleaner.extract_from_pdf(f.read())
```

### Direct LangGraph Workflow

```python
from app.agents.ingestion_agent import IngestionAgent

agent = IngestionAgent()
graph = agent._build_graph()

# Execute graph directly
result = graph.invoke({
    "raw_input": "Document content",
    "input_type": "text",
    "source": "source.txt",
    ...
})
```

### Error Recovery

```python
async def ingest_with_retry(content, source, max_retries=3):
    agent = IngestionAgent()

    for attempt in range(max_retries):
        try:
            result = await agent.ingest(
                content=content,
                source=source,
                input_type="markdown"
            )

            if result.success:
                return result

        except Exception as e:
            if attempt == max_retries - 1:
                raise

            await asyncio.sleep(2 ** attempt)

    return result
```

## Next Steps

1. **Deploy to Cloud**: AWS EC2, DigitalOcean, or Heroku
2. **Add Authentication**: Implement API key or OAuth
3. **Setup Monitoring**: Use DataDog, New Relic, or CloudWatch
4. **Add Caching**: Redis for frequently accessed documents
5. **Implement Webhooks**: Notify external systems on ingestion
6. **Create Dashboard**: Monitor ingestion status and metrics

## Documentation

- [API Reference](./API.md) - Complete endpoint documentation
- [Ingestion Agent](./INGESTION_AGENT.md) - Agent architecture
- [Memory System](./MEMORY.md) - Vector and metadata stores
- [Content Preprocessing](./PREPROCESSING.md) - Chunking and tagging
- [Setup Guide](./SETUP.md) - Installation and configuration

## Support & Troubleshooting

- **Logs**: `logs/app.log`
- **API Docs**: http://localhost:8000/docs
- **Groq Docs**: https://console.groq.com/docs
- **Supabase Docs**: https://supabase.com/docs

---

**Last Updated**: 2024
**Version**: 1.0.0
**Status**: Production Ready ✅
