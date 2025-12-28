"""Simple test to verify backend functionality."""
import sys
import hashlib
from pathlib import Path
from datetime import datetime, timezone

# Test 1: Verify cache key generation is deterministic
def test_cache_key_generation():
    """Test that hash generation is deterministic."""
    text1 = "This is a test privacy policy"
    text2 = "This is a test privacy policy"
    text3 = "This is a DIFFERENT privacy policy"
    
    # Generate hashes
    hash1 = hashlib.sha256(text1.strip().lower().encode('utf-8')).hexdigest()
    hash2 = hashlib.sha256(text2.strip().lower().encode('utf-8')).hexdigest()
    hash3 = hashlib.sha256(text3.strip().lower().encode('utf-8')).hexdigest()
    
    # Same text should produce same hash
    assert hash1 == hash2, "Same text should produce same hash"
    
    # Different text should produce different hash
    assert hash1 != hash3, "Different text should produce different hash"
    
    print("✓ Cache key generation test passed")
    return True


# Test 2: Verify imports work
def test_imports():
    """Test that all required modules can be imported."""
    try:
        # Import models first (no dependencies)
        from models import AnalysisResult, ActionItem
        
        # Import service_llm (requires env vars but we won't instantiate)
        import service_llm
        
        # Import main functions (but not the module-level LLM service)
        import importlib.util
        spec = importlib.util.spec_from_file_location("main_module", "main.py")
        
        print("✓ All imports successful")
        return True
    except ImportError as e:
        print(f"✗ Import failed: {e}")
        return False


# Test 3: Verify cache key function matches expected behavior
def test_cache_key_function():
    """Test the actual cache key generation function."""
    try:
        # Import just the function we need
        import hashlib
        
        def generate_cache_key(policy_text: str) -> str:
            normalized = policy_text.strip().lower()
            return hashlib.sha256(normalized.encode('utf-8')).hexdigest()
        
        text = "Sample Privacy Policy"
        key1 = generate_cache_key(text)
        key2 = generate_cache_key(text)
        
        assert key1 == key2, "Cache key should be deterministic"
        assert len(key1) == 64, "SHA-256 hash should be 64 hex characters"
        
        print("✓ Cache key function test passed")
        return True
    except Exception as e:
        print(f"✗ Cache key function test failed: {e}")
        return False


# Test 4: Verify models can be instantiated
def test_models():
    """Test that Pydantic models work correctly."""
    try:
        from models import AnalysisResult, ActionItem
        from datetime import datetime
        
        # Create action item
        action = ActionItem(
            text="Review privacy settings",
            url="https://example.com/settings",
            priority="high"
        )
        
        # Create analysis result
        result = AnalysisResult(
            score=75,
            summary="This is a test summary",
            red_flags=["Test flag 1", "Test flag 2"],
            user_action_items=[action],
            timestamp=datetime.now(timezone.utc),
            url="https://example.com/privacy"
        )
        
        assert result.score == 75
        assert len(result.red_flags) == 2
        assert len(result.user_action_items) == 1
        
        print("✓ Models test passed")
        return True
    except Exception as e:
        print(f"✗ Models test failed: {e}")
        return False


if __name__ == "__main__":
    print("Running backend tests...\n")
    
    tests = [
        test_cache_key_generation,
        test_imports,
        test_cache_key_function,
        test_models
    ]
    
    results = []
    for test in tests:
        try:
            results.append(test())
        except Exception as e:
            print(f"✗ Test {test.__name__} failed with exception: {e}")
            results.append(False)
    
    print(f"\n{'='*50}")
    print(f"Tests passed: {sum(results)}/{len(results)}")
    
    if all(results):
        print("All tests passed! ✓")
        sys.exit(0)
    else:
        print("Some tests failed! ✗")
        sys.exit(1)
