/**
 * Content Script for Privacy Policy Analyzer
 * Scans pages for privacy-related links and extracts policy text
 */

console.log('Privacy Policy Analyzer content script loaded');

// Constants
const MAX_TEXT_LENGTH = 50000;
const PRIVACY_KEYWORDS = ['privacy', 'terms', 'cookies'];
const EXTRACTION_TIMEOUT = 10000; // 10 seconds

interface ExtractedData {
  success: boolean;
  policyText?: string;
  policyUrl?: string;
  error?: string;
}

interface PrivacyLinks {
  urls: string[];
  found: boolean;
}

/**
 * Scans the current page for links containing privacy-related keywords
 * Requirements: 1.1, 1.2, 1.3
 */
function scanForPrivacyLinks(): PrivacyLinks {
  try {
    const allLinks = document.querySelectorAll('a');
    const matchingUrls: string[] = [];

    allLinks.forEach((link) => {
      const linkText = link.textContent?.toLowerCase() || '';
      const href = link.getAttribute('href');

      // Check if link text contains any privacy keywords (case-insensitive)
      const hasKeyword = PRIVACY_KEYWORDS.some(keyword => 
        linkText.includes(keyword)
      );

      if (hasKeyword && href) {
        // Convert relative URLs to absolute URLs
        try {
          const absoluteUrl = new URL(href, window.location.href);
          matchingUrls.push(absoluteUrl.href);
        } catch (e) {
          console.warn('Invalid URL:', href);
        }
      }
    });

    // Store links in Chrome storage for popup access (Requirement 1.3)
    chrome.storage.local.set({ 
      privacyLinks: matchingUrls,
      lastScanned: new Date().toISOString()
    });

    return {
      urls: matchingUrls,
      found: matchingUrls.length > 0
    };
  } catch (error) {
    console.error('Error scanning for privacy links:', error);
    return {
      urls: [],
      found: false
    };
  }
}

/**
 * Extracts visible text from the current page
 * Requirements: 2.2, 2.3
 */
function extractPolicyText(): string {
  try {
    // Extract all visible text from document body
    const text = document.body.innerText || '';
    
    // Truncate to max length if needed (Requirement 2.3)
    if (text.length > MAX_TEXT_LENGTH) {
      return text.substring(0, MAX_TEXT_LENGTH) + '\n\n[Text truncated at 50,000 characters]';
    }
    
    return text;
  } catch (error) {
    console.error('Error extracting policy text:', error);
    throw new Error('Failed to extract text from page');
  }
}

/**
 * Fetches and extracts text from a privacy policy URL
 * Requirements: 2.1, 2.2, 2.3, 2.5
 */
async function fetchPolicyFromUrl(url: string): Promise<ExtractedData> {
  try {
    // Create a timeout promise
    const timeoutPromise = new Promise<never>((_, reject) => {
      setTimeout(() => reject(new Error('Page load timeout')), EXTRACTION_TIMEOUT);
    });

    // Fetch the page content
    const fetchPromise = fetch(url).then(async (response) => {
      if (!response.ok) {
        throw new Error(`Failed to fetch policy: ${response.status}`);
      }
      
      const html = await response.text();
      
      // Parse HTML and extract text
      const parser = new DOMParser();
      const doc = parser.parseFromString(html, 'text/html');
      const text = doc.body.innerText || '';
      
      // Truncate if needed
      const finalText = text.length > MAX_TEXT_LENGTH 
        ? text.substring(0, MAX_TEXT_LENGTH) + '\n\n[Text truncated at 50,000 characters]'
        : text;
      
      return {
        success: true,
        policyText: finalText,
        policyUrl: url
      };
    });

    // Race between fetch and timeout (Requirement 2.5)
    return await Promise.race([fetchPromise, timeoutPromise]);
    
  } catch (error) {
    console.error('Error fetching policy from URL:', error);
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Failed to fetch policy'
    };
  }
}

/**
 * Handles messages from the popup
 * Requirements: 1.5, 2.4
 */
chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  (async () => {
    try {
      if (message.action === 'scanLinks') {
        // Scan current page for privacy links
        const links = scanForPrivacyLinks();
        sendResponse({
          success: true,
          links: links.urls,
          found: links.found
        });
        
      } else if (message.action === 'extractCurrentPage') {
        // Extract text from current page
        try {
          const text = extractPolicyText();
          sendResponse({
            success: true,
            policyText: text,
            policyUrl: window.location.href
          });
        } catch (error) {
          sendResponse({
            success: false,
            error: 'Failed to extract text from current page'
          });
        }
        
      } else if (message.action === 'extractFromUrl') {
        // Fetch and extract text from a specific URL
        if (!message.url) {
          sendResponse({
            success: false,
            error: 'No URL provided'
          });
          return;
        }
        
        const result = await fetchPolicyFromUrl(message.url);
        sendResponse(result);
        
      } else if (message.action === 'getLinks') {
        // Return previously scanned links from storage
        const data = await chrome.storage.local.get(['privacyLinks']);
        sendResponse({
          success: true,
          links: data.privacyLinks || []
        });
      }
    } catch (error) {
      console.error('Error handling message:', error);
      sendResponse({
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error occurred'
      });
    }
  })();
  
  // Return true to indicate async response
  return true;
});

// Automatically scan for privacy links when page loads (Requirement 1.1)
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    scanForPrivacyLinks();
  });
} else {
  scanForPrivacyLinks();
}

// Signal completion to popup (Requirement 1.5)
chrome.storage.local.set({ 
  scanComplete: true,
  scanTimestamp: new Date().toISOString()
});

export {};
