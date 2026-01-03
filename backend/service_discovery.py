import logging
import asyncio
import httpx
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from typing import Optional
from duckduckgo_search import DDGS

logger = logging.getLogger("privacy-api")

class DiscoveryService:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        self.common_paths = [
            # High priority
            '/privacy',
            '/privacy-policy',
            '/privacy_policy',
            '/legal/privacy',
            '/legal/privacy-policy',
            '/terms',
            '/terms-of-service',
            '/tos',
            
            # Additional common variants
            '/legal',
            '/about/privacy',
            '/policies/privacy',
            '/policies/privacy-policy',
            '/security/privacy',
            '/help/privacy',
            '/data-privacy',
            '/data-protection',
            '/gdpr',
            '/ccpa',
            '/cookie-policy',
            '/cookies',
            '/legal/terms',
            '/terms-conditions',
            '/user-agreement',
            '/misc/privacy',
            '/global/privacy'
        ]
        self.keywords = ['privacy', 'terms', 'legal', 'policy', 'tos', 'conditions', 'data protection', 'user agreement']

    async def find_policy(self, url: str) -> Optional[str]:
        """
        Aggressively find the privacy policy URL.
        1. Parallel Scan: Check 25+ common paths simultaneously.
        2. Homepage Scraping: If paths fail, scrape homepage for links.
        3. Search Fallback: If scraping fails, use DuckDuckGo.
        """
        try:
            domain = self._get_domain(url)
            base_url = f"https://{domain}"
            
            logger.info(f"🔍 Starting AGGRESSIVE policy discovery for {domain}")

            # Step 1: Parallel Path Checking (Fastest if it hits)
            logger.info(f"🚀 Launching parallel check for {len(self.common_paths)} paths...")
            found_path = await self._check_paths_parallel(base_url)
            if found_path:
                logger.info(f"✅ Found policy via Parallel Path check: {found_path}")
                return found_path

            # Step 2: Scrape Homepage (If standard paths fail)
            logger.info("⚠️ Standard paths failed. Scraping homepage for policy links...")
            scraped_url = await self._scrape_homepage_links(base_url)
            if scraped_url:
                logger.info(f"✅ Found policy via Homepage Scraping: {scraped_url}")
                return scraped_url

            # Step 3: Hackathon Way (DuckDuckGo Search - Last Resort)
            logger.info("⚠️ Scraping failed. Trying DuckDuckGo search...")
            search_url = await self._search_ddg_async(domain)
            if search_url:
                logger.info(f"✅ Found policy via DuckDuckGo: {search_url}")
                return search_url

            logger.warning(f"❌ Could not find policy for {domain} after comprehensive search.")
            return None

        except Exception as e:
            logger.error(f"Error in discovery service: {e}")
            return None

    def _get_domain(self, url: str) -> str:
        parsed = urlparse(url)
        if not parsed.netloc:
             parsed = urlparse(f"https://{url}")
        return parsed.netloc

    async def _check_paths_parallel(self, base_url: str) -> Optional[str]:
        """Check all common paths in parallel using httpx."""
        async with httpx.AsyncClient(headers=self.headers, verify=False, timeout=5.0) as client:
            tasks = []
            for path in self.common_paths:
                target = urljoin(base_url, path)
                tasks.append(self._check_single_path(client, target))
            
            # Run all requests
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Return the first successful URL
            for res in results:
                if isinstance(res, str) and res:
                    return res
        return None

    async def _check_single_path(self, client: httpx.AsyncClient, url: str) -> Optional[str]:
        try:
            # HEAD request is faster, but some servers block it, so GET with stream=True is a safer compromise
            # We'll stick to HEAD for speed, maybe fallback? simpler is better for speed.
            resp = await client.head(url, follow_redirects=True)
            if resp.status_code == 200:
                # Basic check: content-type should be html
                ctype = resp.headers.get('content-type', '').lower()
                if 'html' in ctype:
                    return str(resp.url)
        except:
            pass
        return None

    async def _scrape_homepage_links(self, base_url: str) -> Optional[str]:
        """Scrape homepage for links with relevant keywords."""
        try:
            async with httpx.AsyncClient(headers=self.headers, verify=False, timeout=10.0) as client:
                resp = await client.get(base_url, follow_redirects=True)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, 'html.parser')
                    
                    # Score-based link selection
                    best_link = None
                    best_score = 0

                    for a in soup.find_all('a', href=True):
                        text = a.get_text().lower()
                        href = a['href'].lower()
                        
                        # Calculate score based on keyword match
                        score = 0
                        
                        # Exact matches get highest priority
                        if text in ['privacy', 'privacy policy']:
                            score += 10
                        elif text in ['terms', 'terms of service']:
                            score += 8
                        elif 'privacy' in text or 'privacy' in href:
                             score += 5
                        elif any(k in text for k in self.keywords):
                             score += 2
                        
                        if score > best_score:
                            full_url = urljoin(base_url, a['href'])
                            if full_url.startswith('http'):
                                best_score = score
                                best_link = full_url
                    
                    if best_link:
                        return best_link
        except Exception as e:
            logger.warning(f"Homepage scraping failed: {e}")
        return None

    async def _search_ddg_async(self, domain: str) -> Optional[str]:
        """Wrapper for synchronous DDG search to run in async loop."""
        def run_search():
            try:
                query = f"site:{domain} privacy policy"
                with DDGS() as ddgs:
                    # Try to get 2 results to be safe, return first valid one
                    results = list(ddgs.text(query, max_results=2))
                    if results:
                        return results[0]['href']
            except Exception as e:
                logger.error(f"DuckDuckGo search error: {e}")
            return None

        # Run configured sync function in thread pool
        return await asyncio.to_thread(run_search)
