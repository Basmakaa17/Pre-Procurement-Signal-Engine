"""
Source Metadata Manager
Handles tracking and updating metadata for data sources
"""
import logging
from datetime import datetime, timezone
from typing import Optional

from app.database.client import get_supabase_client

logger = logging.getLogger(__name__)


class SourceMetadataManager:
    """Manages metadata for data sources, including last fetch time"""
    
    def __init__(self):
        self.supabase = get_supabase_client()
    
    async def get_last_fetch_time(self, source: str) -> Optional[datetime]:
        """
        Get the last successful fetch time for a source
        
        Args:
            source: The source name (e.g., "open_canada")
            
        Returns:
            The last fetch time as a datetime object, or None if not found
        """
        try:
            # Try to get from pipeline_source_metadata table
            try:
                result = self.supabase.table("pipeline_source_metadata").select("last_fetch_timestamp").eq("source", source).execute()
                if result.data and result.data[0].get("last_fetch_timestamp"):
                    # Convert ISO format to datetime
                    timestamp_str = result.data[0]["last_fetch_timestamp"]
                    # Handle Z suffix for UTC time
                    if timestamp_str.endswith('Z'):
                        timestamp_str = timestamp_str[:-1] + '+00:00'
                    dt = datetime.fromisoformat(timestamp_str)
                    # Ensure timezone-aware
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    return dt
            except Exception as e:
                # Table might not exist yet, that's okay
                logger.warning(f"Could not query pipeline_source_metadata table: {e}")
                # We'll return None below
            
            return None
        except Exception as e:
            logger.warning(f"Error getting last fetch time for {source}: {e}")
            return None
    
    async def update_last_fetch_time(self, source: str, records_fetched: int = 0, status: str = "completed") -> None:
        """
        Update the last fetch time for a source to now
        
        Args:
            source: The source name (e.g., "open_canada")
            records_fetched: Number of records fetched in this run
            status: The status of the run (e.g., "completed", "failed")
        """
        now = datetime.utcnow().isoformat() + "Z"
        try:
            try:
                # Get current total
                result = self.supabase.table("pipeline_source_metadata").select("total_records_fetched").eq("source", source).execute()
                current_total = 0
                if result.data:
                    current_total = result.data[0].get("total_records_fetched", 0) or 0
                
                # Upsert the metadata
                self.supabase.table("pipeline_source_metadata").upsert({
                    "source": source,
                    "last_fetch_timestamp": now,
                    "total_records_fetched": current_total + records_fetched,
                    "last_run_status": status,
                    "updated_at": now
                }).execute()
                
                logger.info(f"Updated metadata for {source}: {records_fetched} new records, status={status}")
            except Exception as e:
                # Table might not exist yet, log and continue
                logger.warning(f"Could not update pipeline_source_metadata table: {e}")
                # We'll still update pipeline_runs table below
                
            # Also update the pipeline_runs table as a fallback
            try:
                # Find the most recent run for this source
                runs = self.supabase.table("pipeline_runs").select("id").eq("source", source).order("started_at", desc=True).limit(1).execute()
                if runs.data:
                    run_id = runs.data[0]["id"]
                    self.supabase.table("pipeline_runs").update({
                        "metadata": {
                            "last_fetch_time": now,
                            "records_fetched": records_fetched,
                            "status": status
                        }
                    }).eq("id", run_id).execute()
            except Exception:
                # This is just a fallback, so ignore errors
                pass
        except Exception as e:
            logger.warning(f"Error updating metadata for {source}: {e}")
    
    async def get_all_sources_metadata(self):
        """Get metadata for all sources"""
        try:
            result = self.supabase.table("pipeline_source_metadata").select("*").execute()
            return result.data
        except Exception as e:
            logger.warning(f"Error getting all sources metadata: {e}")
            return []