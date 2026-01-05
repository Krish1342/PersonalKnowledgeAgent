# Quick Reference Guide

## Installation (5 minutes)

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
# Edit .env with Supabase credentials
python -c "from app.memory import MemoryManager; MemoryManager().init_db()"
uvicorn app.main:app --reload
```

## Basic Usage

### Add Documents
```python
from app.memory import MemoryManager

manager = MemoryManager()
manager.init_db()  # One-time setup

doc_ids = manager.add_documents(
    documents=["Your document text..."],
    source="my_source",
    auto_chunk=True,    # Enable chunking
    auto_tag=True,      # Enable tagging
)
```

### Search Documents
```python
results = manager.similarity_search(
    query="Search query",
    k=5,
    filter_source="my_source"  # Optional
)

for result in results:
    print(f"Domain: {result['domain']}")
    print(f"Difficulty: {result['difficulty_level']}")
    print(f"Topics: {result['topics']}")
    print(f"Similarity: {result['similarity_score']:.1%}")
```

### Get Statistics
```python
stats = manager.get_memory_stats()
print(f"Documents: {stats['total_documents']}")
print(f"Model: {stats['model']}")
print(f"Storage: {stats['index_size_mb']:.2f} MB")
```

## Configuration

### Key .env Variables
```env
DATABASE_URL=postgresql://...       # Supabase connection
CHUNK_SIZE=512                      # Chars per chunk
CHUNK_OVERLAP=50                    # Overlapping chars
EMBEDDING_MODEL=all-MiniLM-L6-v2   # Sentence encoder
VECTOR_STORE_PATH=./data/vector_store  # Storage location
```

## API Quick Reference

### Chunking
```python
from app.utils.chunking import create_chunker

chunker = create_chunker(chunk_size=512, chunk_overlap=50)
chunks = chunker.chunk("Your text", source="test")

for chunk in chunks:
    print(f"{chunk.heading}: {chunk.text}")
```

### Tagging
```python
from app.utils.tagging import create_tagger

tagger = create_tagger()
metadata = tagger.tag_content("Your content")

print(f"Domain: {metadata.domain}")
print(f"Difficulty: {metadata.difficulty_level}")
print(f"Topics: {metadata.topics}")
print(f"Terms: {metadata.key_terms}")
```

## Common Tasks

### Filter by Domain
```python
# In database directly
from sqlalchemy.orm import sessionmaker
from app.memory.metadata_store import DocumentMetadata

session = sessionmaker(bind=engine)()
docs = session.query(DocumentMetadata).filter_by(
    domain="backend-development"
).all()
```

### Filter by Difficulty
```python
beginner = session.query(DocumentMetadata).filter_by(
    difficulty_level="beginner"
).all()
```

### Delete by Source
```python
result = manager.delete_by_source("old_source")
print(f"Deleted {result['documents_deleted']} documents")
```

### Batch Processing
```python
documents = [
    open("doc1.md").read(),
    open("doc2.md").read(),
]

manager.add_documents(
    documents=documents,
    source="batch",
    auto_chunk=True,
    auto_tag=True,
)
```

## Topics Available

| Topic | Detection | Use Case |
|-------|-----------|----------|
| code | \`\`\` blocks | Programming content |
| api | endpoint, request, response | API documentation |
| database | query, schema, table | Database docs |
| security | encryption, password, auth | Security guides |
| performance | optimization, latency | Performance guides |
| configuration | config, settings, parameters | Setup docs |
| mathematics | equations, proofs | Academic content |
| best-practices | best practice, recommendation | Guidelines |

## Domains Available

| Domain | Keywords | Example |
|--------|----------|---------|
| machine-learning | neural, model, tensor | AI/ML papers |
| data-science | statistics, analysis, visualization | Data docs |
| backend-development | API, database, server | Backend guides |
| frontend-development | React, JavaScript, component | Web docs |
| devops | Docker, Kubernetes, CI/CD | DevOps guides |
| cloud | AWS, Azure, GCP | Cloud docs |

## Difficulty Scoring

```
Score > 3        → advanced
0 < Score ≤ 3    → intermediate
Score ≤ 0        → beginner
```

**Increases score:**
- Proof, theorem, mathematical (+2)
- Complex, optimization (+1.5)
- Architecture, design pattern (+1)
- Long words (>8 chars)
- High technical density (>30% long words)

**Decreases score:**
- Introduction, getting started, basics (-2)
- Simple, tutorial (-1)
- Example (-0.5)

## Performance Tips

### Speed Up
```python
# Use larger chunks
chunker = create_chunker(chunk_size=1024)

# Skip tagging if not needed
manager.add_documents(..., auto_tag=False)

# Use GPU for embeddings
# pip install faiss-gpu
```

### Optimize Search
```python
# Use threshold to filter poor matches
results = manager.similarity_search(
    query="...",
    k=10,
    threshold=0.5  # Similarity distance threshold
)
```

### Manage Storage
```python
# Check storage usage
stats = manager.get_memory_stats()
print(f"Index size: {stats['index_size_mb']:.1f} MB")

# Clear old source
manager.delete_by_source("obsolete_source")
```

## Troubleshooting

### Connection Error
```python
# Check DATABASE_URL format
# Should be: postgresql://user:pass@host:5432/db
```

### FAISS Error
```python
# Reinitialize if corrupted
import shutil
shutil.rmtree("./data/vector_store")
MemoryManager().init_db()
```

### Embedding Model
```python
# If download fails, pre-download:
from sentence_transformers import SentenceTransformer
SentenceTransformer('all-MiniLM-L6-v2')
```

## Documentation Links

| Document | Purpose |
|----------|---------|
| [SETUP.md](SETUP.md) | Installation & setup |
| [PREPROCESSING.md](PREPROCESSING.md) | Detailed usage guide |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Technical design |
| [EXAMPLES.py](EXAMPLES.py) | Code examples |
| [CHECKLIST.md](CHECKLIST.md) | Implementation checklist |

## Environment Templates

### Development
```env
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=DEBUG
LOG_FORMAT=text
CHUNK_SIZE=512
CHUNK_OVERLAP=50
```

### Production
```env
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO
LOG_FORMAT=json
CHUNK_SIZE=1024
CHUNK_OVERLAP=100
```

## Testing

### Quick Test
```python
from app.memory import MemoryManager

manager = MemoryManager()
manager.init_db()

# Test chunking
doc_ids = manager.add_documents(
    ["Test document text"],
    "test",
    auto_chunk=True,
    auto_tag=True
)

# Test search
results = manager.similarity_search("test query", k=1)

print(f"✓ {len(doc_ids)} chunks created")
print(f"✓ {len(results)} results found")
```

## Next Steps

1. **Install**: Follow [SETUP.md](SETUP.md)
2. **Learn**: Review [EXAMPLES.py](EXAMPLES.py)
3. **Explore**: Check [PREPROCESSING.md](PREPROCESSING.md)
4. **Integrate**: Add API endpoints
5. **Deploy**: Follow production checklist

## Getting Help

- Check [SETUP.md](SETUP.md) troubleshooting section
- Review [ARCHITECTURE.md](ARCHITECTURE.md) for design details
- Look at [EXAMPLES.py](EXAMPLES.py) for usage patterns
- Check docstrings in source code
