"""
API routes for procurement signals
"""
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.database.client import get_supabase_client
from app.intelligence.rfp_predictor import predict_rfps_for_signal

# Rate limiter instance (will be set from main.py)
limiter = Limiter(key_func=get_remote_address)

router = APIRouter(prefix="/api/signals", tags=["signals"])


class GrantPreview(BaseModel):
    """Preview of a supporting grant record"""
    id: str
    recipient_name: str
    amount_cad: Optional[float]
    award_date: Optional[str]


class SignalResponse(BaseModel):
    """Full signal response with preview"""
    id: str
    signal_name: str
    funding_theme: str
    procurement_category: str
    department_cluster: Optional[str]
    region: Optional[str]
    total_funding_cad: Optional[float]
    grant_count: int
    earliest_grant_date: Optional[str]
    latest_grant_date: Optional[str]
    time_horizon_min_months: Optional[int]
    time_horizon_max_months: Optional[int]
    confidence_score: Optional[float]
    signal_strength: Optional[str]
    predicted_rfp_window_start: Optional[str]
    predicted_rfp_window_end: Optional[str]
    supporting_grant_ids: list[str]
    is_active: bool
    created_at: str
    updated_at: str
    supporting_grants_preview: list[GrantPreview]


class SignalDetailResponse(SignalResponse):
    """Full signal response with all supporting grants and RFP predictions"""
    supporting_grants: list[dict]
    rfp_predictions: Optional[dict] = None


class ThemeStats(BaseModel):
    """Theme statistics"""
    theme: str
    count: int
    total_funding: float


class RegionStats(BaseModel):
    """Region statistics"""
    region: str
    signal_count: int


@router.get("", response_model=list[SignalResponse])
@limiter.limit("100/minute")
async def get_signals(
    request: Request,
    region: Optional[str] = Query(None, description="Filter by region code"),
    theme: Optional[str] = Query(None, description="Filter by funding theme"),
    strength: Optional[str] = Query(None, description="Filter by signal strength: weak, moderate, strong"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of results"),
):
    """
    Get list of procurement signals with optional filters
    Returns signals ordered by confidence_score DESC
    """
    try:
        supabase = get_supabase_client()
        query = supabase.table("procurement_signals").select("*").eq("is_active", True)
        
        if region:
            query = query.eq("region", region)
        if theme:
            query = query.eq("funding_theme", theme)
        if strength:
            query = query.eq("signal_strength", strength)
        
        query = query.order("confidence_score", desc=True).limit(limit)
        response = query.execute()
        
        signals = []
        for signal in response.data:
            # Get preview of supporting grants (first 3)
            grant_ids = signal.get("supporting_grant_ids", [])
            grant_previews = []
            
            if grant_ids:
                grants_response = supabase.table("grant_records").select(
                    "id, recipient_name, amount_cad, award_date, issuer_canonical"
                ).in_("id", grant_ids).execute()
                
                # Deduplicate grants based on content (not just ID)
                seen_hashes = set()
                deduped_grants = []
                
                for grant in grants_response.data:
                    # Create a content hash for deduplication
                    content_hash = f"{grant.get('recipient_name', '')}|{grant.get('amount_cad', '')}|{grant.get('award_date', '')}|{grant.get('issuer_canonical', '')}"
                    
                    if content_hash not in seen_hashes:
                        seen_hashes.add(content_hash)
                        deduped_grants.append(grant)
                
                # Take first 3 after deduplication
                for grant in deduped_grants[:3]:
                    grant_previews.append(GrantPreview(
                        id=grant["id"],
                        recipient_name=grant.get("recipient_name", ""),
                        amount_cad=float(grant["amount_cad"]) if grant.get("amount_cad") else None,
                        award_date=grant.get("award_date"),
                    ))
            
            signals.append(SignalResponse(
                **signal,
                supporting_grants_preview=grant_previews,
            ))
        
        return signals
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch signals: {str(e)}")


@router.get("/{signal_id}", response_model=SignalDetailResponse)
@limiter.limit("100/minute")
async def get_signal_detail(request: Request, signal_id: str):
    """
    Get full signal record with all supporting grant records
    """
    try:
        supabase = get_supabase_client()
        
        # Get signal
        signal_response = supabase.table("procurement_signals").select("*").eq("id", signal_id).execute()
        
        if not signal_response.data:
            raise HTTPException(status_code=404, detail="Signal not found")
        
        signal = signal_response.data[0]
        grant_ids = signal.get("supporting_grant_ids", [])
        
        # Get all supporting grants
        supporting_grants = []
        if grant_ids:
            grants_response = supabase.table("grant_records").select("*").in_("id", grant_ids).execute()
            
            # Deduplicate grants based on content (not just ID)
            seen_hashes = set()
            for grant in grants_response.data:
                # Create a content hash for deduplication
                content_hash = f"{grant.get('recipient_name', '')}|{grant.get('amount_cad', '')}|{grant.get('award_date', '')}|{grant.get('issuer_canonical', '')}"
                
                if content_hash not in seen_hashes:
                    seen_hashes.add(content_hash)
                    supporting_grants.append(grant)
        
        # Get preview (first 3)
        grant_previews = []
        for grant in supporting_grants[:3]:
            grant_previews.append(GrantPreview(
                id=grant["id"],
                recipient_name=grant.get("recipient_name", ""),
                amount_cad=float(grant["amount_cad"]) if grant.get("amount_cad") else None,
                award_date=grant.get("award_date"),
            ))
        
        # Generate aggregated RFP predictions for this signal
        rfp_preds = predict_rfps_for_signal(
            signal_name=signal.get("signal_name", ""),
            funding_theme=signal.get("funding_theme", ""),
            total_funding_cad=float(signal.get("total_funding_cad", 0) or 0),
            grant_count=signal.get("grant_count", 0),
            department_cluster=signal.get("department_cluster"),
        )
        
        return SignalDetailResponse(
            **signal,
            supporting_grants_preview=grant_previews,
            supporting_grants=supporting_grants,
            rfp_predictions=rfp_preds,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch signal: {str(e)}")


@router.get("/themes", response_model=list[ThemeStats])
@limiter.limit("100/minute")
async def get_themes(request: Request):
    """
    Get distinct list of funding themes with count and total funding
    """
    try:
        supabase = get_supabase_client()
        
        # Get all active signals grouped by theme
        response = supabase.table("procurement_signals").select(
            "funding_theme, total_funding_cad"
        ).eq("is_active", True).execute()
        
        # Aggregate by theme
        theme_stats: dict[str, dict] = {}
        for signal in response.data:
            theme = signal.get("funding_theme")
            if not theme:
                continue
            
            if theme not in theme_stats:
                theme_stats[theme] = {"count": 0, "total_funding": 0.0}
            
            theme_stats[theme]["count"] += 1
            funding = float(signal.get("total_funding_cad", 0) or 0)
            theme_stats[theme]["total_funding"] += funding
        
        return [
            ThemeStats(theme=theme, count=stats["count"], total_funding=stats["total_funding"])
            for theme, stats in theme_stats.items()
        ]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch themes: {str(e)}")


@router.get("/regions", response_model=list[RegionStats])
@limiter.limit("100/minute")
async def get_regions(request: Request):
    """
    Get distinct regions with signal count
    """
    try:
        supabase = get_supabase_client()
        
        # Get all active signals
        response = supabase.table("procurement_signals").select("region").eq("is_active", True).execute()
        
        # Count by region
        region_counts: dict[str, int] = {}
        for signal in response.data:
            region = signal.get("region") or "Unknown"
            region_counts[region] = region_counts.get(region, 0) + 1
        
        return [
            RegionStats(region=region, signal_count=count)
            for region, count in region_counts.items()
        ]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch regions: {str(e)}")
