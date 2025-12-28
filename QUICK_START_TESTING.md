# Quick Start - Testing the Privacy Policy Analyzer Extension

## Prerequisites ✓
- ✓ Backend running on http://localhost:8000 (in TEST MODE)
- ✓ Extension built successfully in `extension/dist/`
- ✓ Chrome browser installed

## Step 1: Start the Backend (Already Running)

The backend is currently running in TEST MODE at http://localhost:8000

To verify:
```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "timestamp": "2025-12-28T..."
}
```

## Step 2: Load Extension in Chrome

1. Open Chrome browser
2. Navigate to: `chrome://extensions/`
3. Enable "Developer mode" (toggle switch in top-right corner)
4. Click "Load unpacked" button
5. Navigate to and select: `C:\Users\Pragnyan\dev\docs\extension\dist`
6. The Privacy Policy Analyzer extension should now appear in your extensions list
7. Pin the extension to your toolbar (click the puzzle icon, then pin)

## Step 3: Test the Extension

### Quick Test (Any Website)
1. Visit any website (e.g., https://www.google.com)
2. Click the Privacy Policy Analyzer extension icon
3. Wait for analysis to complete (5-10 seconds)
4. Verify you see:
   - Traffic light with colored circle and score
   - Summary text
   - Red flags section (may be empty)
   - Action items section (may be empty)

### Recommended Test Websites

#### Test 1: Google Privacy Policy (Expected: Green/Yellow)
1. Visit: https://policies.google.com/privacy
2. Click extension icon
3. Expected results:
   - Score: 70-90 (Yellow or Green)
   - Clear summary
   - Few or no red flags
   - Minimal action items

#### Test 2: Facebook Privacy Policy (Expected: Yellow/Red)
1. Visit: https://www.facebook.com/privacy/policy
2. Click extension icon
3. Expected results:
   - Score: 40-70 (Yellow or Red)
   - Detailed summary
   - Multiple red flags
   - Several action items

#### Test 3: Amazon Privacy Notice (Expected: Yellow)
1. Visit: https://www.amazon.com/gp/help/customer/display.html?nodeId=GX7NJQ4ZB8MHFRNJ
2. Click extension icon
3. Expected results:
   - Score: 50-75 (Yellow)
   - Moderate summary
   - Some red flags
   - Some action items

## Step 4: Verify UI Components

### Traffic Light Colors
- **Green (80-100)**: User-friendly policy
- **Yellow (50-79)**: Moderate concerns
- **Red (0-49)**: Significant concerns

### Summary Section
- Should display below traffic light
- If > 500 characters, should show "Read More" button
- Click "Read More" to expand full text
- Click "Show Less" to collapse

### Red Flags Section
- Red/orange background
- Warning icons (⚠️) for each flag
- If no flags: "✓ No major concerns identified" (green background)
- If > 5 flags: "Show More" button appears

### Action Items Section
- Blue background
- Arrow icons (→) for each item
- If no items: "✓ Policy appears acceptable"
- Items with URLs should be clickable links
- Links should open in NEW TAB

## Step 5: Test Clickable Links

1. Find an action item with a URL (blue, underlined text)
2. Hover over it - cursor should change to pointer
3. Click the link
4. Verify:
   - New tab opens with the URL
   - Original popup stays open
   - Link has proper security attributes

## Step 6: Test Responsive Layout

1. Open extension popup
2. Verify:
   - Popup is 400px wide
   - Popup is 600px tall
   - Content scrolls vertically if needed
   - No horizontal scrolling
   - All text wraps properly
   - All sections are visible

## Step 7: Test Error Handling

### Test Backend Disconnection
1. Stop the backend server (Ctrl+C in backend terminal)
2. Click extension icon
3. Expected: Error message "Could not analyze policy. Check backend is running."
4. Verify "Retry" button appears
5. Restart backend
6. Click "Retry" button
7. Verify analysis completes successfully

## Step 8: Test Caching

1. Analyze a policy (e.g., Google's)
2. Note the response time
3. Reload the extension (or close and reopen popup)
4. Analyze the same policy again
5. Verify:
   - Second analysis is faster (cache hit)
   - Results are identical
   - Backend logs show "Cache hit" message

## Troubleshooting

### Extension Not Loading
- Verify you selected the `dist` folder, not the `extension` folder
- Check Chrome console for errors (F12)
- Try rebuilding: `cd extension && npm run build`

### Backend Not Responding
- Verify backend is running: `curl http://localhost:8000/health`
- Check backend terminal for errors
- Restart backend: `cd backend && python -m uvicorn main:app --reload --port 8000`

### No Policy Text Extracted
- Some websites may not have detectable privacy policy links
- Try visiting the privacy policy page directly
- Check browser console for content script errors (F12)

### Styling Issues
- Clear browser cache
- Rebuild extension: `cd extension && npm run build`
- Reload extension in Chrome

## Visual Component Testing

To test UI components in isolation:
1. Open `extension/test_ui_visual.html` in Chrome
2. Verify all 11 test cases render correctly
3. Check colors, spacing, and styling

## Automated Testing

To run automated backend tests:
```bash
python test_ui_manual.py
```

This will test:
- Backend connectivity
- Score ranges and traffic light colors
- Summary generation
- Red flags identification
- Action items generation

## Success Criteria

✓ Extension loads without errors
✓ Traffic light displays correct color based on score
✓ Summary text is readable and can expand
✓ Red flags display with warning icons
✓ Action items with URLs are clickable
✓ Links open in new tabs
✓ Layout fits in 400x600 popup
✓ Error handling works
✓ Caching improves performance

## Next Steps

After manual testing is complete:
1. Document any issues found
2. Test with additional websites
3. Verify all requirements are met
4. Prepare for production deployment (add real Azure OpenAI credentials)

## Additional Resources

- **Comprehensive Testing Guide**: `UI_TESTING_GUIDE.md`
- **Test Checklist**: `FINAL_UI_TEST_CHECKLIST.md`
- **Visual Tests**: `extension/test_ui_visual.html`
- **Automated Tests**: `test_ui_manual.py`

## Current Status

✓ Backend running in TEST MODE
✓ Extension built successfully
✓ All components implemented
✓ All automated tests passing
✓ Ready for manual testing

**You can now load the extension in Chrome and start testing!**
