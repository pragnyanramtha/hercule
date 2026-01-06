"""
Cache module for Hercule.
Handles in-memory caching with JSON file persistence.
Supports local (JSON file) and cloud (Cosmos DB) storage backends.
"""
import json
import hashlib
import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any, Union
from datetime import datetime, timedelta, timezone
from threading import Lock

logger = logging.getLogger("hercule-api.cache")

from models import AnalysisResult

# Cache configuration
CACHE_FILE = Path(__file__).parent / "cache.json"
CACHE_TTL_DAYS = 30


class CacheManager:
    """
    Thread-safe cache manager with in-memory caching and JSON file persistence.
    Uses SHA-256 hash of normalized policy text as cache key.
    """

    _instance: Optional['CacheManager'] = None
    _lock = Lock()

    def __new__(cls) -> 'CacheManager':
        """Singleton pattern for cache manager."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize cache manager with in-memory cache."""
        if self._initialized:
            return

        self._memory_cache: Dict[str, Dict[str, Any]] = {}
        self._file_lock = Lock()
        self._load_from_file()
        self._initialized = True

    def _load_from_file(self) -> None:
        """Load cache from JSON file into memory."""
        if not CACHE_FILE.exists():
            self._memory_cache = {}
            return

        try:
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                self._memory_cache = json.load(f)
        except json.JSONDecodeError as e:
            print(f"Cache file corrupted, resetting: {e}")
            self._memory_cache = {}
        except IOError as e:
            print(f"Error reading cache file: {e}")
            self._memory_cache = {}

    def _save_to_file(self) -> None:
        """Persist in-memory cache to JSON file."""
        with self._file_lock:
            try:
                with open(CACHE_FILE, 'w', encoding='utf-8') as f:
                    json.dump(self._memory_cache, f, indent=2, default=str)
            except IOError as e:
                print(f"Error saving cache file: {e}")

    @staticmethod
    def generate_key(policy_text: str) -> str:
        """
        Generate SHA-256 hash of normalized policy text.

        Args:
            policy_text: The privacy policy text

        Returns:
            SHA-256 hash as hexadecimal string
        """
        normalized = policy_text.strip().lower()
        return hashlib.sha256(normalized.encode('utf-8')).hexdigest()
    
    @staticmethod
    def generate_url_key(url: str) -> str:
        """
        Generate SHA-256 hash of normalized URL/domain.
        Used for cache-first lookup before discovery.

        Args:
            url: The URL to generate key for

        Returns:
            SHA-256 hash as hexadecimal string prefixed with 'url:'
        """
        from urllib.parse import urlparse
        
        # Parse URL and extract domain
        if not url.startswith('http'):
            url = f'https://{url}'
        
        parsed = urlparse(url)
        domain = parsed.netloc.lower().replace('www.', '')
        
        # Include path if it's not just root (for specific policy pages)
        path = parsed.path.strip('/')
        if path:
            normalized = f"{domain}/{path}"
        else:
            normalized = domain
        
        # Prefix with 'url:' to distinguish from text-based keys
        return 'url:' + hashlib.sha256(normalized.encode('utf-8')).hexdigest()

    def get(self, text_hash: str) -> Optional[AnalysisResult]:
        """
        Retrieve cached analysis result if it exists and is valid.

        Args:
            text_hash: SHA-256 hash of the policy text

        Returns:
            AnalysisResult if cache hit and valid, None otherwise
        """
        if text_hash not in self._memory_cache:
            return None

        cached_entry = self._memory_cache[text_hash]

        # Check if cache is still valid (within TTL)
        try:
            cached_timestamp = datetime.fromisoformat(cached_entry["timestamp"])
            if datetime.now(timezone.utc) - cached_timestamp > timedelta(days=CACHE_TTL_DAYS):
                # Expired - remove from cache
                del self._memory_cache[text_hash]
                self._save_to_file()
                return None
        except (KeyError, ValueError) as e:
            print(f"Invalid cache entry timestamp: {e}")
            return None

        # Convert cached result to AnalysisResult model
        try:
            return AnalysisResult(**cached_entry["result"])
        except (KeyError, ValueError) as e:
            print(f"Error parsing cached result: {e}")
            return None

    def set(self, text_hash: str, result: AnalysisResult) -> None:
        """
        Store analysis result in cache.

        Args:
            text_hash: SHA-256 hash of the policy text
            result: AnalysisResult to cache
        """
        self._memory_cache[text_hash] = {
            "result": result.model_dump(mode='json'),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "text_hash": text_hash
        }
        self._save_to_file()

    def clear(self) -> None:
        """Clear all cached entries."""
        self._memory_cache = {}
        self._save_to_file()

    def size(self) -> int:
        """Return number of cached entries."""
        return len(self._memory_cache)


def get_cache_manager() -> Union[CacheManager, 'CosmosDBCacheManager']:
    """
    Factory function to get appropriate cache manager based on environment.
    
    Returns:
        CacheManager for local storage, CosmosDBCacheManager for cloud storage.
    """
    storage_mode = os.getenv("STORAGE_MODE", "local").lower()
    
    if storage_mode == "cosmos":
        try:
            from cache_cosmos import CosmosDBCacheManager
            logger.info("🌐 Using Cosmos DB cache backend")
            return CosmosDBCacheManager()
        except ImportError as e:
            logger.warning(f"Failed to import Cosmos DB cache: {e}. Falling back to local.")
        except Exception as e:
            logger.warning(f"Failed to initialize Cosmos DB cache: {e}. Falling back to local.")
    
    logger.info("📁 Using local JSON file cache backend")
    return CacheManager()


# Global cache instance - uses factory to select backend
cache_manager = get_cache_manager()

