"""
LLM Service for privacy policy analysis using OpenRouter and Groq APIs.
"""
import os
import re
import json
import logging
import time
import httpx
from typing import Dict, Any, Optional
from urllib.parse import quote, urlparse
import google.generativeai as genai
from groq import Groq
from models import AnalysisResult, ActionItem
from datetime import datetime, timezone
from api_key_manager import api_key_manager

logger = logging.getLogger("hercule-api.llm")

# Context limits per model (in characters)
MODEL_CONTEXT_LIMITS = {
    "gemini-3.1-flash-lite-preview": 1000000,
    "gemini-3-flash-preview": 1000000,
    "nvidia/nemotron-3-nano-30b-a3b:free": 1000000,
    "groq/compound": 70000,
    "llama-3.3-70b-versatile": 12000,
    "groq/compound-mini": 70000,
    "moonshotai/kimi-k2-instruct-0905": 10000,
}

# Model order for fallback chain - WHEN POLICY TEXT IS AVAILABLE
FALLBACK_MODELS_WITH_TEXT = [
    ("gemini-3.1-flash-lite-preview", "gemini"),
    ("gemini-3-flash-preview", "gemini"),
    ("nvidia/nemotron-3-nano-30b-a3b:free", "openrouter"),
    ("groq/compound", "groq"),
    ("llama-3.3-70b-versatile", "groq"),
    ("groq/compound-mini", "groq"),
    ("moonshotai/kimi-k2-instruct-0905", "groq"),
]

# Model order for fallback chain - WHEN NO POLICY TEXT (URL only)
# Prioritizes models with web search capability
FALLBACK_MODELS_URL_ONLY = [
    ("gemini-3.1-flash-lite-preview", "gemini"),
    ("gemini-3-flash-preview", "gemini"),
    ("groq/compound", "groq"),              # Best: has web search capability
    ("groq/compound-mini", "groq"),         # Also has web search
    ("moonshotai/kimi-k2-instruct-0905", "groq"),  # Knowledge-based fallback
    ("nvidia/nemotron-3-nano-30b-a3b:free", "openrouter"),
    ("llama-3.3-70b-versatile", "groq"),
]

# Backwards compatibility alias
FALLBACK_MODELS = FALLBACK_MODELS_WITH_TEXT



class LLMService:
    """Service for analyzing privacy policies using OpenRouter and Groq APIs."""

    def __init__(self):
        """Initialize LLM client with API keys."""
        self.key_manager = api_key_manager
        self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        
        # Check if we have any keys available
        if self.key_manager.has_keys() or self.openrouter_api_key or self.gemini_api_key:
            self.test_mode = False
            # Determine default provider
            if self.gemini_api_key:
                self.provider = "gemini"
            elif self.openrouter_api_key:
                self.provider = "openrouter"
            else:
                self.provider = "groq"
                
            self.deployment = FALLBACK_MODELS[0][0]
            self.dev_mode = True
            logger.info("🚀 LLM Service initialized with fallback chain")
            logger.info(f"   Primary: {FALLBACK_MODELS[0][0]} ({FALLBACK_MODELS[0][1]})")
            logger.info(f"   Fallback models: {len(FALLBACK_MODELS) - 1}")
            
            if self.gemini_api_key:
                logger.info(f"   Gemini key: ...{self.gemini_api_key[-6:]}")
            if self.openrouter_api_key:
                logger.info(f"   OpenRouter key: ...{self.openrouter_api_key[-6:]}")
            if self.key_manager.has_keys():
                logger.info(f"   Groq keys: {self.key_manager.get_stats()['total_keys']}")
        else:
            # Test mode: No API keys
            self.test_mode = True
            self.provider = "mock"
            self.deployment = "mock_model"
            self.dev_mode = True
            logger.warning("⚠️  Running in TEST MODE - using mock LLM responses")
    
    def _get_groq_client(self, user_api_key: Optional[str] = None) -> Groq:
        """Get Groq client with appropriate API key."""
        if user_api_key:
            self.key_manager.add_key(user_api_key)
            logger.info(f"🔑 Using user-provided Groq API key (ending ...{user_api_key[-6:]})")
            return Groq(api_key=user_api_key)
        
        current_key = self.key_manager.get_current_key()
        if not current_key:
            raise ValueError("No Groq API keys available")
        
        logger.debug(f"Using Groq key from pool (ending ...{current_key[-6:]})")
        return Groq(api_key=current_key)
    
    def _call_openrouter(self, model: str, messages: list, max_context: int) -> dict:
        """Call OpenRouter API."""
        if not self.openrouter_api_key:
            raise ValueError("OpenRouter API key not configured")
        
        headers = {
            "Authorization": f"Bearer {self.openrouter_api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://hercule-privacy.azurewebsites.net",
            "X-Title": "Hercule Privacy Analyzer"
        }
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": 0.3,
            "max_tokens": 2000,
            "response_format": {"type": "json_object"}
        }
        
        with httpx.Client(timeout=60.0) as client:
            response = client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload
            )
            
            if response.status_code == 429:
                raise Exception("Rate limit exceeded on OpenRouter")
            
            response.raise_for_status()
            return response.json()

    def _call_gemini(self, model: str, messages: list, user_api_key: Optional[str] = None) -> dict:
        """Call Gemini API."""
        api_key = user_api_key or self.gemini_api_key
        if not api_key:
            raise ValueError("Gemini API key not configured")
        
        genai.configure(api_key=api_key)
        
        # Convert messages to Gemini format
        system_instruction = ""
        gemini_messages = []
        
        for msg in messages:
            if msg["role"] == "system":
                system_instruction = msg["content"]
            else:
                gemini_messages.append({
                    "role": "user" if msg["role"] == "user" else "model",
                    "parts": [msg["content"]]
                })
        
        # Gemini 1.5+ uses system_instruction
        model_instance = genai.GenerativeModel(
            model_name=model,
            system_instruction=system_instruction
        )
        
        response = model_instance.generate_content(
            gemini_messages,
            generation_config=genai.GenerationConfig(
                temperature=0.3,
                max_output_tokens=2000,
                response_mime_type="application/json"
            )
        )
        
        try:
            return json.loads(response.text)
        except json.JSONDecodeError:
            # Fallback for models that might not support JSON mode perfectly
            # or if the response text contains extra bits
            return self._extract_json_from_response(response.text)

    def _build_system_prompt(self, user_name: str = "") -> str:
        """Constructs the Privacy Lawyer Agent system prompt."""
        name_clause = ""
        if user_name and user_name.strip():
            name_clause = f"\n\nIMPORTANT: The user's name is '{user_name.strip()}'. When generating email templates in 'email_body', use their actual name '{user_name.strip()}' instead of '[Your Name]' in the signature/closing."
        
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
    },
    ...
  ]
}

MINIMUM OUTPUT REQUIREMENTS:
- "summary": MUST be at least 4-5 sentences providing a comprehensive overview
- "red_flags": MUST include at least 5 items (find concerning practices or potential issues)
- "user_action_items": MUST include at least 3 items (no maximum limit - include all relevant actions)

For each action item:
- "reference_url": Create a URL pointing to the specific section of the privacy policy. Use anchors like #data-collection, #third-party-sharing, #user-rights, etc.
- "recipient_email": Extract the specific contact email address mentioned in the policy (e.g., privacy@company.com, support@company.com, dpo@company.com). If no specific email is found, use privacy@<domain> as a fallback.
- "email_subject": A clear, concise subject line for the email.
- "email_body": Write a PERSONALIZED, polite formal email (2-3 paragraphs) tailored to the SPECIFIC privacy concern you found. Reference specific clauses or practices from THIS policy. Include: greeting, specific concern with details, request for action/clarification, and closing. Use [Your Name] as placeholder if no name provided.

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

Return ONLY the JSON object, no additional text.""" + name_clause

    def _build_url_only_system_prompt(self, website_url: str, website_name: str, user_name: str = "", has_web_search: bool = False) -> str:
        """
        Build system prompt for URL-only analysis (no policy text available).
        Different prompts for models with/without web search capability.
        """
        name_clause = ""
        if user_name and user_name.strip():
            name_clause = f"\n\nIMPORTANT: The user's name is '{user_name.strip()}'. Use their actual name instead of '[Your Name]' in any email templates."
        
        if has_web_search:
            # Prompt for models with web search capability (groq/compound)
            return f"""You are a Privacy Lawyer Agent with web search capability.

The user wants to analyze the privacy practices of: {website_name}
Website URL: {website_url}

YOUR TASK:
1. Use your web search capability to find and read the privacy policy for {website_name}
2. Search for: "{website_name} privacy policy" or visit {website_url}/privacy
3. Analyze the privacy policy you find and provide a comprehensive report

After finding and analyzing the privacy policy, provide your analysis as a JSON object with this EXACT structure:
{{
  "score": <number 0-100>,
  "summary": "<4-5 sentence summary of key privacy practices and concerns you found>",
  "red_flags": ["<concerning practice 1>", "<concerning practice 2>", "<at least 3-5 red flags>"],
  "user_action_items": [
    {{
      "text": "<specific actionable recommendation>",
      "url": "<relevant settings URL if known>",
      "priority": "<high|medium|low>",
      "reference_url": "<URL to specific section of policy>",
      "recipient_email": "<privacy contact email>",
      "email_subject": "<specific subject line>",
      "email_body": "<personalized 2-3 paragraph email>"
    }}
  ]
}}

MINIMUM REQUIREMENTS:
- "summary": At least 4-5 detailed sentences
- "red_flags": At least 3 items
- "user_action_items": At least 3 items with complete email templates

Scoring guidelines:
- 80-100: User-friendly, clear rights, strong privacy protections
- 50-79: Moderate concerns, some unclear terms or data sharing  
- 0-49: Significant concerns, vague language, extensive data collection/sharing

Return ONLY the JSON object, no additional text.""" + name_clause
        
        else:
            # Prompt for models WITHOUT web search (use general knowledge)
            return f"""You are a Privacy Lawyer Agent. The user wants to understand the privacy practices of: {website_name}
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

Return ONLY the JSON object, no additional text.""" + name_clause

    def _build_website_only_prompt(self, website_name: str, user_name: str = "") -> str:
        """Legacy method - redirects to new URL-only prompt without web search."""
        return self._build_url_only_system_prompt(
            website_url=f"https://{website_name}",
            website_name=website_name,
            user_name=user_name,
            has_web_search=False
        )

    def _assemble_mailto_link(self, recipient: str, subject: str, body: str) -> str:
        """Assemble full Gmail mailto URL with encoded body."""
        encoded_subject = quote(subject, safe='')
        encoded_body = quote(body, safe='')
        return f"https://mail.google.com/mail/?view=cm&fs=1&to={recipient}&su={encoded_subject}&body={encoded_body}"
    
    def _process_action_items(self, items: list) -> list:
        """Process action items to assemble mailto links."""
        processed = []
        for item in items:
            # Extract email components
            recipient = item.get("recipient_email", "")
            subject = item.get("email_subject", "Privacy Inquiry")
            body = item.get("email_body", "")
            
            # Assemble mailto link if we have recipient
            mailto_link = None
            if recipient:
                mailto_link = self._assemble_mailto_link(recipient, subject, body)
            
            processed.append(ActionItem(
                text=item.get("text", ""),
                url=item.get("url"),
                priority=item.get("priority", "medium"),
                reference_url=item.get("reference_url"),
                mailto_link=mailto_link,
                email_body=body
            ))
        
        return processed

    def _truncate_policy(self, policy_text: str, max_chars: int) -> str:
        """Truncate policy text to fit within model context limit."""
        if len(policy_text) <= max_chars:
            return policy_text
        
        truncated = policy_text[:max_chars]
        truncated += "\n[Text truncated due to length limits]"
        logger.info(f"📄 Policy truncated: {len(policy_text):,} → {max_chars:,} chars")
        return truncated

    def _generate_mock_analysis(self, policy_text: str, url: str) -> AnalysisResult:
        """Generate mock analysis for testing without API key."""
        text_lower = policy_text.lower()
        text_length = len(policy_text)

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

        base_score = 70
        score = base_score - (concern_count * 5) + (positive_count * 3)

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
        if 'third party' in text_lower or 'third-party' in text_lower:
            red_flags.append("Extensive third-party data sharing mentioned")
        if 'sell' in text_lower and 'data' in text_lower:
            red_flags.append("Policy may allow selling of user data")

        domain = ""
        if url:
            try:
                parsed = urlparse(url)
                domain = parsed.netloc.replace("www.", "")
            except:
                domain = "example.com"
        
        base_url = url if url else "https://example.com/privacy"

        action_items = []
        if score < 70:
            email_body = """Dear Privacy Team,

I am writing to request information about how I can limit the data sharing practices outlined in your privacy policy.

Please respond with the steps I can take to exercise my privacy rights.

Thank you,
[Your Name]"""
            
            action_items.append(ActionItem(
                text="Review privacy settings and limit data sharing where possible",
                priority="high",
                reference_url=f"{base_url}#data-sharing",
                mailto_link=self._assemble_mailto_link(f"privacy@{domain}", "Request to Limit Data Sharing", email_body),
                email_body=email_body
            ))

        return AnalysisResult(
            score=score,
            summary=summary,
            red_flags=red_flags,
            user_action_items=action_items,
            timestamp=datetime.now(timezone.utc),
            url=url
        )

    def analyze_policy(
        self, 
        policy_text: str, 
        url: str, 
        user_name: str = "",
        user_groq_api_key: str = "",
        user_gemini_api_key: str = ""
    ) -> AnalysisResult:
        """
        Analyze policy with fallback chain across multiple models and providers.

        When policy text IS available:
        1. nvidia/nemotron (OpenRouter) - Full context
        2. groq/compound - 70k context + web search
        3. llama-3.3-70b - 12k context
        4. groq/compound-mini - 70k context
        5. kimi-k2 - Knowledge-based fallback

        When NO policy text (URL only):
        1. groq/compound - Web search to find policy
        2. groq/compound-mini - Web search backup
        3. kimi-k2 - Knowledge-based analysis
        4. nvidia/nemotron - Try anyway
        5. llama-3.3-70b - Last resort
        """
        if self.test_mode and not user_groq_api_key:
            logger.debug("Using mock analysis (test mode)")
            return self._generate_mock_analysis(policy_text, url)

        # Extract website info from URL
        website_name = ""
        website_url = url or ""
        if url:
            try:
                parsed = urlparse(url)
                website_name = parsed.netloc.replace("www.", "")
            except:
                website_name = url
        
        # Determine if we have policy text
        has_policy_text = bool(policy_text and policy_text.strip())
        
        # Select appropriate fallback chain
        if has_policy_text:
            fallback_chain = FALLBACK_MODELS_WITH_TEXT
            logger.info(f"📄 Policy text available ({len(policy_text):,} chars) - using standard model chain")
        else:
            fallback_chain = FALLBACK_MODELS_URL_ONLY
            logger.info(f"🔗 No policy text - using URL-only chain (web search models first)")

        # Models with web search capability
        web_search_models = ["groq/compound", "groq/compound-mini"]
        
        last_error = None
        max_key_rotations = 10
        
        for attempt, (model, provider) in enumerate(fallback_chain):
            is_last_fallback = (attempt == len(fallback_chain) - 1)
            context_limit = MODEL_CONTEXT_LIMITS.get(model, 50000)
            has_web_search = model in web_search_models
            
            # Build appropriate prompt based on situation
            if has_policy_text:
                # Standard analysis with policy text
                truncated_text = self._truncate_policy(policy_text, context_limit)
                prompt_text = self._build_system_prompt(user_name)
                user_message = f"Analyze this privacy policy:\n\n{truncated_text}"
            else:
                # URL-only analysis
                prompt_text = self._build_url_only_system_prompt(
                    website_url=website_url,
                    website_name=website_name,
                    user_name=user_name,
                    has_web_search=has_web_search
                )
                
                if has_web_search:
                    user_message = f"""Please find and analyze the privacy policy for: {website_name}
                    
Website URL: {website_url}

Use your web search capability to locate their privacy policy, read it, and provide a comprehensive analysis."""
                else:
                    user_message = f"Analyze the privacy practices of: {website_name} ({website_url})"
            
            key_rotation_count = 0
            invalid_response_retries = 0
            max_invalid_retries = 2  # Retry up to 2 times for invalid responses on same model
            
            while key_rotation_count < max_key_rotations:
                try:
                    logger.info(f"🤖 Attempt {attempt + 1}/{len(fallback_chain)} - {model} ({provider})")
                    start_time = time.time()
                    
                    messages = [
                        {"role": "system", "content": prompt_text},
                        {"role": "user", "content": user_message}
                    ]
                    
                    if provider == "gemini":
                        # Gemini API call
                        result_dict = self._call_gemini(
                            model, 
                            messages, 
                            user_api_key=user_gemini_api_key if attempt == 0 and key_rotation_count == 0 else None
                        )
                    elif provider == "openrouter":
                        # OpenRouter API call
                        response_data = self._call_openrouter(model, messages, context_limit)
                        content = response_data["choices"][0]["message"]["content"]
                        result_dict = self._extract_json_from_response(content)
                    else:
                        # Groq API call
                        client = self._get_groq_client(user_groq_api_key if attempt == 0 and key_rotation_count == 0 else None)
                        self.key_manager.increment_request_count()
                        
                        response = client.chat.completions.create(
                            model=model,
                            messages=messages,
                            temperature=0.3,
                            max_tokens=2000,
                            response_format={"type": "json_object"}
                        )
                        content = response.choices[0].message.content
                        result_dict = self._extract_json_from_response(content)
                    
                    api_duration = (time.time() - start_time) * 1000
                    logger.info(f"📡 API response from {model} in {api_duration:.0f}ms")
                    
                    if result_dict is None:
                        logger.warning(f"❌ Could not parse JSON from {model} response")
                        invalid_response_retries += 1
                        if invalid_response_retries < max_invalid_retries:
                            logger.info(f"🔄 Retrying {model} ({invalid_response_retries}/{max_invalid_retries})...")
                            continue
                        logger.warning(f"❌ Max retries reached for {model}, trying next model...")
                        last_error = ValueError("Could not parse JSON response")
                        break
                    
                    # Validate response content quality
                    if not self._validate_response(result_dict):
                        logger.warning(f"❌ Invalid/low-quality response from {model}")
                        invalid_response_retries += 1
                        if invalid_response_retries < max_invalid_retries:
                            logger.info(f"🔄 Retrying {model} for better response ({invalid_response_retries}/{max_invalid_retries})...")
                            continue
                        logger.warning(f"❌ Max retries reached for {model}, trying next model...")
                        last_error = ValueError("Response validation failed")
                        break
                    
                    # Log successful results
                    score = result_dict["score"]
                    num_red_flags = len(result_dict.get("red_flags", []))
                    num_actions = len(result_dict.get("user_action_items", []))
                    logger.info(f"✅ Model {model} succeeded!")
                    logger.info(f"📊 Analysis - Score: {score}/100, Red flags: {num_red_flags}, Actions: {num_actions}")
                    
                    # Process action items (assemble mailto links)
                    action_items = self._process_action_items(result_dict.get("user_action_items", []))
                    
                    # Update current deployment info
                    self.deployment = model
                    self.provider = provider
                    
                    return AnalysisResult(
                        score=result_dict["score"],
                        summary=result_dict["summary"],
                        red_flags=result_dict.get("red_flags", []),
                        user_action_items=action_items,
                        timestamp=datetime.now(timezone.utc),
                        url=url
                    )
                    
                except json.JSONDecodeError as e:
                    logger.warning(f"❌ Model {model} returned unparseable JSON: {e}")
                    invalid_response_retries += 1
                    if invalid_response_retries < max_invalid_retries:
                        logger.info(f"🔄 Retrying {model} ({invalid_response_retries}/{max_invalid_retries})...")
                        continue
                    last_error = e
                    break
                    
                except Exception as e:
                    error_str = str(e).lower()
                    
                    # Check for rate limit errors
                    if "rate_limit" in error_str or "429" in error_str or "too many requests" in error_str:
                        if provider == "groq":
                            logger.warning(f"⚠️ Rate limit hit on Groq key, rotating...")
                            next_key = self.key_manager.mark_rate_limited()
                            
                            if next_key:
                                key_rotation_count += 1
                                logger.info(f"🔄 Rotated to next Groq key (rotation #{key_rotation_count})")
                                continue
                        
                        logger.warning(f"⚠️ Rate limit on {provider}, trying next model...")
                        last_error = e
                        break
                    
                    # Check for context length errors
                    elif "context" in error_str or "too long" in error_str or "tokens" in error_str:
                        logger.warning(f"⚠️ Context too long for {model}, trying next model with lower limit...")
                        last_error = e
                        break
                    
                    # Check for model unavailability
                    elif "unavailable" in error_str or "503" in error_str or "502" in error_str:
                        logger.warning(f"⚠️ Model {model} temporarily unavailable, trying next...")
                        last_error = e
                        break
                    
                    # Generic error - try next model
                    else:
                        logger.warning(f"❌ Model {model} failed: {type(e).__name__}: {str(e)[:100]}")
                        last_error = e
                        break
            
            # Reset counters for next model
            key_rotation_count = 0
            invalid_response_retries = 0

        logger.error(f"💥 All {len(fallback_chain)} models failed!")
        raise Exception(f"All LLM models failed. Last error: {str(last_error)}")

    def _validate_response(self, response: Dict[str, Any]) -> bool:
        """
        Validates LLM response contains required fields with quality content.
        Returns True if valid, False if should try another model.
        """
        required_fields = ["score", "summary", "red_flags", "user_action_items"]
        
        # Check all required fields exist
        for field in required_fields:
            if field not in response:
                logger.warning(f"❌ Missing required field: {field}")
                return False
        
        # Validate score is a number between 0-100
        score = response.get("score")
        if not isinstance(score, (int, float)) or score < 0 or score > 100:
            logger.warning(f"❌ Invalid score value: {score}")
            return False
        
        # Validate summary has meaningful content (at least 50 characters)
        summary = response.get("summary", "")
        if not isinstance(summary, str) or len(summary.strip()) < 50:
            logger.warning(f"❌ Summary too short or invalid: {len(summary) if isinstance(summary, str) else 'not a string'} chars")
            return False
        
        # Validate red_flags is a list
        red_flags = response.get("red_flags")
        if not isinstance(red_flags, list):
            logger.warning(f"❌ red_flags is not a list: {type(red_flags)}")
            return False
        
        # Validate user_action_items is a list
        action_items = response.get("user_action_items")
        if not isinstance(action_items, list):
            logger.warning(f"❌ user_action_items is not a list: {type(action_items)}")
            return False
        
        # Validate action items have required fields
        for i, item in enumerate(action_items):
            if not isinstance(item, dict):
                logger.warning(f"❌ Action item {i} is not a dict")
                return False
            if not item.get("text"):
                logger.warning(f"❌ Action item {i} missing 'text' field")
                return False
        
        logger.debug(f"✅ Response validation passed - score: {score}, summary: {len(summary)} chars, flags: {len(red_flags)}, actions: {len(action_items)}")
        return True

    def _extract_json_from_response(self, content: str) -> Optional[Dict[str, Any]]:
        """
        Attempts to extract valid JSON from LLM response.
        Handles cases where model returns markdown-wrapped JSON or extra text.
        """
        if not content:
            return None
        
        content = content.strip()
        
        # Try direct parse first
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass
        
        # Try to extract JSON from markdown code blocks
        json_patterns = [
            r'```json\s*([\s\S]*?)\s*```',  # ```json ... ```
            r'```\s*([\s\S]*?)\s*```',       # ``` ... ```
            r'\{[\s\S]*\}',                  # Raw JSON object
        ]
        
        for pattern in json_patterns:
            match = re.search(pattern, content)
            if match:
                try:
                    json_str = match.group(1) if '```' in pattern else match.group(0)
                    return json.loads(json_str)
                except (json.JSONDecodeError, IndexError):
                    continue
        
        return None

    def _make_llm_request(
        self, 
        model: str, 
        provider: str, 
        messages: list, 
        context_limit: int,
        user_groq_api_key: str = "",
        user_gemini_api_key: str = ""
    ) -> Dict[str, Any]:
        """
        Make a single LLM request and return parsed JSON response.
        Raises exception on failure.
        """
        start_time = time.time()
        
        if provider == "gemini":
            return self._call_gemini(model, messages, user_api_key=user_gemini_api_key)
        
        if provider == "openrouter":
            response_data = self._call_openrouter(model, messages, context_limit)
            content = response_data["choices"][0]["message"]["content"]
        else:
            client = self._get_groq_client(user_groq_api_key if user_groq_api_key else None)
            self.key_manager.increment_request_count()
            
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.3,
                max_tokens=2000,
                response_format={"type": "json_object"}
            )
            content = response.choices[0].message.content
        
        api_duration = (time.time() - start_time) * 1000
        logger.info(f"📡 API call to {model} completed in {api_duration:.0f}ms")
        
        # Try to extract JSON from response
        result_dict = self._extract_json_from_response(content)
        
        if result_dict is None:
            raise ValueError(f"Could not parse JSON from response: {content[:200]}...")
        
        return result_dict

