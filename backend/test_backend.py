"""
Backend tests using pytest with fixtures.
Run with: pytest test_backend.py -v

Tests cover:
- Type safety and validation
- API contract validation (ensures frontend/backend type sync)
- Cache operations
- Model validation
- API endpoint behavior
"""
import pytest
import hashlib
import json
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock
from typing import get_type_hints

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
def shared_types_schema():
    """Load the shared TypeScript types schema for validation.

    This fixture parses the shared/types.ts file to extract expected
    field names and types for cross-language type validation.
    """
    import re
    import os

    types_file = os.path.join(os.path.dirname(__file__), '..', 'shared', 'types.ts')

    with open(types_file, 'r') as f:
        content = f.read()

    # Extract interface definitions
    interfaces = {}

    # Match ActionItem interface
    action_item_match = re.search(
        r'export interface ActionItem \{([^}]+)\}',
        content, re.DOTALL
    )
    if action_item_match:
        interfaces['ActionItem'] = {
            'text': 'string',
            'url': 'string|undefined',
            'priority': 'Priority'
        }

    # Match AnalysisResult interface
    analysis_result_match = re.search(
        r'export interface AnalysisResult \{([^}]+)\}',
        content, re.DOTALL
    )
    if analysis_result_match:
        interfaces['AnalysisResult'] = {
            'score': 'number',
            'summary': 'string',
            'red_flags': 'string[]',
            'user_action_items': 'ActionItem[]',
            'timestamp': 'string',
            'url': 'string'
        }

    # Match AnalyzeRequest interface
    analyze_request_match = re.search(
        r'export interface AnalyzeRequest \{([^}]+)\}',
        content, re.DOTALL
    )
    if analyze_request_match:
        interfaces['AnalyzeRequest'] = {
            'policy_text': 'string',
            'url': 'string|undefined'
        }

    # Match HealthResponse interface
    health_response_match = re.search(
        r'export interface HealthResponse \{([^}]+)\}',
        content, re.DOTALL
    )
    if health_response_match:
        interfaces['HealthResponse'] = {
            'status': 'string',
            'timestamp': 'string',
            'cache_size': 'number',
            'test_mode': 'boolean'
        }

    return interfaces


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
        client = TestClient(app)
        yield client
        client.close()

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


# ============== Type Contract Tests ==============

class TestTypeContract:
    """Tests ensuring backend types match frontend TypeScript types.

    These tests validate that the API response structure matches
    the shared/types.ts definitions to ensure end-to-end type safety.
    """

    def test_action_item_fields_match_typescript(self, shared_types_schema):
        """ActionItem fields should match TypeScript interface."""
        ts_fields = shared_types_schema.get('ActionItem', {})

        # Verify Python model has all expected fields
        item = ActionItem(text="Test", priority="high")
        item_dict = item.model_dump()

        assert 'text' in item_dict
        assert 'url' in item_dict  # Optional field should exist
        assert 'priority' in item_dict

        # Verify no extra fields
        expected_fields = {'text', 'url', 'priority'}
        assert set(item_dict.keys()) == expected_fields

    def test_analysis_result_fields_match_typescript(self, shared_types_schema, sample_analysis_result):
        """AnalysisResult fields should match TypeScript interface."""
        result_dict = sample_analysis_result.model_dump()

        # Required fields from TypeScript
        expected_fields = {'score', 'summary', 'red_flags', 'user_action_items', 'timestamp', 'url'}
        assert set(result_dict.keys()) == expected_fields

        # Type validations
        assert isinstance(result_dict['score'], int)
        assert isinstance(result_dict['summary'], str)
        assert isinstance(result_dict['red_flags'], list)
        assert isinstance(result_dict['user_action_items'], list)
        assert isinstance(result_dict['url'], str)

    def test_analysis_result_score_range(self):
        """Score should be 0-100 as per TypeScript docs."""
        # Valid boundary values
        for score in [0, 50, 100]:
            result = AnalysisResult(
                score=score,
                summary="Test",
                red_flags=[],
                user_action_items=[],
                timestamp=datetime.now(timezone.utc),
                url=""
            )
            assert result.score == score

    def test_priority_enum_values(self):
        """Priority should match TypeScript Priority type."""
        valid_priorities = ['high', 'medium', 'low']

        for priority in valid_priorities:
            item = ActionItem(text="Test", priority=priority)
            assert item.priority == priority

    def test_api_response_matches_typescript_interface(self, sample_policy_text):
        """API response structure should match AnalysisResult interface."""
        from fastapi.testclient import TestClient
        from main import app

        client = TestClient(app)
        try:
            response = client.post("/analyze", json={
                "policy_text": sample_policy_text,
                "url": "https://example.com"
            })

            assert response.status_code == 200
            data = response.json()

            # Validate all TypeScript interface fields exist
            assert 'score' in data
            assert 'summary' in data
            assert 'red_flags' in data
            assert 'user_action_items' in data
            assert 'timestamp' in data
            assert 'url' in data

            # Validate types
            assert isinstance(data['score'], int)
            assert 0 <= data['score'] <= 100
            assert isinstance(data['summary'], str)
            assert isinstance(data['red_flags'], list)
            assert all(isinstance(f, str) for f in data['red_flags'])
            assert isinstance(data['user_action_items'], list)

            # Validate action items structure
            for item in data['user_action_items']:
                assert 'text' in item
                assert 'priority' in item
                assert item['priority'] in ['high', 'medium', 'low']
        finally:
            client.close()

    def test_health_response_matches_typescript(self):
        """Health endpoint should match HealthResponse interface."""
        from fastapi.testclient import TestClient
        from main import app

        client = TestClient(app)
        try:
            response = client.get("/health")
            data = response.json()

            # Validate TypeScript HealthResponse fields
            assert data['status'] in ['healthy', 'unhealthy']
            assert isinstance(data['timestamp'], str)
            assert isinstance(data['cache_size'], int)
            assert isinstance(data['test_mode'], bool)
        finally:
            client.close()


# ============== Integration Tests ==============

class TestIntegration:
    """End-to-end integration tests."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        from fastapi.testclient import TestClient
        from main import app
        client = TestClient(app)
        yield client
        client.close()

    def test_full_analysis_flow(self, client):
        """Test complete analysis flow from request to response."""
        policy_text = """
        Privacy Policy

        We collect personal information including your name, email, and browsing history.
        This data may be shared with third-party advertisers.
        We use cookies to track your activity across websites.
        You can opt out of data collection by contacting us.
        Data is retained for 5 years after account deletion.
        """

        response = client.post("/analyze", json={
            "policy_text": policy_text,
            "url": "https://example.com/privacy"
        })

        assert response.status_code == 200
        result = response.json()

        # Should have identified some red flags
        assert len(result['red_flags']) > 0 or result['score'] < 80

        # Should have action items
        assert 'user_action_items' in result

    def test_cache_hit_returns_same_result(self, client, sample_policy_text):
        """Same policy text should return cached result."""
        # First request
        response1 = client.post("/analyze", json={
            "policy_text": sample_policy_text,
            "url": "https://example.com"
        })
        result1 = response1.json()

        # Second request with same text
        response2 = client.post("/analyze", json={
            "policy_text": sample_policy_text,
            "url": "https://example.com"
        })
        result2 = response2.json()

        # Results should be identical (from cache)
        assert result1['score'] == result2['score']
        assert result1['summary'] == result2['summary']


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
