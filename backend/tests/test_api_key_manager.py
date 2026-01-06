"""
Tests for API Key Manager.
Run with: pytest tests/test_api_key_manager.py -v
"""
import pytest
import json
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone

# Import the module under test
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from api_key_manager import APIKeyManager, KEYS_FILE


# ============== Fixtures ==============

@pytest.fixture
def temp_keys_file(tmp_path):
    """Create a temporary keys.json file for testing."""
    keys_file = tmp_path / "keys.json"
    keys_file.write_text('{"keys": []}')
    return keys_file


@pytest.fixture
def fresh_manager(tmp_path, monkeypatch):
    """Create a fresh APIKeyManager instance with isolated state."""
    # Reset singleton
    APIKeyManager._instance = None
    
    # Use temp keys file
    temp_keys = tmp_path / "keys.json"
    temp_keys.write_text('{"keys": []}')
    monkeypatch.setattr('api_key_manager.KEYS_FILE', temp_keys)
    
    # No env key by default
    monkeypatch.delenv('GROQ_API_KEY', raising=False)
    
    manager = APIKeyManager()
    yield manager
    
    # Reset singleton after test
    APIKeyManager._instance = None


@pytest.fixture
def manager_with_env_key(tmp_path, monkeypatch):
    """Manager with .env key set."""
    APIKeyManager._instance = None
    
    temp_keys = tmp_path / "keys.json"
    temp_keys.write_text('{"keys": []}')
    monkeypatch.setattr('api_key_manager.KEYS_FILE', temp_keys)
    monkeypatch.setenv('GROQ_API_KEY', 'env_test_key_123456')
    
    manager = APIKeyManager()
    yield manager
    
    APIKeyManager._instance = None


@pytest.fixture
def manager_with_pool(tmp_path, monkeypatch):
    """Manager with keys already in pool."""
    APIKeyManager._instance = None
    
    temp_keys = tmp_path / "keys.json"
    temp_keys.write_text('{"keys": ["key1_abcdef", "key2_ghijkl", "key3_mnopqr"]}')
    monkeypatch.setattr('api_key_manager.KEYS_FILE', temp_keys)
    monkeypatch.delenv('GROQ_API_KEY', raising=False)
    
    manager = APIKeyManager()
    yield manager
    
    APIKeyManager._instance = None


# ============== Basic Tests ==============

class TestAPIKeyManagerBasics:
    """Test basic APIKeyManager functionality."""
    
    def test_singleton_pattern(self, fresh_manager):
        """APIKeyManager should be a singleton."""
        manager2 = APIKeyManager()
        assert fresh_manager is manager2
    
    def test_empty_pool_no_env_key(self, fresh_manager):
        """With no keys, get_current_key should return None."""
        assert fresh_manager.get_current_key() is None
        assert not fresh_manager.has_keys()
    
    def test_env_key_fallback(self, manager_with_env_key):
        """Should use .env key when pool is empty."""
        assert manager_with_env_key.has_keys()
        assert manager_with_env_key.get_current_key() == 'env_test_key_123456'
    
    def test_pool_keys_loaded(self, manager_with_pool):
        """Should load keys from keys.json."""
        assert manager_with_pool.has_keys()
        stats = manager_with_pool.get_stats()
        assert stats['total_keys'] == 3
        assert not stats['using_env_fallback']


# ============== Add Key Tests ==============

class TestAddKey:
    """Test adding keys to the pool."""
    
    def test_add_key(self, fresh_manager, tmp_path, monkeypatch):
        """Adding a key should store it in pool."""
        fresh_manager.add_key('new_key_123456')
        assert fresh_manager.has_keys()
        assert fresh_manager.get_current_key() == 'new_key_123456'
    
    def test_add_duplicate_key(self, manager_with_pool):
        """Duplicate keys should not be added."""
        initial_count = manager_with_pool.get_stats()['total_keys']
        manager_with_pool.add_key('key1_abcdef')  # Already exists
        assert manager_with_pool.get_stats()['total_keys'] == initial_count
    
    def test_add_empty_key(self, fresh_manager):
        """Empty keys should not be added."""
        fresh_manager.add_key('')
        fresh_manager.add_key('   ')
        assert not fresh_manager.has_keys()
    
    def test_add_key_persisted(self, fresh_manager, tmp_path, monkeypatch):
        """Added keys should be persisted to file."""
        temp_keys = tmp_path / "keys.json"
        monkeypatch.setattr('api_key_manager.KEYS_FILE', temp_keys)
        
        fresh_manager._save_keys()  # Ensure we're using the right file
        fresh_manager.add_key('persisted_key_123')
        
        # Read the file directly
        data = json.loads(temp_keys.read_text())
        assert 'persisted_key_123' in data.get('keys', [])


# ============== Key Rotation Tests ==============

class TestKeyRotation:
    """Test key rotation on rate limits."""
    
    def test_mark_rate_limited_rotates(self, manager_with_pool):
        """Marking current key as rate limited should rotate to next."""
        first_key = manager_with_pool.get_current_key()
        assert first_key == 'key1_abcdef'
        
        next_key = manager_with_pool.mark_rate_limited()
        assert next_key == 'key2_ghijkl'
        assert manager_with_pool.get_current_key() == 'key2_ghijkl'
    
    def test_rotation_wraps_around(self, manager_with_pool):
        """Rotation should wrap back to first key after exhausting all."""
        # Rate limit all keys
        manager_with_pool.mark_rate_limited()  # key1 -> key2
        manager_with_pool.mark_rate_limited()  # key2 -> key3
        next_key = manager_with_pool.mark_rate_limited()  # key3 -> key1 (wrap)
        
        assert next_key == 'key1_abcdef'
        assert manager_with_pool.get_current_key() == 'key1_abcdef'
    
    def test_rate_limit_clears_on_wrap(self, manager_with_pool):
        """Rate limit flags should clear when wrapping around."""
        # Rate limit all keys
        for _ in range(3):
            manager_with_pool.mark_rate_limited()
        
        # All should be cleared now
        stats = manager_with_pool.get_stats()
        assert all(not k['is_rate_limited'] for k in stats['keys'])
    
    def test_rate_limit_no_pool_no_env(self, fresh_manager):
        """Rate limiting with no keys should return None."""
        result = fresh_manager.mark_rate_limited()
        assert result is None


# ============== Stats Tests ==============

class TestStats:
    """Test statistics reporting."""
    
    def test_stats_structure(self, manager_with_pool):
        """Stats should have correct structure."""
        stats = manager_with_pool.get_stats()
        
        assert 'total_keys' in stats
        assert 'current_index' in stats
        assert 'using_env_fallback' in stats
        assert 'keys' in stats
        
        for key_info in stats['keys']:
            assert 'index' in key_info
            assert 'ending' in key_info
            assert 'is_rate_limited' in key_info
            assert 'request_count' in key_info
    
    def test_request_count_increments(self, manager_with_pool):
        """Request count should increment."""
        initial_count = manager_with_pool.get_stats()['keys'][0]['request_count']
        manager_with_pool.increment_request_count()
        assert manager_with_pool.get_stats()['keys'][0]['request_count'] == initial_count + 1


# ============== Priority Tests ==============

class TestKeyPriority:
    """Test key priority order."""
    
    def test_pool_over_env(self, tmp_path, monkeypatch):
        """Pool keys should be used before .env key."""
        APIKeyManager._instance = None
        
        temp_keys = tmp_path / "keys.json"
        temp_keys.write_text('{"keys": ["pool_key_123456"]}')
        monkeypatch.setattr('api_key_manager.KEYS_FILE', temp_keys)
        monkeypatch.setenv('GROQ_API_KEY', 'env_key_123456')
        
        manager = APIKeyManager()
        
        # Should use pool key, not env key
        assert manager.get_current_key() == 'pool_key_123456'
        assert not manager.get_stats()['using_env_fallback']
        
        APIKeyManager._instance = None
