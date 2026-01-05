"""
Pytest configuration and shared fixtures.
"""
import sys
import os

# Add parent directory to path so tests can import backend modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from datetime import datetime, timezone


@pytest.fixture
def sample_policy_text():
    """Sample privacy policy text for testing."""
    return "This is a sample privacy policy that collects your data and shares it with third parties."


@pytest.fixture
def sample_privacy_policy_full():
    """Full sample privacy policy text."""
    return """
    Privacy Policy
    
    We collect personal information including your name, email, and browsing history.
    This data may be shared with third-party advertisers.
    We use cookies to track your activity across websites.
    You can opt out of data collection by contacting us.
    Data is retained for 5 years after account deletion.
    
    Your Rights:
    - Access your data
    - Delete your data  
    - Opt out of marketing
    
    GDPR and CCPA compliant.
    """
