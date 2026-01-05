# API Reference - Ingestion Endpoints

## Base URL

```
http://localhost:8000/documents
```

## Endpoints

### POST /documents/ingest

Ingest plain text or markdown content.

#### Request

```json
{
  "content": "string (required)",
  "source": "string (required)",
  "input_type": "string (optional, default: text)"
}
```

#### Parameters

| Parameter    | Type   | Description                             | Example                     |
| ------------ | ------ | --------------------------------------- | --------------------------- |
| `content`    | string | Document content                        | "# Heading\n\nContent here" |
| `source`     | string | Source identifier                       | "my_document.md"            |
| `input_type` | string | Content type: text, markdown, pdf, docx | "markdown"                  |

#### Response (200 OK)

```json
{
  "success": true,
  "chunks_created": 5,
  "documents_processed": 1,
  "metadata_stored": true,
  "vector_embeddings_stored": true,
  "message": "Successfully ingested 1 document with 5 chunks",
  "errors": [],
  "document_ids": [
    "doc_123abc",
    "doc_124def",
    "doc_125ghi",
    "doc_126jkl",
    "doc_127mno"
  ]
}
```

#### Error Responses

**400 Bad Request** - Invalid input

```json
{
  "detail": "Invalid request: Content cannot be empty"
}
```

**500 Internal Server Error** - Processing failure

```json
{
  "detail": "Ingestion failed: Vector store error"
}
```

#### Examples

**cURL**

```bash
curl -X POST http://localhost:8000/documents/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "content": "# My Document\n\nThis is test content.",
    "source": "test.md",
    "input_type": "markdown"
  }'
```

**Python**

```python
import requests

response = requests.post(
    "http://localhost:8000/documents/ingest",
    json={
        "content": "Your content here",
        "source": "document.md",
        "input_type": "markdown"
    }
)

result = response.json()
print(f"Chunks created: {result['chunks_created']}")
```

**JavaScript**

```javascript
const response = await fetch("http://localhost:8000/documents/ingest", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    content: "Your content here",
    source: "document.md",
    input_type: "markdown",
  }),
});

const result = await response.json();
console.log(`Chunks created: ${result.chunks_created}`);
```

---

### POST /documents/ingest/upload

Upload and ingest a document file.

#### Request

**Multipart Form Data**

| Field    | Type   | Description                               | Required |
| -------- | ------ | ----------------------------------------- | -------- |
| `file`   | file   | Document file (PDF, DOCX, Markdown, Text) | Yes      |
| `source` | string | Source identifier (defaults to filename)  | No       |

#### Supported Formats

- **PDF** (.pdf): Text extraction from PDF documents
- **DOCX** (.docx): Microsoft Word document processing
- **Markdown** (.md): Markdown formatted content
- **Text** (.txt): Plain text files

#### Response (200 OK)

```json
{
  "success": true,
  "chunks_created": 8,
  "documents_processed": 1,
  "metadata_stored": true,
  "vector_embeddings_stored": true,
  "message": "Successfully ingested 1 document with 8 chunks",
  "errors": [],
  "document_ids": ["doc_456abc", "doc_457def", "doc_458ghi"]
}
```

#### Error Responses

**400 Bad Request** - Unsupported file type

```json
{
  "detail": "Invalid request: Unsupported file type: docx. Supported: pdf, docx, md, txt"
}
```

**400 Bad Request** - Empty file

```json
{
  "detail": "Invalid request: File is empty"
}
```

**500 Internal Server Error** - Processing failure

```json
{
  "detail": "File ingestion failed: PDF extraction error"
}
```

#### Examples

**cURL**

```bash
# Upload PDF
curl -X POST http://localhost:8000/documents/ingest/upload \
  -F "file=@document.pdf" \
  -F "source=my_document"

# Upload with default filename as source
curl -X POST http://localhost:8000/documents/ingest/upload \
  -F "file=@research_paper.pdf"
```

**Python**

```python
import requests

with open('document.pdf', 'rb') as f:
    files = {'file': f}
    data = {'source': 'my_document'}
    response = requests.post(
        'http://localhost:8000/documents/ingest/upload',
        files=files,
        data=data
    )

result = response.json()
print(f"Chunks: {result['chunks_created']}")
```

**JavaScript (FormData)**

```javascript
const formData = new FormData();
formData.append("file", fileInput.files[0]);
formData.append("source", "my_document");

const response = await fetch("http://localhost:8000/documents/ingest/upload", {
  method: "POST",
  body: formData,
});

const result = await response.json();
console.log(`Chunks created: ${result.chunks_created}`);
```

---

### POST /documents/ingest/batch

Ingest multiple documents in a single batch request.

#### Request

```json
{
  "documents": [
    {
      "content": "string (required)",
      "source": "string (required)",
      "input_type": "string (optional)"
    }
  ]
}
```

#### Response (200 OK)

Array of ingestion results, one per document:

```json
[
  {
    "success": true,
    "chunks_created": 5,
    "documents_processed": 1,
    "metadata_stored": true,
    "vector_embeddings_stored": true,
    "message": "Successfully ingested 1 document with 5 chunks",
    "errors": [],
    "document_ids": ["doc_001", "doc_002"]
  },
  {
    "success": false,
    "chunks_created": 0,
    "documents_processed": 0,
    "metadata_stored": false,
    "vector_embeddings_stored": false,
    "message": "Ingestion failed: Invalid content",
    "errors": ["Content is too short"],
    "document_ids": []
  }
]
```

#### Examples

**cURL**

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

**Python**

```python
import requests

response = requests.post(
    "http://localhost:8000/documents/ingest/batch",
    json={
        "documents": [
            {
                "content": "Document 1 content",
                "source": "doc1.md",
                "input_type": "markdown"
            },
            {
                "content": "Document 2 content",
                "source": "doc2.md",
                "input_type": "markdown"
            }
        ]
    }
)

results = response.json()
for i, result in enumerate(results):
    print(f"Doc {i+1}: {'✓' if result['success'] else '✗'} "
          f"- {result['chunks_created']} chunks")
```

---

### GET /documents/ingest/status

Check if the ingestion agent is ready.

#### Response (200 OK)

```json
{
  "status": "ready",
  "agent": "ingestion",
  "message": "Document ingestion agent is operational"
}
```

#### Error Response (500 Internal Server Error)

```json
{
  "detail": "Ingestion agent not available"
}
```

#### Examples

**cURL**

```bash
curl http://localhost:8000/documents/ingest/status
```

**Python**

```python
import requests

response = requests.get('http://localhost:8000/documents/ingest/status')
status = response.json()
print(f"Agent status: {status['status']}")
```

---

## Response Models

### IngestResponse

Standard response format for all ingestion endpoints.

```typescript
interface IngestResponse {
  success: boolean; // Operation succeeded
  chunks_created: number; // Number of chunks created
  documents_processed: number; // Number of documents processed
  metadata_stored: boolean; // Metadata persistence successful
  vector_embeddings_stored: boolean; // Embeddings stored successfully
  message: string; // Human-readable status message
  errors: string[]; // Error messages if any
  document_ids: string[]; // IDs of created documents
}
```

### IngestRequest

Request format for `/documents/ingest`

```typescript
interface IngestRequest {
  content: string; // Document content
  source: string; // Source identifier
  input_type?: string; // Type: text, markdown, pdf, docx
}
```

### BatchIngestRequest

Request format for `/documents/ingest/batch`

```typescript
interface BatchIngestRequest {
  documents: IngestRequest[]; // Array of documents to ingest
}
```

---

## Status Codes

| Code | Meaning               | When                                |
| ---- | --------------------- | ----------------------------------- |
| 200  | OK                    | Successful ingestion                |
| 400  | Bad Request           | Invalid input, unsupported format   |
| 500  | Internal Server Error | Processing failure, API unavailable |

---

## Best Practices

### Error Handling

Always check the `success` field and handle errors:

```python
response = requests.post(...)
result = response.json()

if result['success']:
    print(f"Ingested {result['chunks_created']} chunks")
    for doc_id in result['document_ids']:
        print(f"  - {doc_id}")
else:
    print(f"Failed: {result['message']}")
    for error in result['errors']:
        print(f"  - {error}")
```

### Large Documents

For documents larger than 1MB:

1. Split into smaller files before uploading
2. Use batch endpoint for multiple files
3. Or use Python SDK directly for streaming

### Retry Strategy

For transient failures:

```python
import time

max_retries = 3
for attempt in range(max_retries):
    try:
        response = requests.post(...)
        if response.status_code == 200:
            return response.json()
    except requests.ConnectionError:
        if attempt < max_retries - 1:
            time.sleep(2 ** attempt)  # Exponential backoff
        else:
            raise
```

### Batch Processing

For bulk ingestion:

```python
# Process in batches of 10
batch_size = 10
for i in range(0, len(documents), batch_size):
    batch = documents[i:i + batch_size]
    results = requests.post(
        'http://localhost:8000/documents/ingest/batch',
        json={'documents': batch}
    ).json()

    # Handle results...
```

---

## Rate Limiting

No rate limits are currently implemented, but consider:

- Default chunking: 512 tokens per chunk
- Embedding generation: ~100-500 tokens/sec
- Groq API: Subject to Groq's rate limits
- PostgreSQL: Connection pool of 10 by default

---

## See Also

- [Ingestion Agent Documentation](./INGESTION_AGENT.md)
- [Configuration](./SETUP.md)
- [Memory System](./MEMORY.md)
