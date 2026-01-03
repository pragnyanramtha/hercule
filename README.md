# Hercule

A browser extension that uses Groq LLM to analyze privacy policies and present them through an intuitive traffic-light interface with actionable insights.

## Architecture

- **Frontend**: React-based Chrome extension (Manifest V3)
- **Backend**: Python FastAPI service
- **AI**: Groq LLM (llama-3.1-70b-versatile)
- **Storage**: Local JSON cache

## Prerequisites

- **Python 3.11+** - [Download Python](https://www.python.org/downloads/)
- **Node.js 18+** - [Download Node.js](https://nodejs.org/)
- **Groq API Key** - [Get free key at console.groq.com](https://console.groq.com/)

## Quick Start

### 1. Clone the Repository

```bash
git clone git@github.com:pragnyanramtha/hercule.git
cd hercule
```

### 2. Configure Groq API

1. Copy the example environment file:
   ```bash
   cd backend
   copy .env.example .env
   ```

2. Edit `backend/.env` and add your Groq API key:
   ```
   GROQ_API_KEY=your-api-key-here
   GROQ_MODEL=llama-3.1-70b-versatile
   ```

### 3. Run Setup Script

```bash
start.bat
```

### 4. Start Development Environment

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
2. Enable "Developer mode"
3. Click "Load unpacked"
4. Select the `frontend/dist` directory

## Project Structure

```
hercule/
├── frontend/          # Chrome extension (React + TypeScript)
│   ├── src/
│   │   ├── content/   # Content scripts
│   │   └── popup/     # Popup UI components
│   └── dist/          # Built extension
├── backend/           # FastAPI backend
│   ├── main.py        # API endpoints
│   ├── service_llm.py # Groq LLM integration
│   ├── service_discovery.py # Policy discovery
│   └── cache.json     # Local cache
├── shared/            # Shared TypeScript types
└── start.bat          # Setup script
```

## Usage

1. Visit any website
2. Click the Hercule extension icon
3. The extension will:
   - Automatically find the privacy policy (checks 25+ common paths, scrapes links, searches if needed)
   - Analyze the policy with AI
   - Display a traffic-light score (Green/Yellow/Red)
   - Show key concerns and recommended actions

## Configuration

### Environment Variables (Backend)

```env
GROQ_API_KEY=your-api-key-here
GROQ_MODEL=llama-3.1-70b-versatile
ALLOWED_ORIGINS=*
```

## Troubleshooting

### Backend won't start
- Verify Python 3.11+ is installed
- Check dependencies: `pip install -r backend/requirements.txt`
- Ensure `.env` file exists with valid Groq API key

### Extension won't load
- Verify Node.js 18+ is installed
- Check dependencies: `cd frontend && npm install`
- Build the extension: `npm run dev`

### "Could not find policy" error
- The site may not have a discoverable privacy policy
- Try navigating directly to the privacy policy page

## License

MIT License - see [LICENSE](LICENSE)

---
# Contributions 

- pragnyanramtha

Open a pull request to contribute!
