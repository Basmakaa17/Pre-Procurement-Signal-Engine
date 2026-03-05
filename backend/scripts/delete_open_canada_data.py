"""
Script to delete all data from the open_canada source
This will delete:
- All grant records with source='open_canada'
- All quarantined records with source='open_canada'
- All pipeline runs related to 'open_canada'
- Source metadata for 'open_canada'
"""
import sys
import os
import logging

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.client import get_supabase_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def delete_open_canada_data():
    """Delete all data related to the open_canada source"""
    supabase = get_supabase_client()
    
    logger.info("Starting deletion of all Open Canada data...")
    
    # 1. Delete grant records
    logger.info("Deleting grant records...")
    try:
        grants_response = supabase.table("grant_records").select("id", count="exact").eq("source", "open_canada").execute()
        grant_count = grants_response.count or 0
        logger.info(f"Found {grant_count} grant records to delete")
        
        if grant_count > 0:
            # Delete in smaller batches to avoid URL length limits
            deleted = 0
            batch_size = 100  # Smaller batches to avoid URL length issues
            while True:
                batch = supabase.table("grant_records").select("id").eq("source", "open_canada").limit(batch_size).execute()
                if not batch.data:
                    break
                
                ids = [g["id"] for g in batch.data]
                # Delete one by one or in very small batches
                for record_id in ids:
                    try:
                        supabase.table("grant_records").delete().eq("id", record_id).execute()
                        deleted += 1
                    except Exception as e:
                        logger.warning(f"Error deleting record {record_id}: {e}")
                
                logger.info(f"Deleted {deleted}/{grant_count} grant records...")
                
                # If we got fewer than batch_size, we're done
                if len(batch.data) < batch_size:
                    break
            
            logger.info(f"✓ Deleted {deleted} grant records")
        else:
            logger.info("✓ No grant records to delete")
    except Exception as e:
        logger.error(f"Error deleting grant records: {e}")
        raise
    
    # 2. Delete quarantined records
    logger.info("Deleting quarantined records...")
    try:
        quarantine_response = supabase.table("quarantine_queue").select("id", count="exact").eq("source", "open_canada").execute()
        quarantine_count = quarantine_response.count or 0
        logger.info(f"Found {quarantine_count} quarantined records to delete")
        
        if quarantine_count > 0:
            deleted = 0
            batch_size = 100
            while True:
                batch = supabase.table("quarantine_queue").select("id").eq("source", "open_canada").limit(batch_size).execute()
                if not batch.data:
                    break
                
                ids = [q["id"] for q in batch.data]
                # Delete one by one to avoid URL length issues
                for record_id in ids:
                    try:
                        supabase.table("quarantine_queue").delete().eq("id", record_id).execute()
                        deleted += 1
                    except Exception as e:
                        logger.warning(f"Error deleting quarantined record {record_id}: {e}")
                
                logger.info(f"Deleted {deleted}/{quarantine_count} quarantined records...")
                
                if len(batch.data) < batch_size:
                    break
            
            logger.info(f"✓ Deleted {deleted} quarantined records")
        else:
            logger.info("✓ No quarantined records to delete")
    except Exception as e:
        logger.error(f"Error deleting quarantined records: {e}")
        raise
    
    # 3. Delete pipeline runs (where source is in sources array or metadata contains open_canada)
    logger.info("Deleting pipeline runs...")
    try:
        # Get all pipeline runs
        all_runs = supabase.table("pipeline_runs").select("*").execute()
        runs_to_delete = []
        
        for run in all_runs.data:
            sources = run.get("sources", [])
            metadata = run.get("metadata", {})
            # Check if open_canada is in sources array or metadata
            if "open_canada" in sources or metadata.get("source") == "open_canada":
                runs_to_delete.append(run["id"])
        
        if runs_to_delete:
            logger.info(f"Found {len(runs_to_delete)} pipeline runs to delete")
            for run_id in runs_to_delete:
                supabase.table("pipeline_runs").delete().eq("id", run_id).execute()
            logger.info(f"✓ Deleted {len(runs_to_delete)} pipeline runs")
        else:
            logger.info("✓ No pipeline runs to delete")
    except Exception as e:
        logger.error(f"Error deleting pipeline runs: {e}")
        raise
    
    # 4. Delete/reset source metadata
    logger.info("Deleting source metadata...")
    try:
        metadata_response = supabase.table("pipeline_source_metadata").select("id").eq("source", "open_canada").execute()
        if metadata_response.data:
            supabase.table("pipeline_source_metadata").delete().eq("source", "open_canada").execute()
            logger.info(f"✓ Deleted source metadata for open_canada")
        else:
            logger.info("✓ No source metadata to delete")
    except Exception as e:
        # Table might not exist, that's okay
        logger.warning(f"Could not delete source metadata (table may not exist): {e}")
    
    logger.info("✓ All Open Canada data deletion complete!")


if __name__ == "__main__":
    delete_open_canada_data()
