"""
Classify all unclassified grants in the database
This script processes all grants that have funding_theme IS NULL
and applies procurement signal scoring and classification.
"""
import asyncio
import os
import sys
import logging
from datetime import datetime

# Add the backend directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.database.client import get_supabase_client
from app.pipeline.orchestrator import PipelineOrchestrator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def classify_all_grants():
    """
    Classify all unclassified grants in the database
    """
    supabase = get_supabase_client()
    
    logger.info("Starting classification of all unclassified grants...")
    
    # Count unclassified grants
    unclassified_resp = supabase.table("grant_records").select(
        "id", count="exact"
    ).is_("funding_theme", "null").eq("is_quarantined", False).execute()
    
    unclassified_count = unclassified_resp.count or 0
    logger.info(f"Found {unclassified_count} unclassified grants")
    
    if unclassified_count == 0:
        logger.info("No unclassified grants found. Exiting.")
        return
    
    # Use the orchestrator's classification method
    orchestrator = PipelineOrchestrator()
    
    # Create a dummy cleaned_grants list (the method queries DB directly anyway)
    # This is just to satisfy the method signature
    cleaned_grants = []
    
    logger.info("Running classification pipeline...")
    classified_count = await orchestrator._classify_grants(cleaned_grants)
    
    logger.info(f"✓ Classification complete!")
    logger.info(f"  Classified: {classified_count} grants")
    
    # Verify results
    classified_resp = supabase.table("grant_records").select(
        "id", count="exact"
    ).not_.is_("funding_theme", "null").eq("is_quarantined", False).execute()
    
    classified_count_after = classified_resp.count or 0
    logger.info(f"  Total classified grants in DB: {classified_count_after}")
    
    # Show distribution
    logger.info("\nClassification distribution:")
    theme_resp = supabase.table("grant_records").select("funding_theme").not_.is_("funding_theme", "null").execute()
    themes = {}
    for grant in theme_resp.data:
        theme = grant.get("funding_theme") or "Unknown"
        themes[theme] = themes.get(theme, 0) + 1
    
    for theme, count in sorted(themes.items(), key=lambda x: x[1], reverse=True):
        logger.info(f"  {theme}: {count}")
    
    # Show procurement signal distribution
    logger.info("\nProcurement signal distribution:")
    signal_resp = supabase.table("grant_records").select("procurement_signal_category").not_.is_("procurement_signal_category", "null").execute()
    signals = {}
    for grant in signal_resp.data:
        signal = grant.get("procurement_signal_category") or "unscored"
        signals[signal] = signals.get(signal, 0) + 1
    
    for signal, count in sorted(signals.items(), key=lambda x: x[1], reverse=True):
        logger.info(f"  {signal}: {count}")


if __name__ == "__main__":
    asyncio.run(classify_all_grants())
