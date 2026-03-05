"""
API routes for grant records
"""
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request, Response
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.database.client import get_supabase_client

# Rate limiter instance
limiter = Limiter(key_func=get_remote_address)

router = APIRouter(prefix="/api/grants", tags=["grants"])


class GrantResponse(BaseModel):
    """Grant record response"""
    id: str
    source: str
    source_record_id: Optional[str] = None
    issuer_canonical: str = ""
    issuer_raw: Optional[str] = None
    recipient_name: str = ""
    recipient_name_normalized: Optional[str] = None
    recipient_type: Optional[str] = None
    agreement_type: Optional[str] = None
    amount_cad: Optional[float] = None
    amount_unknown: bool = False
    award_date: Optional[str] = None
    fiscal_year: Optional[str] = None
    region: Optional[str] = None
    description: Optional[str] = None
    funding_theme: Optional[str] = None
    procurement_category: Optional[str] = None
    sector_tags: Optional[list[str]] = None
    llm_confidence: Optional[float] = None
    llm_classified_at: Optional[str] = None
    quality_flags: Optional[list] = None
    business_relevance: Optional[str] = None
    business_relevance_score: Optional[float] = None
    business_relevance_reasons: Optional[list] = None
    procurement_signal_score: Optional[int] = None
    procurement_signal_category: Optional[str] = None
    procurement_signal_reasons: Optional[list] = None
    grant_duration_months: Optional[int] = None
    predicted_rfps: Optional[list] = None
    rfp_forecast_summary: Optional[str] = None
    rfp_forecast_confidence: Optional[str] = None
    total_predicted_rfp_value_min: Optional[float] = None
    total_predicted_rfp_value_max: Optional[float] = None
    predicted_rfp_count: Optional[int] = None
    is_quarantined: bool = False
    dedup_hash: Optional[str] = None
    raw_data: Optional[dict] = None
    created_at: str = ""
    updated_at: str = ""


class GrantStats(BaseModel):
    """Grant statistics"""
    total_grants: int
    total_funding_cad: float
    sources: dict[str, int]
    regions: dict[str, int]
    themes: dict[str, int]
    business_relevance: dict[str, int]
    procurement_signal: dict[str, int]
    quarantined_count: int
    avg_llm_confidence: float
    last_pipeline_run: Optional[str]


@router.get("", response_model=list[GrantResponse])
@limiter.limit("100/minute")
async def get_grants(
    request: Request,
    response: Response,
    source: Optional[str] = Query(None, description="Filter by source"),
    region: Optional[str] = Query(None, description="Filter by region"),
    theme: Optional[str] = Query(None, description="Filter by funding theme"),
    business_relevance: Optional[list[str]] = Query(None, description="Filter by business relevance (high, medium, low)"),
    procurement_signal: Optional[list[str]] = Query(None, description="Filter by procurement signal category (high, medium, low, noise)"),
    quarantined: bool = Query(False, description="Include quarantined records"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
):
    """
    Get paginated list of grant records with optional filters
    """
    try:
        supabase = get_supabase_client()
        query = supabase.table("grant_records").select("*", count="exact")
        
        if source:
            query = query.eq("source", source)
        if region:
            query = query.eq("region", region)
        if theme:
            query = query.eq("funding_theme", theme)
        
        # Handle business relevance filter (single value or list)
        if business_relevance:
            if len(business_relevance) == 1:
                query = query.eq("business_relevance", business_relevance[0])
            else:
                query = query.in_("business_relevance", business_relevance)
        
        # Handle procurement signal filter (single value or list)
        if procurement_signal:
            if len(procurement_signal) == 1:
                query = query.eq("procurement_signal_category", procurement_signal[0])
            else:
                query = query.in_("procurement_signal_category", procurement_signal)
                
        if not quarantined:
            query = query.eq("is_quarantined", False)
        
        # Get total count
        count_response = query.execute()
        total_count = count_response.count if hasattr(count_response, 'count') else len(count_response.data)
        
        # Apply pagination
        query = query.order("created_at", desc=True).range(offset, offset + limit - 1)
        data_response = query.execute()
        
        # Set total count header
        response.headers["X-Total-Count"] = str(total_count)
        
        return data_response.data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch grants: {str(e)}")


@router.get("/stats", response_model=GrantStats)
@limiter.limit("100/minute")
async def get_grant_stats(request: Request):
    """
    Get aggregate statistics for grant records
    """
    try:
        supabase = get_supabase_client()
        
        # Get all grants
        all_grants = supabase.table("grant_records").select("*").execute()
        grants = all_grants.data
        
        # Calculate stats
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
        
        # Count by business relevance
        business_relevance: dict[str, int] = {
            "high": 0,
            "medium": 0,
            "low": 0,
            "unknown": 0
        }
        for g in grants:
            relevance = g.get("business_relevance", "unknown")
            business_relevance[relevance] = business_relevance.get(relevance, 0) + 1
        
        # Count by procurement signal category
        procurement_signal: dict[str, int] = {
            "high": 0,
            "medium": 0,
            "low": 0,
            "noise": 0,
            "unscored": 0,
        }
        for g in grants:
            ps_cat = g.get("procurement_signal_category")
            if ps_cat and ps_cat in procurement_signal:
                procurement_signal[ps_cat] += 1
            else:
                procurement_signal["unscored"] += 1
        
        # Quarantined count
        quarantined_count = sum(1 for g in grants if g.get("is_quarantined", False))
        
        # Average LLM confidence
        confidences = [
            float(g.get("llm_confidence", 0) or 0)
            for g in grants
            if g.get("llm_confidence") is not None
        ]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        
        # Last pipeline run
        pipeline_runs = supabase.table("pipeline_runs").select("started_at").order(
            "started_at", desc=True
        ).limit(1).execute()
        
        last_run = None
        if pipeline_runs.data:
            last_run = pipeline_runs.data[0].get("started_at")
        
        return GrantStats(
            total_grants=total_grants,
            total_funding_cad=total_funding,
            sources=sources,
            regions=regions,
            themes=themes,
            business_relevance=business_relevance,
            procurement_signal=procurement_signal,
            quarantined_count=quarantined_count,
            avg_llm_confidence=avg_confidence,
            last_pipeline_run=last_run,
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch stats: {str(e)}")


@router.get("/{grant_id}", response_model=GrantResponse)
@limiter.limit("100/minute")
async def get_grant(request: Request, grant_id: str):
    """
    Get full grant record by ID
    """
    try:
        supabase = get_supabase_client()
        
        response = supabase.table("grant_records").select("*").eq("id", grant_id).execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="Grant not found")
        
        return response.data[0]
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch grant: {str(e)}")
