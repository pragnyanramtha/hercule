"""
Hercule API
FastAPI backend for analyzing privacy policies using Groq LLM.
"""
import os
import logging
import time
import asyncio
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator
from dotenv import load_dotenv

from models import AnalysisResult
from service_llm import LLMService
from service_discovery import DiscoveryService
from cache import cache_manager

# Load environment variables
load_dotenv()

# Configure logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("hercule-api")

# Initialize FastAPI app
app = FastAPI(title="Hercule API")

# CORS configuration
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

# Initialize services
llm_service = LLMService()
discovery_service = DiscoveryService()


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Middleware to log all incoming requests."""
    start_time = time.time()
    logger.info(f"➡️  {request.method} {request.url.path} from {request.client.host if request.client else 'unknown'}")
    
    response = await call_next(request)
    
    duration_ms = (time.time() - start_time) * 1000
    status_emoji = "✅" if response.status_code < 400 else "❌"
    logger.info(f"{status_emoji} {request.method} {request.url.path} → {response.status_code} ({duration_ms:.1f}ms)")
    
    return response


class AnalyzeRequest(BaseModel):
    """Request model for /analyze endpoint."""
    policy_text: str = ""
    url: str = ""
    user_name: str = ""  # User's name for personalized emails
    user_groq_api_key: str = ""  # User-provided API key

    @field_validator('policy_text')
    @classmethod
    def validate_policy_text(cls, v: str) -> str:
        if v:
            return v.replace('\x00', '').strip()
        return ""

    @field_validator('url')
    @classmethod
    def validate_url(cls, v: str) -> str:
        if v:
            return v.replace('\x00', '').strip()
        return ""
    
    @field_validator('user_name')
    @classmethod
    def validate_user_name(cls, v: str) -> str:
        if v:
            return v.replace('\x00', '').strip()[:100]  # Limit name length
        return ""
    
    @field_validator('user_groq_api_key')
    @classmethod
    def validate_api_key(cls, v: str) -> str:
        if v:
            return v.replace('\x00', '').strip()
        return ""


class HealthResponse(BaseModel):
    """Response model for health check."""
    status: str
    timestamp: str
    cache_size: int
    test_mode: bool
    provider: str
    model: Optional[str] = None


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(timezone.utc).isoformat(),
        cache_size=cache_manager.size(),
        test_mode=llm_service.test_mode,
        provider=llm_service.provider,
        model=llm_service.deployment
    )


@app.post("/analyze", response_model=AnalysisResult)
async def analyze_policy(request: AnalyzeRequest):
    """
    Analyze a privacy policy.
    
    If policy_text is empty but url is provided, will aggressively search for
    the privacy policy using:
    1. Parallel checking of 25+ common privacy policy paths
    2. Homepage scraping for privacy links
    3. DuckDuckGo search as last resort
    
    Does NOT return until privacy policy is found and analyzed.
    """
    policy_text = request.policy_text
    policy_url = request.url
    user_name = request.user_name
    user_api_key = request.user_groq_api_key
    
    # Log user settings if provided
    if user_name:
        logger.info(f"👤 User name provided: {user_name}")
    if user_api_key:
        logger.info(f"🔑 User API key provided (ending ...{user_api_key[-6:]})")
    
    # CACHE-FIRST: Check cache by URL and domain BEFORE any discovery
    if policy_url:
        # Try exact URL match first
        url_hash = cache_manager.generate_url_key(policy_url)
        cached_result = cache_manager.get(url_hash)
        if cached_result is not None:
            logger.info(f"💾 Cache HIT by URL - returning cached result (score: {cached_result.score})")
            return cached_result
        
        # Try domain-level cache (catches any page on the same domain)
        domain_hash = cache_manager.generate_domain_key(policy_url)
        cached_result = cache_manager.get(domain_hash)
        if cached_result is not None:
            logger.info(f"💾 Cache HIT by domain - returning cached result (score: {cached_result.score})")
            return cached_result
        
        logger.info(f"🔍 Cache MISS - starting discovery for: {policy_url}")
    
    # If no policy text provided, use aggressive discovery
    if not policy_text and policy_url:
        logger.info(f"🔍 No policy text provided. Starting aggressive discovery for: {policy_url}")
        
        try:
            # Try discovery with 10-second timeout (reduced from 20s)
            discovery_result = await asyncio.wait_for(
                discovery_service.discover_and_extract(policy_url),
                timeout=10.0
            )
            
            if not discovery_result.success or not discovery_result.policy_text:
                logger.warning(f"❌ Discovery failed for {policy_url}: {discovery_result.error}")
                raise ValueError("Discovery unsuccessful")
            
            policy_text = discovery_result.policy_text
            policy_url = discovery_result.policy_url or policy_url
            logger.info(f"✅ Discovery successful via {discovery_result.method}: {policy_url}")
            
        except (asyncio.TimeoutError, ValueError) as e:
            # Discovery failed or timed out - use groq/compound with web search
            if isinstance(e, asyncio.TimeoutError):
                logger.warning(f"⏱️ Discovery timeout after 10s. Using groq/compound with web search...")
            else:
                logger.warning(f"❌ Discovery failed. Using groq/compound with web search...")
            policy_text = None  # Let groq/compound fetch it via web search
        except Exception as e:
            # Unexpected error - use groq/compound with web search
            logger.warning(f"❌ Discovery error: {e}. Using groq/compound with web search...")
            policy_text = None
    
    # If we still don't have policy text, use groq/compound with web search
    if not policy_text and policy_url:
        logger.info(f"🌐 Using groq/compound to analyze URL via web search: {policy_url}")
        
        # Force groq/compound model for this request
        original_models = llm_service.models
        llm_service.models = ["groq/compound"]  # Only use compound for web search
        
        try:
            # Call LLM with URL only - groq/compound will search and analyze
            result = llm_service.analyze_policy(
                "", policy_url,
                user_name=user_name,
                user_groq_api_key=user_api_key
            )
            logger.info(f"✨ Analysis via groq/compound complete - Score: {result.score}/100")
            
            # Restore original models
            llm_service.models = original_models
            
            # Cache the result by URL and domain
            if policy_url:
                url_hash = cache_manager.generate_url_key(policy_url)
                cache_manager.set(url_hash, result)
                domain_hash = cache_manager.generate_domain_key(policy_url)
                cache_manager.set(domain_hash, result)
            
            return result
        except Exception as e:
            llm_service.models = original_models
            error_msg = str(e)
            
            # Check if it's a rate limit error
            if "rate_limit" in error_msg.lower() or "429" in error_msg:
                logger.error(f"💸 Rate limit reached - try again in a few seconds")
                raise HTTPException(
                    status_code=429,
                    detail="Rate limit exceeded. Please try again in a few seconds."
                )
            
            logger.error(f"❌ groq/compound analysis failed: {e}")
            raise HTTPException(
                status_code=404,
                detail=f"Could not find or analyze privacy policy. Discovery timed out and fallback failed: {error_msg[:100]}"
            )
    
    # Validate we have policy text
    if not policy_text:
        raise HTTPException(
            status_code=400,
            detail="Either policy_text or url must be provided"
        )
    
    # Generate cache key from text
    text_hash = cache_manager.generate_key(policy_text)
    logger.info(f"📝 Analyzing policy from: {policy_url or 'direct text'} (hash: {text_hash[:12]}...)")
    
    # Check cache by text hash (in case URL check missed but text is same)
    cached_result = cache_manager.get(text_hash)
    if cached_result is not None:
        logger.info(f"💾 Cache HIT by text - returning cached result (score: {cached_result.score})")
        return cached_result
    
    logger.info(f"🔍 Cache MISS - calling {llm_service.provider.upper()} LLM...")
    
    # Call LLM with user settings
    start_time = time.time()
    try:
        result = llm_service.analyze_policy(
            policy_text, policy_url,
            user_name=user_name,
            user_groq_api_key=user_api_key
        )
        duration_ms = (time.time() - start_time) * 1000
        logger.info(f"✨ Analysis complete - Score: {result.score}/100, Red flags: {len(result.red_flags)}, Duration: {duration_ms:.0f}ms")
    except ValueError as e:
        logger.warning(f"⚠️ Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except ConnectionError as e:
        logger.error(f"🔌 Connection error: {e}")
        raise HTTPException(status_code=503, detail=f"LLM service unavailable: {e}")
    except Exception as e:
        logger.error(f"❌ Analysis error: {type(e).__name__}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to analyze policy: {type(e).__name__}")
    
    # Cache result by text hash, URL, and domain
    cache_manager.set(text_hash, result)
    if policy_url:
        url_hash = cache_manager.generate_url_key(policy_url)
        cache_manager.set(url_hash, result)
        # Also cache by domain for faster lookups from any page on the domain
        domain_hash = cache_manager.generate_domain_key(policy_url)
        cache_manager.set(domain_hash, result)
    logger.info(f"💾 Result cached by text, URL, and domain (cache size: {cache_manager.size()})")
    
    return result


@app.get("/discover_policy")
async def discover_policy(url: str):
    """
    Discover privacy policy URL for a website.
    Returns the policy URL and extracted text.
    """
    if not url:
        raise HTTPException(status_code=400, detail="URL is required")
    
    result = await discovery_service.discover_and_extract(url)
    
    if not result.success:
        raise HTTPException(status_code=404, detail=result.error or "Privacy policy not found")
    
    return {
        "policy_url": result.policy_url,
        "policy_text": result.policy_text,
        "method": result.method
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
