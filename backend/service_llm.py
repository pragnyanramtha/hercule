"""
LLM Service for privacy policy analysis using Groq API.
"""
import os
import json
import logging
import time
from typing import Dict, Any
from urllib.parse import quote
from groq import Groq
from models import AnalysisResult, ActionItem
from datetime import datetime, timezone

logger = logging.getLogger("hercule-api.llm")


class LLMService:
    """Service for analyzing privacy policies using Groq API."""

    def __init__(self):
        """Initialize LLM client with Groq API and rotation fallback."""
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        
        # Model rotation order (try in sequence for resilience)
        self.models = [
            "moonshotai/kimi-k2-instruct-0905",
            "moonshotai/kimi-k2-instruct",
            "meta-llama/llama-4-maverick-17b-128e-instruct",
            "openai/gpt-oss-120b",
            "llama-3.3-70b-versatile",
            "groq/compound"  # Last resort - has native web search
        ]
        
        if self.groq_api_key:
            self.test_mode = False
            self.provider = "groq"
            self.client = Groq(api_key=self.groq_api_key)
            self.current_model_index = 0
            self.deployment = self.models[0]  # Start with first model
            self.dev_mode = True  # Groq is always dev mode
            logger.info("🚀 Using Groq API with model rotation")
            logger.info(f"   Primary model: {self.deployment}")
            logger.info(f"   Fallback models: {len(self.models) - 1}")
        else:
            # Test mode: No API key provided
            self.test_mode = True
            self.provider = "mock"
            self.client = None
            self.deployment = "mock_model"
            self.dev_mode = True
            self.models = ["mock_model"]
            self.current_model_index = 0
            logger.warning("⚠️  Running in TEST MODE - using mock LLM responses (set GROQ_API_KEY to enable)")

    def _build_system_prompt(self) -> str:
        """Constructs the Privacy Lawyer Agent system prompt."""
        return """You are a Privacy Lawyer Agent, an expert in analyzing privacy policies and terms of service.

Your task is to analyze privacy policies and provide clear, actionable insights for everyday users.

Analyze the following aspects:
1. User rights (access, deletion, portability)
2. Data collection practices (what data is collected and why)
3. Third-party sharing (who gets access to user data)
4. Data retention policies (how long data is kept)
5. User control and consent mechanisms

Provide your analysis as a JSON object with this exact structure:
{
  "score": <number 0-100>,
  "summary": "<plain-language summary of key points>",
  "red_flags": ["<concerning practice 1>", "<concerning practice 2>", ...],
  "user_action_items": [
    {
      "text": "<actionable recommendation>",
      "url": "<optional general link>",
      "priority": "<high|medium|low>",
      "reference_url": "<URL with #section-anchor pointing to relevant policy section>",
      "mailto_link": "https://mail.google.com/mail/?view=cm&fs=1&to=<company-email>&su=<URL-encoded-subject>&body=<URL-encoded-email-body>",
      "email_body": "<pre-generated formal email message>"
    },
    ...
  ]
}

For each action item:
- "reference_url": Create a URL pointing to the specific section of the privacy policy. Use anchors like #data-collection, #third-party-sharing, #user-rights, etc.
- "email_body": Write a PERSONALIZED, polite formal email (2-3 paragraphs) tailored to the SPECIFIC privacy concern you found. Reference specific clauses or practices from THIS policy. Include: greeting, specific concern with details, request for action/clarification, and closing. Use [Your Name] as placeholder.
- "mailto_link": Create a Gmail compose URL. Format: "https://mail.google.com/mail/?view=cm&fs=1&to=<specific-contact-email>&su=<URL-encoded subject>&body=<URL-encoded email_body>". IMPORTANT: Extract the specific contact email address mentioned in the policy (e.g., privacy@company.com, support@company.com, dpo@company.com). If no specific email is found, use privacy@<domain> as a fallback. The body parameter must contain the SAME content as email_body field but URL-encoded. Use %20 for spaces, %0A for newlines.

Email writing guidelines:
- Be specific - cite actual practices you found in THIS policy
- Be professional and polite
- Make clear, actionable requests
- Keep it concise (2-3 paragraphs max)
- Don't use generic templates - make it relevant to the specific privacy issues found

Scoring guidelines:
- 80-100: User-friendly, clear rights, strong privacy protections
- 50-79: Moderate concerns, some unclear terms or data sharing
- 0-49: Significant concerns, vague language, extensive data collection/sharing

Return ONLY the JSON object, no additional text."""

    def _generate_mock_analysis(self, policy_text: str, url: str) -> AnalysisResult:
        """
        Generate mock analysis for testing without API key.

        Args:
            policy_text: The privacy policy text
            url: The URL of the privacy policy

        Returns:
            Mock AnalysisResult based on policy text characteristics
        """
        text_lower = policy_text.lower()
        text_length = len(policy_text)

        # Analyze text for concerning keywords
        concerning_keywords = [
            'third party', 'third-party', 'share', 'sell', 'indefinitely',
            'arbitration', 'waive', 'biometric', 'tracking', 'surveillance',
            'cannot control', 'may modify', 'without notice'
        ]

        positive_keywords = [
            'delete', 'opt out', 'opt-out', 'gdpr', 'ccpa', 'encrypted',
            'never share', 'never sell', 'your rights', 'you can', 'contact us'
        ]

        concern_count = sum(1 for keyword in concerning_keywords if keyword in text_lower)
        positive_count = sum(1 for keyword in positive_keywords if keyword in text_lower)

        # Calculate score based on characteristics
        base_score = 70
        score = base_score - (concern_count * 5) + (positive_count * 3)

        # Adjust for length (very long policies are harder to understand)
        if text_length > 5000:
            score -= 10
        elif text_length < 1000:
            score += 10

        # Clamp score to 0-100
        score = max(0, min(100, score))

        # Generate summary based on score
        if score >= 80:
            summary = "This privacy policy is relatively user-friendly and transparent. It clearly outlines data collection practices, provides users with control over their information, and demonstrates respect for privacy rights. The policy uses accessible language and offers straightforward options for data management."
        elif score >= 50:
            summary = "This privacy policy has moderate clarity with some areas of concern. While it outlines basic data practices, there are aspects that could be more transparent. Users should be aware of third-party data sharing and review the specific terms that apply to their usage. Some user rights are provided but may require additional steps to exercise."
        else:
            summary = "This privacy policy raises significant concerns regarding user privacy and data protection. The policy contains vague language, extensive data collection practices, and broad third-party sharing provisions. Users should carefully consider the implications before agreeing to these terms and explore alternative services if privacy is a priority."

        # Generate red flags based on concerning keywords found
        red_flags = []
        if 'third party' in text_lower or 'third-party' in text_lower:
            red_flags.append("Extensive third-party data sharing mentioned")
        if 'sell' in text_lower and 'data' in text_lower:
            red_flags.append("Policy may allow selling of user data")
        if 'indefinitely' in text_lower:
            red_flags.append("Data may be retained indefinitely")
        if 'arbitration' in text_lower:
            red_flags.append("Mandatory arbitration clause limits legal options")
        if 'biometric' in text_lower:
            red_flags.append("Collection of biometric data mentioned")
        if 'tracking' in text_lower:
            red_flags.append("User tracking across devices or websites")
        if 'without notice' in text_lower:
            red_flags.append("Policy can be changed without user notification")
        if concern_count > 5 and positive_count < 3:
            red_flags.append("Limited user control over personal data")

        # Extract domain from URL for email generation
        domain = ""
        if url:
            try:
                from urllib.parse import urlparse
                parsed = urlparse(url)
                domain = parsed.netloc.replace("www.", "")
            except:
                domain = "example.com"
        
        base_url = url if url else "https://example.com/privacy"

        # Generate action items based on score and content
        action_items = []
        if score < 70:
            email_body = """Dear Privacy Team,

I am writing to request information about how I can limit the data sharing practices outlined in your privacy policy. After reviewing your policy, I have concerns about the extent of data collection and sharing with third parties.

Specifically, I would like to:
1. Understand what options I have to opt out of data sharing
2. Request a list of third parties my data has been shared with
3. Learn how I can minimize the data collected about me

Please respond with the steps I can take to exercise my privacy rights.

Thank you for your attention to this matter.

Sincerely,
[Your Name]"""
            
            action_items.append(ActionItem(
                text="Review privacy settings and limit data sharing where possible",
                priority="high",
                reference_url=f"{base_url}#data-sharing",
                mailto_link=f"https://mail.google.com/mail/?view=cm&fs=1&to=privacy@{domain}&su={quote('Request to Limit Data Sharing')}&body={quote(email_body)}",
                email_body=email_body
            ))
        if 'opt out' in text_lower or 'opt-out' in text_lower:
            email_body = """Dear Privacy Team,

I am writing to exercise my right to opt out of certain data collection and sharing practices as mentioned in your privacy policy.

Please process my opt-out request for:
- Marketing communications
- Data sharing with third-party advertisers
- Cross-site tracking

Please confirm once my opt-out preferences have been updated.

Thank you,
[Your Name]"""
            
            action_items.append(ActionItem(
                text="Look for opt-out options in your account settings",
                url=url + "#settings" if url else None,
                priority="medium",
                reference_url=f"{base_url}#opt-out",
                mailto_link=f"https://mail.google.com/mail/?view=cm&fs=1&to=privacy@{domain}&su={quote('Opt-Out Request')}&body={quote(email_body)}",
                email_body=email_body
            ))
        if score < 50:
            email_body1 = """Dear Privacy Team,

I am writing to express my concerns regarding the data collection practices outlined in your privacy policy. The extent of data collection appears to be quite extensive and I would like clarification on the following:

1. What is the legal basis for collecting this data?
2. Is all this data collection strictly necessary for providing the service?
3. How long is my personal data retained?

I would appreciate a detailed response addressing these concerns.

Best regards,
[Your Name]"""
            
            action_items.append(ActionItem(
                text="Consider using privacy-focused alternatives to this service",
                priority="high",
                reference_url=f"{base_url}#data-collection",
                mailto_link=f"https://mail.google.com/mail/?view=cm&fs=1&to=privacy@{domain}&su={quote('Privacy Concerns Regarding Data Collection')}&body={quote(email_body1)}",
                email_body=email_body1
            ))
            email_body2 = """Dear Privacy Team,

I have reviewed your privacy policy and noticed references to tracking technologies. I would like to better understand:

1. What tracking technologies are used on your platform?
2. How can I disable or limit this tracking?
3. Do you honor Do Not Track browser signals?

Thank you for your transparency.

Regards,
[Your Name]"""
            
            action_items.append(ActionItem(
                text="Use a VPN and privacy browser extensions when using this service",
                priority="medium",
                reference_url=f"{base_url}#tracking",
                mailto_link=f"https://mail.google.com/mail/?view=cm&fs=1&to=privacy@{domain}&su={quote('Question About Tracking Practices')}&body={quote(email_body2)}",
                email_body=email_body2
            ))
        if 'delete' in text_lower:
            email_body3 = """Dear Privacy Team,

Pursuant to my rights under applicable data protection laws, I am writing to request the deletion of all personal data you hold about me.

Please confirm:
1. Receipt of this deletion request
2. The timeline for completing the deletion
3. Any data that cannot be deleted and the reason why

Please send confirmation once my data has been fully deleted from your systems.

Thank you,
[Your Name]"""
            
            action_items.append(ActionItem(
                text="Exercise your right to delete your data if you no longer use the service",
                priority="low",
                reference_url=f"{base_url}#user-rights",
                mailto_link=f"https://mail.google.com/mail/?view=cm&fs=1&to=privacy@{domain}&su={quote('Data Deletion Request')}&body={quote(email_body3)}",
                email_body=email_body3
            ))

        return AnalysisResult(
            score=score,
            summary=summary,
            red_flags=red_flags,
            user_action_items=action_items,
            timestamp=datetime.now(timezone.utc),
            url=url
        )

    def analyze_policy(self, policy_text: str, url: str) -> AnalysisResult:
        """
        Sends policy text to Groq LLM with automatic model rotation fallback.

        Args:
            policy_text: The privacy policy text to analyze (max 50,000 chars)
            url: The URL of the privacy policy

        Returns:
            AnalysisResult object with score, summary, red flags, and action items

        Raises:
            Exception: If all models fail
        """
        # If in test mode, return mock analysis
        if self.test_mode:
            logger.debug("Using mock analysis (test mode)")
            return self._generate_mock_analysis(policy_text, url)

        # Truncate policy text to 50,000 characters
        original_length = len(policy_text)
        truncated_text = policy_text[:50000]
        if original_length > 50000:
            truncated_text += "\n[Text truncated at 50,000 characters]"
            logger.info(f"📄 Policy text truncated: {original_length:,} → 50,000 chars")

        # Try each model in sequence until one succeeds
        last_error = None
        for attempt, model in enumerate(self.models):
            try:
                logger.debug(f"Attempt {attempt + 1}/{len(self.models)} - Trying model: {model}")
                start_time = time.time()

                # Special handling for groq/compound - it has web search
                if model == "groq/compound":
                    # Just send the URL and let it search and analyze
                    response = self.client.chat.completions.create(
                        model=model,
                        messages=[
                            {"role": "system", "content": self._build_system_prompt()},
                            {"role": "user", "content": f"""Please use your web search capability to access and analyze the privacy policy at this URL: {url}

Search for and read the privacy policy, then provide your analysis in the required JSON format.

URL to analyze: {url}"""}
                        ],
                        temperature=0.3,
                        max_tokens=2000,
                        response_format={"type": "json_object"}
                    )
                else:
                    # Normal models - send the policy text
                    response = self.client.chat.completions.create(
                        model=model,
                        messages=[
                            {"role": "system", "content": self._build_system_prompt()},
                            {"role": "user", "content": f"Analyze this privacy policy:\n\n{truncated_text}"}
                        ],
                        temperature=0.3,
                        max_tokens=2000,
                        response_format={"type": "json_object"}
                    )

                # Parse the response
                api_duration = (time.time() - start_time) * 1000
                logger.info(f"✅ Model {model} succeeded in {api_duration:.0f}ms")

                content = response.choices[0].message.content
                result_dict = json.loads(content)

                # Validate response structure
                if not self._validate_response(result_dict):
                    logger.warning(f"Invalid response from {model}, trying next model...")
                    continue

                # Log analysis results
                score = result_dict["score"]
                num_red_flags = len(result_dict.get("red_flags", []))
                num_actions = len(result_dict.get("user_action_items", []))
                logger.info(f"📊 Analysis - Score: {score}/100, Red flags: {num_red_flags}, Actions: {num_actions}")

                # Convert to AnalysisResult model
                action_items = [
                    ActionItem(**item) for item in result_dict.get("user_action_items", [])
                ]

                # Update current model for next request
                self.deployment = model
                self.current_model_index = attempt

                return AnalysisResult(
                    score=result_dict["score"],
                    summary=result_dict["summary"],
                    red_flags=result_dict.get("red_flags", []),
                    user_action_items=action_items,
                    timestamp=datetime.now(timezone.utc),
                    url=url
                )

            except json.JSONDecodeError as e:
                logger.warning(f"❌ Model {model} returned invalid JSON: {e}")
                last_error = e
                continue
            except Exception as e:
                logger.warning(f"❌ Model {model} failed: {type(e).__name__}: {e}")
                last_error = e
                continue

        # All models failed
        logger.error(f"💥 All {len(self.models)} models failed!")
        raise Exception(f"All LLM models failed. Last error: {str(last_error)}")

    def _validate_response(self, response: Dict[str, Any]) -> bool:
        """
        Validates LLM response contains required fields.

        Args:
            response: Dictionary parsed from LLM JSON response

        Returns:
            True if response is valid, False otherwise
        """
        required_fields = ["score", "summary", "red_flags", "user_action_items"]
        return all(field in response for field in required_fields)
