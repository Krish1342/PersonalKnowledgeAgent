"""
Content Preprocessing Documentation
====================================

The preprocessing layer provides intelligent text chunking, content analysis,
and automatic metadata generation for knowledge base documents.
"""

# SEMANTIC-AWARE CHUNKING
# ======================

## Overview
The SemanticChunker respects document structure while creating meaningful chunks.
It preserves context by:
- Recognizing paragraph boundaries
- Maintaining sentence integrity  
- Preserving section headings
- Supporting overlap between chunks

## Usage

```python
from app.utils.chunking import create_chunker

# Create chunker with defaults
chunker = create_chunker()

# Chunk single document
chunks = chunker.chunk(
    text="Your document text...",
    source="my_document"
)

# Access chunk metadata
for chunk in chunks:
    print(f"{chunk.heading}: {chunk.text[:50]}...")
    print(f"  Position: {chunk.chunk_index}/{chunk.total_chunks}")

# Chunk multiple documents
all_chunks = chunker.chunk_documents(
    documents=[doc1, doc2, doc3],
    source="batch_import"
)
```

## Chunk Structure

Each Chunk contains:
- `text`: The actual chunk content
- `start_char`: Character position in original document
- `end_char`: End character position
- `heading`: Associated heading if found
- `section`: Section name
- `chunk_index`: Index in chunk sequence
- `total_chunks`: Total chunks from document


# AUTO-GENERATED METADATA (TAGGING)
# ==================================

## Overview
ContentTagger automatically extracts:
- **Topics**: What the content is about (code, api, database, security, etc.)
- **Domain**: Technical domain (ml, backend, frontend, devops, cloud)
- **Difficulty Level**: Content complexity (beginner, intermediate, advanced)
- **Key Terms**: Most important words in content

## Tagging Strategy

### Topic Detection
Uses pattern matching to identify:
- Code blocks and programming content
- API and endpoint discussions
- Database operations
- Security-related content
- Performance optimization
- Best practices
- Mathematical/theoretical content

### Domain Classification
Keywords-based detection across:
- Machine Learning (neural networks, deep learning, models)
- Data Science (statistics, visualization, analysis)
- Backend Development (APIs, databases, servers)
- Frontend Development (React, JavaScript, components)
- DevOps (Docker, Kubernetes, CI/CD)
- Cloud Services (AWS, Azure, GCP)

### Difficulty Scoring
Weighted heuristics consider:
- **Advanced indicators**: proof, theorem, complex, optimization (+weights)
- **Beginner indicators**: introduction, tutorial, basics (-weights)
- **Text complexity**: Average word length, technical density
- **Structure**: Lists, code blocks, references

## Usage

```python
from app.utils.tagging import create_tagger

# Create tagger
tagger = create_tagger()

# Tag single text
metadata = tagger.tag_content(
    "Your content here..."
)

print(f"Domain: {metadata.domain}")
print(f"Difficulty: {metadata.difficulty_level}")
print(f"Topics: {metadata.topics}")
print(f"Key Terms: {metadata.key_terms}")

# Tag multiple texts
results = tagger.tag_batch([text1, text2, text3])
```

## ContentMetadata Structure

```python
@dataclass
class ContentMetadata:
    topics: List[str]              # e.g., ["code", "api", "security"]
    domain: str                    # e.g., "backend-development"
    difficulty_level: str          # "beginner" | "intermediate" | "advanced"
    key_terms: List[str]           # Top 10 extracted terms
    language: str                  # Default "en"
    content_length: int            # Character count
```


# INTEGRATED PIPELINE
# ====================

## MemoryManager Processing

The MemoryManager integrates chunking and tagging:

```python
from app.memory import MemoryManager

manager = MemoryManager()
manager.init_db()

# Process documents with auto-chunking and tagging
doc_ids = manager.add_documents(
    documents=["Long document...", "Another doc..."],
    source="my_knowledge_base",
    auto_chunk=True,      # Enable chunking
    auto_tag=True,        # Enable tagging
    tags=["important"],   # Additional tags
)

# Search with filtering
results = manager.similarity_search(
    query="How to optimize database queries?",
    k=5,
    filter_source="my_knowledge_base"
)

# Results include auto-generated metadata
for result in results:
    print(f"Domain: {result['domain']}")
    print(f"Difficulty: {result['difficulty_level']}")
    print(f"Topics: {result['topics']}")
```

## Data Flow

```
Raw Documents
    ↓
[SemanticChunker] → Semantic Chunks with structure
    ↓
[ContentTagger] → Auto-generated metadata
    ↓
[VectorStore] → Embeddings stored in FAISS
    ↓
[MetadataStore] → Metadata persisted in Supabase
    ↓
Queryable Knowledge Base
```


# DATABASE SCHEMA (SUPABASE)
# ===========================

The documents table includes new fields:

```sql
CREATE TABLE documents (
  id UUID PRIMARY KEY,
  source VARCHAR(255) NOT NULL,
  content_hash VARCHAR(64) UNIQUE NOT NULL,
  tags JSONB,
  topics JSONB,              -- Auto-generated
  domain VARCHAR(100),        -- Auto-generated
  difficulty_level VARCHAR(50), -- Auto-generated
  key_terms JSONB,            -- Auto-generated
  metadata JSONB,
  created_at TIMESTAMP NOT NULL,
  updated_at TIMESTAMP,
  embedding_id INTEGER UNIQUE NOT NULL,
  -- Indexes for filtering
  INDEX idx_domain (domain),
  INDEX idx_difficulty (difficulty_level),
  INDEX idx_source_created (source, created_at)
);
```

## Supabase Configuration

Set in `.env`:
```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
DATABASE_URL=postgresql://postgres:password@your-project.supabase.co:5432/postgres
```

The backend uses standard SQLAlchemy with PostgreSQL, so it works seamlessly
with Supabase's PostgreSQL database.


# CONFIGURATION
# ==============

In config.py:

```python
CHUNK_SIZE = 512           # Characters per chunk
CHUNK_OVERLAP = 50         # Overlapping characters
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
SUPABASE_URL = "https://..."
SUPABASE_KEY = "..."
DATABASE_URL = "postgresql://..."
```


# EXAMPLE: COMPLETE WORKFLOW
# ============================

```python
from app.memory import MemoryManager

# 1. Initialize
manager = MemoryManager()
manager.init_db()

# 2. Read documents
documents = [
    open("guide1.md").read(),
    open("guide2.md").read(),
]

# 3. Add to knowledge base
# Auto-chunks into ~512 char chunks with 50 char overlap
# Auto-tags each chunk with domain, difficulty, topics
doc_ids = manager.add_documents(
    documents=documents,
    source="knowledge_base",
    tags=["official"],
    auto_chunk=True,
    auto_tag=True,
)

# 4. Search
results = manager.similarity_search(
    query="How to handle authentication?",
    k=5,
    filter_source="knowledge_base"
)

# 5. Explore results
for result in results:
    print(f"Match: {result['domain']} - {result['difficulty_level']}")
    print(f"Topics: {result['topics']}")
    print(f"Key terms: {result['key_terms']}")
    print(f"Similarity: {result['similarity_score']:.3f}")
    print()

# 6. Update organization
stats = manager.get_memory_stats()
print(f"Total documents: {stats['total_documents']}")
print(f"Sources: {stats['sources']}")
```


# PERFORMANCE NOTES
# ==================

- **Chunking**: O(n) where n = document length
  - Respects boundaries for semantic meaning
  - Minimal overhead compared to fixed-size splits

- **Tagging**: O(n) for pattern matching
  - No external model calls (fast heuristics)
  - Domain classification: 6 domain checks
  - Topic extraction: regex-based patterns

- **Embedding**: O(m) where m = number of chunks
  - Uses efficient sentence-transformers
  - FAISS provides ~O(log n) search

- **Storage**: Optimized with indexes on:
  - domain (for filtering by area)
  - difficulty_level (for skill-based filtering)
  - source + created_at (for temporal queries)
