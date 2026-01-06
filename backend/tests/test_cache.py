"""
Tests for Cache Manager including URL-based caching.
Run with: pytest tests/test_cache.py -v
"""
import pytest
import json
import hashlib
from pathlib import Path
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from cache import CacheManager, get_cache_manager
from models import AnalysisResult, ActionItem


# ============== Fixtures ==============

@pytest.fixture
def sample_result():
    """Create a sample AnalysisResult for testing."""
    return AnalysisResult(
        score=75,
        summary="Test policy summary",
        red_flags=["Flag 1", "Flag 2"],
        user_action_items=[
            ActionItem(text="Action 1", priority="high"),
            ActionItem(text="Action 2", priority="low"),
        ],
        timestamp=datetime.now(timezone.utc),
        url="https://example.com/privacy"
    )


@pytest.fixture
def isolated_cache(tmp_path, monkeypatch):
    """Create an isolated CacheManager for testing."""
    # Reset singleton
    CacheManager._instance = None
    
    # Use temp cache file
    temp_cache = tmp_path / "cache.json"
    monkeypatch.setattr('cache.CACHE_FILE', temp_cache)
    
    manager = CacheManager()
    yield manager
    
    # Reset singleton
    CacheManager._instance = None


# ============== URL Key Generation Tests ==============

class TestURLKeyGeneration:
    """Tests for URL-based cache key generation."""
    
    def test_generate_url_key_basic(self):
        """URL key should be generated correctly."""
        key = CacheManager.generate_url_key("https://example.com")
        assert key.startswith("url:")
        assert len(key) == 4 + 64  # 'url:' + 64 hex chars
    
    def test_generate_url_key_strips_www(self):
        """www. should be stripped from domain."""
        key1 = CacheManager.generate_url_key("https://www.example.com")
        key2 = CacheManager.generate_url_key("https://example.com")
        assert key1 == key2
    
    def test_generate_url_key_case_insensitive(self):
        """Domain should be case insensitive."""
        key1 = CacheManager.generate_url_key("https://EXAMPLE.COM")
        key2 = CacheManager.generate_url_key("https://example.com")
        assert key1 == key2
    
    def test_generate_url_key_includes_path(self):
        """Path should be included in key."""
        key1 = CacheManager.generate_url_key("https://example.com/privacy")
        key2 = CacheManager.generate_url_key("https://example.com")
        assert key1 != key2
    
    def test_generate_url_key_without_scheme(self):
        """URL without scheme should work."""
        key = CacheManager.generate_url_key("example.com")
        assert key.startswith("url:")
    
    def test_generate_url_key_deterministic(self):
        """Same URL should produce same key."""
        key1 = CacheManager.generate_url_key("https://test.com/privacy")
        key2 = CacheManager.generate_url_key("https://test.com/privacy")
        assert key1 == key2
    
    def test_url_key_different_from_text_key(self):
        """URL key should be distinguishable from text key."""
        url_key = CacheManager.generate_url_key("https://example.com")
        text_key = CacheManager.generate_key("https://example.com")
        
        assert url_key.startswith("url:")
        assert not text_key.startswith("url:")


# ============== Cache Operations Tests ==============

class TestCacheOperations:
    """Tests for cache get/set operations."""
    
    def test_set_and_get(self, isolated_cache, sample_result):
        """Should be able to set and get a result."""
        key = "test_key_123"
        isolated_cache.set(key, sample_result)
        
        retrieved = isolated_cache.get(key)
        assert retrieved is not None
        assert retrieved.score == sample_result.score
        assert retrieved.summary == sample_result.summary
    
    def test_get_nonexistent(self, isolated_cache):
        """Getting nonexistent key should return None."""
        result = isolated_cache.get("nonexistent_key")
        assert result is None
    
    def test_cache_with_url_key(self, isolated_cache, sample_result):
        """Should work with URL-based keys."""
        url_key = CacheManager.generate_url_key("https://example.com")
        isolated_cache.set(url_key, sample_result)
        
        retrieved = isolated_cache.get(url_key)
        assert retrieved is not None
        assert retrieved.url == sample_result.url
    
    def test_cache_persistence(self, tmp_path, sample_result, monkeypatch):
        """Cache should persist to file."""
        CacheManager._instance = None
        temp_cache = tmp_path / "cache.json"
        monkeypatch.setattr('cache.CACHE_FILE', temp_cache)
        
        # Create manager and set value
        manager1 = CacheManager()
        manager1.set("persist_test", sample_result)
        
        # Verify file exists with data
        assert temp_cache.exists()
        data = json.loads(temp_cache.read_text())
        assert "persist_test" in data
        
        CacheManager._instance = None
    
    def test_cache_size(self, isolated_cache, sample_result):
        """Size should track number of entries."""
        assert isolated_cache.size() == 0
        
        isolated_cache.set("key1", sample_result)
        assert isolated_cache.size() == 1
        
        isolated_cache.set("key2", sample_result)
        assert isolated_cache.size() == 2
    
    def test_cache_clear(self, isolated_cache, sample_result):
        """Clear should remove all entries."""
        isolated_cache.set("key1", sample_result)
        isolated_cache.set("key2", sample_result)
        assert isolated_cache.size() == 2
        
        isolated_cache.clear()
        assert isolated_cache.size() == 0


# ============== TTL Tests ==============

class TestCacheTTL:
    """Tests for cache TTL expiration."""
    
    def test_expired_entry_returns_none(self, isolated_cache, sample_result, monkeypatch):
        """Expired entries should return None."""
        # Set TTL to 1 day for testing
        monkeypatch.setattr('cache.CACHE_TTL_DAYS', 1)
        
        # Set a result
        isolated_cache.set("ttl_test", sample_result)
        
        # Mock the timestamp to be 2 days ago
        old_timestamp = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
        isolated_cache._memory_cache["ttl_test"]["timestamp"] = old_timestamp
        
        # Should return None (expired)
        result = isolated_cache.get("ttl_test")
        assert result is None


# ============== Factory Tests ==============

class TestCacheFactory:
    """Tests for cache backend factory."""
    
    def test_factory_returns_local_by_default(self, monkeypatch):
        """Factory should return local cache by default."""
        CacheManager._instance = None
        monkeypatch.delenv('STORAGE_MODE', raising=False)
        
        manager = get_cache_manager()
        assert isinstance(manager, CacheManager)
        
        CacheManager._instance = None
    
    def test_factory_local_mode(self, monkeypatch):
        """Factory should return local cache when mode is 'local'."""
        CacheManager._instance = None
        monkeypatch.setenv('STORAGE_MODE', 'local')
        
        manager = get_cache_manager()
        assert isinstance(manager, CacheManager)
        
        CacheManager._instance = None
    
    def test_factory_cosmos_mode_fallback(self, monkeypatch):
        """Factory should fallback to local when cosmos fails."""
        CacheManager._instance = None
        monkeypatch.setenv('STORAGE_MODE', 'cosmos')
        # Don't set COSMOS_CONNECTION_STRING, so it will fail
        monkeypatch.delenv('COSMOS_CONNECTION_STRING', raising=False)
        
        # Should fallback to local
        manager = get_cache_manager()
        assert isinstance(manager, CacheManager)
        
        CacheManager._instance = None
