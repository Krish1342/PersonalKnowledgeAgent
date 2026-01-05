# Architecture Overview: Content Preprocessing & Memory

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                      FASTAPI APPLICATION                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              API LAYER (app/api/)                        │   │
│  │  - /documents POST (ingest)                              │   │
│  │  - /search POST (query)                                  │   │
│  │  - /memory/stats GET (statistics)                        │   │
│  └──────────────────────────────────────────────────────────┘   │
│                           ▼                                       │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │           MEMORY MANAGER (app/memory/__init__.py)        │   │
│  │  Orchestrates the complete pipeline                      │   │
│  └──────────────────────────────────────────────────────────┘   │
│                           │                                       │
│            ┌──────────────┼──────────────┬──────────────┐         │
│            ▼              ▼              ▼              ▼         │
│  ┌──────────────┐ ┌────────────┐ ┌─────────────┐ ┌──────────┐  │
│  │  CHUNKER     │ │   TAGGER   │ │VECTOR STORE │ │ METADATA │  │
│  │              │ │            │ │             │ │  STORE   │  │
│  │ Semantic     │ │ Auto-tags: │ │ FAISS Index │ │          │  │
│  │ chunking:    │ │ - topics   │ │ - L2 search │ │ SQLAlch  │  │
│  │ - Boundaries │ │ - domain   │ │ - Index:    │ │ PostgreS │  │
│  │ - Headings   │ │ - difficulty│ │  sentence-  │ │ Supabase │  │
│  │ - Structure  │ │ - key_terms │ │  trans      │ │          │  │
│  └──────────────┘ └────────────┘ │             │ │ Metadata │  │
│         ▲              ▲          │ Persistent  │ │ fields:  │  │
│         │              │          │ storage:    │ │ - source │  │
│         │              │          │ ./data/     │ │ - domain │  │
│         └──────────────┴──────────┤  vector_    │ │ - topics │  │
│                                   │  store/     │ │ - difficulty│
│                                   │             │ │ - key_terms│
│                                   └─────────────┘ └──────────┘  │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
         │                    │                        │
         │                    │                        │
         ▼                    ▼                        ▼
    Raw Documents       Vector Index         Database Tables
    (markdown, txt)    (FAISS format)         (Supabase)
```

## Data Flow Pipeline

```
INPUT: Raw Document
  ↓
[CHUNKING PHASE]
  - Split by paragraph boundaries (semantic-aware)
  - Preserve heading and section information
  - Maintain configurable overlap
  ↓
INTERMEDIATE: Semantic Chunks with context
  ↓
[TAGGING PHASE]
  - Extract topics (pattern matching)
  - Detect domain (keyword analysis)
  - Assess difficulty (heuristic scoring)
  - Extract key terms (frequency analysis)
  ↓
ENRICHED: Chunks with metadata
  ↓
[VECTOR PHASE]
  - Encode with sentence-transformers
  - Generate embeddings (384-dim vectors)
  - Store in FAISS index (L2 distance)
  - Persist to disk (faiss.index + id_map.pkl)
  ↓
[DATABASE PHASE]
  - Store metadata record in Supabase
  - Link to embedding via ID
  - Create indexes for filtering
  ↓
OUTPUT: Searchable Knowledge Base
```

## Component Details

### 1. SemanticChunker (app/utils/chunking.py)

**Purpose:** Intelligent text splitting that preserves document structure

**Algorithm:**
```
for each section:
  current_position = 0
  while current_position < section_length:
    target_end = current_position + CHUNK_SIZE
    
    # Try to find boundary (paragraph > sentence > word)
    split_point = find_semantic_boundary(
      text,
      current_position,
      target_end
    )
    
    if split_point > 0:
      create_chunk(text[current_position:split_point])
      current_position = split_point - OVERLAP
    else:
      break
```

**Key Features:**
- Respects paragraph breaks (double newlines)
- Maintains sentence endings
- Preserves headings and sections
- Configurable size and overlap
- Tracks position metadata

**Time Complexity:** O(n) where n = document length
**Space Complexity:** O(m) where m = number of chunks

### 2. ContentTagger (app/utils/tagging.py)

**Purpose:** Auto-generate metadata without external API calls

**Topics Detection (Pattern Matching):**
- `code`: Detects code blocks (``` or indented)
- `api`: Matches API/endpoint patterns
- `database`: Finds database-related keywords
- `security`: Identifies security mentions
- `performance`: Finds optimization references
- `mathematics`: Detects equations and proofs
- `configuration`: Finds config/settings patterns
- `best-practices`: Detects practice recommendations

**Domain Classification (Keyword Matching):**
```
domain_keywords = {
    "machine-learning": [neural, learning, model, tensor, ...],
    "backend-development": [api, database, server, rest, ...],
    "frontend-development": [react, javascript, component, ...],
    ...
}

score_domain(text):
  max_score = 0
  for domain, keywords in domain_keywords:
    score = count_occurrences(text, keywords)
    if score > max_score:
      best_domain = domain
  return best_domain
```

**Difficulty Assessment (Scoring System):**
```
score = 0

# Advanced indicators
for (indicator, weight) in ADVANCED_INDICATORS:
  score += count(indicator) * weight

# Beginner indicators
for (indicator, weight) in BEGINNER_INDICATORS:
  score += count(indicator) * weight

# Text complexity
avg_word_length = measure_word_length(text)
if avg_word_length > 6:
  score += 0.5

if score > 3:
  difficulty = "advanced"
elif score > 0:
  difficulty = "intermediate"
else:
  difficulty = "beginner"
```

**Time Complexity:** O(n) where n = text length
**Space Complexity:** O(1) (constant pattern matches)

### 3. VectorStore (app/memory/vector_store.py)

**Purpose:** Efficient semantic search via embeddings

**Technology Stack:**
- **Embeddings:** Sentence-Transformers (all-MiniLM-L6-v2)
  - 384-dimensional vectors
  - ~80MB model size
  - Fast encoding (~100 docs/sec)
  
- **Index:** FAISS IndexIDMap
  - L2 Euclidean distance
  - ~O(log n) search with indexing
  - Supports ~billions of vectors

**Storage Structure:**
```
./data/vector_store/
├── faiss.index          # FAISS binary index
└── id_map.pkl           # Python pickle: {embedding_id: content_hash}
```

**Search Process:**
```
1. Encode query with Sentence-Transformer
2. Search FAISS index for k nearest neighbors
3. Map embedding IDs back to content hashes
4. Return (content_hash, distance) pairs
5. Convert distance to similarity score: 1 / (1 + distance)
```

**Time Complexity:**
- Add: O(m * d) where m = batch size, d = embedding dim
- Search: O(d + log n) where n = index size, d = embedding dim
- Delete: O(k) where k = items to delete

### 4. MetadataStore (app/memory/metadata_store.py)

**Purpose:** Persistent metadata and filtering

**Database Schema (Supabase PostgreSQL):**
```sql
documents {
  id: UUID (primary key)
  source: VARCHAR(255) [indexed]
  content_hash: VARCHAR(64) [unique, indexed]
  tags: JSONB (manual tags)
  topics: JSONB (auto-generated)
  domain: VARCHAR(100) [indexed]
  difficulty_level: VARCHAR(50) [indexed]
  key_terms: JSONB
  metadata: JSONB (flexible)
  created_at: TIMESTAMP [indexed with source]
  updated_at: TIMESTAMP
  embedding_id: INTEGER [unique, indexed]
}
```

**Index Strategy:**
```
- idx_source_created: (source, created_at)
  → Fast lookup by source with time range
  
- idx_domain: (domain)
  → Filter by technical domain
  
- idx_difficulty: (difficulty_level)
  → Find beginner/advanced content
  
- idx_embedding_id: (embedding_id)
  → Quick metadata lookup from vector search
```

**Deduplication:**
- Content hash ensures no duplicate content
- Embedding ID links to single vector
- Unique constraints prevent redundancy

## Configuration Hierarchy

```
Default Values (app/config.py)
         ↓
Environment Variables (.env file)
         ↓
Runtime Overrides (function parameters)
         ↓
Active Configuration
```

Example:
```python
# Default: CHUNK_SIZE = 512
# .env: CHUNK_SIZE = 1024
# Runtime: chunker = SemanticChunker(chunk_size=800)
# Result: uses 800
```

## Integration Points

### API Integration (Future)
```python
@app.post("/documents")
async def ingest_document(request: DocumentRequest):
    """API endpoint for document ingestion"""
    manager = MemoryManager()
    doc_ids = manager.add_documents(
        documents=request.documents,
        source=request.source,
        auto_chunk=True,
        auto_tag=True,
    )
    return {"doc_ids": doc_ids, "count": len(doc_ids)}

@app.post("/search")
async def search(query: str, k: int = 5):
    """Semantic search endpoint"""
    manager = MemoryManager()
    results = manager.similarity_search(query, k=k)
    return results
```

### LangGraph Integration (Future)
```python
from langgraph.graph import StateGraph
from app.memory import MemoryManager

def memory_tool(state, query):
    """Tool for agents to query knowledge base"""
    manager = MemoryManager()
    results = manager.similarity_search(query, k=5)
    return format_results(results)

graph = StateGraph(AgentState)
graph.add_node("retrieve", memory_tool)
```

## Performance Characteristics

| Operation | Complexity | Time (1M docs) |
|-----------|-----------|---|
| Chunk 1000 chars | O(n) | < 1ms |
| Tag 1000 chars | O(n) | < 5ms |
| Embed 1000 chars | O(d) | 10ms |
| FAISS search | O(log n + d) | 50ms |
| DB filter | O(log n) | 10ms |
| **Total pipeline** | O(n log n + d) | ~75ms |

Where:
- n = corpus size
- d = embedding dimension (384)

## Deployment Architecture

```
Production Environment:

  [Load Balancer]
         ↓
  [FastAPI Replicas] ← Stateless (multiple instances)
         ↓
    [Cache Layer] ← Optional Redis/Memcached
         ↓
    [FAISS Index] ← Shared filesystem or S3
    [PostgreSQL] ← Supabase managed database
```

Notes:
- FAISS index is read-heavy → can cache in memory
- Metadata queries → benefit from PostgreSQL indexing
- Embeddings → can be distributed across replicas
- Supabase handles connection pooling and replication

## Scalability Considerations

**Horizontal Scaling:**
- Each API replica has own in-memory model (sentence-transformer)
- FAISS index can be shared or replicated
- Database queries scale with PostgreSQL replication

**Vertical Scaling:**
- Increase CHUNK_SIZE for fewer vectors
- Use GPU for embeddings (faiss-gpu)
- Optimize database with more resources

**Data Scaling:**
- FAISS supports billions of vectors
- PostgreSQL proven for large tables
- Supabase auto-scales storage

## Security Considerations

- [ ] Validate document sources
- [ ] Authenticate API endpoints
- [ ] Encrypt vector store on disk
- [ ] Use Supabase row-level security
- [ ] Rate limit ingestion endpoints
- [ ] Audit document deletions
- [ ] Separate API key from connection string
