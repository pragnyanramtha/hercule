"""
Aggressive Privacy Policy Discovery Service
Finds and extracts privacy policy text from any website.
"""
import logging
import asyncio
import httpx
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from typing import Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger("hercule-api.discovery")

@dataclass
class DiscoveryResult:
    """Result of privacy policy discovery."""
    success: bool
    policy_text: Optional[str] = None
    policy_url: Optional[str] = None
    method: Optional[str] = None  # 'parallel_paths', 'homepage_scrape', 'duckduckgo'
    error: Optional[str] = None


class DiscoveryService:
    """
    Aggressive privacy policy discovery service.
    
    Strategy:
    1. Parallel check 25+ common privacy policy URL paths
    2. If none hit, scrape current page for "privacy policy" links
    3. If that fails, DuckDuckGo search as last resort
    """
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        }
        
        # 25+ common privacy policy paths to check in parallel
        self.common_paths = [
            '/privacy',
            '/privacy-policy',
            '/privacy_policy',
            '/privacypolicy',
            '/legal/privacy',
            '/legal/privacy-policy',
            '/policies/privacy',
            '/policies/privacy-policy',
            '/about/privacy',
            '/info/privacy',
            '/terms/privacy',
            '/en/privacy',
            '/us/privacy',
            '/privacy.html',
            '/privacy-policy.html',
            '/legal',
            '/legal/terms',
            '/terms',
            '/terms-of-service',
            '/tos',
            '/terms-and-conditions',
            '/data-privacy',
            '/data-protection',
            '/gdpr',
            '/ccpa',
            '/cookie-policy',
        ]
        
        # Keywords to look for in link text/href
        self.link_keywords = [
            'privacy policy', 'privacy', 'data policy', 'data protection',
            'terms of service', 'terms and conditions', 'terms of use',
            'legal', 'user agreement'
        ]

    async def discover_and_extract(self, url: str) -> DiscoveryResult:
        """
        Main entry point: Find privacy policy and extract its text.
        Does NOT return until policy text is found or all methods exhausted.
        """
        try:
            domain = self._get_domain(url)
            base_url = f"https://{domain}"
            
            logger.info(f"🔍 Starting aggressive policy discovery for {domain}")

            # Step 1: Parallel path checking (fastest)
            logger.info(f"🚀 Step 1: Checking {len(self.common_paths)} common paths in parallel...")
            result = await self._parallel_path_check(base_url)
            if result.success:
                logger.info(f"✅ Found via parallel paths: {result.policy_url}")
                return result

            # Step 2: Scrape homepage for privacy links
            logger.info("🔍 Step 2: Scraping homepage for privacy policy links...")
            result = await self._scrape_for_privacy_links(base_url)
            if result.success:
                logger.info(f"✅ Found via homepage scraping: {result.policy_url}")
                return result

            # Step 3: DuckDuckGo search as last resort
            logger.info("🔍 Step 3: Searching DuckDuckGo for privacy policy...")
            result = await self._duckduckgo_search(domain)
            if result.success:
                logger.info(f"✅ Found via DuckDuckGo: {result.policy_url}")
                return result

            logger.warning(f"❌ Could not find privacy policy for {domain}")
            return DiscoveryResult(
                success=False,
                error=f"Could not find privacy policy for {domain} after exhaustive search"
            )

        except Exception as e:
            logger.error(f"Discovery error: {e}")
            return DiscoveryResult(success=False, error=str(e))

    def _get_domain(self, url: str) -> str:
        """Extract domain from URL."""
        if not url.startswith(('http://', 'https://')):
            url = f"https://{url}"
        parsed = urlparse(url)
        return parsed.netloc or parsed.path.split('/')[0]

    async def _parallel_path_check(self, base_url: str) -> DiscoveryResult:
        """Check all common paths in parallel, return first successful one with text."""
        async with httpx.AsyncClient(
            headers=self.headers,
            follow_redirects=True,
            timeout=8.0,
            verify=False
        ) as client:
            tasks = [
                self._check_path_and_extract(client, base_url, path)
                for path in self.common_paths
            ]
            
            # Use as_completed to return as soon as we find one
            for coro in asyncio.as_completed(tasks):
                try:
                    result = await coro
                    if result and result.success and result.policy_text:
                        # Cancel remaining tasks
                        return result
                except Exception:
                    continue
            
        return DiscoveryResult(success=False)

    async def _check_path_and_extract(
        self, client: httpx.AsyncClient, base_url: str, path: str
    ) -> Optional[DiscoveryResult]:
        """Check a single path and extract text if it looks like a privacy policy."""
        url = urljoin(base_url, path)
        try:
            resp = await client.get(url)
            if resp.status_code != 200:
                return None
            
            content_type = resp.headers.get('content-type', '').lower()
            if 'html' not in content_type:
                return None
            
            # Extract and validate text
            text = self._extract_text(resp.text)
            if self._looks_like_privacy_policy(text):
                return DiscoveryResult(
                    success=True,
                    policy_text=text,
                    policy_url=str(resp.url),
                    method='parallel_paths'
                )
            return None
        except Exception:
            return None

    async def _scrape_for_privacy_links(self, base_url: str) -> DiscoveryResult:
        """Scrape the homepage for links containing privacy-related keywords."""
        try:
            async with httpx.AsyncClient(
                headers=self.headers,
                follow_redirects=True,
                timeout=10.0,
                verify=False
            ) as client:
                # Fetch homepage
                resp = await client.get(base_url)
                if resp.status_code != 200:
                    return DiscoveryResult(success=False)
                
                soup = BeautifulSoup(resp.text, 'html.parser')
                
                # Find all links and score them
                candidates = []
                for a in soup.find_all('a', href=True):
                    href = a.get('href', '')
                    text = a.get_text(strip=True).lower()
                    
                    # Skip empty or javascript links
                    if not href or href.startswith(('javascript:', '#', 'mailto:')):
                        continue
                    
                    # Score based on keyword matches
                    score = 0
                    href_lower = href.lower()
                    
                    # Exact text matches (highest priority)
                    if text in ['privacy policy', 'privacy']:
                        score += 100
                    elif text in ['terms of service', 'terms', 'legal']:
                        score += 50
                    
                    # Partial matches
                    for keyword in self.link_keywords:
                        if keyword in text:
                            score += 30
                        if keyword.replace(' ', '-') in href_lower or keyword.replace(' ', '_') in href_lower:
                            score += 20
                    
                    if score > 0:
                        full_url = urljoin(base_url, href)
                        candidates.append((score, full_url))
                
                # Sort by score descending
                candidates.sort(key=lambda x: x[0], reverse=True)
                
                # Try top candidates
                for score, url in candidates[:5]:
                    try:
                        resp = await client.get(url)
                        if resp.status_code == 200:
                            text = self._extract_text(resp.text)
                            if self._looks_like_privacy_policy(text):
                                return DiscoveryResult(
                                    success=True,
                                    policy_text=text,
                                    policy_url=str(resp.url),
                                    method='homepage_scrape'
                                )
                    except Exception:
                        continue
                
                return DiscoveryResult(success=False)
                
        except Exception as e:
            logger.warning(f"Homepage scraping failed: {e}")
            return DiscoveryResult(success=False)

    async def _duckduckgo_search(self, domain: str) -> DiscoveryResult:
        """Search DuckDuckGo for the privacy policy and fetch the result."""
        try:
            from duckduckgo_search import DDGS
            
            def search_sync():
                query = f"site:{domain} privacy policy"
                with DDGS() as ddgs:
                    results = list(ddgs.text(query, max_results=3))
                    return results
            
            # Run sync search in thread pool
            results = await asyncio.to_thread(search_sync)
            
            if not results:
                return DiscoveryResult(success=False)
            
            # Try to fetch each result
            async with httpx.AsyncClient(
                headers=self.headers,
                follow_redirects=True,
                timeout=10.0,
                verify=False
            ) as client:
                for result in results:
                    url = result.get('href') or result.get('link')
                    if not url:
                        continue
                    
                    try:
                        resp = await client.get(url)
                        if resp.status_code == 200:
                            text = self._extract_text(resp.text)
                            if self._looks_like_privacy_policy(text):
                                return DiscoveryResult(
                                    success=True,
                                    policy_text=text,
                                    policy_url=str(resp.url),
                                    method='duckduckgo'
                                )
                    except Exception:
                        continue
            
            return DiscoveryResult(success=False)
            
        except Exception as e:
            logger.error(f"DuckDuckGo search failed: {e}")
            return DiscoveryResult(success=False)

    def _extract_text(self, html: str) -> str:
        """Extract clean text from HTML."""
        soup = BeautifulSoup(html, 'html.parser')
        
        # Remove script, style, nav, header, footer elements
        for tag in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 'noscript']):
            tag.decompose()
        
        # Get text
        text = soup.get_text(separator=' ', strip=True)
        
        # Clean up whitespace
        import re
        text = re.sub(r'\s+', ' ', text)
        
        # Truncate to 50k chars
        if len(text) > 50000:
            text = text[:50000] + "\n[Text truncated at 50,000 characters]"
        
        return text

    def _looks_like_privacy_policy(self, text: str) -> bool:
        """
        Heuristic check if text looks like a privacy policy.
        Must contain several privacy-related terms.
        """
        if len(text) < 500:
            return False
        
        text_lower = text.lower()
        
        # Must-have keywords (need at least 3)
        privacy_keywords = [
            'privacy', 'personal data', 'personal information',
            'collect', 'data collection', 'information we collect',
            'cookies', 'third party', 'third-party',
            'data protection', 'gdpr', 'ccpa',
            'your rights', 'opt out', 'opt-out',
            'data retention', 'how we use', 'share your',
            'consent', 'disclosure', 'security'
        ]
        
        matches = sum(1 for kw in privacy_keywords if kw in text_lower)
        
        # Need at least 3 keyword matches to be considered a privacy policy
        return matches >= 3


# Legacy method for backward compatibility
    async def find_policy(self, url: str) -> Optional[str]:
        """Legacy method - returns just the URL."""
        result = await self.discover_and_extract(url)
        return result.policy_url if result.success else None
