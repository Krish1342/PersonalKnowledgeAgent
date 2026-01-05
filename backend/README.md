# Backend for Personal Knowledge Agent

## Setup

```bash
cd backend
python -m venv venv
venv\Scripts\activate  # On Windows
# source venv/bin/activate  # On macOS/Linux
pip install -r requirements.txt
```

## Configuration

Copy `.env.example` to `.env` and update values as needed:

```bash
cp .env.example .env
```

## Running the Application

```bash
# Development with auto-reload
uvicorn app.main:app --reload

# Production
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## API Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Health Checks

- **Health**: GET `/health/`
- **Liveness**: GET `/health/live`
- **Readiness**: GET `/health/ready`

## Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py           # FastAPI application entry point
│   ├── config.py         # Configuration management
│   ├── api/              # API routers and endpoints
│   │   ├── __init__.py
│   │   └── health.py     # Health check endpoints
│   └── utils/            # Utility modules
│       ├── __init__.py
│       └── logging.py    # Logging configuration
├── requirements.txt      # Python dependencies
├── .env                  # Environment variables (local)
├── .env.example          # Environment template
└── README.md
```

## Architecture

- **Modular Structure**: Organized for easy addition of new API routes and business logic
- **Environment-based Config**: Uses Pydantic Settings for configuration management
- **Structured Logging**: JSON and text formatters for different environments
- **Health Checks**: Liveness and readiness probes for container orchestration
- **CORS Configured**: Ready for frontend integration
- **Extensible**: Prepared for LangGraph agent integration
