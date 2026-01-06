"""
API Key Manager for Hercule.
Handles API key storage, rotation, and rate limit handling.

Priority order:
1. User-provided key (also saved to keys.json for pool)
2. Keys from keys.json (with rotation on rate limits)
3. Fallback to .env GROQ_API_KEY (only if keys.json is empty)
"""
import json
import os
import logging
from pathlib import Path
from threading import Lock
from typing import Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timezone

logger = logging.getLogger("hercule-api.keys")

KEYS_FILE = Path(__file__).parent / "keys.json"


@dataclass
class KeyStatus:
    """Status of an API key."""
    key: str
    is_rate_limited: bool = False
    rate_limited_at: Optional[datetime] = None
    request_count: int = 0


class APIKeyManager:
    """
    Manages API keys with rotation and rate limit handling.
    
    - Stores user-provided keys in keys.json
    - Rotates to next key on 429 errors
    - Wraps around to first key after exhausting all keys
    - Falls back to .env key only if keys.json is empty
    """
    
    _instance: Optional['APIKeyManager'] = None
    _lock = Lock()
    
    def __new__(cls) -> 'APIKeyManager':
        """Singleton pattern for key manager."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize key manager."""
        if self._initialized:
            return
        
        self._keys: List[KeyStatus] = []
        self._current_index: int = 0
        self._file_lock = Lock()
        self._env_key = os.getenv("GROQ_API_KEY")
        
        # Load existing keys from file
        self._load_keys()
        self._initialized = True
        
        logger.info(f"🔑 API Key Manager initialized with {len(self._keys)} keys from keys.json")
        if self._env_key and len(self._keys) == 0:
            logger.info("   Fallback: .env GROQ_API_KEY available")
    
    def _load_keys(self) -> None:
        """Load keys from keys.json file."""
        if not KEYS_FILE.exists():
            self._keys = []
            return
        
        try:
            with open(KEYS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                keys_list = data.get("keys", [])
                self._keys = [KeyStatus(key=k) for k in keys_list if k]
                # Remove duplicates while preserving order
                seen = set()
                unique_keys = []
                for ks in self._keys:
                    if ks.key not in seen:
                        seen.add(ks.key)
                        unique_keys.append(ks)
                self._keys = unique_keys
        except json.JSONDecodeError as e:
            logger.warning(f"keys.json corrupted, resetting: {e}")
            self._keys = []
        except IOError as e:
            logger.warning(f"Error reading keys.json: {e}")
            self._keys = []
    
    def _save_keys(self) -> None:
        """Save keys to keys.json file."""
        with self._file_lock:
            try:
                keys_list = [ks.key for ks in self._keys]
                with open(KEYS_FILE, 'w', encoding='utf-8') as f:
                    json.dump({"keys": keys_list}, f, indent=2)
            except IOError as e:
                logger.error(f"Error saving keys.json: {e}")
    
    def add_key(self, key: str) -> None:
        """
        Add a user-provided key to the pool.
        
        Args:
            key: The API key to add
        """
        if not key or not key.strip():
            return
        
        key = key.strip()
        
        # Check if key already exists
        for ks in self._keys:
            if ks.key == key:
                logger.debug(f"Key already exists in pool (ending ...{key[-6:]})")
                return
        
        # Add new key
        self._keys.append(KeyStatus(key=key))
        self._save_keys()
        logger.info(f"🔑 Added new API key to pool (ending ...{key[-6:]}), total keys: {len(self._keys)}")
    
    def get_current_key(self) -> Optional[str]:
        """
        Get the current API key to use.
        
        Returns:
            API key string, or None if no keys available
        """
        # If we have keys in the pool, use them
        if self._keys:
            if self._current_index >= len(self._keys):
                self._current_index = 0
            return self._keys[self._current_index].key
        
        # Fall back to .env key only if no keys in pool
        if self._env_key:
            return self._env_key
        
        return None
    
    def mark_rate_limited(self) -> Optional[str]:
        """
        Mark current key as rate limited and rotate to next.
        
        Returns:
            The next key to use, or None if all exhausted
        """
        if not self._keys:
            # Using .env key, can't rotate
            logger.warning("Rate limited on .env key, no rotation available")
            return None
        
        # Mark current key as rate limited
        current_key = self._keys[self._current_index]
        current_key.is_rate_limited = True
        current_key.rate_limited_at = datetime.now(timezone.utc)
        
        old_index = self._current_index
        
        # Try to find a non-rate-limited key
        for _ in range(len(self._keys)):
            self._current_index = (self._current_index + 1) % len(self._keys)
            next_key = self._keys[self._current_index]
            
            # If we've wrapped back to start, clear all rate limits and try again
            if self._current_index == old_index:
                logger.warning("All keys rate limited, resetting and wrapping to first key")
                for ks in self._keys:
                    ks.is_rate_limited = False
                    ks.rate_limited_at = None
                self._current_index = 0
                return self._keys[0].key
            
            if not next_key.is_rate_limited:
                logger.info(f"🔄 Rotating to key {self._current_index + 1}/{len(self._keys)} (ending ...{next_key.key[-6:]})")
                return next_key.key
        
        # All keys exhausted, wrap back to first
        logger.warning("All keys rate limited, wrapping to first key")
        self._current_index = 0
        for ks in self._keys:
            ks.is_rate_limited = False
        return self._keys[0].key
    
    def increment_request_count(self) -> None:
        """Increment request count for current key."""
        if self._keys and self._current_index < len(self._keys):
            self._keys[self._current_index].request_count += 1
    
    def get_stats(self) -> dict:
        """Get statistics about the key pool."""
        return {
            "total_keys": len(self._keys),
            "current_index": self._current_index,
            "using_env_fallback": len(self._keys) == 0 and self._env_key is not None,
            "keys": [
                {
                    "index": i,
                    "ending": f"...{ks.key[-6:]}" if len(ks.key) > 6 else "***",
                    "is_rate_limited": ks.is_rate_limited,
                    "request_count": ks.request_count
                }
                for i, ks in enumerate(self._keys)
            ]
        }
    
    def has_keys(self) -> bool:
        """Check if any keys are available (pool or .env)."""
        return len(self._keys) > 0 or self._env_key is not None


# Global instance
api_key_manager = APIKeyManager()
