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
        
        
        # 40+ common privacy policy paths
        self.common_paths = [
            # Standard privacy paths
            '/privacy', '/privacy-policy', '/privacy_policy', '/privacypolicy',
            '/privacy-notice', '/privacy-statement',
            # Legal paths
            '/legal/privacy', '/legal/privacy-policy', '/legal/data-privacy', '/legal', '/legal/terms',
            # Policy paths  
            '/policies/privacy', '/policies/privacy-policy', '/policy/privacy',
            # About/Info paths
            '/about/privacy', '/about/legal', '/info/privacy', '/company/privacy',
            # Localized
            '/en/privacy', '/en-us/privacy', '/us/privacy', '/global/privacy',
            # Data protection
            '/data-privacy', '/data-protection', '/gdpr', '/ccpa',
            # Terms
            '/terms', '/terms-of-service', '/tos', '/terms-and-conditions', '/terms/privacy',
            # HTML files
            '/privacy.html', '/privacy-policy.html', '/legal.html',
            # Support paths
            '/help/privacy', '/support/privacy', '/faq/privacy',
            # Security
            '/security/privacy', '/security',
            # Other
            '/cookie-policy', '/cookies', '/user-agreement', '/compliance/privacy'
        ]
        
        # Keywords for link detection
        self.link_keywords = [
            'privacy policy', 'privacy', 'data policy', 'data protection',
            'terms of service', 'terms and conditions', 'terms of use', 'legal'
        ]

    async def discover_and_extract(self, url: str) -> DiscoveryResult:
        """
        Main entry point: Find privacy policy and extract its text.
        
        STRATEGY:
        1. Run page scans AND path checks CONCURRENTLY (fast)
        2. Prioritize page scan results (90% success rate)
        3. Fall back to DuckDuckGo only if both fail
        """
        try:
            parsed = urlparse(url if url.startswith('http') else f'https://{url}')
            domain = parsed.netloc
            base_url = f"https://{domain}"
            current_url = url if url.startswith('http') else f'https://{url}'
            
            logger.info(f"🔍 Starting discovery for {domain}")

            async with httpx.AsyncClient(
                headers=self.headers,
                follow_redirects=True,
                timeout=10.0,
                verify=False
            ) as client:
                
                # Run BOTH page scans AND path checks in parallel
                all_tasks = []
                
                # Page scan tasks (higher priority)
                page_scan_tasks = [
                    self._scrape_page_for_links(client, current_url, "current"),
                    self._scrape_page_for_links(client, base_url, "root")
                ]
                all_tasks.extend(page_scan_tasks)
                
                # Path check tasks
                path_tasks = [
                    self._check_path_and_extract(client, base_url, path)
                    for path in self.common_paths
                ]
                all_tasks.extend(path_tasks)
                
                logger.info(f"🚀 Launching {len(all_tasks)} parallel requests ({len(page_scan_tasks)} page scans + {len(path_tasks)} path checks)...")
                
                # Run ALL tasks concurrently
                all_results = await asyncio.gather(*all_tasks, return_exceptions=True)
                
                # Process results: Check page scans first (higher priority)
                page_scan_results = all_results[:len(page_scan_tasks)]
                path_check_results = all_results[len(page_scan_tasks):]
                
                # First, check page scan results
                for result in page_scan_results:
                    if result and not isinstance(result, Exception) and result.success:
                        logger.info(f"✅ Found via page scan: {result.policy_url}")
                        return result
                
                # If page scans failed, check path results
                for result in path_check_results:
                    if result and not isinstance(result, Exception) and result.success:
                        logger.info(f"✅ Found via path check: {result.policy_url}")
                        return result

            # Both failed - fall back to DuckDuckGo
            logger.info("🔍 Page scan and path checks failed. Trying DuckDuckGo...")
            
            # Fallback 1: DuckDuckGo search with site: restriction
            logger.info("⚠️ Trying DuckDuckGo search (site-specific)...")
            result = await self._duckduckgo_search(domain, site_specific=True)
            if result and result.success:
                logger.info(f"✅ Found via DuckDuckGo (site-specific): {result.policy_url}")
                return result

            # If site-specific search failed, we GIVE UP and let groq/compound handle it
            # We do NOT want to do broad searches (finds random ads) or return homepage content
            logger.warning("❌ All discovery methods failed. Letting groq/compound handle it via web search.")
            return DiscoveryResult(
                success=False,
                error="Could not find privacy policy via standard methods",
                method="failed"
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
            logger.debug(f"Path {path} returned {len(text)} chars")
            
            # Strategy 1: Strict validation
            if self._looks_like_privacy_policy(text):
                logger.info(f"✅ Path {path} looks like privacy policy ({len(text)} chars)")
                return DiscoveryResult(
                    success=True,
                    policy_text=text,
                    policy_url=str(resp.url),
                    method=f'path:{path}'
                )
            
            # Strategy 2: Relaxed validation for privacy-related paths
            # If the path itself suggests it's a privacy page, accept it even if content is weak
            privacy_indicators = ['privacy', 'gdpr', 'ccpa', 'data-protection']
            path_lower = path.lower()
            
            if any(indicator in path_lower for indicator in privacy_indicators):
                # Check if it has at least SOME privacy-related content (very relaxed)
                if len(text) > 200 and 'privacy' in text.lower():
                    logger.info(f"✅ Path {path} accepted via relaxed validation ({len(text)} chars)")
                    return DiscoveryResult(
                        success=True,
                        policy_text=text,
                        policy_url=str(resp.url),
                        method=f'path:{path}:relaxed'
                    )
            
            logger.debug(f"Path {path} doesn't look like privacy policy (too short or missing keywords)")
            return None
        except Exception as e:
            logger.debug(f"Path {path} failed: {e}")
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
            
            # Try top 10 candidates (increased from 3)
            for score, url in candidates[:10]:
                try:
                    link_resp = await client.get(url)
                    if link_resp.status_code == 200:
                        text = self._extract_text(link_resp.text)
                        
                        # Relaxed validation for scraped links - if we scored it highly, trust it more
                        if score > 50:
                            # High-scoring link - very relaxed check
                            if len(text) > 200:
                                logger.info(f"✅ Found via scrape (score={score}): {url}")
                                return DiscoveryResult(
                                    success=True,
                                    policy_text=text,
                                    policy_url=str(link_resp.url),
                                    method=f'scrape:{source}'
                                )
                        elif self._looks_like_privacy_policy(text):
                            # Lower score - use strict validation
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
        text_lower = text.lower()
        
        # Exact text matches (highest priority)
        exact_matches = [
            'privacy policy', 'privacy', 'privacy notice', 'privacy statement',
            'terms of service', 'terms', 'terms of use', 'terms and conditions',
            'legal', 'legal notice', 'user agreement', 'data protection',
            'cookie policy', 'cookies', 'gdpr', 'ccpa'
        ]
        for match in exact_matches:
            if text_lower == match:
                score += 100
                break
        
        # Partial text matches (check if keyword appears in link text)
        privacy_keywords = [
            'privacy', 'privacidad', 'datenschutz',  # English, Spanish, German
            'terms', 'conditions', 'legal', 'policy', 'policies',
            'agreement', 'data protection', 'cookie', 'gdpr', 'ccpa',
            'user rights', 'your data', 'security', 'compliance'
        ]
        
        for keyword in privacy_keywords:
            if keyword in text_lower:
                score += 30
        
        # URL path matches (very reliable indicator)
        url_patterns = [
            '/privacy', '/privacidad', '/datenschutz',
            '/legal', '/terms', '/tos', '/conditions',
            '/policy', '/policies', '/agreement',
            '/cookie', '/gdpr', '/ccpa', '/data-protection',
            'privacy-policy', 'privacy_policy', 'privacypolicy',
            'terms-of-service', 'terms_of_service', 'termsofservice',
            'user-agreement', 'user_agreement'
        ]
        
        for pattern in url_patterns:
            if pattern in href_lower:
                score += 40
                break
        
        # Boost score if both text AND URL contain privacy-related terms
        if any(kw in text_lower for kw in ['privacy', 'terms', 'legal']) and \
           any(kw in href_lower for kw in ['privacy', 'terms', 'legal']):
            score += 50
        
        return score

    async def _duckduckgo_search(self, domain: str, site_specific: bool = True) -> Optional[DiscoveryResult]:
        """
        Search DuckDuckGo using direct HTML scraping.
        This ensures we ONLY hit DuckDuckGo and avoid the 'ddgs' library trying random backends (Wikipedia/etc).
        """
        try:
            # Search terms in PRIORITY ORDER (privacy policy is most important)
            search_terms = [
                ("privacy policy", 100),      # Highest priority
                ("privacy notice", 90),
                ("privacy statement", 85),
                ("data protection", 80),
                ("terms of service", 50),     # Lower priority
                ("terms and conditions", 45),
                ("user agreement", 40),
                ("terms of use", 35),
                ("legal notice", 30),
                ("cookie policy", 25)         # Lowest priority
            ]
            
            # Browser headers to avoid 403s
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Referer": "https://html.duckduckgo.com/",
                "Origin": "https://html.duckduckgo.com",
                "Content-Type": "application/x-www-form-urlencoded"
            }

            async def search_single_term(term: str, priority: int) -> Optional[tuple]:
                """Search for a single term using manual HTML scraping."""
                try:
                    query = f"site:{domain} {term}" if site_specific else f"{domain} {term}"
                    
                    async with httpx.AsyncClient(headers=headers, timeout=5.0, verify=False) as search_client:
                        # Use POST to html.duckduckgo.com - it's more robust than GET for scraping
                        resp = await search_client.post(
                            "https://html.duckduckgo.com/html/",
                            data={"q": query},
                        )
                        
                        if resp.status_code == 200:
                            results = []
                            soup = BeautifulSoup(resp.text, 'html.parser')
                            
                            # Parse result links (class 'result__a' in simple HTML version)
                            for link in soup.select('.result__a'):
                                href = link.get('href')
                                if href and not 'duckduckgo.com' in href:
                                    results.append(href)
                                    if len(results) >= 2: # Keep it tight
                                        break
                            
                            if results:
                                return (priority, term, results)
                                
                except Exception as e:
                    logger.debug(f"Manual search failed for '{term}': {e}")
                return None
            
            # Launch ALL searches in parallel
            logger.info(f"🚀 Launching {len(search_terms)} parallel DuckDuckGo (HTML) searches...")
            search_tasks = [search_single_term(term, priority) for term, priority in search_terms]
            all_results = await asyncio.gather(*search_tasks, return_exceptions=True)
            
            # Filter and sort results by priority
            valid_results = []
            for result in all_results:
                if result and not isinstance(result, Exception):
                    valid_results.append(result)
            
            # Sort by priority (highest first)
            valid_results.sort(key=lambda x: x[0], reverse=True)
            
            # Process results in priority order
            async with httpx.AsyncClient(
                headers=self.headers,
                follow_redirects=True,
                timeout=5.0, # Fast check
                verify=False
            ) as client:
                for priority, term, results in valid_results:
                    for url in results:
                        if not url: continue
                        
                        # Filter out junk URLs (videos, user posts, etc)
                        url_lower = url.lower()
                        junk_patterns = [
                            '/videos/', '/video/', '/watch?', '/reel/',
                            '/posts/', '/post/', '/status/', '/user/',
                            '/photo/', '/photos/', '/groups/', '/events/',
                            'linkedin.com', 'facebook.com', 'twitter.com', 'instagram.com'
                        ]
                        
                        if any(pattern in url_lower for pattern in junk_patterns):
                            logger.debug(f"Skipping junk URL: {url}")
                            continue
                        
                        try:
                            resp = await client.get(url)
                            if resp.status_code == 200:
                                text = self._extract_text(resp.text)
                                
                                # RELAXED validation - DDG found it, trust it
                                if len(text) > 500:  # Higher threshold for search results
                                    logger.info(f"✅ DDG found via '{term}' (priority={priority}): {url} ({len(text)} chars)")
                                    return DiscoveryResult(
                                        success=True,
                                        policy_text=text,
                                        policy_url=str(resp.url),
                                        method=f'duckduckgo:{term}'
                                    )
                        except Exception as e:
                            logger.debug(f"Failed to fetch {url}: {e}")
                            continue
            
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
