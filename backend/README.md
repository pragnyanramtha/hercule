# Hercule - Backend API

FastAPI backend service for analyzing privacy policies using Gemini models.

## Setup

### 1. Install Dependencies

Using `uv` (recommended):

```bash
uv venv
uv pip install -r requirements.txt
```

### 2. Configure Environment Variables

Create a `.env` file in the `backend` directory:

```bash
GEMINI_API_KEY=your_gemini_api_key_here
STORAGE_MODE=local
ALLOWED_ORIGINS=*
```

Get your API key at https://aistudio.google.com/

### 3. Run the Server

```bash
# Windows
.venv\Scripts\python.exe -m uvicorn main:app --reload --port 8000

# Linux/Mac
.venv/bin/python -m uvicorn main:app --reload --port 8000
```

## API Endpoints

### POST /analyze

Analyze a privacy policy. If only URL is provided, backend tries discovery first and then Gemini URL-only analysis as fallback.

### GET /discover_policy

Find the privacy policy URL for a website.

### GET /health

Health check endpoint.

## Features

- Gemini-only model fallback chain
- Aggressive policy discovery (parallel path checks, homepage scraping, search fallback)
- Local JSON caching with 30-day TTL
- Automatic action-item mailto link generation

## Railway Deployment

1. Deploy `backend` with Nixpacks.
2. Set environment variables:
   - `GEMINI_API_KEY` (required)
   - `STORAGE_MODE` (`local` or `cosmos`)
   - `ALLOWED_ORIGINS` (comma-separated)
   - `LOG_LEVEL` (optional)

## Appwrite Deployment Prep

This backend is now prepared to run as a standard ASGI web service on Appwrite using a containerized deployment flow.

### Required Variables

- `GEMINI_API_KEY`
- `STORAGE_MODE` (recommended `local` unless Cosmos is configured)
- `ALLOWED_ORIGINS`
- `LOG_LEVEL` (optional)

### Start Command

Use the same ASGI command:

```bash
uvicorn main:app --host 0.0.0.0 --port $PORT
```

### Health Check Path

`/health`

### Notes

- The backend no longer relies on Groq or OpenRouter at runtime.
- Azure-specific files still exist for teams that want to keep Azure Function compatibility, but model execution is Gemini-only.

## Testing

```bash
.venv\Scripts\python.exe -m pytest tests -v
```
