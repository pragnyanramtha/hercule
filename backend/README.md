# Hercule - Backend API

FastAPI backend service for analyzing privacy policies using Azure OpenAI.

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
AZURE_OPENAI_KEY=your_api_key_here
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=gpt-4
```

### 3. Run the Server

Using the virtual environment:

```bash
# Windows
.venv\Scripts\python.exe -m uvicorn main:app --reload --port 8000

# Linux/Mac
.venv/bin/python -m uvicorn main:app --reload --port 8000
```

Or directly with uvicorn:

```bash
uvicorn main:app --reload --port 8000
```

## API Endpoints

### POST /analyze

Analyze a privacy policy and return structured insights.

**Request:**
```json
{
  "policy_text": "Your privacy policy text here...",
  "url": "https://example.com/privacy"
}
```

**Response:**
```json
{
  "score": 75,
  "summary": "Plain-language summary of the policy...",
  "red_flags": [
    "Concerning practice 1",
    "Concerning practice 2"
  ],
  "user_action_items": [
    {
      "text": "Review your privacy settings",
      "url": "https://example.com/settings",
      "priority": "high"
    }
  ],
  "timestamp": "2025-12-27T10:30:00Z",
  "url": "https://example.com/privacy"
}
```

### GET /health

Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-12-27T10:30:00Z"
}
```

## Features

- **Local JSON Caching**: Analysis results are cached in `cache.json` using SHA-256 hash of policy text
- **30-Day TTL**: Cached results expire after 30 days
- **CORS Enabled**: Configured for development with all origins allowed
- **Error Handling**: Basic try/except with 500 status codes on failure
- **Text Truncation**: Policy text is automatically truncated to 50,000 characters before LLM analysis

## Testing

Run the basic functionality tests:

```bash
.venv\Scripts\python.exe test_backend.py
```

## Cache Structure

The `cache.json` file stores analysis results:

```json
{
  "hash_key_1": {
    "result": {
      "score": 75,
      "summary": "...",
      "red_flags": ["..."],
      "user_action_items": [{"text": "...", "url": "...", "priority": "high"}],
      "url": "https://example.com/privacy",
      "timestamp": "2025-12-27T10:30:00Z"
    },
    "timestamp": "2025-12-27T10:30:00Z",
    "text_hash": "hash_key_1"
  }
}
```
