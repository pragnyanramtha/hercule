# Manual Testing Guide - Core Loop Verification

This guide walks you through testing the complete core loop of the Privacy Policy Analyzer.

## Test Objective

Verify that the complete flow works end-to-end:
1. Text extraction from webpage
2. Backend API receives the text
3. LLM analyzes the policy
4. Results are returned and displayed
5. Cache is created and used on subsequent requests

**Requirements Validated:** 3.3 (Cache hit), 3.4 (Cache miss)

---

## Prerequisites

Before starting the test, ensure:

- [ ] Python 3.11+ is installed
- [ ] Node.js 18+ is installed
- [ ] Azure OpenAI credentials are configured in `backend/.env`

### ⚠️ IMPORTANT: Configure Azure OpenAI Credentials

If you haven't already, create `backend/.env` file:

```bash
cd backend
copy .env.example .env
```

Then edit `backend/.env` with your actual Azure OpenAI credentials:
```
AZURE_OPENAI_KEY=your-actual-api-key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=your-deployment-name
```

---

## Test Setup

### Step 1: Start the Backend Server

Open **Terminal 1** and run:

```bash
cd backend
uvicorn main:app --reload --port 8000
```

**Expected Output:**
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

**✅ Verification:** Backend is running when you see "Application startup complete"

### Step 2: Build the Extension

Open **Terminal 2** and run:

```bash
cd extension
npm run dev
```

**Expected Output:**
```
VITE v5.x.x  ready in xxx ms

➜  Local:   http://localhost:5173/
➜  Network: use --host to expose
```

**✅ Verification:** Extension build completes without errors

### Step 3: Load Extension in Chrome

1. Open Chrome browser
2. Navigate to `chrome://extensions/`
3. Enable **"Developer mode"** (toggle in top-right corner)
4. Click **"Load unpacked"**
5. Navigate to and select: `extension/dist` directory
6. The Privacy Policy Analyzer icon should appear in your toolbar

**✅ Verification:** Extension icon is visible in Chrome toolbar

---

## Core Loop Test - First Run (Cache Miss)

### Test 1: Visit a Website with Privacy Policy

1. **Navigate to:** `https://www.google.com`
2. **Wait** for the page to fully load
3. **Click** the Privacy Policy Analyzer extension icon

### Expected Behavior:

**Phase 1: Text Extraction**
- Popup opens (400x600 pixels)
- Shows loading spinner
- Message: "Extracting policy text..."

**Phase 2: Backend Analysis**
- Message changes to: "Analyzing policy..."
- Backend Terminal 1 should show:
  ```
  Cache miss for hash: <hash_value>... Calling LLM
  ```

**Phase 3: Results Display**
- Loading spinner disappears
- Analysis results appear:
  - Score (0-100)
  - Summary text
  - Red flags (if any)
  - Action items (if any)

**✅ Verification Checklist:**
- [ ] Popup opened successfully
- [ ] Loading states displayed correctly
- [ ] Backend logged "Cache miss"
- [ ] Backend logged "Calling LLM"
- [ ] Results displayed in popup
- [ ] No error messages shown

### Test 2: Verify Cache File Creation

1. **Check** that `backend/cache.json` file was created
2. **Open** `backend/cache.json` in a text editor

**Expected Content Structure:**
```json
{
  "hash_key_here": {
    "result": {
      "score": 75,
      "summary": "...",
      "red_flags": [...],
      "user_action_items": [...],
      "url": "https://www.google.com",
      "timestamp": "2025-12-28T..."
    },
    "timestamp": "2025-12-28T...",
    "text_hash": "hash_key_here"
  }
}
```

**✅ Verification Checklist:**
- [ ] `cache.json` file exists in `backend/` directory
- [ ] File contains valid JSON
- [ ] Has at least one cache entry
- [ ] Entry has `result`, `timestamp`, and `text_hash` fields
- [ ] `result` contains `score`, `summary`, `red_flags`, `user_action_items`

---

## Core Loop Test - Second Run (Cache Hit)

### Test 3: Reload Extension and Test Again

1. **Stay on** `https://www.google.com` (same page)
2. **Close** the extension popup if still open
3. **Click** the Privacy Policy Analyzer icon again

### Expected Behavior:

**Phase 1: Text Extraction**
- Popup opens
- Shows loading spinner
- Message: "Extracting policy text..."

**Phase 2: Cache Hit**
- Message changes to: "Analyzing policy..."
- Backend Terminal 1 should show:
  ```
  Cache hit for hash: <hash_value>...
  ```
- **Response should be MUCH FASTER** (no LLM call)

**Phase 3: Results Display**
- Same results as before
- Should appear almost instantly

**✅ Verification Checklist:**
- [ ] Popup opened successfully
- [ ] Backend logged "Cache hit"
- [ ] Backend did NOT log "Calling LLM"
- [ ] Results appeared faster than first run
- [ ] Results are identical to first run
- [ ] No error messages shown

---

## Additional Verification Tests

### Test 4: Test with Different Website

1. **Navigate to:** `https://www.facebook.com`
2. **Click** the extension icon
3. **Observe:** Should be a cache miss (different policy text)

**✅ Verification:**
- [ ] Backend logs "Cache miss"
- [ ] New entry added to `cache.json`
- [ ] Results displayed successfully

### Test 5: Verify Cache Persistence

1. **Stop** the backend server (CTRL+C in Terminal 1)
2. **Restart** the backend server:
   ```bash
   uvicorn main:app --reload --port 8000
   ```
3. **Navigate to:** `https://www.google.com`
4. **Click** the extension icon

**✅ Verification:**
- [ ] Backend logs "Cache hit" (cache persisted across restarts)
- [ ] Results displayed quickly

---

## Error Handling Tests

### Test 6: Backend Unavailable

1. **Stop** the backend server (CTRL+C in Terminal 1)
2. **Navigate to:** any website
3. **Click** the extension icon

**Expected Behavior:**
- Loading spinner appears
- After timeout, error message displays:
  - "Could not analyze policy. Check backend is running."
- Retry button is available

**✅ Verification:**
- [ ] Error message displayed correctly
- [ ] Retry button is present
- [ ] No crash or blank screen

### Test 7: Page Without Privacy Policy

1. **Restart** the backend server
2. **Navigate to:** `https://example.com` (minimal page)
3. **Click** the extension icon

**Expected Behavior:**
- Extension extracts whatever text is available
- Backend analyzes the text
- Results may indicate "No privacy policy detected" or similar

**✅ Verification:**
- [ ] No crash or error
- [ ] Some analysis result is returned
- [ ] Extension handles minimal content gracefully

---

## Test Results Summary

### Requirements Validation

**Requirement 3.3: Cache Hit Prevents LLM Calls**
- [ ] ✅ PASS - Cache hit returned cached result without LLM call
- [ ] ❌ FAIL - Describe issue: _______________

**Requirement 3.4: Cache Miss Triggers LLM Calls**
- [ ] ✅ PASS - Cache miss triggered LLM analysis
- [ ] ❌ FAIL - Describe issue: _______________

### Overall Test Status

- [ ] ✅ ALL TESTS PASSED - Core loop is working correctly
- [ ] ⚠️ PARTIAL - Some tests passed, issues noted below
- [ ] ❌ FAILED - Core loop has critical issues

### Issues Found

_Document any issues discovered during testing:_

1. _______________________________________________
2. _______________________________________________
3. _______________________________________________

---

## Cleanup

After testing is complete:

1. Stop the backend server (CTRL+C in Terminal 1)
2. Stop the extension build (CTRL+C in Terminal 2)
3. Optionally, remove the extension from Chrome
4. Optionally, delete `backend/cache.json` to start fresh

---

## Next Steps

Once all tests pass:
- [ ] Mark task 7 as complete
- [ ] Proceed to Phase 3: UI Polish (Task 8+)
- [ ] Consider adding automated tests for the core loop

---

**Test Completed By:** _______________
**Test Date:** _______________
**Test Duration:** _______________
