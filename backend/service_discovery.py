import logging
import requests
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
            '/privacy',
            '/privacy-policy',
            '/privacy_policy',
            '/legal',
            '/legal/privacy',
            '/terms',
            '/terms-of-service',
            '/tos'
        ]
        self.keywords = ['privacy', 'terms', 'legal', 'policy', 'tos', 'conditions']

    def find_policy(self, url: str) -> Optional[str]:
        """
        Try to find the privacy policy URL for a given website.
        Steps:
        1. Soft Discovery: Check homepage links and standard paths.
        2. Hackathon Way: Use DuckDuckGo search.
        """
        try:
            domain = self._get_domain(url)
            base_url = f"https://{domain}"
            
            logger.info(f"🔍 Starting policy discovery for {domain}")

            # Step 1: Soft Discovery
            policy_url = self._soft_discovery(base_url)
            if policy_url:
                logger.info(f"✅ Found policy via Soft Discovery: {policy_url}")
                return policy_url

            # Step 2: Hackathon Way (DuckDuckGo)
            policy_url = self._search_ddg(domain)
            if policy_url:
                logger.info(f"✅ Found policy via DuckDuckGo: {policy_url}")
                return policy_url

            logger.warning(f"❌ Could not find policy for {domain}")
            return None

        except Exception as e:
            logger.error(f"Error in discovery service: {e}")
            return None

    def _get_domain(self, url: str) -> str:
        parsed = urlparse(url)
        # Handle cases where url is just "example.com"
        if not parsed.netloc:
             parsed = urlparse(f"https://{url}")
        return parsed.netloc

    def _soft_discovery(self, base_url: str) -> Optional[str]:
        """Scan homepage and common paths."""
        try:
            # 1. Scan Homepage
            try:
                response = requests.get(base_url, headers=self.headers, timeout=5)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Look for links with keywords
                    for a in soup.find_all('a', href=True):
                        text = a.get_text().lower()
                        href = a['href'].lower()
                        
                        if any(k in text for k in self.keywords) or any(k in href for k in self.keywords):
                            full_url = urljoin(base_url, a['href'])
                            # Basic validation: ensure it's http(s)
                            if full_url.startswith('http'):
                                return full_url
            except Exception as e:
                logger.warning(f"Homepage scan failed: {e}")

            # 2. Check Standard Paths
            for path in self.common_paths:
                target_url = urljoin(base_url, path)
                try:
                    response = requests.head(target_url, headers=self.headers, timeout=3, allow_redirects=True)
                    if response.status_code == 200:
                        return target_url
                except:
                    continue
            
            return None

        except Exception as e:
            logger.error(f"Soft discovery error: {e}")
            return None

    def _search_ddg(self, domain: str) -> Optional[str]:
        """Use DuckDuckGo to find the policy."""
        try:
            query = f"site:{domain} privacy policy"
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=1))
                if results:
                    return results[0]['href']
        except Exception as e:
            logger.error(f"DuckDuckGo search error: {e}")
        return None
