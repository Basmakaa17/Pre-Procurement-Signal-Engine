"""
FastAPI application entry point for Publicus Signal Engine
"""
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware

from app.api import grants, pipeline, search, signals

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown"""
    # Startup
    yield
    # Shutdown


# Create FastAPI app
app = FastAPI(
    title="Publicus Signal Engine",
    description="Government grant data intelligence and procurement signal detection",
    version="1.0.0",
    lifespan=lifespan,
)

# Add rate limiter to app
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS middleware
# Read allowed origins from environment variable
import os
from dotenv import load_dotenv

load_dotenv()

allowed_origins_env = os.getenv("ALLOWED_ORIGINS", "*")
if allowed_origins_env == "*":
    # For prototype, allow all origins (restrict in production)
    allow_origins = ["*"]
else:
    # Parse comma-separated list
    allow_origins = [origin.strip() for origin in allowed_origins_env.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins if allow_origins != ["*"] else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request logging middleware
class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log all requests with timing"""
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Process request
        response = await call_next(request)
        
        # Calculate duration
        duration_ms = int((time.time() - start_time) * 1000)
        
        # Log request
        print(f"{request.method} {request.url.path} → {response.status_code} in {duration_ms}ms")
        
        return response


app.add_middleware(LoggingMiddleware)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors"""
    error_type = type(exc).__name__
    error_message = str(exc)
    
    print(f"Unhandled exception: {error_type} - {error_message}")
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": error_message,
            "type": error_type,
        },
    )


# Validation error handler
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handler for request validation errors"""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Validation error",
            "type": "RequestValidationError",
            "details": exc.errors(),
        },
    )


# Include routers and set rate limiter state
app.include_router(signals.router)
app.include_router(grants.router)
app.include_router(pipeline.router)
app.include_router(search.router)

# Set rate limiter state for all routers
app.state.limiter = limiter
# Share the limiter state with all router limiters
for router_module in [signals, grants, pipeline, search]:
    router_module.limiter.state = app.state.limiter


# Rate limiting is applied via decorators on individual routes


# Health endpoint
@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "ok", "service": "publicus-signal-engine"}


# Overview endpoint combining stats
@app.get("/api/overview")
async def get_overview(request: Request):
    """
    Get combined overview statistics for dashboard
    Combines grant stats and signal stats in one call
    """
    try:
        from app.database.client import get_supabase_client
        
        supabase = get_supabase_client()
        
        # Get grant stats (exclude noise grants from dashboard)
        all_grants = supabase.table("grant_records").select("*").neq(
            "procurement_signal_category", "noise"
        ).eq("is_quarantined", False).execute()
        grants = all_grants.data
        
        total_grants = len(grants)
        total_funding = sum(
            float(g.get("amount_cad", 0) or 0)
            for g in grants
        )
        
        # Count by source
        sources: dict[str, int] = {}
        for g in grants:
            source = g.get("source", "unknown")
            sources[source] = sources.get(source, 0) + 1
        
        # Count by region
        regions: dict[str, int] = {}
        for g in grants:
            region = g.get("region") or "Unknown"
            regions[region] = regions.get(region, 0) + 1
        
        # Count by theme
        themes: dict[str, int] = {}
        for g in grants:
            theme = g.get("funding_theme")
            if theme:
                themes[theme] = themes.get(theme, 0) + 1
        
        quarantined_count = sum(1 for g in grants if g.get("is_quarantined", False))
        
        # Average LLM confidence
        confidences = [
            float(g.get("llm_confidence", 0) or 0)
            for g in grants
            if g.get("llm_confidence") is not None
        ]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        
        # Business relevance distribution
        business_relevance: dict[str, int] = {"high": 0, "medium": 0, "low": 0, "unknown": 0}
        for g in grants:
            br = g.get("business_relevance", "unknown") or "unknown"
            if br in business_relevance:
                business_relevance[br] += 1
            else:
                business_relevance["unknown"] += 1
        
        # Procurement signal distribution
        procurement_signal: dict[str, int] = {"high": 0, "medium": 0, "low": 0, "noise": 0, "unscored": 0}
        for g in grants:
            ps = g.get("procurement_signal_category")
            if ps and ps in procurement_signal:
                procurement_signal[ps] += 1
            else:
                procurement_signal["unscored"] += 1
        
        # Get signal stats
        all_signals = supabase.table("procurement_signals").select("*").eq("is_active", True).execute()
        signals = all_signals.data
        
        total_signals = len(signals)
        signal_funding = sum(
            float(s.get("total_funding_cad", 0) or 0)
            for s in signals
        )
        
        # Signal strength breakdown
        signal_strengths = {
            "strong": sum(1 for s in signals if s.get("signal_strength") == "strong"),
            "moderate": sum(1 for s in signals if s.get("signal_strength") == "moderate"),
            "weak": sum(1 for s in signals if s.get("signal_strength") == "weak"),
        }
        
        # Last pipeline run
        pipeline_runs = supabase.table("pipeline_runs").select("started_at").order(
            "started_at", desc=True
        ).limit(1).execute()
        
        last_run = None
        if pipeline_runs.data:
            last_run = pipeline_runs.data[0].get("started_at")
        
        return {
            "grants": {
                "total": total_grants,
                "total_funding_cad": total_funding,
                "sources": sources,
                "regions": regions,
                "themes": themes,
                "quarantined_count": quarantined_count,
                "avg_llm_confidence": avg_confidence,
                "business_relevance": business_relevance,
                "procurement_signal": procurement_signal,
            },
            "signals": {
                "total": total_signals,
                "total_funding_cad": signal_funding,
                "strengths": signal_strengths,
            },
            "last_pipeline_run": last_run,
        }
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "error": str(e),
                "type": type(e).__name__,
            },
        )


# Rate limiting is applied via decorators on individual routes
