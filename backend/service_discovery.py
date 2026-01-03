"""
Aggressive Privacy Policy Discovery Service
Finds and extracts privacy policy text from any website - FAST.
"""
import logging
import asyncio
import httpx
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from typing import Optional, List
from dataclasses import dataclass

logger = logging.getLogger("hercule-api.discovery")

@dataclass
class DiscoveryResult:
    """Result of privacy policy discovery."""
    success: bool
    policy_text: Optional[str] = None
    policy_url: Optional[str] = None
    method: Optional[str] = None
    error: Optional[str] = None


class DiscoveryService:
    """
    Ultra-fast privacy policy discovery service.
    
    Strategy (ALL IN PARALLEL):
    1. Check 26 common privacy policy URL paths
    2. Scrape root domain landing page for privacy links
    3. Scrape current page for privacy links (if different from root)
    
    If all parallel attempts fail, fall back to DuckDuckGo search.
    """
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        }
        
        # 26 common privacy policy paths
        self.common_paths = [
            '/privacy', '/privacy-policy', '/privacy_policy', '/privacypolicy',
            '/legal/privacy', '/legal/privacy-policy', '/policies/privacy',
            '/policies/privacy-policy', '/about/privacy', '/info/privacy',
            '/terms/privacy', '/en/privacy', '/us/privacy', '/privacy.html',
            '/privacy-policy.html', '/legal', '/legal/terms', '/terms',
            '/terms-of-service', '/tos', '/terms-and-conditions',
            '/data-privacy', '/data-protection', '/gdpr', '/ccpa', '/cookie-policy',
        ]
        
        # Keywords for link detection
        self.link_keywords = [
            'privacy policy', 'privacy', 'data policy', 'data protection',
            'terms of service', 'terms and conditions', 'terms of use', 'legal'
        ]

    async def discover_and_extract(self, url: str) -> DiscoveryResult:
        """
        Main entry point: Find privacy policy and extract its text.
        Runs path checking and page scraping IN PARALLEL for speed.
        """
        try:
            parsed = urlparse(url if url.startswith('http') else f'https://{url}')
            domain = parsed.netloc
            base_url = f"https://{domain}"
            current_url = url if url.startswith('http') else f'https://{url}'
            
            logger.info(f"🔍 Starting parallel discovery for {domain}")

            # Run ALL discovery methods in parallel
            async with httpx.AsyncClient(
                headers=self.headers,
                follow_redirects=True,
                timeout=10.0,
                verify=False
            ) as client:
                
                # Create all tasks
                tasks = []
                
                # Task 1: Check all 26 common paths in parallel
                path_tasks = [
                    self._check_path_and_extract(client, base_url, path)
                    for path in self.common_paths
                ]
                tasks.extend(path_tasks)
                
                # Task 2: Scrape root domain landing page
                tasks.append(self._scrape_page_for_links(client, base_url, "root"))
                
                # Task 3: Scrape current page (if different from root)
                if current_url.rstrip('/') != base_url.rstrip('/'):
                    tasks.append(self._scrape_page_for_links(client, current_url, "current"))
                
                logger.info(f"🚀 Launching {len(tasks)} parallel requests...")
                
                # Run all tasks, return first success
                result = await self._race_for_success(tasks)
                
                if result and result.success:
                    logger.info(f"✅ Found via {result.method}: {result.policy_url}")
                    return result

            # Fallback: DuckDuckGo search (only if parallel methods failed)
            logger.info("⚠️ Parallel discovery failed. Trying DuckDuckGo search...")
            result = await self._duckduckgo_search(domain)
            if result and result.success:
                logger.info(f"✅ Found via DuckDuckGo: {result.policy_url}")
                return result

            logger.warning(f"❌ Could not find privacy policy for {domain}")
            return DiscoveryResult(
                success=False,
                error=f"Could not find privacy policy for {domain}"
            )

        except Exception as e:
            logger.error(f"Discovery error: {e}")
            return DiscoveryResult(success=False, error=str(e))

    async def _race_for_success(self, tasks: List) -> Optional[DiscoveryResult]:
        """Run all tasks and return the first successful result."""
        pending = set()
        
        for task in tasks:
            pending.add(asyncio.create_task(task))
        
        while pending:
            done, pending = await asyncio.wait(
                pending,
                return_when=asyncio.FIRST_COMPLETED
            )
            
            for task in done:
                try:
                    result = task.result()
                    if result and result.success and result.policy_text:
                        # Cancel remaining tasks
                        for p in pending:
                            p.cancel()
                        return result
                except Exception:
                    continue
        
        return None

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
            
            text = self._extract_text(resp.text)
            if self._looks_like_privacy_policy(text):
                return DiscoveryResult(
                    success=True,
                    policy_text=text,
                    policy_url=str(resp.url),
                    method=f'path:{path}'
                )
            return None
        except Exception:
            return None

    async def _scrape_page_for_links(
        self, client: httpx.AsyncClient, page_url: str, source: str
    ) -> Optional[DiscoveryResult]:
        """Scrape a page for privacy policy links and follow the best one."""
        try:
            resp = await client.get(page_url)
            if resp.status_code != 200:
                return None
            
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # Find and score all links
            candidates = []
            for a in soup.find_all('a', href=True):
                href = a.get('href', '')
                text = a.get_text(strip=True).lower()
                
                if not href or href.startswith(('javascript:', '#', 'mailto:')):
                    continue
                
                score = self._score_link(text, href)
                if score > 0:
                    full_url = urljoin(page_url, href)
                    candidates.append((score, full_url))
            
            # Sort by score and try top candidates
            candidates.sort(key=lambda x: x[0], reverse=True)
            
            for score, url in candidates[:3]:
                try:
                    link_resp = await client.get(url)
                    if link_resp.status_code == 200:
                        text = self._extract_text(link_resp.text)
                        if self._looks_like_privacy_policy(text):
                            return DiscoveryResult(
                                success=True,
                                policy_text=text,
                                policy_url=str(link_resp.url),
                                method=f'scrape:{source}'
                            )
                except Exception:
                    continue
            
            return None
            
        except Exception:
            return None

    def _score_link(self, text: str, href: str) -> int:
        """Score a link based on how likely it is to be a privacy policy."""
        score = 0
        href_lower = href.lower()
        
        # Exact text matches (highest priority)
        if text in ['privacy policy', 'privacy']:
            score += 100
        elif text in ['terms of service', 'terms', 'legal']:
            score += 50
        
        # Partial text matches
        for keyword in self.link_keywords:
            if keyword in text:
                score += 30
            if keyword.replace(' ', '-') in href_lower or keyword.replace(' ', '_') in href_lower:
                score += 20
        
        # URL path matches
        if '/privacy' in href_lower:
            score += 40
        if '/legal' in href_lower:
            score += 20
        
        return score

    async def _duckduckgo_search(self, domain: str) -> Optional[DiscoveryResult]:
        """Search DuckDuckGo for the privacy policy (last resort)."""
        try:
            try:
                from ddgs import DDGS
            except ImportError:
                from duckduckgo_search import DDGS
            
            def search_sync():
                query = f"site:{domain} privacy policy"
                with DDGS() as ddgs:
                    return list(ddgs.text(query, max_results=3))
            
            results = await asyncio.to_thread(search_sync)
            
            if not results:
                return None
            
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
            
            return None
            
        except Exception as e:
            logger.error(f"DuckDuckGo search failed: {e}")
            return None

    def _extract_text(self, html: str) -> str:
        """Extract clean text from HTML."""
        soup = BeautifulSoup(html, 'html.parser')
        
        for tag in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 'noscript']):
            tag.decompose()
        
        text = soup.get_text(separator=' ', strip=True)
        
        import re
        text = re.sub(r'\s+', ' ', text)
        
        if len(text) > 50000:
            text = text[:50000] + "\n[Text truncated at 50,000 characters]"
        
        return text

    def _looks_like_privacy_policy(self, text: str) -> bool:
        """Heuristic check if text looks like a privacy policy."""
        if len(text) < 500:
            return False
        
        text_lower = text.lower()
        
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
        return matches >= 3

    # Legacy method for backward compatibility
    async def find_policy(self, url: str) -> Optional[str]:
        """Legacy method - returns just the URL."""
        result = await self.discover_and_extract(url)
        return result.policy_url if result.success else None
