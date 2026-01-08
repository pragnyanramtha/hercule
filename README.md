# Hercule

A browser extension that leverages azure to democratize privacy policy comprehension. The system analyzes privacy policies and presents them through an intuitive interface with actionable insights.

## Features

- **Privacy Policy Analysis** - AI-powered analysis of privacy policies
- **Score** - Easy-to-understand 0-100 privacy score
- **Red Flags Detection** - Highlights concerning privacy practices
- **Action Items** - Personalized recommendations with one-click email templates
- **Smart Discovery** - Automatically finds privacy policies on any website
- **Caching** - Results are cached for instant repeat visits
- **API Key Pooling** - Automatic key rotation for rate limit resilience

## Architecture

- **Frontend**: React-based Chrome extension (Manifest V3)
- **Backend**: Python FastAPI service (deployable as Azure Functions)
- **AI**: Groq LLM with multi-model fallback
- **Storage**: Local JSON cache (dev) / Azure Cosmos DB (production)

## Prerequisites

- **Python 3.11+** - [Download Python](https://www.python.org/downloads/)
- **Node.js 18+** - [Download Node.js](https://nodejs.org/)
- **Groq API Key** - [Get free API key](https://console.groq.com/)

## Quick Start

### 1. Clone the Repository

```bash
git clone git@github.com:pragnyanramtha/hercule.git
cd hercule
```

### 2. Configure API Credentials

1. Copy the example environment file:
   ```bash
   cp .env.example backend/.env
   ```

2. Edit `backend/.env` and add your Groq API key:
   ```env
   GROQ_API_KEY=gsk_your_api_key_here
   ```

3. Get your API key from [console.groq.com](https://console.groq.com/)

### 3. Install Dependencies

**Backend:**
```bash
cd backend
pip install -r requirements.txt
```

**Frontend:**
```bash
cd frontend
npm install
```

### 4. Start Development Environment

You need to run these commands in **separate terminal windows**:

**Terminal 1 - Backend API:**
```bash
cd backend
uvicorn main:app --reload --port 8000
```

**Terminal 2 - Extension Build:**
```bash
cd frontend
npm run dev
```

### 5. Load Extension in Chrome

1. Open Chrome and navigate to `chrome://extensions/`
2. Enable "Developer mode" (toggle in top-right corner)
3. Click "Load unpacked"
4. Select the `frontend/dist` directory
5. The extension icon should appear in your browser toolbar

## Project Structure

```
hercule/
├── frontend/              # Chrome extension (React + TypeScript)
│   ├── src/
│   │   ├── content/       # Content scripts for page scraping
│   │   └── popup/         # Popup UI components
│   │       └── components/
│   │           ├── Settings.tsx    # User settings modal
│   │           ├── TrafficLight.tsx
│   │           ├── Summary.tsx
│   │           ├── RedFlags.tsx
│   │           └── ActionItems.tsx
│   └── dist/              # Built extension (generated)
├── backend/               # FastAPI backend
│   ├── main.py            # API endpoints
│   ├── service_llm.py     # Groq LLM integration
│   ├── service_discovery.py # Privacy policy discovery
│   ├── api_key_manager.py # API key pooling & rotation
│   ├── cache.py           # Cache manager (local/cosmos)
│   ├── cache_cosmos.py    # Azure Cosmos DB cache
│   ├── models.py          # Pydantic data models
│   ├── keys.json          # API key pool storage
│   ├── cache.json         # Local cache (generated)
│   ├── function_app.py    # Azure Functions entry point
│   └── host.json          # Azure Functions config
├── shared/                # Shared TypeScript types
└── .env.example           # Environment template
```

## Usage

1. Visit any website (e.g., google.com, facebook.com)
2. Click the Hercule extension icon
3. The extension will:
   - Detect privacy policy links on the page
   - Extract and analyze the policy text
   - Display a traffic-light score (Green/Yellow/Red)
   - Show key concerns and recommended actions
4. Click **Settings** (gear icon) to add your name and API key

## User Settings

Click the **gear icon** in the extension header to configure:

- **Your Name**: Used to personalize email templates (replaces `[Your Name]`)
- **Groq API Key**: Optional - use your own key for faster analysis

Your settings are stored locally in the browser and never sent to external servers (except the API key which is sent to Groq for authentication).

## Development

### Backend Development

The backend runs on `http://localhost:8000` with hot-reload enabled.

**API Endpoints:**
- `POST /analyze` - Analyze privacy policy text
- `GET /health` - Health check
- `GET /discover_policy` - Discover policy URL for a domain

**Testing:**
```bash
cd backend
pytest tests/ -v
```

### Extension Development

The extension builds to `frontend/dist/` with hot-reload.

**Building for production:**
```bash
cd frontend
npm run build
```

**Testing:**
```bash
cd frontend
npm test
```

**Run all tests:**
```bash
cd frontend
npm run test:all
```

## Configuration

### Environment Variables (Backend)

Copy `.env.example` to `backend/.env` and configure:

```env
# Groq API Configuration (REQUIRED)
GROQ_API_KEY=gsk_your_api_key_here

# Storage Configuration
STORAGE_MODE=local              # local or cosmos
CACHE_TTL_DAYS=30               # Cache expiration in days

# Azure Cosmos DB (Production only)
COSMOS_CONNECTION_STRING=your-connection-string
COSMOS_DATABASE_NAME=privacy-analyzer
COSMOS_CONTAINER_NAME=analysis-cache

# Optional
GOOGLE_SEARCH_API=your_key      # Fallback for policy discovery
ALLOWED_ORIGINS=*               # CORS configuration
LOG_LEVEL=INFO                  # DEBUG, INFO, WARNING, ERROR
```

### API Key Rotation

The backend supports automatic API key rotation:

1. **User keys** (from extension settings) are added to the pool
2. **Pool keys** are stored in `backend/keys.json`
3. On **429 rate limit errors**, the system rotates to the next key
4. Falls back to `.env` `GROQ_API_KEY` only if pool is empty

## Troubleshooting

### Backend won't start
- Verify Python 3.11+ is installed: `python --version`
- Check that all dependencies are installed: `pip install -r backend/requirements.txt`
- Ensure `.env` file exists with valid Groq API key

### Extension won't load
- Verify Node.js 18+ is installed: `node --version`
- Check that dependencies are installed: `cd frontend && npm install`
- Ensure the extension is built: `npm run dev` or `npm run build`
- Check Chrome console for errors

### "Could not analyze policy" error
- Verify the backend is running on `http://localhost:8000`
- Check backend logs for errors
- Verify Groq API key is correct
- Test the backend directly: `curl http://localhost:8000/health`

### Rate limit errors
- Add your own API key in extension settings
- Wait a few seconds and retry
- The system will automatically rotate to backup keys if available

### Cache not working
- Check that `backend/cache.json` is being created
- Verify file permissions allow read/write
- Check backend logs for cache-related errors

## Deployment

### Azure Functions (Production)

1. **Install Azure Functions Core Tools**:
   ```bash
   npm install -g azure-functions-core-tools@4
   ```

2. **Install Azure dependencies**:
   ```bash
   pip install azure-functions azure-cosmos
   ```

3. **Configure environment variables** in Azure:
   - `GROQ_API_KEY`
   - `STORAGE_MODE=cosmos`
   - `COSMOS_CONNECTION_STRING`
   - `COSMOS_DATABASE_NAME`
   - `COSMOS_CONTAINER_NAME`

4. **Deploy backend**:
   ```bash
   cd backend
   func azure functionapp publish <your-function-app-name>
   ```

5. **Update extension** to use production API URL:
   - Set `VITE_API_URL` during build

6. **Build and package** extension for Chrome Web Store:
   ```bash
   cd frontend
   npm run build
   ```

## Contributing

This project was created for the Microsoft Imagine Cup. Contributions are welcome!

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

For issues and questions, please open an issue on GitHub.

---

# Contributions 

- pragnyanramtha

Open a pull request and become a contributor!
