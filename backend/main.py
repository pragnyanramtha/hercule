"""
Privacy Policy Analyzer API
FastAPI backend for analyzing privacy policies using Azure OpenAI.
"""
import os
import logging
import time
from datetime import datetime, timezone
from typing import List

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator
from dotenv import load_dotenv

from models import AnalysisResult
from service_llm import LLMService
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
logger = logging.getLogger("privacy-api")

# Initialize FastAPI app
app = FastAPI(title="Privacy Policy Analyzer API")

# CORS configuration - restrict in production
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

# Initialize LLM service
llm_service = LLMService()


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Middleware to log all incoming requests."""
    start_time = time.time()
    
    # Log incoming request
    logger.info(f"➡️  {request.method} {request.url.path} from {request.client.host if request.client else 'unknown'}")
    
    response = await call_next(request)
    
    # Calculate duration
    duration_ms = (time.time() - start_time) * 1000
    
    # Log response
    status_emoji = "✅" if response.status_code < 400 else "❌"
    logger.info(f"{status_emoji} {request.method} {request.url.path} → {response.status_code} ({duration_ms:.1f}ms)")
    
    return response


class AnalyzeRequest(BaseModel):
    """Request model for /analyze endpoint with validation."""
    policy_text: str
    url: str = ""
    
    @field_validator('policy_text')
    @classmethod
    def validate_policy_text(cls, v: str) -> str:
        """Validate policy_text is not empty or whitespace-only."""
        if not v or not v.strip():
            raise ValueError('policy_text cannot be empty or whitespace-only')
        # Basic sanitization - remove null bytes
        sanitized = v.replace('\x00', '')
        return sanitized
    
    @field_validator('url')
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Basic URL sanitization."""
        if v:
            # Remove null bytes and trim
            return v.replace('\x00', '').strip()
        return v


class HealthResponse(BaseModel):
    """Response model for health check."""
    status: str
    timestamp: str
    cache_size: int
    test_mode: bool
    provider: str
    dev_mode: bool


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint with cache and service status."""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(timezone.utc).isoformat(),
        cache_size=cache_manager.size(),
        test_mode=llm_service.test_mode,
        provider=llm_service.provider,
        dev_mode=getattr(llm_service, 'dev_mode', False)
    )


@app.post("/analyze", response_model=AnalysisResult)
async def analyze_policy(request: AnalyzeRequest):
    """
    Analyze a privacy policy and return structured insights.
    
    Args:
        request: AnalyzeRequest containing policy_text and optional url
        
    Returns:
        AnalysisResult with score, summary, red flags, and action items
        
    Raises:
        HTTPException: 400 if validation fails, 500 if analysis fails
    """
    # Generate cache key from policy text
    text_hash = cache_manager.generate_key(request.policy_text)
    policy_preview = request.policy_text[:100].replace('\n', ' ')[:50] + "..."
    
    logger.debug(f"Policy preview: {policy_preview}")
    logger.info(f"📝 Analyzing policy from URL: {request.url or 'N/A'} (hash: {text_hash[:12]}...)")
    
    # Check cache first
    cached_result = cache_manager.get(text_hash)
    if cached_result is not None:
        logger.info(f"💾 Cache HIT - returning cached result (score: {cached_result.score})")
        return cached_result
    
    logger.info(f"🔍 Cache MISS - calling {llm_service.provider.upper()} LLM...")
    
    # Cache miss - call LLM service
    start_time = time.time()
    try:
        result = llm_service.analyze_policy(request.policy_text, request.url)
        duration_ms = (time.time() - start_time) * 1000
        logger.info(f"✨ Analysis complete - Score: {result.score}/100, Red flags: {len(result.red_flags)}, Duration: {duration_ms:.0f}ms")
    except ValueError as e:
        logger.warning(f"⚠️  Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except ConnectionError as e:
        logger.error(f"🔌 Connection error to LLM service: {e}")
        raise HTTPException(status_code=503, detail=f"LLM service unavailable: {e}")
    except Exception as e:
        logger.error(f"❌ Error analyzing policy: {type(e).__name__}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to analyze policy: {type(e).__name__}"
        )
    
    # Store result in cache
    cache_manager.set(text_hash, result)
    logger.debug(f"💾 Result cached (cache size: {cache_manager.size()})")
    
    return result


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
