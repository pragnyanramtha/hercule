# Privacy Policy Analyzer

A browser extension that leverages Azure OpenAI to democratize privacy policy comprehension. The system analyzes privacy policies and presents them through an intuitive traffic-light interface with actionable insights.

## Architecture

- **Frontend**: React-based Chrome extension (Manifest V3)
- **Backend**: Python FastAPI service (deployable as Azure Functions)
- **AI**: Azure OpenAI for policy analysis
- **Storage**: Local JSON cache (dev) / Azure Cosmos DB (production)

## Prerequisites

- **Python 3.11+** - [Download Python](https://www.python.org/downloads/)
- **Node.js 18+** - [Download Node.js](https://nodejs.org/)
- **Azure OpenAI Account** - [Get Azure OpenAI Access](https://azure.microsoft.com/en-us/products/ai-services/openai-service)

## Quick Start

### 1. Clone the Repository

```bash
git clone <repository-url>
cd privacy-policy-analyzer
```

### 2. Configure Azure OpenAI Credentials

**TODO: Set up your Azure OpenAI API keys**

1. Copy the example environment file:
   ```bash
   cd backend
   copy .env.example .env
   ```

2. Edit `backend/.env` and add your Azure OpenAI credentials:
   ```
   AZURE_OPENAI_KEY=your-api-key-here
   AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
   AZURE_OPENAI_DEPLOYMENT=your-deployment-name
   ```

3. Get your credentials from the [Azure Portal](https://portal.azure.com/):
   - Navigate to your Azure OpenAI resource
   - Go to "Keys and Endpoint"
   - Copy the key and endpoint

### 3. Run Setup Script

```bash
start.bat
```

This will:
- Install Python dependencies from `backend/requirements.txt`
- Install Node dependencies for the extension

### 4. Start Development Environment

You need to run these commands in **separate terminal windows**:

**Terminal 1 - Backend API:**
```bash
cd backend
uvicorn main:app --reload --port 8000
```

**Terminal 2 - Extension Build:**
```bash
cd extension
npm run dev
```

### 5. Load Extension in Chrome

1. Open Chrome and navigate to `chrome://extensions/`
2. Enable "Developer mode" (toggle in top-right corner)
3. Click "Load unpacked"
4. Select the `extension/dist` directory
5. The extension icon should appear in your browser toolbar

## Project Structure

```
privacy-policy-analyzer/
├── extension/          # Chrome extension (React + TypeScript)
│   ├── src/
│   │   ├── content/   # Content scripts for page scraping
│   │   └── popup/     # Popup UI components
│   └── dist/          # Built extension (generated)
├── backend/           # FastAPI backend
│   ├── main.py       # API endpoints
│   ├── service_llm.py # Azure OpenAI integration
│   ├── models.py     # Data models
│   └── cache.json    # Local cache (generated)
├── shared/           # Shared TypeScript types
└── start.bat         # Development setup script
```

## Usage

1. Visit any website (e.g., google.com, facebook.com)
2. Click the Privacy Policy Analyzer extension icon
3. The extension will:
   - Detect privacy policy links on the page
   - Extract and analyze the policy text
   - Display a traffic-light score (Green/Yellow/Red)
   - Show key concerns and recommended actions

## Development

### Backend Development

The backend runs on `http://localhost:8000` with hot-reload enabled.

**API Endpoints:**
- `POST /analyze` - Analyze privacy policy text
- `GET /health` - Health check

**Testing:**
```bash
cd backend
pytest
```

### Extension Development

The extension builds to `extension/dist/` with hot-reload.

**Building for production:**
```bash
cd extension
npm run build
```

**Testing:**
```bash
cd extension
npm test
```

## Configuration

### Environment Variables (Backend)

Create `backend/.env` with:

```env
# Azure OpenAI Configuration (REQUIRED)
AZURE_OPENAI_KEY=your-api-key-here
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=gpt-4

# Storage Configuration (Optional)
STORAGE_MODE=local              # local or cloud
CACHE_TTL_DAYS=30              # Cache expiration in days

# Azure Cosmos DB (Production only)
COSMOS_CONNECTION_STRING=your-connection-string
COSMOS_DATABASE_NAME=privacy-analyzer
COSMOS_CONTAINER_NAME=analysis-cache
```

## Troubleshooting

### Backend won't start
- Verify Python 3.11+ is installed: `python --version`
- Check that all dependencies are installed: `pip install -r backend/requirements.txt`
- Ensure `.env` file exists with valid Azure OpenAI credentials

### Extension won't load
- Verify Node.js 18+ is installed: `node --version`
- Check that dependencies are installed: `cd extension && npm install`
- Ensure the extension is built: `npm run dev` or `npm run build`
- Check Chrome console for errors

### "Could not analyze policy" error
- Verify the backend is running on `http://localhost:8000`
- Check backend logs for errors
- Verify Azure OpenAI credentials are correct
- Test the backend directly: `curl http://localhost:8000/health`

### Cache not working
- Check that `backend/cache.json` is being created
- Verify file permissions allow read/write
- Check backend logs for cache-related errors

## Deployment

### Azure Functions (Production)

1. Install Azure Functions Core Tools
2. Configure Azure resources (Function App, Cosmos DB, OpenAI)
3. Deploy backend:
   ```bash
   cd backend
   func azure functionapp publish <your-function-app-name>
   ```
4. Update extension to use production API URL
5. Build and package extension for Chrome Web Store

## Contributing

This project was created for the Microsoft Imagine Cup. Contributions are welcome!

## License

[Add your license here]

## Support

For issues and questions, please open an issue on GitHub.

---

**Built with ❤️ for the Microsoft Imagine Cup**
