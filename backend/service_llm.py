"""
LLM Service for privacy policy analysis using Gemini models only.
"""

import json
import logging
import os
import re
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from urllib.parse import quote, urlparse

import google.generativeai as genai

from models import ActionItem, AnalysisResult

logger = logging.getLogger("hercule-api.llm")

# Context limits per model (in characters)
MODEL_CONTEXT_LIMITS = {
    "gemini-3.1-flash-lite-preview": 1_000_000,
    "gemini-3-flash-preview": 1_000_000,
    "gemini-2.5-flash": 800_000,
    "gemini-2.5-pro": 800_000,
}

# Gemini-only model fallback order
FALLBACK_MODELS = [
    "gemini-3.1-flash-lite-preview",
    "gemini-3-flash-preview",
    "gemini-2.5-flash",
    "gemini-2.5-pro",
]


class LLMService:
    """Service for analyzing privacy policies using Gemini models."""

    def __init__(self):
        """Initialize Gemini configuration."""
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")

        if self.gemini_api_key:
            self.test_mode = False
            self.provider = "gemini"
            self.deployment = FALLBACK_MODELS[0]
            self.dev_mode = True

            logger.info("LLM Service initialized with Gemini-only fallback chain")
            logger.info(f"Primary: {FALLBACK_MODELS[0]} (gemini)")
            logger.info(f"Fallback models: {len(FALLBACK_MODELS) - 1}")
            logger.info(f"Gemini key: ...{self.gemini_api_key[-6:]}")
        else:
            self.test_mode = True
            self.provider = "mock"
            self.deployment = "mock_model"
            self.dev_mode = True
            logger.warning("Running in TEST MODE - using mock LLM responses")

    def _call_gemini(self, model: str, messages: list, user_api_key: Optional[str] = None) -> dict:
        """Call Gemini API."""
        api_key = user_api_key or self.gemini_api_key
        if not api_key:
            raise ValueError("Gemini API key not configured")

        genai.configure(api_key=api_key)

        system_instruction = ""
        gemini_messages = []

        for msg in messages:
            if msg["role"] == "system":
                system_instruction = msg["content"]
            else:
                gemini_messages.append(
                    {
                        "role": "user" if msg["role"] == "user" else "model",
                        "parts": [msg["content"]],
                    }
                )

        model_instance = genai.GenerativeModel(model_name=model, system_instruction=system_instruction)

        response = model_instance.generate_content(
            gemini_messages,
            generation_config=genai.GenerationConfig(
                temperature=0.3,
                max_output_tokens=2000,
                response_mime_type="application/json",
            ),
        )

        try:
            return json.loads(response.text)
        except json.JSONDecodeError:
            return self._extract_json_from_response(response.text)

    def _build_system_prompt(self, user_name: str = "") -> str:
        """Construct the Privacy Lawyer Agent prompt for policy text input."""
        name_clause = ""
        if user_name and user_name.strip():
            name_clause = (
                f"\n\nIMPORTANT: The user's name is '{user_name.strip()}'. "
                f"When generating email templates in 'email_body', use their actual name "
                f"'{user_name.strip()}' instead of '[Your Name]' in the signature/closing."
            )

        return (
            """You are a Privacy Lawyer Agent, an expert in analyzing privacy policies and terms of service.

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
  "summary": "<plain-language summary of key points - MUST be 4-5 sentences minimum>",
  "red_flags": ["<concerning practice 1>", "<concerning practice 2>", ...],
  "user_action_items": [
    {
      "text": "<actionable recommendation>",
      "url": "<optional general link>",
      "priority": "<high|medium|low>",
      "reference_url": "<URL with #section-anchor pointing to relevant policy section>",
      "recipient_email": "<company-email@domain.com>",
      "email_subject": "<subject line for the email>",
      "email_body": "<pre-generated formal email message>"
    }
  ]
}

MINIMUM OUTPUT REQUIREMENTS:
- "summary": MUST be at least 4-5 sentences providing a comprehensive overview
- "red_flags": MUST include at least 5 items
- "user_action_items": MUST include at least 3 items

For each action item:
- "reference_url": Create a URL pointing to the specific section of the privacy policy
- "recipient_email": Extract the specific contact email address mentioned in the policy
- "email_subject": A clear, concise subject line for the email
- "email_body": Write a personalized, polite formal email (2-3 paragraphs)

Scoring guidelines:
- 80-100: User-friendly, clear rights, strong privacy protections
- 50-79: Moderate concerns, some unclear terms or data sharing
- 0-49: Significant concerns, vague language, extensive data collection/sharing

Return ONLY the JSON object, no additional text."""
            + name_clause
        )

    def _build_url_only_system_prompt(self, website_url: str, website_name: str, user_name: str = "") -> str:
        """Build prompt for URL-only analysis when policy text could not be extracted."""
        name_clause = ""
        if user_name and user_name.strip():
            name_clause = (
                f"\n\nIMPORTANT: The user's name is '{user_name.strip()}'. "
                "Use their actual name instead of '[Your Name]' in any email templates."
            )

        return (
            f"""You are a Privacy Lawyer Agent. The user wants to understand the privacy practices of: {website_name}
Website URL: {website_url}

We were unable to retrieve their privacy policy directly. Based on your knowledge of this website/service and common industry practices, provide a privacy analysis.

Provide your analysis as a JSON object with this EXACT structure:
{{
  "score": <number 0-100>,
  "summary": "<4-5 sentence summary based on what you know about this service's typical privacy practices>",
  "red_flags": ["<known or likely concerning practice 1>", "<practice 2>", "<at least 3-5 items>"],
  "user_action_items": [
    {{
      "text": "<actionable recommendation>",
      "priority": "<high|medium|low>",
      "recipient_email": "privacy@{website_name}",
      "email_subject": "Privacy Policy Inquiry",
      "email_body": "<2-3 paragraph email requesting information>"
    }}
  ]
}}

MINIMUM REQUIREMENTS:
- "summary": At least 4-5 sentences
- "red_flags": At least 3 items
- "user_action_items": At least 3 items

Be conservative with scoring if you're uncertain. Focus on general privacy best practices and what users should look out for with this type of service.

Return ONLY the JSON object, no additional text."""
            + name_clause
        )

    def _assemble_mailto_link(self, recipient: str, subject: str, body: str) -> str:
        """Assemble full Gmail mailto URL with encoded body."""
        encoded_subject = quote(subject, safe="")
        encoded_body = quote(body, safe="")
        return f"https://mail.google.com/mail/?view=cm&fs=1&to={recipient}&su={encoded_subject}&body={encoded_body}"

    def _process_action_items(self, items: list) -> list:
        """Process action items to assemble mailto links."""
        processed = []
        for item in items:
            recipient = item.get("recipient_email", "")
            subject = item.get("email_subject", "Privacy Inquiry")
            body = item.get("email_body", "")

            mailto_link = None
            if recipient:
                mailto_link = self._assemble_mailto_link(recipient, subject, body)

            processed.append(
                ActionItem(
                    text=item.get("text", ""),
                    url=item.get("url"),
                    priority=item.get("priority", "medium"),
                    reference_url=item.get("reference_url"),
                    mailto_link=mailto_link,
                    email_body=body,
                )
            )

        return processed

    def _truncate_policy(self, policy_text: str, max_chars: int) -> str:
        """Truncate policy text to fit within model context limit."""
        if len(policy_text) <= max_chars:
            return policy_text

        truncated = policy_text[:max_chars]
        truncated += "\n[Text truncated due to length limits]"
        logger.info(f"Policy truncated: {len(policy_text):,} -> {max_chars:,} chars")
        return truncated

    def _generate_mock_analysis(self, policy_text: str, url: str) -> AnalysisResult:
        """Generate mock analysis for testing without API key."""
        text_lower = policy_text.lower()
        text_length = len(policy_text)

        concerning_keywords = [
            "third party",
            "third-party",
            "share",
            "sell",
            "indefinitely",
            "arbitration",
            "waive",
            "biometric",
            "tracking",
            "surveillance",
            "cannot control",
            "may modify",
            "without notice",
        ]
        positive_keywords = [
            "delete",
            "opt out",
            "opt-out",
            "gdpr",
            "ccpa",
            "encrypted",
            "never share",
            "never sell",
            "your rights",
            "you can",
            "contact us",
        ]

        concern_count = sum(1 for keyword in concerning_keywords if keyword in text_lower)
        positive_count = sum(1 for keyword in positive_keywords if keyword in text_lower)

        score = 70 - (concern_count * 5) + (positive_count * 3)

        if text_length > 5000:
            score -= 10
        elif text_length < 1000:
            score += 10

        score = max(0, min(100, score))

        if score >= 80:
            summary = "This privacy policy is relatively user-friendly and transparent."
        elif score >= 50:
            summary = "This privacy policy has moderate clarity with some areas of concern."
        else:
            summary = "This privacy policy raises significant concerns regarding user privacy."

        red_flags = []
        if "third party" in text_lower or "third-party" in text_lower:
            red_flags.append("Extensive third-party data sharing mentioned")
        if "sell" in text_lower and "data" in text_lower:
            red_flags.append("Policy may allow selling of user data")

        domain = "example.com"
        if url:
            try:
                parsed = urlparse(url)
                domain = parsed.netloc.replace("www.", "") or "example.com"
            except Exception:
                domain = "example.com"

        base_url = url if url else "https://example.com/privacy"

        action_items = []
        if score < 70:
            email_body = """Dear Privacy Team,

I am writing to request information about how I can limit the data sharing practices outlined in your privacy policy.

Please respond with the steps I can take to exercise my privacy rights.

Thank you,
[Your Name]"""

            action_items.append(
                ActionItem(
                    text="Review privacy settings and limit data sharing where possible",
                    priority="high",
                    reference_url=f"{base_url}#data-sharing",
                    mailto_link=self._assemble_mailto_link(
                        f"privacy@{domain}", "Request to Limit Data Sharing", email_body
                    ),
                    email_body=email_body,
                )
            )

        return AnalysisResult(
            score=score,
            summary=summary,
            red_flags=red_flags,
            user_action_items=action_items,
            timestamp=datetime.now(timezone.utc),
            url=url,
        )

    def analyze_policy(
        self,
        policy_text: str,
        url: str,
        user_name: str = "",
        user_gemini_api_key: str = "",
    ) -> AnalysisResult:
        """
        Analyze policy with Gemini-only fallback chain.
        """
        if self.test_mode and not user_gemini_api_key:
            logger.debug("Using mock analysis (test mode)")
            return self._generate_mock_analysis(policy_text, url)

        website_name = ""
        website_url = url or ""
        if url:
            try:
                parsed = urlparse(url)
                website_name = parsed.netloc.replace("www.", "")
            except Exception:
                website_name = url

        has_policy_text = bool(policy_text and policy_text.strip())

        last_error: Optional[Exception] = None
        max_invalid_retries = 2

        for attempt, model in enumerate(FALLBACK_MODELS):
            context_limit = MODEL_CONTEXT_LIMITS.get(model, 50000)

            if has_policy_text:
                truncated_text = self._truncate_policy(policy_text, context_limit)
                prompt_text = self._build_system_prompt(user_name)
                user_message = f"Analyze this privacy policy:\n\n{truncated_text}"
            else:
                prompt_text = self._build_url_only_system_prompt(
                    website_url=website_url,
                    website_name=website_name,
                    user_name=user_name,
                )
                user_message = f"Analyze the privacy practices of: {website_name} ({website_url})"

            invalid_response_retries = 0

            while invalid_response_retries < max_invalid_retries:
                try:
                    logger.info(f"Attempt {attempt + 1}/{len(FALLBACK_MODELS)} - {model} (gemini)")
                    start_time = time.time()

                    messages = [
                        {"role": "system", "content": prompt_text},
                        {"role": "user", "content": user_message},
                    ]

                    result_dict = self._call_gemini(
                        model,
                        messages,
                        user_api_key=user_gemini_api_key if attempt == 0 and invalid_response_retries == 0 else None,
                    )

                    api_duration = (time.time() - start_time) * 1000
                    logger.info(f"API response from {model} in {api_duration:.0f}ms")

                    if result_dict is None:
                        invalid_response_retries += 1
                        logger.warning(f"Could not parse JSON from {model} response")
                        continue

                    if not self._validate_response(result_dict):
                        invalid_response_retries += 1
                        logger.warning(f"Invalid response from {model}")
                        continue

                    self.deployment = model
                    self.provider = "gemini"

                    action_items = self._process_action_items(result_dict.get("user_action_items", []))

                    return AnalysisResult(
                        score=result_dict["score"],
                        summary=result_dict["summary"],
                        red_flags=result_dict.get("red_flags", []),
                        user_action_items=action_items,
                        timestamp=datetime.now(timezone.utc),
                        url=url,
                    )

                except Exception as e:
                    last_error = e
                    logger.warning(f"Model {model} failed: {type(e).__name__}: {str(e)[:120]}")
                    break

        logger.error(f"All {len(FALLBACK_MODELS)} Gemini models failed")
        raise Exception(f"All Gemini models failed. Last error: {str(last_error)}")

    def _validate_response(self, response: Dict[str, Any]) -> bool:
        """Validate LLM response has required fields with meaningful values."""
        required_fields = ["score", "summary", "red_flags", "user_action_items"]

        for field in required_fields:
            if field not in response:
                return False

        score = response.get("score")
        if not isinstance(score, (int, float)) or score < 0 or score > 100:
            return False

        summary = response.get("summary", "")
        if not isinstance(summary, str) or len(summary.strip()) < 50:
            return False

        red_flags = response.get("red_flags")
        if not isinstance(red_flags, list):
            return False

        action_items = response.get("user_action_items")
        if not isinstance(action_items, list):
            return False

        for item in action_items:
            if not isinstance(item, dict):
                return False
            if not item.get("text"):
                return False

        return True

    def _extract_json_from_response(self, content: str) -> Optional[Dict[str, Any]]:
        """Extract JSON from plain text or fenced markdown response."""
        if not content:
            return None

        content = content.strip()

        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass

        json_patterns = [
            r"```json\s*([\s\S]*?)\s*```",
            r"```\s*([\s\S]*?)\s*```",
            r"\{[\s\S]*\}",
        ]

        for pattern in json_patterns:
            match = re.search(pattern, content)
            if match:
                try:
                    json_str = match.group(1) if "```" in pattern else match.group(0)
                    return json.loads(json_str)
                except (json.JSONDecodeError, IndexError):
                    continue

        return None
