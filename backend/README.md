# Hercule - Backend API

FastAPI backend service for analyzing privacy policies using Groq LLM.

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
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.1-70b-versatile
```

Get your free API key at https://console.groq.com/

### 3. Run the Server

```bash
# Windows
.venv\Scripts\python.exe -m uvicorn main:app --reload --port 8000

# Linux/Mac
.venv/bin/python -m uvicorn main:app --reload --port 8000
```

## API Endpoints

### POST /analyze

Analyze a privacy policy. If only URL is provided, automatically discovers and extracts the privacy policy.

**Request:**
```json
{
  "policy_text": "",
  "url": "https://example.com"
}
```

**Response:**
```json
{
  "score": 75,
  "summary": "Plain-language summary of the policy...",
  "red_flags": ["Concerning practice 1", "Concerning practice 2"],
  "user_action_items": [
    {"text": "Review your privacy settings", "url": "https://example.com/settings", "priority": "high"}
  ],
  "timestamp": "2025-12-27T10:30:00Z",
  "url": "https://example.com/privacy"
}
```

### GET /discover_policy

Find the privacy policy URL for a website.

**Request:** `GET /discover_policy?url=https://example.com`

**Response:**
```json
{
  "policy_url": "https://example.com/privacy",
  "policy_text": "...",
  "method": "parallel_paths"
}
```

### GET /health

Health check endpoint.

## Features

- **Aggressive Policy Discovery**: Parallel path checking (25+ URLs), homepage scraping, DuckDuckGo search fallback
- **Local JSON Caching**: Results cached using SHA-256 hash of policy text
- **30-Day TTL**: Cached results expire after 30 days
- **Text Truncation**: Policy text truncated to 50,000 characters before LLM analysis

## Railway Deployment

### Prerequisites

1. Create an account at [railway.app](https://railway.app)
2. Install the Railway CLI:
   ```bash
   npm install -g @railway/cli
   ```
3. Login to Railway:
   ```bash
   railway login
   ```

### Deploy from GitHub (Recommended)

1. Push your code to GitHub
2. Go to [railway.app/new](https://railway.app/new)
3. Click **"Deploy from GitHub repo"**
4. Select your repository
5. Railway will auto-detect the `backend` directory
6. Add environment variables in the Railway dashboard:
   - `GROQ_API_KEY` - Your Groq API key
   - `OPENROUTER_API_KEY` - Your OpenRouter API key (optional)
   - `STORAGE_MODE` - Set to `local`
   - `ALLOWED_ORIGINS` - Your frontend origins (or `*`)

### Deploy with CLI

```bash
cd backend

# Initialize Railway project
railway init

# Link to existing project (if needed)
railway link

# Add environment variables
railway variables set GROQ_API_KEY=your_key_here
railway variables set STORAGE_MODE=local
railway variables set ALLOWED_ORIGINS="*"

# Deploy
railway up
```

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GROQ_API_KEY` | Yes* | Groq API key for LLM analysis |
| `OPENROUTER_API_KEY` | Yes* | OpenRouter API key (fallback) |
| `STORAGE_MODE` | No | `local` (default) or `cosmos` |
| `ALLOWED_ORIGINS` | No | CORS origins, default `*` |
| `LOG_LEVEL` | No | `DEBUG`, `INFO`, `WARNING`, `ERROR` |

*At least one LLM API key required

### Verify Deployment

After deployment, test your API:

```bash
# Health check
curl https://your-app.up.railway.app/health

# Test analysis
curl -X POST https://your-app.up.railway.app/analyze \
  -H "Content-Type: application/json" \
  -d '{"url": "https://google.com"}'
```

## Testing

```bash
.venv\Scripts\python.exe -m pytest test_backend.py -v
```

