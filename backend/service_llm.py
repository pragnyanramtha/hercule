import os
import json
import logging
import time
from typing import Dict, Any
from openai import AzureOpenAI
from groq import Groq
from models import AnalysisResult, ActionItem
from datetime import datetime, timezone

logger = logging.getLogger("privacy-api.llm")


class LLMService:
    """Service for analyzing privacy policies using Azure OpenAI or Groq (dev mode)."""

    def __init__(self):
        """Initialize LLM client with environment variables."""
        # Check for dev mode (Groq API)
        self.dev_mode = os.getenv("DEV_MODE", "").lower() == "true"
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        self.azure_api_key = os.getenv("AZURE_OPENAI_KEY")

        # Determine which mode to use
        if self.dev_mode and self.groq_api_key:
            # Dev mode: Use Groq API
            self.test_mode = False
            self.provider = "groq"
            self.client = Groq(api_key=self.groq_api_key)
            self.deployment = os.getenv("GROQ_MODEL", "moonshotai/kimi-k2-instruct-0905")
            logger.info("🚀 Running in DEV MODE - using Groq API")
            logger.info(f"   Model: {self.deployment}")
        elif self.azure_api_key:
            # Production mode: Use Azure OpenAI
            self.test_mode = False
            self.provider = "azure"
            self.client = AzureOpenAI(
                api_key=self.azure_api_key,
                api_version="2024-02-15-preview",
                azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
            )
            self.deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4")
            logger.info("🔵 Running in PRODUCTION MODE - using Azure OpenAI")
            logger.info(f"   Deployment: {self.deployment}")
        else:
            # Test mode: No API keys provided
            self.test_mode = True
            self.provider = "mock"
            self.client = None
            self.deployment = None
            logger.warning("⚠️  Running in TEST MODE - using mock LLM responses")

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
    {"text": "<actionable recommendation>", "url": "<optional link>", "priority": "<high|medium|low>"},
    ...
  ]
}

Scoring guidelines:
- 80-100: User-friendly, clear rights, strong privacy protections
- 50-79: Moderate concerns, some unclear terms or data sharing
- 0-49: Significant concerns, vague language, extensive data collection/sharing

Return ONLY the JSON object, no additional text."""

    def _generate_mock_analysis(self, policy_text: str, url: str) -> AnalysisResult:
        """
        Generate mock analysis for testing without Azure OpenAI.

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

        # Generate action items based on score and content
        action_items = []
        if score < 70:
            action_items.append(ActionItem(
                text="Review privacy settings and limit data sharing where possible",
                priority="high"
            ))
        if 'opt out' in text_lower or 'opt-out' in text_lower:
            action_items.append(ActionItem(
                text="Look for opt-out options in your account settings",
                url=url + "#settings" if url else None,
                priority="medium"
            ))
        if score < 50:
            action_items.append(ActionItem(
                text="Consider using privacy-focused alternatives to this service",
                priority="high"
            ))
            action_items.append(ActionItem(
                text="Use a VPN and privacy browser extensions when using this service",
                priority="medium"
            ))
        if 'delete' in text_lower:
            action_items.append(ActionItem(
                text="Exercise your right to delete your data if you no longer use the service",
                priority="low"
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
        Sends policy text to LLM (Azure OpenAI or Groq) and returns structured analysis.

        Args:
            policy_text: The privacy policy text to analyze (max 50,000 chars)
            url: The URL of the privacy policy

        Returns:
            AnalysisResult object with score, summary, red flags, and action items

        Raises:
            Exception: If LLM call fails or response is invalid
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
        else:
            logger.debug(f"📄 Policy text length: {original_length:,} chars")

        try:
            logger.debug(f"Calling {self.provider} API with model: {self.deployment}")
            start_time = time.time()

            if self.provider == "groq":
                # Groq API call
                response = self.client.chat.completions.create(
                    model=self.deployment,
                    messages=[
                        {"role": "system", "content": self._build_system_prompt()},
                        {"role": "user", "content": f"Analyze this privacy policy:\n\n{truncated_text}"}
                    ],
                    temperature=0.3,
                    max_tokens=2000,
                    response_format={"type": "json_object"}
                )
            else:
                # Azure OpenAI API call
                response = self.client.chat.completions.create(
                    model=self.deployment,
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
            logger.info(f"🤖 LLM API response received in {api_duration:.0f}ms")

            content = response.choices[0].message.content
            logger.debug(f"Response content length: {len(content)} chars")

            result_dict = json.loads(content)

            # Validate response structure
            if not self._validate_response(result_dict):
                logger.error(f"Invalid LLM response structure. Keys: {list(result_dict.keys())}")
                raise ValueError("LLM response missing required fields")

            # Log analysis results
            score = result_dict["score"]
            num_red_flags = len(result_dict.get("red_flags", []))
            num_actions = len(result_dict.get("user_action_items", []))
            logger.info(f"📊 Analysis results - Score: {score}/100, Red flags: {num_red_flags}, Actions: {num_actions}")

            # Convert to AnalysisResult model
            action_items = [
                ActionItem(**item) for item in result_dict.get("user_action_items", [])
            ]

            return AnalysisResult(
                score=result_dict["score"],
                summary=result_dict["summary"],
                red_flags=result_dict.get("red_flags", []),
                user_action_items=action_items,
                timestamp=datetime.now(timezone.utc),
                url=url
            )

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM JSON response: {e}")
            logger.debug(f"Raw response: {content[:500]}...")
            raise Exception(f"Failed to parse LLM response: {str(e)}")
        except Exception as e:
            logger.error(f"LLM analysis failed: {type(e).__name__}: {e}")
            raise Exception(f"Failed to analyze policy: {str(e)}")

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
