"""
Discovery Service Tests
Tests for privacy policy discovery functionality.

Run with: uv run pytest tests/test_discovery.py -v
"""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
import asyncio

# Import the service
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from service_discovery import DiscoveryService, DiscoveryResult, SEARCH_PRIORITY


@pytest.fixture
def discovery_service():
    """Create a fresh DiscoveryService instance."""
    return DiscoveryService()


# ============== Base Domain Extraction Tests ==============

class TestBaseDomainExtraction:
    """Tests for _get_base_domain method."""

    def test_simple_subdomain(self, discovery_service):
        """Should extract base domain from simple subdomain."""
        assert discovery_service._get_base_domain("docs.python.org") == "python.org"
        assert discovery_service._get_base_domain("sub.example.com") == "example.com"
        assert discovery_service._get_base_domain("api.github.com") == "github.com"

    def test_deep_subdomain(self, discovery_service):
        """Should extract base domain from deep subdomain."""
        assert discovery_service._get_base_domain("a.b.c.example.com") == "example.com"
        assert discovery_service._get_base_domain("deep.nested.sub.domain.org") == "domain.org"

    def test_special_tld(self, discovery_service):
        """Should handle special TLDs like .co.uk, .com.au."""
        assert discovery_service._get_base_domain("sub.example.co.uk") == "example.co.uk"
        assert discovery_service._get_base_domain("sub.company.com.au") == "company.com.au"
        assert discovery_service._get_base_domain("api.service.org.uk") == "service.org.uk"

    def test_already_base_domain(self, discovery_service):
        """Should return same domain if already base domain."""
        assert discovery_service._get_base_domain("example.com") == "example.com"
        assert discovery_service._get_base_domain("python.org") == "python.org"

    def test_www_prefix(self, discovery_service):
        """Should strip www. prefix."""
        assert discovery_service._get_base_domain("www.example.com") == "example.com"
        assert discovery_service._get_base_domain("www.sub.example.com") == "example.com"


# ============== URL Validation Tests ==============

class TestURLValidation:
    """Tests for _is_same_base_domain method."""

    def test_same_domain(self, discovery_service):
        """Should return True for same base domain."""
        assert discovery_service._is_same_base_domain(
            "docs.python.org", 
            "https://python.org/privacy"
        ) is True
        
        assert discovery_service._is_same_base_domain(
            "sub.example.com",
            "https://example.com/privacy-policy"
        ) is True

    def test_different_domain(self, discovery_service):
        """Should return False for different base domain."""
        # This is the key test - DDG returning wrong domain should be rejected
        assert discovery_service._is_same_base_domain(
            "python.org",
            "https://fastly.com/privacy"
        ) is False
        
        assert discovery_service._is_same_base_domain(
            "example.com",
            "https://otherdomain.com/privacy"
        ) is False

    def test_subdomain_match(self, discovery_service):
        """Should match subdomains to their base domain."""
        assert discovery_service._is_same_base_domain(
            "api.example.com",
            "https://www.example.com/privacy"
        ) is True
        
        assert discovery_service._is_same_base_domain(
            "docs.python.org",
            "https://www.python.org/psf/privacy/"
        ) is True


# ============== Text Truncation Tests ==============

class TestTextTruncation:
    """Tests for _truncate_text method."""

    def test_no_truncation_under_threshold(self, discovery_service):
        """Should not truncate text under 10k chars."""
        text = "x" * 9000  # Under 10k threshold
        result = discovery_service._truncate_text(text)
        assert len(result) == 9000
        assert "[Text truncated" not in result

    def test_truncation_over_threshold(self, discovery_service):
        """Should truncate text over 10k chars to 8k."""
        text = "x" * 15000  # Over 10k threshold
        result = discovery_service._truncate_text(text)
        assert "[Text truncated at 8,000 characters]" in result
        # 8000 chars + truncation message
        assert len(result) < 10000

    def test_exact_threshold(self, discovery_service):
        """Should not truncate text at exactly 10k chars."""
        text = "x" * 10000
        result = discovery_service._truncate_text(text)
        assert len(result) == 10000
        assert "[Text truncated" not in result


# ============== Link Scoring Tests ==============

class TestLinkScoring:
    """Tests for _score_link method."""

    def test_privacy_scores_higher_than_terms(self, discovery_service):
        """Privacy links should score higher than terms links."""
        privacy_score = discovery_service._score_link("privacy policy", "/privacy-policy")
        terms_score = discovery_service._score_link("terms of service", "/terms")
        
        assert privacy_score > terms_score, "Privacy should score higher than terms"

    def test_exact_match_bonus(self, discovery_service):
        """Exact text match should get bonus score."""
        exact_match = discovery_service._score_link("privacy policy", "/privacy")
        partial_match = discovery_service._score_link("our privacy policy page", "/privacy")
        
        assert exact_match > partial_match, "Exact match should score higher"

    def test_url_and_text_match_boost(self, discovery_service):
        """Both URL and text containing privacy should get boost."""
        both_match = discovery_service._score_link("privacy policy", "/privacy-policy")
        text_only = discovery_service._score_link("privacy policy", "/legal")
        
        assert both_match > text_only, "Both matching should score higher"

    def test_terms_penalty_without_privacy(self, discovery_service):
        """Terms without privacy should be penalized."""
        terms_only = discovery_service._score_link("terms of service", "/terms")
        privacy_score = discovery_service._score_link("privacy", "/privacy")
        
        assert privacy_score > terms_only


# ============== Result Priority Tests ==============

class TestResultPriority:
    """Tests for _get_result_priority method."""

    def test_privacy_url_priority(self, discovery_service):
        """Privacy policy URL should have high priority."""
        privacy_result = DiscoveryResult(
            success=True,
            policy_text="Privacy policy content...",
            policy_url="https://example.com/privacy-policy",
            method="path:/privacy-policy"
        )
        
        terms_result = DiscoveryResult(
            success=True,
            policy_text="Terms of service content...",
            policy_url="https://example.com/terms",
            method="path:/terms"
        )
        
        privacy_priority = discovery_service._get_result_priority(privacy_result)
        terms_priority = discovery_service._get_result_priority(terms_result)
        
        assert privacy_priority > terms_priority

    def test_privacy_text_boost(self, discovery_service):
        """Privacy policy text at start should boost priority."""
        privacy_at_start = DiscoveryResult(
            success=True,
            policy_text="Privacy Policy. We collect data...",
            policy_url="https://example.com/legal",
            method="scrape:root"
        )
        
        no_privacy = DiscoveryResult(
            success=True,
            policy_text="Terms and conditions apply...",
            policy_url="https://example.com/legal",
            method="scrape:root"
        )
        
        assert discovery_service._get_result_priority(privacy_at_start) > \
               discovery_service._get_result_priority(no_privacy)


# ============== Search Priority Config Tests ==============

class TestSearchPriorityConfig:
    """Tests for SEARCH_PRIORITY constant."""

    def test_privacy_has_higher_priority(self):
        """Privacy-related terms should have higher priority than terms."""
        assert SEARCH_PRIORITY["privacy policy"] > SEARCH_PRIORITY["terms of service"]
        assert SEARCH_PRIORITY["privacy"] > SEARCH_PRIORITY["terms"]
        assert SEARCH_PRIORITY["data protection"] > SEARCH_PRIORITY["user agreement"]

    def test_privacy_policy_is_highest(self):
        """Privacy policy should be the highest priority."""
        max_priority = max(SEARCH_PRIORITY.values())
        assert SEARCH_PRIORITY["privacy policy"] == max_priority


# ============== Integration Tests ==============

class TestDiscoveryIntegration:
    """Integration tests for the discovery service."""

    @pytest.mark.asyncio
    async def test_looks_like_privacy_policy(self, discovery_service):
        """Should correctly identify privacy policy content."""
        # Need 3+ keywords from: privacy, personal data, personal information,
        # collect, cookies, third party, gdpr, ccpa, opt out, etc.
        privacy_text = """
        Privacy Policy
        
        We collect personal data including your name, email address, and browsing history.
        This personal information may be shared with third-party advertisers.
        We use cookies to track your activity across websites.
        You have the right to opt out of data collection at any time.
        Data retention policy: 5 years. We comply with GDPR and CCPA.
        Your rights include access to your data, deletion, and disclosure requests.
        We take security seriously and protect your information.
        """ * 2  # Repeat to ensure > 500 chars
        
        assert discovery_service._looks_like_privacy_policy(privacy_text) is True

    @pytest.mark.asyncio
    async def test_not_privacy_policy(self, discovery_service):
        """Should correctly reject non-privacy content."""
        non_privacy_text = """
        Welcome to our website!
        
        Click here to shop our latest products.
        Free shipping on orders over $50.
        """
        
        assert discovery_service._looks_like_privacy_policy(non_privacy_text) is False

    @pytest.mark.asyncio
    async def test_too_short_text_rejected(self, discovery_service):
        """Should reject text that's too short."""
        short_text = "Privacy policy: we collect data."
        
        assert discovery_service._looks_like_privacy_policy(short_text) is False


# ============== Mock Discovery Tests ==============

class TestMockDiscovery:
    """Tests using mocked HTTP responses."""

    @pytest.mark.asyncio
    async def test_path_check_success(self, discovery_service):
        """Should successfully find privacy policy at common path."""
        import httpx
        
        # Create a mock client that we pass directly
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        
        # Create mock response with enough privacy keywords
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {'content-type': 'text/html'}
        mock_response.text = """
        <html><body>
        <h1>Privacy Policy</h1>
        <p>We collect personal data and personal information from users.
        This data may be shared with third parties and third-party advertisers.
        We use cookies for tracking your activity across our website.
        You can opt out by contacting us. You have the right to opt-out.
        Data protection is important to us. We are GDPR and CCPA compliant.
        Your rights include data access, deletion, and disclosure.
        We take security measures to protect your information.
        Data retention: We keep your data for 2 years.
        How we use your data: analytics and personalization.</p>
        </body></html>
        """
        mock_response.url = "https://example.com/privacy"
        
        # Make get() return the mock response as an awaitable
        mock_client.get = AsyncMock(return_value=mock_response)
        
        result = await discovery_service._check_path_and_extract(
            mock_client, 
            "https://example.com", 
            "/privacy"
        )
        
        assert result is not None
        assert result.success is True
        assert "privacy" in result.policy_url.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
