import os
import json
import hashlib
from pathlib import Path
from typing import Optional
from datetime import datetime, timedelta, timezone
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from models import AnalysisResult
from service_llm import LLMService
# use uv


# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(title="Privacy Policy Analyzer API")

# Configure CORS - allow all origins for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize LLM service
llm_service = LLMService()

# Cache file path
CACHE_FILE = Path(__file__).parent / "cache.json"


class AnalyzeRequest(BaseModel):
    """Request model for /analyze endpoint."""
    policy_text: str
    url: str = ""


def generate_cache_key(policy_text: str) -> str:
    """
    Generate SHA-256 hash of policy text for cache lookup.
    
    Args:
        policy_text: The privacy policy text
        
    Returns:
        SHA-256 hash as hexadecimal string
    """
    normalized = policy_text.strip().lower()
    return hashlib.sha256(normalized.encode('utf-8')).hexdigest()


def load_cache() -> dict:
    """
    Load cache from JSON file.
    
    Returns:
        Dictionary containing cached analysis results
    """
    if not CACHE_FILE.exists():
        return {}
    
    try:
        with open(CACHE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading cache: {e}")
        return {}


def save_cache(cache: dict) -> None:
    """
    Save cache to JSON file.
    
    Args:
        cache: Dictionary containing cached analysis results
    """
    try:
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cache, f, indent=2, default=str)
    except Exception as e:
        print(f"Error saving cache: {e}")


def get_cached_analysis(text_hash: str) -> Optional[AnalysisResult]:
    """
    Retrieve cached analysis result if it exists and is valid.
    
    Args:
        text_hash: SHA-256 hash of the policy text
        
    Returns:
        AnalysisResult if cache hit and valid, None otherwise
    """
    cache = load_cache()
    
    if text_hash not in cache:
        return None
    
    cached_entry = cache[text_hash]
    
    # Check if cache is still valid (within 30 days)
    try:
        cached_timestamp = datetime.fromisoformat(cached_entry["timestamp"])
        if datetime.now(timezone.utc) - cached_timestamp > timedelta(days=30):
            return None
    except Exception:
        return None
    
    # Convert cached result to AnalysisResult model
    try:
        return AnalysisResult(**cached_entry["result"])
    except Exception as e:
        print(f"Error parsing cached result: {e}")
        return None


def store_analysis(text_hash: str, result: AnalysisResult) -> None:
    """
    Store analysis result in cache.
    
    Args:
        text_hash: SHA-256 hash of the policy text
        result: AnalysisResult to cache
    """
    cache = load_cache()
    
    cache[text_hash] = {
        "result": result.model_dump(mode='json'),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "text_hash": text_hash
    }
    
    save_cache(cache)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@app.post("/analyze", response_model=AnalysisResult)
async def analyze_policy(request: AnalyzeRequest):
    """
    Analyze a privacy policy and return structured insights.
    
    Args:
        request: AnalyzeRequest containing policy_text and optional url
        
    Returns:
        AnalysisResult with score, summary, red flags, and action items
        
    Raises:
        HTTPException: 500 if analysis fails
    """
    try:
        # Generate cache key from policy text
        text_hash = generate_cache_key(request.policy_text)
        
        # Check cache first
        cached_result = get_cached_analysis(text_hash)
        if cached_result is not None:
            print(f"Cache hit for hash: {text_hash[:16]}...")
            return cached_result
        
        print(f"Cache miss for hash: {text_hash[:16]}... Calling LLM")
        
        # Cache miss - call LLM service
        result = llm_service.analyze_policy(request.policy_text, request.url)
        
        # Store result in cache
        store_analysis(text_hash, result)
        
        return result
        
    except Exception as e:
        print(f"Error analyzing policy: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to analyze policy: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
