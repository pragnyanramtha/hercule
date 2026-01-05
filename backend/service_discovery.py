"""
Aggressive Privacy Policy Discovery Service
Finds and extracts privacy policy text from any website - FAST.
"""
import logging
import asyncio
import httpx
import os
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from typing import Optional, List
from dataclasses import dataclass

logger = logging.getLogger("hercule-api.discovery")

# Priority order for search terms (privacy > terms)
SEARCH_PRIORITY = {
    "privacy policy": 100,
    "privacy notice": 95,
    "privacy statement": 90,
    "privacy": 85,
    "data protection": 80,
    "data privacy": 75,
    "gdpr": 70,
    "ccpa": 65,
    "cookie policy": 50,
    "terms of service": 30,
    "terms and conditions": 25,
    "terms of use": 20,
    "user agreement": 15,
    "legal notice": 10,
    "terms": 5,
    "legal": 5,
}

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
    1. Check 26 common privacy policy URL paths (on BOTH subdomain AND base domain)
    2. Scrape root domain landing page for privacy links
    3. Scrape current page for privacy links (if different from root)
    4. Also scrape base domain if different from subdomain
    
    If all parallel attempts fail, fall back to DuckDuckGo search (with base URL validation).
    If DuckDuckGo fails, fall back to Google Search API.
    """
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        }
        
        # Character limits for policy text
        self.max_chars = 8000  # Truncate to 8k chars
        self.max_chars_threshold = 10000  # Only truncate if over 10k
        
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
            # Terms (lower priority, but still check)
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
        
        # Keywords for link detection (ordered by priority)
        self.link_keywords = [
            'privacy policy', 'privacy', 'data policy', 'data protection',
            'terms of service', 'terms and conditions', 'terms of use', 'legal'
        ]

    def _get_base_domain(self, domain: str) -> str:
        """
        Extract base domain from subdomain.
        
        Examples:
            docs.python.org -> python.org
            sub.example.co.uk -> example.co.uk
            example.com -> example.com
        """
        # Remove www. prefix if present
        domain = domain.lower().replace('www.', '')
        
        parts = domain.split('.')
        if len(parts) <= 2:
            return domain
        
        # Handle special TLDs like .co.uk, .com.au, .org.uk, etc.
        special_second_level = ['co', 'com', 'org', 'net', 'gov', 'edu', 'ac']
        if len(parts) >= 3 and parts[-2] in special_second_level:
            return '.'.join(parts[-3:])
        
        return '.'.join(parts[-2:])

    def _is_same_base_domain(self, original_domain: str, result_url: str) -> bool:
        """
        Check if result URL belongs to the same base domain as original.
        Used to validate DuckDuckGo results don't return unrelated sites.
        """
        try:
            result_parsed = urlparse(result_url)
            result_domain = result_parsed.netloc.lower().replace('www.', '')
            
            original_base = self._get_base_domain(original_domain)
            result_base = self._get_base_domain(result_domain)
            
            return original_base == result_base
        except Exception:
            return False

    def _truncate_text(self, text: str) -> str:
        """
        Truncate policy text if it exceeds threshold.
        Only truncate if over 10k chars, cut to 8k.
        """
        if len(text) > self.max_chars_threshold:
            logger.info(f"📄 Policy text truncated: {len(text):,} → {self.max_chars:,} chars")
            return text[:self.max_chars] + "\n\n[Text truncated at 8,000 characters]"
        return text

    async def discover_and_extract(self, url: str) -> DiscoveryResult:
        """
        Main entry point: Find privacy policy and extract its text.
        
        STRATEGY:
        1. Run page scans AND path checks CONCURRENTLY (on both subdomain and base domain)
        2. Prioritize privacy-related results over terms
        3. Fall back to DuckDuckGo (with base URL validation)
        4. Fall back to Google Search API if DuckDuckGo fails
        """
        try:
            parsed = urlparse(url if url.startswith('http') else f'https://{url}')
            domain = parsed.netloc
            base_domain = self._get_base_domain(domain)
            subdomain_url = f"https://{domain}"
            base_domain_url = f"https://{base_domain}"
            current_url = url if url.startswith('http') else f'https://{url}'
            
            logger.info(f"🔍 Starting discovery for {domain}")
            if domain != base_domain:
                logger.info(f"   Also checking base domain: {base_domain}")

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
                    self._scrape_page_for_links(client, subdomain_url, "root")
                ]
                
                # Also scrape base domain if different from subdomain
                if domain != base_domain:
                    page_scan_tasks.append(
                        self._scrape_page_for_links(client, base_domain_url, "base_domain")
                    )
                
                all_tasks.extend(page_scan_tasks)
                
                # Path check tasks for subdomain
                path_tasks = [
                    self._check_path_and_extract(client, subdomain_url, path)
                    for path in self.common_paths
                ]
                
                # Also check paths on base domain if different
                if domain != base_domain:
                    base_path_tasks = [
                        self._check_path_and_extract(client, base_domain_url, path)
                        for path in self.common_paths
                    ]
                    path_tasks.extend(base_path_tasks)
                
                all_tasks.extend(path_tasks)
                
                logger.info(f"🚀 Launching {len(all_tasks)} parallel requests ({len(page_scan_tasks)} page scans + {len(path_tasks)} path checks)...")
                
                # Run ALL tasks concurrently
                all_results = await asyncio.gather(*all_tasks, return_exceptions=True)
                
                # Process results: Check page scans first (higher priority)
                page_scan_results = all_results[:len(page_scan_tasks)]
                path_check_results = all_results[len(page_scan_tasks):]
                
                # Collect all successful results with their priority scores
                successful_results = []
                
                # First, collect page scan results
                for result in page_scan_results:
                    if result and not isinstance(result, Exception) and result.success:
                        priority = self._get_result_priority(result)
                        successful_results.append((priority, result))
                
                # Then collect path results
                for result in path_check_results:
                    if result and not isinstance(result, Exception) and result.success:
                        priority = self._get_result_priority(result)
                        successful_results.append((priority, result))
                
                # Sort by priority (highest first) and return best result
                if successful_results:
                    successful_results.sort(key=lambda x: x[0], reverse=True)
                    best_result = successful_results[0][1]
                    logger.info(f"✅ Found via {best_result.method}: {best_result.policy_url} (priority: {successful_results[0][0]})")
                    # Truncate if needed
                    best_result.policy_text = self._truncate_text(best_result.policy_text)
                    return best_result

            # Both failed - fall back to DuckDuckGo
            logger.info("🔍 Page scan and path checks failed. Trying DuckDuckGo...")
            
            # Fallback 1: DuckDuckGo search with site: restriction AND base URL validation
            logger.info("⚠️ Trying DuckDuckGo search (site-specific with URL validation)...")
            result = await self._duckduckgo_search(domain, site_specific=True)
            if result and result.success:
                logger.info(f"✅ Found via DuckDuckGo (site-specific): {result.policy_url}")
                result.policy_text = self._truncate_text(result.policy_text)
                return result

            # Fallback 2: Google Search API
            logger.info("⚠️ DuckDuckGo failed. Trying Google Search API...")
            result = await self._google_search(domain)
            if result and result.success:
                logger.info(f"✅ Found via Google Search: {result.policy_url}")
                result.policy_text = self._truncate_text(result.policy_text)
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

    def _get_result_priority(self, result: DiscoveryResult) -> int:
        """
        Calculate priority score for a discovery result.
        Privacy-related results get higher priority than terms.
        """
        if not result.policy_url:
            return 0
        
        url_lower = result.policy_url.lower()
        text_lower = (result.policy_text or "")[:2000].lower()  # Check first 2000 chars
        
        # Check URL for priority keywords
        max_priority = 0
        for keyword, priority in SEARCH_PRIORITY.items():
            keyword_slug = keyword.replace(' ', '-')
            keyword_underscore = keyword.replace(' ', '_')
            keyword_joined = keyword.replace(' ', '')
            
            if any(k in url_lower for k in [keyword, keyword_slug, keyword_underscore, keyword_joined]):
                max_priority = max(max_priority, priority)
        
        # Boost if "privacy" appears prominently in the text
        if 'privacy policy' in text_lower[:500]:
            max_priority += 20
        elif 'privacy' in text_lower[:500]:
            max_priority += 10
        
        # Penalize if "terms" appears but not "privacy"
        if 'terms' in url_lower and 'privacy' not in url_lower:
            max_priority -= 30
        
        return max_priority

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
                    candidates.append((score, full_url, text))
            
            # Sort by score and try top candidates (highest score = most likely privacy)
            candidates.sort(key=lambda x: x[0], reverse=True)
            
            # Try top 10 candidates (increased from 3)
            for score, url, link_text in candidates[:10]:
                try:
                    link_resp = await client.get(url)
                    if link_resp.status_code == 200:
                        text = self._extract_text(link_resp.text)
                        
                        # Relaxed validation for scraped links - if we scored it highly, trust it more
                        if score > 50:
                            # High-scoring link - very relaxed check
                            if len(text) > 200:
                                logger.info(f"✅ Found via scrape (score={score}, text='{link_text[:30]}'): {url}")
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
        """
        Score a link based on how likely it is to be a privacy policy.
        Privacy-related links score MUCH higher than terms.
        """
        score = 0
        href_lower = href.lower()
        text_lower = text.lower()
        
        # Exact text matches (use priority from SEARCH_PRIORITY)
        for keyword, priority in SEARCH_PRIORITY.items():
            if text_lower == keyword:
                score += priority + 50  # Bonus for exact match
                break
        
        # Partial text matches with priority weighting
        for keyword, priority in SEARCH_PRIORITY.items():
            if keyword in text_lower:
                # Scale priority for partial matches
                score += int(priority * 0.5)
        
        # URL path matches with priority weighting
        for keyword, priority in SEARCH_PRIORITY.items():
            keyword_slug = keyword.replace(' ', '-')
            keyword_underscore = keyword.replace(' ', '_')
            keyword_joined = keyword.replace(' ', '')
            
            if any(k in href_lower for k in [keyword_slug, keyword_underscore, keyword_joined]):
                score += int(priority * 0.6)
                break
        
        # Heavy boost if both text AND URL contain "privacy"
        if 'privacy' in text_lower and 'privacy' in href_lower:
            score += 80
        
        # Penalize if "terms" appears but not "privacy"
        if 'terms' in text_lower and 'privacy' not in text_lower:
            score -= 20
        if 'terms' in href_lower and 'privacy' not in href_lower:
            score -= 20
        
        return max(score, 0)

    async def _duckduckgo_search(self, domain: str, site_specific: bool = True) -> Optional[DiscoveryResult]:
        """
        Search DuckDuckGo using direct HTML scraping.
        This ensures we ONLY hit DuckDuckGo and avoid the 'ddgs' library trying random backends (Wikipedia/etc).
        
        IMPORTANT: Results are validated to ensure they belong to the same base domain.
        """
        try:
            # Search terms in PRIORITY ORDER (privacy policy is most important)
            search_terms = [
                ("privacy policy", 100),      # Highest priority
                ("privacy notice", 90),
                ("privacy statement", 85),
                ("data protection", 80),
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
                                    if len(results) >= 3:  # Get top 3 for validation
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
                        
                        # CRITICAL: Validate that URL belongs to same base domain
                        if not self._is_same_base_domain(domain, url):
                            logger.debug(f"Rejecting DDG result (wrong domain): {url}")
                            continue
                        
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

    async def _google_search(self, domain: str) -> Optional[DiscoveryResult]:
        """
        Fall back to Google Search API when DuckDuckGo fails.
        Uses the GOOGLE_SEARCH_API key from environment.
        
        Note: This uses a simple scraping approach, not the official Custom Search API.
        """
        api_key = os.getenv("GOOGLE_SEARCH_API")
        if not api_key:
            logger.debug("Google Search API key not configured, skipping")
            return None
        
        try:
            # Use Google's JSON API (requires API key but no CX for basic web search)
            query = f"site:{domain} privacy policy"
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "application/json",
            }
            
            # Try using Google Custom Search JSON API
            # Note: This requires a Custom Search Engine ID (cx) for production use
            # For now, we'll try a simplified approach
            cx = os.getenv("GOOGLE_SEARCH_CX", "")
            
            if cx:
                # Official Google Custom Search API
                url = f"https://www.googleapis.com/customsearch/v1?key={api_key}&cx={cx}&q={query}&num=1"
            else:
                # Try SerpAPI-style or fallback approach
                # Using programmable search engine
                logger.debug("No GOOGLE_SEARCH_CX configured, trying alternative approach")
                # Fall back to simple web scraping of Google results
                return await self._google_search_scrape(domain)
            
            async with httpx.AsyncClient(headers=headers, timeout=10.0, verify=False) as client:
                resp = await client.get(url)
                
                if resp.status_code == 200:
                    data = resp.json()
                    items = data.get("items", [])
                    
                    if items:
                        result_url = items[0].get("link")
                        if result_url:
                            logger.info(f"🔍 Google found: {result_url}")
                            
                            # Fetch and extract the policy
                            policy_resp = await client.get(result_url)
                            if policy_resp.status_code == 200:
                                text = self._extract_text(policy_resp.text)
                                if len(text) > 200:
                                    return DiscoveryResult(
                                        success=True,
                                        policy_text=text,
                                        policy_url=str(policy_resp.url),
                                        method='google_search'
                                    )
                elif resp.status_code == 403:
                    logger.warning("Google Search API: Access denied (check API key)")
                else:
                    logger.debug(f"Google Search API returned {resp.status_code}")
                    
        except Exception as e:
            logger.error(f"Google Search failed: {e}")
        
        return None

    async def _google_search_scrape(self, domain: str) -> Optional[DiscoveryResult]:
        """
        Fallback: Scrape Google search results directly.
        Less reliable but doesn't require CX.
        """
        try:
            query = f"site:{domain} privacy policy"
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
            }
            
            async with httpx.AsyncClient(headers=headers, timeout=10.0, verify=False) as client:
                resp = await client.get(
                    f"https://www.google.com/search?q={query}&num=3",
                    follow_redirects=True
                )
                
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, 'html.parser')
                    
                    # Find result links (Google's structure varies)
                    for link in soup.select('a[href^="/url?"]'):
                        href = link.get('href', '')
                        # Extract actual URL from Google's redirect
                        if 'url?q=' in href:
                            import urllib.parse
                            parsed = urllib.parse.parse_qs(urllib.parse.urlparse(href).query)
                            if 'q' in parsed:
                                actual_url = parsed['q'][0]
                                
                                # Skip Google's own pages
                                if 'google.com' in actual_url:
                                    continue
                                
                                logger.info(f"🔍 Google scrape found: {actual_url}")
                                
                                # Fetch and extract the policy
                                try:
                                    policy_resp = await client.get(actual_url)
                                    if policy_resp.status_code == 200:
                                        text = self._extract_text(policy_resp.text)
                                        if len(text) > 200:
                                            return DiscoveryResult(
                                                success=True,
                                                policy_text=text,
                                                policy_url=str(policy_resp.url),
                                                method='google_scrape'
                                            )
                                except Exception:
                                    continue
                                    
        except Exception as e:
            logger.debug(f"Google scrape failed: {e}")
        
        return None

    def _extract_text(self, html: str) -> str:
        """Extract clean text from HTML."""
        soup = BeautifulSoup(html, 'html.parser')
        
        for tag in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 'noscript']):
            tag.decompose()
        
        text = soup.get_text(separator=' ', strip=True)
        
        import re
        text = re.sub(r'\s+', ' ', text)
        
        # Note: Final truncation happens in _truncate_text() after successful discovery
        # This initial extraction can be larger
        if len(text) > 50000:
            text = text[:50000]
        
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
