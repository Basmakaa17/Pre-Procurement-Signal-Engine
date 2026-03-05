"""
Reclassify CSV grants with the latest 6-dimension procurement signal model
This script:
1. Finds all grants with source='csv_file'
2. Re-calculates procurement signal scores using the 6-dimension model
3. Updates the grants in the database with the latest fields
"""
import asyncio
import os
import sys
import logging
from datetime import date, datetime
from typing import Optional, Dict, Any

# Add the backend directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.database.client import get_supabase_client
from app.intelligence.procurement_signal_score import calculate_procurement_signal_score
from app.pipeline.cleaner import map_recipient_type

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def parse_date(date_str: Optional[str]) -> Optional[date]:
    """Parse a date string to a date object"""
    if not date_str:
        return None
    try:
        # Try ISO format first
        if isinstance(date_str, str):
            # Handle various date formats
            if 'T' in date_str:
                return datetime.fromisoformat(date_str.replace('Z', '+00:00')).date()
            return datetime.strptime(date_str, '%Y-%m-%d').date()
        return None
    except (ValueError, TypeError):
        return None


async def reclassify_csv_grants():
    """
    Reclassify all grants with source='csv_file' using the 6-dimension procurement signal model
    """
    supabase = get_supabase_client()
    source_name = "csv_file"

    logger.info(f"Starting reclassification of {source_name} grants...")

    # Fetch all CSV grants
    logger.info("Fetching CSV grants from database...")
    all_grants = []
    offset = 0
    limit = 1000
    
    while True:
        response = supabase.table("grant_records").select("*").eq("source", source_name).limit(limit).offset(offset).execute()
        if not response.data:
            break
        all_grants.extend(response.data)
        offset += limit
        logger.info(f"  Fetched {len(all_grants)} grants so far...")
    
    logger.info(f"Found {len(all_grants)} CSV grants to reclassify")

    if len(all_grants) == 0:
        logger.info("No CSV grants found. Exiting.")
        return

    # Process each grant
    updated_count = 0
    error_count = 0
    
    for idx, grant in enumerate(all_grants):
        try:
            # Extract fields needed for procurement signal calculation
            raw_data = grant.get("raw_data", {}) or {}
            
            # Agreement type
            agreement_type = grant.get("agreement_type") or raw_data.get("agreement_type")
            
            # Recipient info
            recipient_name = grant.get("recipient_name")
            recipient_type = grant.get("recipient_type")
            
            # If recipient_type is missing, try to infer from raw_data
            if not recipient_type and raw_data:
                recipient_type_raw = raw_data.get("recipient_type") or raw_data.get("recipient_type_raw")
                if recipient_type_raw:
                    recipient_type = map_recipient_type(recipient_type_raw)
            
            # Amount
            amount_cad = grant.get("amount_cad")
            if amount_cad is None:
                # Try to get from raw_data
                if raw_data and raw_data.get("amount_cad"):
                    try:
                        amount_cad = float(raw_data["amount_cad"])
                    except (ValueError, TypeError):
                        pass
            
            # Program name and description
            program_name = grant.get("program_name") or raw_data.get("program_name")
            description = grant.get("description") or raw_data.get("description")
            
            # NAICS code
            naics_code = raw_data.get("naics_code") or raw_data.get("naics_identifier")
            
            # Dates
            award_date_str = grant.get("award_date")
            start_date = parse_date(award_date_str)
            end_date = None
            
            # Try to get end_date from raw_data
            if raw_data:
                end_date_str = raw_data.get("agreement_end_date") or raw_data.get("end_date")
                if end_date_str:
                    end_date = parse_date(end_date_str)
            
            # Calculate procurement signal score
            score, reasons, signal_category, duration_months = calculate_procurement_signal_score(
                agreement_type=agreement_type,
                recipient_name=recipient_name,
                recipient_type=recipient_type,
                amount_cad=amount_cad,
                program_name=program_name,
                description=description,
                naics_code=naics_code,
                start_date=start_date,
                end_date=end_date,
            )
            
            # Prepare update fields
            update_fields: Dict[str, Any] = {
                "procurement_signal_score": score,
                "procurement_signal_category": signal_category,
                "procurement_signal_reasons": reasons,
            }
            
            # Add agreement_type if it's missing
            if agreement_type and not grant.get("agreement_type"):
                update_fields["agreement_type"] = agreement_type
            
            # Add duration_months if calculated
            if duration_months is not None:
                update_fields["grant_duration_months"] = duration_months
            
            # Update recipient_type if it was inferred
            if recipient_type and not grant.get("recipient_type"):
                update_fields["recipient_type"] = recipient_type
            
            # Update the grant in the database
            grant_id = grant["id"]
            try:
                supabase.table("grant_records").update(update_fields).eq("id", grant_id).execute()
                updated_count += 1
            except Exception as update_error:
                error_str = str(update_error).lower()
                if "procurement_signal_category" in error_str or "column" in error_str:
                    logger.error(
                        f"\n❌ ERROR: Database columns for procurement signal do not exist!\n"
                        f"Please run the migration file first:\n"
                        f"  backend/database/migrations/add_procurement_signal.sql\n"
                        f"Run it in the Supabase SQL Editor, then re-run this script.\n"
                    )
                    return  # Exit early if columns don't exist
                else:
                    raise  # Re-raise other errors
            
            if (idx + 1) % 100 == 0:
                logger.info(f"  Processed {idx + 1}/{len(all_grants)} grants ({updated_count} updated, {error_count} errors)...")
        
        except Exception as e:
            error_count += 1
            logger.error(f"Error processing grant {grant.get('id', 'unknown')}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            continue
    
    logger.info(f"✓ Reclassification complete!")
    logger.info(f"  Total grants: {len(all_grants)}")
    logger.info(f"  Updated: {updated_count}")
    logger.info(f"  Errors: {error_count}")
    
    # Show distribution of signal categories (only if we successfully updated)
    if updated_count > 0:
        logger.info("\nSignal category distribution:")
        try:
            response = supabase.table("grant_records").select("procurement_signal_category").eq("source", source_name).execute()
            categories = {}
            for grant in response.data:
                cat = grant.get("procurement_signal_category") or "unscored"
                categories[cat] = categories.get(cat, 0) + 1
            
            for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
                logger.info(f"  {cat}: {count}")
        except Exception as e:
            logger.warning(f"Could not fetch signal category distribution: {e}")


if __name__ == "__main__":
    asyncio.run(reclassify_csv_grants())
