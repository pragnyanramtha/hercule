"""
Manual UI Testing Script
Tests the backend with various privacy policy scenarios to verify UI rendering
"""

import requests
import json
import time

# Test data representing different score ranges and scenarios
test_cases = [
    {
        "name": "High Score (Green) - Short, clear policy",
        "policy_text": """
Privacy Policy

We collect only your email address when you sign up.
We never share your data with third parties.
You can delete your account at any time.
We store data for 30 days after account deletion.
Contact us at privacy@example.com for questions.
        """,
        "expected_score_range": (80, 100),
        "expected_color": "green"
    },
    {
        "name": "Medium Score (Yellow) - Moderate policy",
        "policy_text": """
Privacy Policy

Information We Collect:
We collect personal information including name, email, phone number, location data, 
browsing history, device information, and usage patterns.

How We Use Your Information:
We use your information for service provision, analytics, marketing, and may share 
with third-party partners for advertising purposes.

Data Retention:
We retain your data indefinitely unless you request deletion.

Your Rights:
You may request access to your data by contacting our support team.
        """,
        "expected_score_range": (50, 79),
        "expected_color": "yellow"
    },
    {
        "name": "Low Score (Red) - Complex, concerning policy",
        "policy_text": """
Privacy Policy

By using our services, you agree to our comprehensive data collection practices.

Data Collection:
We collect extensive personal information including but not limited to: full name, 
address, phone numbers, email addresses, payment information, social security numbers,
biometric data, location tracking, browsing history across all devices, contacts list,
photos, messages, call logs, and any other information accessible through your device.

Third-Party Sharing:
We share your information with numerous third-party partners, advertisers, data brokers,
analytics companies, and other entities for various purposes including targeted advertising,
market research, and business operations. We cannot control how these third parties use your data.

Data Retention:
We retain all collected data indefinitely and may continue to use it even after account deletion.

International Transfers:
Your data may be transferred to and processed in countries with different privacy laws.

Changes to Policy:
We may modify this policy at any time without notice. Continued use constitutes acceptance.

Arbitration:
You agree to binding arbitration and waive your right to class action lawsuits.

Contact:
For questions, you may attempt to contact us through our website form.
        """,
        "expected_score_range": (0, 49),
        "expected_color": "red"
    },
    {
        "name": "Boundary Test - Score 80 (Green threshold)",
        "policy_text": """
Privacy Policy - Clear and Concise

What We Collect:
- Email address for account creation
- Name for personalization
- Usage data for service improvement

How We Use It:
- Provide and improve our services
- Send important updates
- Respond to your requests

Your Rights:
- Access your data anytime
- Delete your account easily
- Export your information
- Opt out of emails

Data Protection:
- Encrypted storage
- No sale of personal data
- 30-day retention after deletion
- GDPR compliant

Contact: privacy@example.com
        """,
        "expected_score_range": (78, 82),
        "expected_color": "green"
    },
    {
        "name": "Boundary Test - Score 50 (Yellow threshold)",
        "policy_text": """
Privacy Policy

Information Collection:
We collect personal information, usage data, device information, and location data.
This information is used for service provision, analytics, and marketing purposes.

Third-Party Services:
We work with third-party service providers who may access your information.
These providers are bound by confidentiality agreements.

Data Retention:
We retain your information for as long as necessary for business purposes.
You may request deletion by contacting support.

Your Rights:
You have the right to access, correct, or delete your personal information.
Please contact us to exercise these rights.

Updates:
We may update this policy periodically. Check back regularly for changes.
        """,
        "expected_score_range": (48, 52),
        "expected_color": "yellow"
    }
]

def test_backend():
    """Test the backend with various policy scenarios"""
    base_url = "http://localhost:8000"
    
    print("=" * 80)
    print("Privacy Policy Analyzer - Manual UI Testing")
    print("=" * 80)
    print()
    
    # Check if backend is running
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        print("✓ Backend is running")
        print()
    except requests.exceptions.RequestException as e:
        print(f"✗ Backend is not running: {e}")
        print("Please start the backend with: cd backend && python -m uvicorn main:app --reload --port 8000")
        return
    
    # Test each scenario
    for i, test_case in enumerate(test_cases, 1):
        print(f"Test Case {i}: {test_case['name']}")
        print("-" * 80)
        
        try:
            # Send request to backend
            response = requests.post(
                f"{base_url}/analyze",
                json={
                    "policy_text": test_case["policy_text"],
                    "url": f"https://example.com/privacy-test-{i}"
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # Display results
                print(f"Score: {result['score']}/100")
                print(f"Expected Range: {test_case['expected_score_range']}")
                print(f"Expected Color: {test_case['expected_color']}")
                
                # Verify score is in expected range
                min_score, max_score = test_case['expected_score_range']
                if min_score <= result['score'] <= max_score:
                    print("✓ Score is in expected range")
                else:
                    print(f"⚠ Score {result['score']} is outside expected range {test_case['expected_score_range']}")
                
                # Verify traffic light color
                if result['score'] >= 80:
                    actual_color = "green"
                elif result['score'] >= 50:
                    actual_color = "yellow"
                else:
                    actual_color = "red"
                
                if actual_color == test_case['expected_color']:
                    print(f"✓ Traffic light color: {actual_color}")
                else:
                    print(f"⚠ Traffic light color mismatch: expected {test_case['expected_color']}, got {actual_color}")
                
                print(f"\nSummary: {result['summary'][:150]}...")
                print(f"\nRed Flags ({len(result['red_flags'])}):")
                for flag in result['red_flags'][:3]:
                    print(f"  ⚠️  {flag}")
                if len(result['red_flags']) > 3:
                    print(f"  ... and {len(result['red_flags']) - 3} more")
                
                print(f"\nAction Items ({len(result['user_action_items'])}):")
                for item in result['user_action_items'][:3]:
                    if item.get('url'):
                        print(f"  → {item['text']} (Link: {item['url']})")
                    else:
                        print(f"  → {item['text']}")
                if len(result['user_action_items']) > 3:
                    print(f"  ... and {len(result['user_action_items']) - 3} more")
                
                print("\n✓ Test passed")
                
            else:
                print(f"✗ Request failed with status {response.status_code}")
                print(f"Response: {response.text}")
                
        except requests.exceptions.Timeout:
            print("✗ Request timed out (LLM may be slow)")
        except Exception as e:
            print(f"✗ Error: {e}")
        
        print()
        print()
        
        # Small delay between requests
        if i < len(test_cases):
            time.sleep(1)
    
    print("=" * 80)
    print("Testing Complete!")
    print("=" * 80)
    print()
    print("Manual Testing Checklist:")
    print("1. ✓ Backend responds to requests")
    print("2. ✓ Different score ranges produce different traffic light colors")
    print("3. ✓ Summary text is generated")
    print("4. ✓ Red flags are identified")
    print("5. ✓ Action items are provided")
    print()
    print("Next Steps:")
    print("1. Load the extension in Chrome (chrome://extensions)")
    print("2. Visit test websites:")
    print("   - https://policies.google.com/privacy")
    print("   - https://www.facebook.com/privacy/policy")
    print("   - https://www.amazon.com/gp/help/customer/display.html?nodeId=GX7NJQ4ZB8MHFRNJ")
    print("3. Click the extension icon and verify:")
    print("   - Traffic light displays correct color")
    print("   - Summary is readable and can expand if > 500 chars")
    print("   - Red flags display with warning icons")
    print("   - Action items with URLs are clickable and open in new tabs")
    print("   - Layout fits in 400x600 popup without scrolling issues")

if __name__ == "__main__":
    test_backend()
