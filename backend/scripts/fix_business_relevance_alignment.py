"""
Fix business relevance alignment with procurement signal for existing grants

This script:
1. Finds grants with high business relevance but low/noise procurement signal
2. Recalculates and caps business relevance to align with procurement signal
3. Updates grants that have "Not Classified" theme to ensure they have business relevance
"""
import asyncio
import os
import sys
import logging
from datetime import datetime

# Add the backend directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.database.client import get_supabase_client
from app.intelligence.relevance_filter import calculate_business_relevance

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def fix_business_relevance_alignment():
    """
    Fix business relevance alignment with procurement signal for existing grants
    """
    supabase = get_supabase_client()

    logger.info("Starting business relevance alignment fix...")

    # Find grants with inconsistencies: high relevance but low/noise signal
    logger.info("Finding grants with high relevance but low/noise procurement signal...")
    
    inconsistent_resp = supabase.table("grant_records").select(
        "id, description, amount_cad, recipient_type, funding_theme, "
        "issuer_canonical, business_relevance, procurement_signal_category"
    ).in_("business_relevance", ["high"]).in_(
        "procurement_signal_category", ["low", "noise"]
    ).eq("is_quarantined", False).execute()

    inconsistent_count = len(inconsistent_resp.data) if inconsistent_resp.data else 0
    logger.info(f"Found {inconsistent_count} grants with high relevance but low/noise signal")

    fixed_count = 0
    for grant in inconsistent_resp.data or []:
        grant_id = grant["id"]
        procurement_signal = grant.get("procurement_signal_category")
        
        # Recalculate business relevance
        relevance_category, relevance_score, relevance_reasons = calculate_business_relevance(
            description=grant.get("description"),
            amount_cad=grant.get("amount_cad"),
            recipient_type=grant.get("recipient_type"),
            funding_theme=grant.get("funding_theme"),
            issuer_canonical=grant.get("issuer_canonical"),
        )
        
        # Cap at medium if procurement signal is low/noise
        if procurement_signal == "noise" and relevance_category == "high":
            relevance_category = "medium"
            relevance_score = min(relevance_score, 0.65)
            relevance_reasons.append("capped:procurement_signal_noise")
        elif procurement_signal == "low" and relevance_category == "high":
            relevance_category = "medium"
            relevance_score = min(relevance_score, 0.65)
            relevance_reasons.append("capped:procurement_signal_low")
        
        # Update the grant
        try:
            supabase.table("grant_records").update({
                "business_relevance": relevance_category,
                "business_relevance_score": relevance_score,
                "business_relevance_reasons": relevance_reasons,
                "updated_at": datetime.now().isoformat(),
            }).eq("id", grant_id).execute()
            fixed_count += 1
        except Exception as e:
            logger.warning(f"Error updating grant {grant_id}: {e}")

    logger.info(f"Fixed {fixed_count}/{inconsistent_count} grants with inconsistencies")

    # Find grants with "Not Classified" theme that don't have business relevance
    logger.info("Finding grants with 'Not Classified' theme missing business relevance...")
    
    unclassified_resp = supabase.table("grant_records").select(
        "id, description, amount_cad, recipient_type, funding_theme, "
        "issuer_canonical, business_relevance, procurement_signal_category"
    ).eq("funding_theme", "Not Classified").is_(
        "business_relevance", "null"
    ).eq("is_quarantined", False).execute()

    unclassified_count = len(unclassified_resp.data) if unclassified_resp.data else 0
    logger.info(f"Found {unclassified_count} grants with 'Not Classified' theme missing business relevance")

    updated_count = 0
    for grant in unclassified_resp.data or []:
        grant_id = grant["id"]
        procurement_signal = grant.get("procurement_signal_category", "unknown")
        
        # Calculate business relevance
        relevance_category, relevance_score, relevance_reasons = calculate_business_relevance(
            description=grant.get("description"),
            amount_cad=grant.get("amount_cad"),
            recipient_type=grant.get("recipient_type"),
            funding_theme=None,  # Not classified
            issuer_canonical=grant.get("issuer_canonical"),
        )
        
        # Cap at medium if procurement signal is low/noise
        if procurement_signal == "noise" and relevance_category == "high":
            relevance_category = "medium"
            relevance_score = min(relevance_score, 0.65)
            relevance_reasons.append("capped:procurement_signal_noise")
        elif procurement_signal == "low" and relevance_category == "high":
            relevance_category = "medium"
            relevance_score = min(relevance_score, 0.65)
            relevance_reasons.append("capped:procurement_signal_low")
        
        # Update the grant
        try:
            supabase.table("grant_records").update({
                "business_relevance": relevance_category,
                "business_relevance_score": relevance_score,
                "business_relevance_reasons": relevance_reasons,
                "updated_at": datetime.now().isoformat(),
            }).eq("id", grant_id).execute()
            updated_count += 1
        except Exception as e:
            logger.warning(f"Error updating grant {grant_id}: {e}")

    logger.info(f"Updated {updated_count}/{unclassified_count} grants with missing business relevance")

    logger.info("✓ Business relevance alignment fix complete!")
    logger.info(f"  Fixed inconsistencies: {fixed_count}")
    logger.info(f"  Updated unclassified grants: {updated_count}")


if __name__ == "__main__":
    asyncio.run(fix_business_relevance_alignment())
