# Second Brain 🧠

A **production-grade Personal Knowledge Base Agent** powered by RAG (Retrieval Augmented Generation) and LangGraph agents.

![Version](https://img.shields.io/badge/version-2.0.0-blue)
![License](https://img.shields.io/badge/license-MIT-green)

## ✨ Features

### Core Features

- 🔍 **RAG-Powered Search** - Query your knowledge base with natural language
- 📥 **Smart Ingestion** - Upload files or paste text with automatic chunking
- 🤖 **Agent Workflow** - Plan → Retrieve → Reason → Critique → Reflect
- 📊 **Memory Management** - View, search, and organize your memories

### New in v2.0

- 🔐 **Clerk Authentication** - Secure user authentication and data isolation
- 📦 **Data Compression** - Gzip compression saves 60-80% storage space
- 🏷️ **Smart Tagging** - AI-powered automatic content categorization
- ⭐ **Bookmarks** - Star important memories for quick access
- 🌐 **Knowledge Graph** - Visualize connections between memories
- 📤 **Export/Import** - Backup and restore your knowledge base
- 🔍 **Search History** - Track your queries
- 🌙 **Dark Theme** - Beautiful dark mode UI

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        FRONTEND                             │
│  Next.js 14 + React + TypeScript + Tailwind + Clerk Auth   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                        BACKEND                              │
│                   FastAPI + LangGraph                       │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────┐  ┌──────────┐  ┌─────────┐  ┌──────────┐     │
│  │ Planner │→ │ Retrieve │→ │ Reason  │→ │ Critique │     │
│  └─────────┘  └──────────┘  └─────────┘  └──────────┘     │
│       │                          │              │          │
│       ▼                          ▼              ▼          │
│  ┌─────────────────────────────────────────────────────┐  │
│  │              Memory Layer (Compressed)               │  │
│  │  ChromaDB (Vectors) + SQLite (Episodic + Tags)      │  │
│  └─────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- Groq API Key ([Get one free](https://console.groq.com))
- Clerk Account ([Sign up free](https://dashboard.clerk.com))

### Option 1: Local Development

1. **Clone the repository**

   ```bash
   git clone https://github.com/yourusername/second-brain.git
   cd second-brain
   ```

2. **Set up the backend**

   ```bash
   cd backend
   python -m venv venv

   # Windows
   .\venv\Scripts\activate
   # macOS/Linux
   source venv/bin/activate

   pip install -r requirements.txt

   # Copy and edit environment variables
   cp .env.example .env
   # Edit .env and add your GROQ_API_KEY
   ```

3. **Set up the frontend**

   ```bash
   cd ../frontend
   npm install

   # Copy and edit environment variables
   cp .env.example .env.local
   # Edit .env.local and add your Clerk keys
   ```

4. **Start the services**

   ```bash
   # Terminal 1: Backend
   cd backend
   uvicorn app.main:app --reload --port 8000

   # Terminal 2: Frontend
   cd frontend
   npm run dev
   ```

5. **Open your browser**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000/docs

### Option 2: Docker Compose

```bash
# Create .env file with your API keys
cp backend/.env.example .env

# Start all services
docker-compose up -d

# View logs
docker-compose logs -f
```

### Option 3: Windows Quick Start

```powershell
# Run the startup script
.\start_system.bat
```

## 🔧 Configuration

### Backend Environment Variables (.env)

```env
# Required
GROQ_API_KEY=gsk_your_api_key_here

# Optional - Clerk Authentication
CLERK_PUBLISHABLE_KEY=pk_test_...
CLERK_SECRET_KEY=sk_test_...

# Optional - Settings
CORS_ORIGINS=http://localhost:3000,https://your-app.vercel.app
ENVIRONMENT=development
GROQ_MODEL_NAME=llama-3.1-8b-instant
```

### Frontend Environment Variables (.env.local)

```env
# Required for authentication
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_...
CLERK_SECRET_KEY=sk_test_...

# Backend API URL
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## 🌐 Deployment

### Deploy Frontend to Vercel

1. Push your code to GitHub
2. Import your repository in [Vercel](https://vercel.com)
3. Add environment variables:
   - `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`
   - `CLERK_SECRET_KEY`
   - `NEXT_PUBLIC_API_URL` (your backend URL)
4. Deploy!

### Deploy Backend

**Option A: Railway/Render**

1. Connect your GitHub repo
2. Set the build command: `pip install -r requirements.txt`
3. Set the start command: `gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:$PORT`
4. Add environment variables

**Option B: Docker**

```bash
docker build -t second-brain-backend ./backend
docker run -p 8000:8000 --env-file .env second-brain-backend
```

**Option C: AWS/GCP/Azure**
Use the provided Dockerfile with your preferred container service (ECS, Cloud Run, Container Instances)

## 📊 Data Storage

### Compression Benefits

- **Average compression ratio**: 3-5x
- **Typical savings**: 60-80%
- **Example**: 1MB of text → ~250KB stored

### Storage Locations

- **Vector Store**: `backend/data/vector_store/` (ChromaDB)
- **Episodic Memory**: `backend/data/episodic_v2.db` (SQLite with compression)

### Backup & Restore

```bash
# Export via API
curl http://localhost:8000/api/v2/memory/export > backup.json

# Or use the Settings page in the UI
```

## 🔐 Security

- **Authentication**: Clerk handles user auth with OAuth providers
- **Data Isolation**: Each user's data is isolated by user_id
- **API Security**: Bearer token authentication on protected endpoints
- **Content Hashing**: SHA-256 hashes for deduplication and integrity

## 📖 API Documentation

Once running, visit:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Key Endpoints

| Method | Endpoint                  | Description                  |
| ------ | ------------------------- | ---------------------------- |
| POST   | `/api/ingest`             | Ingest new content           |
| POST   | `/api/query`              | Query knowledge base         |
| GET    | `/api/v2/memory`          | List memories (with filters) |
| POST   | `/api/v2/memory/bookmark` | Toggle bookmark              |
| GET    | `/api/v2/memory/export`   | Export all data              |
| POST   | `/api/v2/memory/import`   | Import backup                |

## 🛠️ Tech Stack

### Backend

- **FastAPI** - Modern Python web framework
- **LangGraph** - Agent orchestration
- **LangChain** - LLM integration
- **ChromaDB** - Vector database
- **SQLite + SQLAlchemy** - Relational data
- **Sentence-Transformers** - Embeddings
- **Groq** - Fast LLM inference

### Frontend

- **Next.js 14** - React framework with App Router
- **TypeScript** - Type safety
- **Tailwind CSS** - Styling
- **Clerk** - Authentication
- **Lucide React** - Icons
- **Framer Motion** - Animations

## 🤝 Contributing

Contributions are welcome! Please read our contributing guidelines first.

## 📄 License

MIT License - see LICENSE file for details.

---

Built with ❤️ using Second Brain
