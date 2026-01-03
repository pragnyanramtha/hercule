import pytest
from unittest.mock import MagicMock, patch
from service_discovery import DiscoveryService

@pytest.fixture
def discovery_service():
    return DiscoveryService()

def test_get_domain(discovery_service):
    assert discovery_service._get_domain("https://example.com/foo") == "example.com"
    assert discovery_service._get_domain("http://sub.test.co.uk") == "sub.test.co.uk"
    assert discovery_service._get_domain("example.com") == "example.com"

@patch('requests.get')
def test_soft_discovery_homepage_link(mock_get, discovery_service):
    # Mock homepage response with a privacy link
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = """
    <html>
        <body>
            <footer>
                <a href="/privacy-policy">Privacy Policy</a>
            </footer>
        </body>
    </html>
    """
    mock_get.return_value = mock_response

    url = discovery_service._soft_discovery("https://example.com")
    assert url == "https://example.com/privacy-policy"

@patch('requests.get')
@patch('requests.head')
def test_soft_discovery_standard_path(mock_head, mock_get, discovery_service):
    # Mock homepage with no links
    mock_get.return_value.status_code = 200
    mock_get.return_value.text = "<html><body>No links here</body></html>"
    
    # Mock HEAD request to find /privacy
    def side_effect(url, **kwargs):
        resp = MagicMock()
        if url.endswith("/privacy"):
            resp.status_code = 200
        else:
            resp.status_code = 404
        return resp
        
    mock_head.side_effect = side_effect

    url = discovery_service._soft_discovery("https://example.com")
    assert url == "https://example.com/privacy"

@patch('service_discovery.DDGS')
def test_ddg_search(mock_ddgs_cls, discovery_service):
    # Mock DDG results
    mock_ddgs_instance = mock_ddgs_cls.return_value
    mock_ddgs_instance.__enter__.return_value = mock_ddgs_instance
    mock_ddgs_instance.text.return_value = [
        {'href': 'https://example.com/generated-policy', 'title': 'Privacy Policy'}
    ]

    url = discovery_service._search_ddg("example.com")
    assert url == "https://example.com/generated-policy"

@patch('service_discovery.DiscoveryService._soft_discovery')
@patch('service_discovery.DiscoveryService._search_ddg')
def test_find_policy_flow(mock_search, mock_soft, discovery_service):
    # Test soft discovery success
    mock_soft.return_value = "https://example.com/soft"
    assert discovery_service.find_policy("https://example.com") == "https://example.com/soft"
    mock_search.assert_not_called()

    # Test soft failure, ddg success
    mock_soft.return_value = None
    mock_search.return_value = "https://example.com/ddg"
    assert discovery_service.find_policy("https://example.com") == "https://example.com/ddg"
