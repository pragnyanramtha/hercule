/**
 * Content Script for Hercule
 * Scans pages for privacy-related links and extracts policy text
 */

console.log('Hercule content script loaded');

// Constants
const MAX_TEXT_LENGTH = 50000;
const PRIVACY_KEYWORDS = ['privacy', 'terms', 'cookies'];
const EXTRACTION_TIMEOUT = 10000;
const MAX_RETRIES = 2;
const RETRY_DELAY = 1000;

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
 * Delay helper for retry logic
 */
function delay(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}

/**
 * Scans the current page for links containing privacy-related keywords
 */
function scanForPrivacyLinks(): PrivacyLinks {
  try {
    const allLinks = document.querySelectorAll('a');
    const matchingUrls: string[] = [];

    allLinks.forEach((link) => {
      const linkText = link.textContent?.toLowerCase() || '';
      const href = link.getAttribute('href');

      const hasKeyword = PRIVACY_KEYWORDS.some(keyword =>
        linkText.includes(keyword)
      );

      if (hasKeyword && href) {
        try {
          const absoluteUrl = new URL(href, window.location.href);
          matchingUrls.push(absoluteUrl.href);
        } catch {
          console.warn('Invalid URL:', href);
        }
      }
    });

    chrome.storage.local.set({
      privacyLinks: matchingUrls,
      lastScanned: new Date().toISOString()
    });

    return { urls: matchingUrls, found: matchingUrls.length > 0 };
  } catch (error) {
    console.error('Error scanning for privacy links:', error);
    return { urls: [], found: false };
  }
}

/**
 * Extracts visible text from the current page
 */
function extractPolicyText(): string {
  try {
    const text = document.body.innerText || '';

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
 * Fetches and extracts text from a privacy policy URL with retry logic
 */
async function fetchPolicyFromUrl(url: string, retryCount = 0): Promise<ExtractedData> {
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), EXTRACTION_TIMEOUT);

    const response = await fetch(url, { signal: controller.signal });
    clearTimeout(timeoutId);

    if (!response.ok) {
      throw new Error(`Failed to fetch policy: ${response.status}`);
    }

    const html = await response.text();
    const parser = new DOMParser();
    const doc = parser.parseFromString(html, 'text/html');
    const text = doc.body.innerText || '';

    const finalText = text.length > MAX_TEXT_LENGTH
      ? text.substring(0, MAX_TEXT_LENGTH) + '\n\n[Text truncated at 50,000 characters]'
      : text;

    return { success: true, policyText: finalText, policyUrl: url };

  } catch (error) {
    console.error(`Error fetching policy (attempt ${retryCount + 1}):`, error);

    // Retry logic
    if (retryCount < MAX_RETRIES) {
      console.log(`Retrying fetch... attempt ${retryCount + 2}`);
      await delay(RETRY_DELAY * (retryCount + 1));
      return fetchPolicyFromUrl(url, retryCount + 1);
    }

    return {
      success: false,
      error: error instanceof Error ? error.message : 'Failed to fetch policy'
    };
  }
}

/**
 * Handles messages from the popup
 */
chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  (async () => {
    try {
      if (message.action === 'scanLinks') {
        const links = scanForPrivacyLinks();
        sendResponse({ success: true, links: links.urls, found: links.found });

      } else if (message.action === 'extractCurrentPage') {
        try {
          const text = extractPolicyText();
          sendResponse({ success: true, policyText: text, policyUrl: window.location.href });
        } catch (error) {
          sendResponse({ success: false, error: 'Failed to extract text from current page' });
        }

      } else if (message.action === 'extractFromUrl') {
        if (!message.url) {
          sendResponse({ success: false, error: 'No URL provided' });
          return;
        }
        const result = await fetchPolicyFromUrl(message.url);
        sendResponse(result);

      } else if (message.action === 'getLinks') {
        const data = await chrome.storage.local.get(['privacyLinks']);
        sendResponse({ success: true, links: data.privacyLinks || [] });
      }
    } catch (error) {
      console.error('Error handling message:', error);
      sendResponse({
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error occurred'
      });
    }
  })();

  return true;
});

// Auto-scan on page load
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => scanForPrivacyLinks());
} else {
  scanForPrivacyLinks();
}

chrome.storage.local.set({
  scanComplete: true,
  scanTimestamp: new Date().toISOString()
});

export {};
