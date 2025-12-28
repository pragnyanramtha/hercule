# Manual Test Checklist - Task 7

## Quick Reference Checklist

Use this checklist to track your manual testing progress.

---

## Pre-Test Setup

- [ ] Python 3.11+ installed (`python --version`)
- [ ] Node.js 18+ installed (`node --version`)
- [ ] Backend `.env` file created with Azure OpenAI credentials
- [ ] Python dependencies installed (`pip install -r backend/requirements.txt`)
- [ ] Node dependencies installed (`cd extension && npm install`)
- [ ] Extension built (`cd extension && npm run dev`)
- [ ] Extension loaded in Chrome (`chrome://extensions/`)

**Quick Verification:** Run `verify_setup.bat` to check all prerequisites

---

## Test Execution

### Terminal Setup

- [ ] **Terminal 1:** Backend running (`cd backend && uvicorn main:app --reload --port 8000`)
- [ ] **Terminal 2:** Extension dev server running (`cd extension && npm run dev`)
- [ ] Backend health check passes: `curl http://localhost:8000/health`

---

## Core Loop Test 1: Cache Miss (First Run)

**Website:** https://www.google.com

### Execution Steps
1. [ ] Navigate to https://www.google.com
2. [ ] Click Privacy Policy Analyzer extension icon
3. [ ] Observe loading states and backend logs

### Expected Results
- [ ] Popup opens (400x600 pixels)
- [ ] Shows "Extracting policy text..." message
- [ ] Shows "Analyzing policy..." message
- [ ] Backend Terminal logs: `Cache miss for hash: ...`
- [ ] Backend Terminal logs: `Calling LLM`
- [ ] Analysis results display:
  - [ ] Score (0-100) shown
  - [ ] Summary text shown
  - [ ] Red flags section (if any)
  - [ ] Action items section (if any)
- [ ] No error messages

### Cache Verification
- [ ] `backend/cache.json` file created
- [ ] File contains valid JSON
- [ ] Has one cache entry with:
  - [ ] `result` object
  - [ ] `timestamp` field
  - [ ] `text_hash` field
- [ ] Result contains:
  - [ ] `score` (number 0-100)
  - [ ] `summary` (string)
  - [ ] `red_flags` (array)
  - [ ] `user_action_items` (array)
  - [ ] `url` (string)
  - [ ] `timestamp` (ISO date string)

**✅ Requirement 3.4 Validated:** Cache miss triggers LLM call

---

## Core Loop Test 2: Cache Hit (Second Run)

**Website:** https://www.google.com (same page)

### Execution Steps
1. [ ] Close extension popup (if open)
2. [ ] Click Privacy Policy Analyzer extension icon again
3. [ ] Observe loading states and backend logs

### Expected Results
- [ ] Popup opens
- [ ] Shows "Extracting policy text..." message
- [ ] Shows "Analyzing policy..." message
- [ ] Backend Terminal logs: `Cache hit for hash: ...`
- [ ] Backend does NOT log: `Calling LLM`
- [ ] Results appear FASTER than first run
- [ ] Results are IDENTICAL to first run
- [ ] No error messages

### Performance Check
- [ ] Response time noticeably faster (< 1 second vs several seconds)
- [ ] No LLM API call made (check backend logs)

**✅ Requirement 3.3 Validated:** Cache hit prevents LLM call

---

## Additional Verification Tests

### Test 3: Different Website (Cache Miss)

**Website:** https://www.facebook.com

- [ ] Navigate to https://www.facebook.com
- [ ] Click extension icon
- [ ] Backend logs: `Cache miss`
- [ ] New cache entry added to `cache.json`
- [ ] Results displayed successfully

### Test 4: Cache Persistence Across Restarts

- [ ] Stop backend server (CTRL+C)
- [ ] Restart backend: `uvicorn main:app --reload --port 8000`
- [ ] Navigate to https://www.google.com
- [ ] Click extension icon
- [ ] Backend logs: `Cache hit` (cache persisted)
- [ ] Results displayed quickly

### Test 5: Error Handling - Backend Down

- [ ] Stop backend server
- [ ] Navigate to any website
- [ ] Click extension icon
- [ ] Error message displays: "Could not analyze policy. Check backend is running."
- [ ] Retry button is present
- [ ] No crash or blank screen

---

## Final Verification

### Requirements Validation

**Requirement 3.3: Cache Hit Prevents LLM Calls**
- [ ] ✅ PASS
- [ ] ❌ FAIL (describe issue): _______________________

**Requirement 3.4: Cache Miss Triggers LLM Calls**
- [ ] ✅ PASS
- [ ] ❌ FAIL (describe issue): _______________________

### Overall Status

- [ ] ✅ ALL TESTS PASSED - Ready to mark task complete
- [ ] ⚠️ PARTIAL - Some issues need fixing
- [ ] ❌ FAILED - Critical issues found

---

## Issues Log

Document any issues found during testing:

| Issue # | Description | Severity | Status |
|---------|-------------|----------|--------|
| 1 | | | |
| 2 | | | |
| 3 | | | |

---

## Test Completion

**Tested By:** _______________________  
**Date:** _______________________  
**Duration:** _______________________  
**Status:** _______________________  

---

## Next Steps

Once all tests pass:
1. [ ] Mark Task 7 as complete in tasks.md
2. [ ] Proceed to Task 8: Implement Traffic Light Score component
3. [ ] Consider documenting any edge cases discovered

---

**For detailed instructions, see:** `MANUAL_TEST_GUIDE.md`
