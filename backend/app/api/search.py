"""
API routes for search functionality
"""
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.database.client import get_supabase_client

# Rate limiter instance
limiter = Limiter(key_func=get_remote_address)

router = APIRouter(prefix="/api/search", tags=["search"])


class SearchResult(BaseModel):
    """Search result for a grant record"""
    id: str
    source: str
    issuer_canonical: str
    recipient_name: str
    amount_cad: Optional[float]
    award_date: Optional[str]
    region: Optional[str]
    description: Optional[str]
    funding_theme: Optional[str]
    procurement_category: Optional[str]
    relevance_snippet: Optional[str]


@router.get("", response_model=list[SearchResult])
@limiter.limit("100/minute")
async def search_grants(
    request: Request,
    q: str = Query(..., min_length=2, description="Search query"),
):
    """
    Search across grant records using PostgreSQL full-text search
    Searches in: description, recipient_name, issuer_canonical, funding_theme, program_name
    """
    try:
        if len(q) < 2:
            raise HTTPException(status_code=400, detail="Search query must be at least 2 characters")
        
        supabase = get_supabase_client()
        
        # Use PostgreSQL full-text search
        # Build tsquery from search terms
        search_terms = q.strip().split()
        tsquery = " & ".join([f"{term}:*" for term in search_terms])
        
        # Use Supabase RPC for full-text search, or fallback to LIKE search
        # Since Supabase doesn't directly support to_tsvector, we'll use a combination approach
        
        # Try to use RPC if available, otherwise use multiple LIKE queries
        try:
            # Attempt to use a stored function for full-text search
            # For now, we'll use a multi-field LIKE search as fallback
            response = supabase.rpc(
                "search_grants",
                {"search_query": q}
            ).execute()
            
            if response.data:
                results = response.data[:20]
            else:
                # Fallback to LIKE search
                results = await _fallback_search(supabase, q)
                
        except Exception:
            # Fallback to LIKE search if RPC doesn't exist
            results = await _fallback_search(supabase, q)
        
        # Format results with relevance snippets
        formatted_results = []
        for result in results:
            # Extract snippet from description
            description = result.get("description", "") or ""
            snippet = _extract_snippet(description, q, max_length=200)
            
            formatted_results.append(SearchResult(
                id=result["id"],
                source=result.get("source", ""),
                issuer_canonical=result.get("issuer_canonical", ""),
                recipient_name=result.get("recipient_name", ""),
                amount_cad=float(result["amount_cad"]) if result.get("amount_cad") else None,
                award_date=result.get("award_date"),
                region=result.get("region"),
                description=description,
                funding_theme=result.get("funding_theme"),
                procurement_category=result.get("procurement_category"),
                relevance_snippet=snippet,
            ))
        
        return formatted_results[:20]  # Limit to 20 results
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


async def _fallback_search(supabase, query: str) -> list[dict]:
    """
    Fallback search using LIKE queries across multiple fields
    """
    # Search across multiple fields using OR
    search_term = f"%{query}%"
    
    # Get all grants and filter in Python (since Supabase has limited OR support)
    all_grants = supabase.table("grant_records").select("*").limit(1000).execute()
    
    matching_grants = []
    query_lower = query.lower()
    
    for grant in all_grants.data:
        # Check if query matches any searchable field
        description = (grant.get("description") or "").lower()
        recipient = (grant.get("recipient_name") or "").lower()
        issuer = (grant.get("issuer_canonical") or "").lower()
        theme = (grant.get("funding_theme") or "").lower()
        program = (grant.get("program_name") or "").lower()
        
        if (query_lower in description or
            query_lower in recipient or
            query_lower in issuer or
            query_lower in theme or
            query_lower in program):
            matching_grants.append(grant)
    
    return matching_grants


def _extract_snippet(text: str, query: str, max_length: int = 200) -> str:
    """
    Extract a snippet from text containing the query term
    """
    if not text:
        return ""
    
    text_lower = text.lower()
    query_lower = query.lower()
    
    # Find first occurrence of query
    idx = text_lower.find(query_lower)
    
    if idx == -1:
        # Query not found, return beginning
        return text[:max_length] + "..." if len(text) > max_length else text
    
    # Extract snippet around match
    start = max(0, idx - max_length // 2)
    end = min(len(text), idx + len(query) + max_length // 2)
    
    snippet = text[start:end]
    
    if start > 0:
        snippet = "..." + snippet
    if end < len(text):
        snippet = snippet + "..."
    
    return snippet
