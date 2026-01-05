# Setup Guide: Preprocessing & Supabase Integration

## Prerequisites

- Python 3.11+
- PostgreSQL (or Supabase account)
- FAISS CPU package (comes with faiss-cpu)

## Installation Steps

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

The following new packages are added:
- **nltk**: Natural language toolkit
- **spacy**: NLP library
- **langchain**: LLM framework (for future integration)
- **tiktoken**: Token counter
- **supabase**: Supabase client library

### 2. Configure Supabase

#### Option A: Use Existing Supabase Project

1. Sign up at [supabase.com](https://supabase.com)
2. Create a new project
3. Go to Settings → Database → Connection String
4. Copy the connection string (PostgreSQL format)

Update `.env`:
```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
DATABASE_URL=postgresql://postgres:password@your-project.supabase.co:5432/postgres
```

#### Option B: Local Development (PostgreSQL)

If using local PostgreSQL:
```env
DATABASE_URL=postgresql://postgres:password@localhost:5432/knowledge_agent
```

### 3. Initialize Database

```python
from app.memory import MemoryManager

manager = MemoryManager()
manager.init_db()  # Creates tables automatically
```

Or in Python:
```bash
python -c "from app.memory import MemoryManager; MemoryManager().init_db()"
```

### 4. Verify Installation

```python
from app.utils.chunking import create_chunker
from app.utils.tagging import create_tagger
from app.memory import MemoryManager

# Test chunking
chunker = create_chunker()
chunks = chunker.chunk("Your test document here", source="test")
print(f"✓ Chunking works: {len(chunks)} chunks created")

# Test tagging
tagger = create_tagger()
metadata = tagger.tag_content("Machine learning requires neural networks")
print(f"✓ Tagging works: domain={metadata.domain}")

# Test memory
manager = MemoryManager()
print("✓ Memory manager initialized")
```

## Configuration

### .env File Template

```env
# Application
APP_NAME=Personal Knowledge Agent
APP_VERSION=0.1.0
ENVIRONMENT=development
DEBUG=true

# Server
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=DEBUG

# Logging
LOG_FORMAT=text  # or 'json' for production

# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
DATABASE_URL=postgresql://postgres:password@your-project.supabase.co:5432/postgres

# Vector Store
VECTOR_STORE_PATH=./data/vector_store
EMBEDDING_MODEL=all-MiniLM-L6-v2

# Text Processing
CHUNK_SIZE=512          # Characters per chunk
CHUNK_OVERLAP=50        # Overlapping characters
```

### Production Settings

For production deployment:

```env
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO
LOG_FORMAT=json
CHUNK_SIZE=1024
CHUNK_OVERLAP=100
```

## Usage Patterns

### Basic Document Ingestion

```python
from app.memory import MemoryManager

manager = MemoryManager()

# Add documents with auto-processing
doc_ids = manager.add_documents(
    documents=["Document 1...", "Document 2..."],
    source="my_source",
    tags=["imported"],
    auto_chunk=True,    # Semantic chunking
    auto_tag=True,      # Auto-tagging
)

print(f"Processed {len(doc_ids)} chunks")
```

### Search with Metadata

```python
results = manager.similarity_search(
    query="Your query here",
    k=5,
    filter_source="my_source"
)

for result in results:
    print(f"Domain: {result['domain']}")
    print(f"Difficulty: {result['difficulty_level']}")
    print(f"Topics: {result['topics']}")
```

## Database Schema

The system creates a `documents` table with:

| Column | Type | Purpose |
|--------|------|---------|
| id | UUID | Primary key |
| source | VARCHAR(255) | Document source |
| content_hash | VARCHAR(64) | Content deduplication |
| tags | JSONB | Manual tags |
| topics | JSONB | Auto-generated topics |
| domain | VARCHAR(100) | Auto-detected domain |
| difficulty_level | VARCHAR(50) | Auto-assessed difficulty |
| key_terms | JSONB | Extracted keywords |
| metadata | JSONB | Additional metadata |
| created_at | TIMESTAMP | Creation timestamp |
| updated_at | TIMESTAMP | Last update |
| embedding_id | INTEGER | Vector store reference |

**Indexes:**
- `idx_domain` - For domain filtering
- `idx_difficulty` - For difficulty filtering
- `idx_source_created` - For temporal queries
- `idx_embedding_id` - For embedding lookup

## Troubleshooting

### Issue: "No module named 'faiss'"

Solution:
```bash
pip install faiss-cpu  # For CPU
# or
pip install faiss-gpu  # For GPU (requires CUDA)
```

### Issue: "Connection refused" for database

Check your DATABASE_URL and ensure:
1. PostgreSQL/Supabase is running
2. Credentials are correct
3. Database exists

Test connection:
```bash
psql "postgresql://user:password@host:5432/database"
```

### Issue: Embedding model download failed

The `all-MiniLM-L6-v2` model (~80MB) downloads on first use.

For offline environments, pre-download:
```python
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('all-MiniLM-L6-v2')
```

### Issue: FAISS index corruption

Delete and recreate:
```bash
rm -rf ./data/vector_store/*
python -c "from app.memory import MemoryManager; MemoryManager().init_db()"
```

## Performance Tuning

### Chunking Speed
- Smaller chunks = faster processing but more vectors
- Larger chunks = fewer vectors but less granular search
- Default 512 chars is balanced for most use cases

### Tagging Speed
- Tagging uses heuristics (very fast)
- No external API calls needed
- Can be disabled with `auto_tag=False`

### Embedding Speed
- Sentence-Transformers: ~100 chunks/second (single CPU)
- FAISS search: O(log n) with indexing
- For millions of documents, consider GPU acceleration

### Database Optimization
- Indexes on domain and difficulty enable fast filtering
- JSONB fields are efficient for flexible metadata
- Supabase auto-manages connection pooling

## Monitoring

### Check Memory Stats

```python
manager = MemoryManager()
stats = manager.get_memory_stats()
print(f"Documents: {stats['total_documents']}")
print(f"Index size: {stats['index_size_mb']:.2f} MB")
print(f"Sources: {stats['sources']}")
```

### Database Monitoring

Via Supabase Dashboard:
1. Go to Home → Database → Tables
2. Check `documents` table size and row count
3. Monitor query performance

### Log Analysis

Enable JSON logs for production:
```env
LOG_FORMAT=json
```

Parse with log aggregation tools (ELK, Datadog, etc.)

## Backup Strategy

### FAISS Index Backup
```bash
cp -r ./data/vector_store /backup/vector_store_$(date +%Y%m%d)
```

### Database Backup
Via Supabase Dashboard:
1. Settings → Backups
2. Configure automated backups
3. Download on-demand backups

### Complete Backup Script
```bash
#!/bin/bash
BACKUP_DIR="/backup/knowledge_agent_$(date +%Y%m%d_%H%M%S)"
mkdir -p $BACKUP_DIR

# Backup vector store
cp -r ./data/vector_store $BACKUP_DIR/

# Backup database
pg_dump $DATABASE_URL > $BACKUP_DIR/database.sql

echo "Backup complete: $BACKUP_DIR"
```

## Migration from PostgreSQL to Supabase

1. Backup existing PostgreSQL data
2. Update DATABASE_URL to Supabase connection string
3. Run `manager.init_db()` to create tables
4. Export from old DB and re-import, or use:
   ```bash
   pg_dump old_db | psql new_supabase_url
   ```

## Next Steps

1. **Add API endpoints** in `app/api/` for document ingestion
2. **Implement batch processing** for large document sets
3. **Create LangGraph agents** using enriched memory
4. **Build frontend** for knowledge exploration
5. **Add caching layer** for frequently accessed results

## Support

For issues:
1. Check [PREPROCESSING.md](PREPROCESSING.md) for detailed docs
2. Review [EXAMPLES.py](EXAMPLES.py) for usage patterns
3. Check logs: `tail -f app.log`
4. Test components individually
