# Hercule - Frontend

Browser extension component for Hercule.

## Setup

1. Install dependencies:
```bash
npm install
```

2. Run development build:
```bash
npm run dev
```

3. Build for production:
```bash
npm run build
```

## Loading the Extension in Chrome

1. Build the extension: `npm run build`
2. Open Chrome and navigate to `chrome://extensions/`
3. Enable "Developer mode" (toggle in top right)
4. Click "Load unpacked"
5. Select the `dist/` folder from this directory

## Project Structure

- `src/popup/` - Popup UI components (React)
- `src/content/` - Content script for page analysis
- `public/` - Static assets (icons, manifest)
- `dist/` - Build output (generated)

## Configuration

The extension is configured with:
- Manifest V3
- Permissions: activeTab, storage, scripting
- Popup dimensions: 400x600 pixels
