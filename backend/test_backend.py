"""
Backend tests using pytest with fixtures.
Run with: pytest test_backend.py -v
"""
import pytest
import hashlib
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

from models import AnalysisResult, ActionItem
from cache import CacheManager, cache_manager


# ============== Fixtures ==============

@pytest.fixture
def sample_policy_text():
    """Sample privacy policy text for testing."""
    return "This is a sample privacy policy that collects your data and shares it with third parties."


@pytest.fixture
def sample_action_item():
    """Sample ActionItem for testing."""
    return ActionItem(
        text="Review privacy settings",
        url="https://example.com/settings",
        priority="high"
    )


@pytest.fixture
def sample_analysis_result(sample_action_item):
    """Sample AnalysisResult for testing."""
    return AnalysisResult(
        score=75,
        summary="This is a test summary",
        red_flags=["Test flag 1", "Test flag 2"],
        user_action_items=[sample_action_item],
        timestamp=datetime.now(timezone.utc),
        url="https://example.com/privacy"
    )


@pytest.fixture
def isolated_cache(tmp_path):
    """Create an isolated cache for testing."""
    # Patch the cache file path
    cache_file = tmp_path / "test_cache.json"
    with patch('cache.CACHE_FILE', cache_file):
        # Reset singleton for fresh instance
        CacheManager._instance = None
        manager = CacheManager()
        yield manager
        CacheManager._instance = None


# ============== Cache Key Tests ==============

class TestCacheKeyGeneration:
    """Tests for cache key generation."""
    
    def test_deterministic_hash(self, sample_policy_text):
        """Same text should produce same hash."""
        hash1 = cache_manager.generate_key(sample_policy_text)
        hash2 = cache_manager.generate_key(sample_policy_text)
        assert hash1 == hash2
    
    def test_different_text_different_hash(self):
        """Different text should produce different hash."""
        hash1 = cache_manager.generate_key("Policy A")
        hash2 = cache_manager.generate_key("Policy B")
        assert hash1 != hash2
    
    def test_case_insensitive(self):
        """Hash should be case-insensitive."""
        hash1 = cache_manager.generate_key("Privacy Policy")
        hash2 = cache_manager.generate_key("PRIVACY POLICY")
        assert hash1 == hash2
    
    def test_whitespace_normalized(self):
        """Hash should normalize whitespace."""
        hash1 = cache_manager.generate_key("  Privacy Policy  ")
        hash2 = cache_manager.generate_key("Privacy Policy")
        assert hash1 == hash2
    
    def test_hash_length(self, sample_policy_text):
        """SHA-256 hash should be 64 hex characters."""
        hash_key = cache_manager.generate_key(sample_policy_text)
        assert len(hash_key) == 64
        assert all(c in '0123456789abcdef' for c in hash_key)


# ============== Model Tests ==============

class TestModels:
    """Tests for Pydantic models."""
    
    def test_action_item_creation(self, sample_action_item):
        """ActionItem should be created with valid data."""
        assert sample_action_item.text == "Review privacy settings"
        assert sample_action_item.url == "https://example.com/settings"
        assert sample_action_item.priority == "high"
    
    def test_action_item_optional_url(self):
        """ActionItem url should be optional."""
        item = ActionItem(text="Test", priority="low")
        assert item.url is None
    
    def test_action_item_invalid_priority(self):
        """ActionItem should reject invalid priority."""
        with pytest.raises(ValueError):
            ActionItem(text="Test", priority="invalid")
    
    def test_analysis_result_creation(self, sample_analysis_result):
        """AnalysisResult should be created with valid data."""
        assert sample_analysis_result.score == 75
        assert len(sample_analysis_result.red_flags) == 2
        assert len(sample_analysis_result.user_action_items) == 1
    
    def test_analysis_result_score_bounds(self, sample_action_item):
        """AnalysisResult score should be 0-100."""
        with pytest.raises(ValueError):
            AnalysisResult(
                score=101,
                summary="Test",
                red_flags=[],
                user_action_items=[],
                timestamp=datetime.now(timezone.utc),
                url=""
            )
        
        with pytest.raises(ValueError):
            AnalysisResult(
                score=-1,
                summary="Test",
                red_flags=[],
                user_action_items=[],
                timestamp=datetime.now(timezone.utc),
                url=""
            )


# ============== API Endpoint Tests ==============

class TestAPIEndpoints:
    """Tests for FastAPI endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        from fastapi.testclient import TestClient
        from main import app
        with TestClient(app) as client:
            yield client
    
    def test_health_endpoint(self, client):
        """Health endpoint should return status."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "cache_size" in data
    
    def test_analyze_empty_text(self, client):
        """Analyze should reject empty policy text."""
        response = client.post("/analyze", json={
            "policy_text": "",
            "url": "https://example.com"
        })
        assert response.status_code == 422  # Validation error
    
    def test_analyze_whitespace_only(self, client):
        """Analyze should reject whitespace-only policy text."""
        response = client.post("/analyze", json={
            "policy_text": "   \n\t  ",
            "url": "https://example.com"
        })
        assert response.status_code == 422  # Validation error
    
    def test_analyze_valid_request(self, client, sample_policy_text):
        """Analyze should process valid policy text."""
        response = client.post("/analyze", json={
            "policy_text": sample_policy_text,
            "url": "https://example.com/privacy"
        })
        assert response.status_code == 200
        data = response.json()
        assert "score" in data
        assert "summary" in data
        assert "red_flags" in data
        assert "user_action_items" in data
    
    def test_analyze_missing_url(self, client, sample_policy_text):
        """Analyze should work without URL."""
        response = client.post("/analyze", json={
            "policy_text": sample_policy_text
        })
        assert response.status_code == 200


# ============== LLM Service Tests ==============

class TestLLMService:
    """Tests for LLM service."""
    
    def test_mock_analysis_generation(self, sample_policy_text):
        """Mock analysis should generate valid result."""
        from service_llm import LLMService
        service = LLMService()
        
        # Force test mode
        service.test_mode = True
        result = service.analyze_policy(sample_policy_text, "https://example.com")
        
        assert isinstance(result, AnalysisResult)
        assert 0 <= result.score <= 100
        assert len(result.summary) > 0
    
    def test_mock_analysis_concerning_keywords(self):
        """Mock analysis should detect concerning keywords."""
        from service_llm import LLMService
        service = LLMService()
        service.test_mode = True
        
        concerning_text = "We sell your data to third parties and retain it indefinitely. We track you across websites."
        result = service.analyze_policy(concerning_text, "")
        
        # Should have lower score due to concerning keywords
        assert result.score <= 70
        assert len(result.red_flags) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
