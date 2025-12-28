# Manual Testing Documentation

This directory contains documentation and scripts for manual testing of the Privacy Policy Analyzer.

## Files Overview

### 📋 Test Documentation

- **`MANUAL_TEST_GUIDE.md`** - Comprehensive step-by-step testing guide with detailed instructions
- **`TEST_CHECKLIST.md`** - Quick reference checklist for tracking test progress
- **`TESTING_README.md`** - This file

### 🔧 Test Scripts

- **`verify_setup.bat`** - Verifies that all prerequisites are installed and configured
- **`test_backend_connection.bat`** - Quick test to verify backend is running and responding

## Quick Start

### 1. Verify Your Setup

Run the setup verification script:

```bash
verify_setup.bat
```

This will check:
- Python installation
- Node.js installation
- Backend .env configuration
- Python dependencies
- Node dependencies
- Extension build status

### 2. Follow the Test Guide

Open `MANUAL_TEST_GUIDE.md` for detailed step-by-step instructions.

Or use `TEST_CHECKLIST.md` for a quick checklist format.

### 3. Test Backend Connection

Once the backend is running, verify it's responding:

```bash
test_backend_connection.bat
```

## Test Workflow

```
1. Run verify_setup.bat
   ↓
2. Fix any issues found
   ↓
3. Start backend (Terminal 1)
   ↓
4. Start extension dev (Terminal 2)
   ↓
5. Load extension in Chrome
   ↓
6. Follow MANUAL_TEST_GUIDE.md
   ↓
7. Track progress in TEST_CHECKLIST.md
   ↓
8. Mark task complete when all tests pass
```

## What This Test Validates

**Task 7: Test the core loop manually**

This manual test validates:
- Text extraction from webpages
- Backend API communication
- LLM analysis integration
- Cache creation and storage
- Cache hit behavior (Requirements 3.3)
- Cache miss behavior (Requirements 3.4)

## Prerequisites

Before testing, ensure you have:

1. **Python 3.11+** installed
2. **Node.js 18+** installed
3. **Azure OpenAI credentials** configured in `backend/.env`
4. **Dependencies installed** (run `start.bat` if not done)

## Common Issues

### Backend won't start
- Check that `backend/.env` exists with valid Azure OpenAI credentials
- Verify Python dependencies: `pip install -r backend/requirements.txt`
- Check port 8000 is not already in use

### Extension won't load
- Verify extension is built: `cd extension && npm run dev`
- Check Chrome Developer Mode is enabled
- Look for errors in Chrome console (F12)

### "Could not analyze policy" error
- Verify backend is running: `curl http://localhost:8000/health`
- Check backend terminal for error messages
- Verify Azure OpenAI credentials are correct

### Cache not working
- Check that `backend/cache.json` is created after first analysis
- Verify file permissions allow read/write
- Check backend logs for cache-related errors

## Test Results

After completing the tests, document results in `TEST_CHECKLIST.md`:

- ✅ **PASS** - All tests passed, requirements validated
- ⚠️ **PARTIAL** - Some tests passed, issues documented
- ❌ **FAIL** - Critical issues found, needs fixing

## Next Steps

Once Task 7 is complete:
1. Mark task as complete in `.kiro/specs/privacy-policy-analyzer/tasks.md`
2. Proceed to Phase 3: UI Polish (Task 8+)
3. Consider adding automated tests for the core loop

## Support

For issues or questions:
- Review the main `README.md` in the project root
- Check backend logs for error messages
- Verify all prerequisites are met
- Consult the design document: `.kiro/specs/privacy-policy-analyzer/design.md`

---

**Happy Testing! 🧪**
