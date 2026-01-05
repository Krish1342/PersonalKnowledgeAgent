# Ingestion Agent

The **Ingestion Agent** is a LangGraph-based orchestration system that accepts raw documents in multiple formats (PDF, DOCX, Markdown, plain text) and processes them through an intelligent pipeline to extract, chunk, enrich, and store content in vector and metadata stores.

## Architecture Overview

The ingestion agent implements a 5-stage workflow:

```
START → CLEAN → SPLIT → ENRICH → STORE → FINALIZE → END
```

### Pipeline Stages

1. **CLEAN**: Text normalization and format-specific extraction

   - Handles PDFs, DOCX files, Markdown, and plain text
   - Removes BOM characters and excess whitespace
   - Cleans Markdown-specific syntax

2. **SPLIT**: Semantic chunking with boundary preservation

   - Splits content into manageable chunks (default: 512 tokens)
   - Preserves section headings and context
   - Implements overlap for continuity

3. **ENRICH**: Groq-based intelligent analysis

   - Uses Groq API to analyze chunk content
   - Assigns topics, domains, and difficulty levels
   - Falls back to local tagging if API unavailable

4. **STORE**: Vector and metadata persistence

   - Generates embeddings for each chunk
   - Stores in FAISS vector index
   - Persists metadata to Supabase PostgreSQL

5. **FINALIZE**: Summary generation
   - Creates ingestion result with statistics
   - Tracks document IDs and processing status

## Usage

### Direct Agent Usage

```python
from app.agents.ingestion_agent import IngestionAgent

agent = IngestionAgent()

# Ingest text content
result = await agent.ingest(
    content="Your content here",
    source="document.md",
    input_type="markdown"
)

# Or ingest from file
result = await agent.ingest_from_file(
    file_path="/path/to/document.pdf",
    source="my_document"
)
```

### REST API Endpoints

#### Ingest Text

```bash
curl -X POST http://localhost:8000/documents/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Your content",
    "source": "document.md",
    "input_type": "markdown"
  }'
```

#### Upload File

```bash
curl -X POST http://localhost:8000/documents/ingest/upload \
  -F "file=@document.pdf" \
  -F "source=my_document"
```

#### Batch Ingestion

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

#### Check Status

```bash
curl http://localhost:8000/documents/ingest/status
```

## Response Models

### IngestionResponse

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

## Configuration

### Environment Variables

```bash
# Groq API configuration
GROQ_API_KEY=gsk_xxxxxxxxxxxx
GROQ_MODEL=mixtral-8x7b-32768  # Default

# Vector store
VECTOR_STORE_PATH=./data/vector_store

# Chunking
CHUNK_SIZE=512
CHUNK_OVERLAP=50

# Metadata store (Supabase)
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_KEY=xxxxx
```

## Supported Input Types

| Type       | Description                | Extensions |
| ---------- | -------------------------- | ---------- |
| `text`     | Plain text documents       | .txt       |
| `markdown` | Markdown formatted content | .md        |
| `pdf`      | PDF documents              | .pdf       |
| `docx`     | Microsoft Word documents   | .docx      |

## File Extraction

### PDF Extraction

- Uses PyPDF2 for text extraction
- Handles multi-page documents
- Graceful error handling per page

### DOCX Extraction

- Uses python-docx for Word document parsing
- Preserves paragraph structure
- Handles tables and formatting

## Enrichment with Groq

The enrichment stage uses Groq API to analyze chunks and determine:

### Topics

- code
- api
- database
- security
- performance
- configuration
- mathematics
- best-practices

### Domains

- machine-learning
- data-science
- backend-development
- frontend-development
- devops
- cloud

### Difficulty Levels

- beginner
- intermediate
- advanced

### Key Terms

- Top 10 terms extracted per chunk

## Error Handling

The agent includes comprehensive error handling:

1. **File Format Errors**: Invalid or unsupported file types return 400 Bad Request
2. **API Errors**: Groq API failures fall back to local tagging
3. **Storage Errors**: Metadata or vector store failures are logged and returned
4. **Processing Errors**: Individual document failures don't stop batch operations

All errors are collected in the `errors` field of the response.

## Performance

- Typical ingestion: 100-500 tokens per second
- Batch processing: Sequential with per-document error isolation
- Embeddings: 384-dimensional vectors (all-MiniLM-L6-v2)
- Storage: FAISS index + PostgreSQL metadata

## Example Workflow

```python
import asyncio
from app.agents.ingestion_agent import IngestionAgent

async def main():
    agent = IngestionAgent()

    # Step 1: Prepare content
    content = """
    # Machine Learning

    Key concepts:
    - Supervised Learning
    - Unsupervised Learning
    - Reinforcement Learning
    """

    # Step 2: Ingest
    result = await agent.ingest(
        content=content,
        source="ml_intro.md",
        input_type="markdown"
    )

    # Step 3: Handle result
    if result.success:
        print(f"✓ Created {result.chunks_created} chunks")
        print(f"✓ Document IDs: {result.document_ids}")
    else:
        print(f"✗ Failed: {result.message}")
        print(f"✗ Errors: {result.errors}")

asyncio.run(main())
```

## Integration with Memory Layer

The ingestion agent seamlessly integrates with:

- **VectorStore**: FAISS-based similarity search with persistent index
- **MetadataStore**: Supabase PostgreSQL with enriched schema
- **Chunking**: SemanticChunker with boundary-aware splitting
- **Tagging**: ContentTagger with Groq-powered enrichment

See [PREPROCESSING.md](../docs/PREPROCESSING.md) for details on chunking and tagging.
See [MEMORY.md](../docs/MEMORY.md) for vector and metadata store details.

## Advanced Usage

### Custom Groq Models

Update `GROQ_MODEL` in environment to use different models:

- `mixtral-8x7b-32768` (default)
- `llama2-70b-4096`
- `llama3-8b-8192`

### Batch Processing

Process multiple documents efficiently:

```python
documents = [
    {"content": "...", "source": "doc1.md", "input_type": "markdown"},
    {"content": "...", "source": "doc2.md", "input_type": "markdown"},
]

for doc in documents:
    result = await agent.ingest(**doc)
    print(f"Processed {doc['source']}: {result.success}")
```

### Error Recovery

Failed chunks are tracked in the result and can be reprocessed:

```python
result = await agent.ingest(...)

if result.errors:
    # Log errors for retry
    logger.error(f"Ingestion errors: {result.errors}")
    # Implement retry logic based on error types
```

## Troubleshooting

### Groq API Failures

- Check `GROQ_API_KEY` is set correctly
- Verify API key has quota remaining
- Agent falls back to local tagging if API unavailable

### File Upload Errors

- Ensure file format is supported (.pdf, .docx, .md, .txt)
- Check file is not corrupted
- Verify file size is reasonable (< 50MB recommended)

### Vector Store Issues

- Ensure `VECTOR_STORE_PATH` directory exists and is writable
- Check disk space for index storage
- Delete `./data/vector_store/` to rebuild index

### Metadata Store Issues

- Verify Supabase connection string
- Check database has required tables (created on init_db())
- Ensure user has write permissions

## See Also

- [API Reference](./API.md)
- [Memory System](./MEMORY.md)
- [Content Preprocessing](./PREPROCESSING.md)
- [Configuration](./SETUP.md)
