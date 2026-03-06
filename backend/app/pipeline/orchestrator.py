"""
Pipeline Orchestrator
Coordinates the full data pipeline: fetching → cleaning → classification → signal generation
"""
import asyncio
import hashlib
import json
import logging
import os
import re
from collections import defaultdict
from datetime import datetime, date, timedelta, timezone
from typing import Optional, Dict, Any, List, Tuple, Set, Union

import httpx
from app.adapters import (
    InnovationCanadaAdapter,
    OpenCanadaAdapter,
    ProactiveDisclosureAdapter,
    MockGrantsAdapter,
    CSVFileAdapter,
)
from app.database.client import get_supabase_client
from app.intelligence.classifier import GrantClassifier
from app.intelligence.rule_classifier import HybridClassifier
from app.intelligence.relevance_filter import calculate_business_relevance
from app.intelligence.signal_detector import SignalDetector
from app.intelligence.rfp_predictor import predict_rfps
from app.intelligence.procurement_signal_score import calculate_procurement_signal_score
from app.models.cleaned_grant import CleanedGrantRecord
from app.models.raw_grant import RawGrantRecord
from app.pipeline.source_metadata import SourceMetadataManager
from app.pipeline.cleaner import (
    clean_amount, 
    clean_date, 
    extract_fiscal_year, 
    canonicalize_department, 
    normalize_recipient,
    should_quarantine,
    CleaningReport,
    map_province_name_to_code,
    map_recipient_type,
)
from app.pipeline.profiler import profile_raw

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Helper function for safe debug logging (only in development)
def _safe_debug_log(data: dict):
    """Safely write debug log only if the file exists or can be created"""
    debug_log_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        '.cursor',
        'debug.log'
    )
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(debug_log_path), exist_ok=True)
        with open(debug_log_path, 'a') as f:
            f.write(json.dumps(data) + "\n")
    except (OSError, IOError, PermissionError):
        # Silently fail in production - debug logging is optional
        pass


class PipelineOrchestrator:
    """Orchestrates the complete data pipeline"""
    
    def __init__(self):
        self.supabase = get_supabase_client()
        self.http_client = None  # Will be created per run
        self.source_metadata_manager = SourceMetadataManager()
    
    async def run(
        self,
        sources: list[str] = None,
        run_classification: bool = True,
        run_id: Optional[str] = None,
        incremental: bool = True,  # New parameter
        hours_lookback: int = 6,    # New parameter - how far back to look for incremental fetches
    ):
        """
        Run the complete pipeline
        
        Args:
            sources: List of source names to fetch from (default: all)
            run_classification: Whether to run LLM classification
            run_id: Optional pipeline run ID for tracking
            incremental: Whether to fetch only new data since last run
            hours_lookback: Hours to look back for incremental fetches (default: 6)
        """
        logger.info(f"[PIPELINE] Orchestrator.run() called with run_id={run_id}, sources={sources}, run_classification={run_classification}, incremental={incremental}")
        
        if sources is None:
            sources = ["open_canada"]  # Only open_canada by default
            logger.info(f"[PIPELINE] No sources provided, using default: {sources}")
        
        async with httpx.AsyncClient(timeout=60) as client:
            self.http_client = client
            logger.info(f"[PIPELINE] HTTP client created, starting pipeline for {len(sources)} source(s)")
            
            for source in sources:
                logger.info(f"[PIPELINE] Starting pipeline for source: {source}")
                
                try:
                    # Get last fetch time for this source if incremental mode
                    since_date = None
                    if incremental:
                        since_date = await self.source_metadata_manager.get_last_fetch_time(source)
                        # #region agent log
                        _safe_debug_log({"runId":"debug","hypothesisId":"A","location":"orchestrator.py:93","message":"Got since_date from metadata","data":{"since_date":since_date.isoformat() if since_date else None,"source":source},"timestamp":int(datetime.now().timestamp()*1000)})
                        # #endregion
                        
                        # If no previous fetch or very old, use hours_lookback
                        now_utc = datetime.now(timezone.utc)
                        # CRITICAL FIX: Enforce minimum date of 2025-01-01 for Open Canada data
                        # This ensures we always fetch 2025+ grants regardless of system date or metadata
                        MIN_DATA_DATE = datetime(2025, 1, 1, tzinfo=timezone.utc)
                        
                        # #region agent log
                        _safe_debug_log({"runId":"debug","hypothesisId":"A","location":"orchestrator.py:100","message":"Checking since_date conditions","data":{"since_date":since_date.isoformat() if since_date else None,"now_utc":now_utc.isoformat(),"MIN_DATA_DATE":MIN_DATA_DATE.isoformat(),"hours_lookback":hours_lookback},"timestamp":int(datetime.now().timestamp()*1000)})
                        # #endregion
                        
                        if not since_date:
                            since_date = max(now_utc - timedelta(hours=hours_lookback), MIN_DATA_DATE)
                            logger.info(f"[PIPELINE] No previous fetch for {source}, using {hours_lookback}h lookback (clamped to {MIN_DATA_DATE.date()})")
                        elif (now_utc - since_date).days > 30:
                            since_date = max(now_utc - timedelta(hours=hours_lookback), MIN_DATA_DATE)
                            logger.info(f"[PIPELINE] Last fetch too old for {source}, using {hours_lookback}h lookback (clamped to {MIN_DATA_DATE.date()})")
                        elif since_date > now_utc:
                            # Reject future dates (corrupted metadata)
                            logger.warning(f"[PIPELINE] Last fetch time is in the future ({since_date.isoformat()}), ignoring and using {hours_lookback}h lookback")
                            # #region agent log
                            _safe_debug_log({"runId":"debug","hypothesisId":"A","location":"orchestrator.py:112","message":"Rejecting future since_date","data":{"since_date":since_date.isoformat(),"now_utc":now_utc.isoformat(),"hours_lookback":hours_lookback},"timestamp":int(datetime.now().timestamp()*1000)})
                            # #endregion
                            since_date = max(now_utc - timedelta(hours=hours_lookback), MIN_DATA_DATE)
                            # #region agent log
                            _safe_debug_log({"runId":"debug","hypothesisId":"A","location":"orchestrator.py:116","message":"Adjusted since_date after future date rejection","data":{"new_since_date":since_date.isoformat()},"timestamp":int(datetime.now().timestamp()*1000)})
                            # #endregion
                        
                        # CRITICAL FIX: Always clamp since_date to MIN_DATA_DATE to ensure we fetch 2025+ data
                        # This handles the case where metadata has a 2026 date (system clock issue or corrupted data)
                        if since_date < MIN_DATA_DATE:
                            logger.warning(f"[PIPELINE] since_date ({since_date.isoformat()}) is before minimum data date ({MIN_DATA_DATE.isoformat()}), clamping to {MIN_DATA_DATE.date()}")
                            # #region agent log
#                             _safe_debug_log({"runId":"debug","hypothesisId":"A","location":"orchestrator.py:125","message":"Clamping since_date to MIN_DATA_DATE (before) # FIXME: Incomplete debug log call - commented out for production
                            # #endregion
                            since_date = MIN_DATA_DATE
                        elif since_date > MIN_DATA_DATE and since_date.year >= 2026:
                            # CRITICAL FIX: If since_date is in 2026 or later, force to MIN_DATA_DATE
                            # This handles corrupted metadata or system clock issues
                            logger.warning(f"[PIPELINE] since_date ({since_date.isoformat()}) is in 2026+, forcing to minimum data date ({MIN_DATA_DATE.date()}) to fetch 2025+ grants")
                            # #region agent log
#                             _safe_debug_log({"runId":"debug","hypothesisId":"A","location":"orchestrator.py:133","message":"Forcing since_date to MIN_DATA_DATE (2026+ detected) # FIXME: Incomplete debug log call - commented out for production
                            # #endregion
                            since_date = MIN_DATA_DATE
                        else:
                            logger.info(f"[PIPELINE] Incremental fetch for {source} since {since_date.isoformat()}")
                            # #region agent log
#                             _safe_debug_log({"runId":"debug","hypothesisId":"A","location":"orchestrator.py:140","message":"Using since_date as-is (passed validation) # FIXME: Incomplete debug log call - commented out for production
                            # #endregion
                        
                        # #region agent log
                        _safe_debug_log({"runId":"debug","hypothesisId":"A","location":"orchestrator.py:143","message":"Final since_date after all checks","data":{"final_since_date":since_date.isoformat()},"timestamp":int(datetime.now().timestamp()*1000)})
                        # #endregion
                    
                    # Step 1: Fetch raw grants with optional date filter
                    # Update status: fetching started
                    self._update_pipeline_run(
                        run_id,
                        source,
                        0,  # Not fetched yet
                        0,
                        0,
                        0,
                        "running",
                    )
                    
                    # Start background task to update status every 10 seconds
                    # Keep it running throughout the entire pipeline (fetch, clean, save, classify)
                    status_update_task = asyncio.create_task(
                        self._periodic_status_update(run_id, source)
                    )
                    
                    try:
                        logger.info(f"[PIPELINE] Starting to fetch grants from {source}...")
                        raw_grants = await self._fetch_grants(source, since_date)
                        # #region agent log
                        _safe_debug_log({"runId":"debug","hypothesisId":"E","location":"orchestrator.py:125","message":"After _fetch_grants","data":{"raw_grants_count":len(raw_grants),"source":source,"since_date":since_date.isoformat() if since_date else None},"timestamp":int(datetime.now().timestamp()*1000)})
                        # #endregion
                        logger.info(f"[PIPELINE] Fetched {len(raw_grants)} raw grants from {source}")
                        
                        # Update status: fetching completed
                        self._update_pipeline_run(
                            run_id,
                            source,
                            len(raw_grants),
                            0,  # Not cleaned yet
                            0,
                            0,
                            "running",
                        )
                        
                        if not raw_grants:
                            logger.warning(f"[PIPELINE] No grants fetched from {source}, skipping")
                            # Update metadata even if no grants fetched
                            if incremental:
                                await self.source_metadata_manager.update_last_fetch_time(source, 0, "completed")
                            # Update status: completed with 0 records
                            self._update_pipeline_run(
                                run_id,
                                source,
                                0,
                                0,
                                0,
                                0,
                                "completed",
                            )
                            continue
                        
                        # Profile raw data before cleaning
                        profiling_report = await profile_raw(raw_grants)
                        logger.info(f"[PIPELINE] Profiled {len(raw_grants)} raw grants from {source}")
                        
                        # Step 2: Clean and normalize
                        # #region agent log
                        _safe_debug_log({"runId":"debug","hypothesisId":"B","location":"orchestrator.py:161","message":"Before _clean_grants","data":{"raw_grants_count":len(raw_grants),"source":source},"timestamp":int(datetime.now().timestamp()*1000)})
                        # #endregion
                        cleaned_grants = await self._clean_grants(raw_grants, source, run_id=run_id)
                        # #region agent log
                        _safe_debug_log({"runId":"debug","hypothesisId":"B","location":"orchestrator.py:163","message":"After _clean_grants","data":{"cleaned_grants_count":len(cleaned_grants),"raw_grants_count":len(raw_grants),"source":source},"timestamp":int(datetime.now().timestamp()*1000)})
                        # #endregion
                        logger.info(f"[PIPELINE] Cleaned {len(cleaned_grants)} grants from {source}")
                        
                        # Update status: cleaning completed
                        self._update_pipeline_run(
                            run_id,
                            source,
                            len(raw_grants),
                            len(cleaned_grants),  # Cleaned count (before dedup)
                            0,  # Not saved yet
                            0,
                            "running",
                        )
                        
                        # Step 3: Deduplicate and save to database
                        saved_count, quarantined_count, records_new, records_existing, records_enriched = await self._save_grants(
                            cleaned_grants, source, run_id, total_fetched=len(raw_grants)
                        )
                        # #region agent log
                        _safe_debug_log({"runId":"debug","hypothesisId":"G","location":"orchestrator.py:245","message":"After _save_grants returned","data":{"saved_count":saved_count,"quarantined_count":quarantined_count,"records_new":records_new,"records_existing":records_existing,"records_enriched":records_enriched,"cleaned_grants_count":len(cleaned_grants)},"timestamp":int(datetime.now().timestamp()*1000)})
                        # #endregion
                        logger.info(
                            f"[PIPELINE] Saved {saved_count} grants (new: {records_new}, existing: {records_existing}, enriched: {records_enriched}), "
                            f"quarantined {quarantined_count} from {source}"
                        )
                        
                        # Calculate records with issues (quality flags but not quarantined)
                        records_with_issues = sum(
                            1 for g in cleaned_grants
                            if g.get("quality_flags") and len(g.get("quality_flags", [])) > 0
                        ) - quarantined_count
                        records_with_issues = max(0, records_with_issues)  # Ensure non-negative
                        
                        # Calculate total processed (new + existing) for accurate progress tracking
                        total_processed = records_new + records_existing
                        
                        # Update status: saving completed
                        # Use total_processed for records_cleaned to reflect all processed grants
                        self._update_pipeline_run(
                            run_id,
                            source,
                            len(raw_grants),
                            total_processed,  # Use total_processed instead of saved_count
                            quarantined_count,
                            0,  # Not classified yet
                            "running",
                            records_found=len(raw_grants),
                            records_new=records_new,
                            records_existing=records_existing,
                            records_with_issues=records_with_issues,
                            records_enriched=records_enriched,
                        )
                        
                        # Step 4: Classify (if requested) - classify ALL unclassified grants, not just new ones
                        classified_count = 0
                        if run_classification:
                            # Update status to show we're classifying - keep as "running"
                            self._update_pipeline_run(
                                run_id,
                                source,
                                len(raw_grants),
                                total_processed,  # Use total_processed for consistency
                                quarantined_count,
                                0,  # Not classified yet
                                "running",  # Keep as running during classification
                                records_found=len(raw_grants),
                                records_new=records_new,
                                records_existing=records_existing,
                                records_with_issues=records_with_issues,
                                records_enriched=records_enriched,
                            )
                            # Only classify grants that were actually saved (not deduplicated)
                            # This is awaited, so it will complete before we set status to "completed"
                            # #region agent log
#                             _safe_debug_log({"runId":"debug","hypothesisId":"D","location":"orchestrator.py:227","message":"Before _classify_grants","data":{"cleaned_grants_count":len(cleaned_grants) # FIXME: Incomplete debug log call - commented out for production
                            # #endregion
                            classified_count = await self._classify_grants(cleaned_grants)
                            # #region agent log
#                             _safe_debug_log({"runId":"debug","hypothesisId":"D","location":"orchestrator.py:229","message":"After _classify_grants","data":{"classified_count":classified_count,"cleaned_grants_count":len(cleaned_grants) # FIXME: Incomplete debug log call - commented out for production
                            # #endregion
                            logger.info(f"[PIPELINE] Classified {classified_count} grants from {source}")
                        
                        # Determine final status - only mark as completed after ALL stages are done
                        # This includes: fetching, cleaning, saving, and classification (if requested)
                        # Since classification is awaited above, it's guaranteed to be done by this point
                        final_status = "completed"
                        error_msg = None
                        
                        # Check if we actually processed records successfully
                        if len(raw_grants) > 0 and saved_count == 0 and len(cleaned_grants) == 0:
                            # We fetched records but none were cleaned - this is a problem
                            final_status = "failed"
                            error_msg = f"No records were cleaned from {len(raw_grants)} fetched records"
                            logger.error(f"[PIPELINE] {error_msg}")
                        elif len(raw_grants) > 0 and len(cleaned_grants) == 0:
                            # Records were fetched but cleaning failed
                            final_status = "failed"
                            error_msg = f"Cleaning failed: {len(raw_grants)} fetched but 0 cleaned"
                            logger.error(f"[PIPELINE] {error_msg}")
                        elif len(raw_grants) > 0 and saved_count == 0:
                            # CRITICAL FIX: Records were cleaned but all were deduplicated/quarantined
                            # This is actually a valid scenario (incremental fetch with no new records)
                            # But we should still mark as completed, not failed
                            final_status = "completed"
                            logger.info(
                                f"[PIPELINE] Pipeline completed for {source}: "
                                f"{len(raw_grants)} fetched, {len(cleaned_grants)} cleaned, "
                                f"{saved_count} saved (all deduplicated/quarantined), {classified_count} classified"
                            )
                        elif len(raw_grants) == 0:
                            # No records fetched - valid completion
                            final_status = "completed"
                            logger.info(f"[PIPELINE] No records fetched from {source} - completed")
                        else:
                            # All stages completed successfully with saved records
                            logger.info(
                                f"[PIPELINE] Pipeline completed for {source}: "
                                f"{len(raw_grants)} fetched, {len(cleaned_grants)} cleaned, "
                                f"{saved_count} saved, {classified_count} classified"
                            )
                        
                        # Final status update - only set to completed after everything is truly done
                        # This is the LAST update, after all stages (fetch, clean, save, classify) are complete
                        # #region agent log
#                         _safe_debug_log({"runId":"debug","hypothesisId":"C","location":"orchestrator.py:258","message":"Setting final status","data":{"final_status":final_status,"raw_grants_count":len(raw_grants) # FIXME: Incomplete debug log call - commented out for production
                        # #endregion
                        self._update_pipeline_run(
                            run_id,
                            source,
                            len(raw_grants),
                            saved_count,  # Use saved_count, not len(cleaned_grants)
                            quarantined_count,
                            classified_count,  # Use actual classified count
                            final_status,
                            error_message=error_msg,
                            records_found=len(raw_grants),
                            records_new=records_new,
                            records_existing=records_existing,
                            records_with_issues=records_with_issues,
                            records_enriched=records_enriched,
                        )
                        
                        # Update source metadata for incremental fetching
                        if incremental:
                            await self.source_metadata_manager.update_last_fetch_time(
                                source, 
                                len(raw_grants), 
                                "completed"
                            )
                    finally:
                        # Cancel the periodic update task only after everything is done
                        status_update_task.cancel()
                        try:
                            await status_update_task
                        except asyncio.CancelledError:
                            pass
                    
                except Exception as e:
                    logger.error(f"[PIPELINE] Error processing {source}: {e}")
                    import traceback
                    logger.error(f"[PIPELINE] Traceback: {traceback.format_exc()}")
                    self._update_pipeline_run(
                        run_id,
                        source,
                        0,
                        0,
                        0,
                        0,
                        "failed",
                        str(e),
                    )
                    
                    # Update source metadata for incremental fetching
                    if incremental:
                        await self.source_metadata_manager.update_last_fetch_time(
                            source, 
                            0, 
                            "failed"
                        )
                    # Continue with other sources instead of raising
                    continue
            
            # Step 5: Generate signals (after all sources processed)
            if run_classification:
                logger.info("[PIPELINE] Generating procurement signals...")
                detector = SignalDetector()
                signals = await detector.detect_signals()
                logger.info(f"[PIPELINE] Generated {len(signals)} procurement signals")
    
    async def _fetch_grants(self, source: str, since_date: Optional[datetime] = None) -> list[RawGrantRecord]:
        """
        Fetch raw grants from the specified source with optional date filtering
        
        Args:
            source: The data source to fetch from
            since_date: Only fetch records created/updated after this date
            
        Returns:
            List of RawGrantRecord objects
        """
        try:
            if source == "open_canada":
                adapter = OpenCanadaAdapter(self.http_client)
                
                # Determine min_date: use since_date if available, otherwise default to 2025-01-01
                min_date = "2025-01-01"
                if since_date:
                    min_date = since_date.strftime("%Y-%m-%d")
                    logger.info(f"[PIPELINE] Incremental OpenCanada fetch since {min_date}")
                else:
                    logger.info(f"[PIPELINE] Full OpenCanada fetch from {min_date}")

                # CRITICAL FIX: Ensure min_date is not in the future
                now_utc = datetime.now(timezone.utc)
                # #region agent log
#                 _safe_debug_log({"runId":"debug","hypothesisId":"A","location":"orchestrator.py:347","message":"Checking min_date for future date","data":{"min_date":min_date,"now_utc":now_utc.isoformat() # FIXME: Incomplete debug log call - commented out for production
                # #endregion
                min_date_obj = datetime.strptime(min_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                if min_date_obj > now_utc:
                    logger.warning(f"[PIPELINE] min_date is in the future ({min_date}), using default 2025-01-01")
                    # #region agent log
#                     _safe_debug_log({"runId":"debug","hypothesisId":"A","location":"orchestrator.py:352","message":"Rejecting future min_date","data":{"min_date":min_date,"min_date_obj":min_date_obj.isoformat() # FIXME: Incomplete debug log call - commented out for production
                    # #endregion
                    min_date = "2025-01-01"
                    # #region agent log
#                     _safe_debug_log({"runId":"debug","hypothesisId":"A","location":"orchestrator.py:355","message":"Adjusted min_date after future date rejection","data":{"new_min_date":min_date},"timestamp":int(datetime.now() # FIXME: Incomplete debug log call - commented out for production
                    # #endregion
                
                logger.info(f"[PIPELINE] Calling OpenCanadaAdapter.fetch_grants with min_date={min_date}, max_records=5000")
                records = await adapter.fetch_grants(
                    min_date=min_date,
                    max_records=5000,  # Dev default cap; raise for production
                )
                logger.info(f"[PIPELINE] OpenCanadaAdapter returned {len(records)} records")
                return records
            elif source == "innovation_canada":
                adapter = InnovationCanadaAdapter(self.http_client)
                # Note: Innovation Canada adapter might not support since_date yet
                # We'll filter the results after fetching if needed
                records = await adapter.fetch_all(max_pages=20)
                if since_date:
                    # Filter records by date if the adapter doesn't support it
                    filtered = []
                    for record in records:
                        if self._record_is_after_date(record, since_date):
                            filtered.append(record)
                    logger.info(f"Filtered {len(records) - len(filtered)} records from {source} older than {since_date.isoformat()}")
                    return filtered
                return records
            elif source == "proactive_disclosure":
                adapter = ProactiveDisclosureAdapter(self.http_client)
                # Note: ProactiveDisclosure adapter might not support since_date yet
                # We'll filter the results after fetching if needed
                records = await adapter.fetch_all()
                if since_date:
                    # Filter records by date if the adapter doesn't support it
                    filtered = []
                    for record in records:
                        if self._record_is_after_date(record, since_date):
                            filtered.append(record)
                    logger.info(f"Filtered {len(records) - len(filtered)} records from {source} older than {since_date.isoformat()}")
                    return filtered
                return records
            elif source == "mock_grants":
                # Use new realistic mock grants for testing
                adapter = MockGrantsAdapter(self.http_client)
                current_year = datetime.now().year
                return await adapter.fetch_all(count=50, year_filter=current_year)
            elif source == "csv_file":
                # CSV file adapter (requires file_path in metadata)
                # Get file path from metadata
                file_path = None
                if hasattr(self, 'run_metadata') and self.run_metadata:
                    file_path = self.run_metadata.get('csv_file_path')
                
                if not file_path:
                    raise ValueError("csv_file source requires 'file_path' in pipeline request")
                
                adapter = CSVFileAdapter(file_path)
                return await adapter.fetch_all()
            else:
                logger.warning(f"Unknown source: {source}")
                return []
        except Exception as e:
            logger.error(f"Error fetching grants from {source}: {e}")
            return []
                
    def _record_is_after_date(self, record: RawGrantRecord, since_date: datetime) -> bool:
        """
        Check if a record's date is after the given date
        
        Args:
            record: The record to check
            since_date: The date to compare against (timezone-aware)
            
        Returns:
            True if the record's date is after since_date, False otherwise
        """
        if not record.award_date_raw:
            # If no date, include it to be safe
            return True
        
        try:
            from dateutil import parser as date_parser
            record_date = date_parser.parse(record.award_date_raw)
            
            # Make both datetimes timezone-aware for comparison
            # If record_date is naive, assume it's UTC
            if record_date.tzinfo is None:
                record_date = record_date.replace(tzinfo=timezone.utc)
            
            # Ensure since_date is also timezone-aware
            if since_date.tzinfo is None:
                since_date = since_date.replace(tzinfo=timezone.utc)
            
            return record_date >= since_date
        except Exception:
            # If we can't parse the date, include it to be safe
            return True
    
    def _clean_text(self, text: Optional[str]) -> Optional[str]:
        """
        Deep-clean a text field: remove HTML, normalize whitespace, strip artifacts
        """
        if not text:
            return None
        
        # Strip HTML entities
        text = re.sub(r'&[a-zA-Z]+;', ' ', text)
        text = re.sub(r'&#\d+;', ' ', text)
        # Strip HTML tags
        text = re.sub(r'<[^>]+>', ' ', text)
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        # Remove leading/trailing punctuation artifacts
        text = text.strip('|•·–—-')
        
        return text if len(text) > 1 else None
    
    async def _clean_grants(
        self, raw_grants: list[RawGrantRecord], source: str, cleaning_report: CleaningReport = None, run_id: Optional[str] = None
    ) -> list[dict]:
        """
        Clean and normalize grant records
        Converts RawGrantRecord to database-ready format with deep cleaning
        """
        cleaned = []
        if cleaning_report is None:
            cleaning_report = CleaningReport(source)
        cleaning_report.total_raw = len(raw_grants)
        
        skipped_count = 0
        error_count = 0
        for idx, raw in enumerate(raw_grants):
            try:
                all_flags = []
                
                # Deep clean text fields
                recipient_cleaned = self._clean_text(raw.recipient_name)
                description_cleaned = self._clean_text(raw.description)
                issuer_cleaned = self._clean_text(raw.issuer_raw)
                
                # #region agent log - sample every 100th record to see what's being filtered
                if idx % 100 == 0 or idx < 10:
                    # _safe_debug_log({"runId":"debug","hypothesisId":"B","location":"orchestrator.py:580","message":"Processing raw grant","data":{"idx":idx,"total":len(raw_grants)},"timestamp":int(datetime.now().timestamp()*1000)}) # Commented out for production
                    pass
                # #endregion
                
                # Filter out records where recipient is actually an amount string
                if recipient_cleaned and recipient_cleaned.startswith("$"):
                    # #region agent log
#                     _safe_debug_log({"runId":"debug","hypothesisId":"B","location":"orchestrator.py:592","message":"Skipping record - recipient is amount","data":{"recipient_cleaned":recipient_cleaned[:50],"source_record_id":raw.source_record_id},"timestamp":int(datetime.now() # FIXME: Incomplete debug log call - commented out for production
                    # #endregion
                    logger.debug(f"Skipping record where recipient is amount: {recipient_cleaned}")
                    all_flags.append("recipient_is_amount")
                    skipped_count += 1
                    continue
                
                # Clean and normalize recipient name
                try:
                    if recipient_cleaned:
                        result = normalize_recipient(recipient_cleaned)
                        if result is None:
                            raise ValueError("normalize_recipient returned None")
                        display_name, recipient_normalized = result
                    else:
                        display_name = "Unknown"
                        recipient_normalized = "unknown"
                        all_flags.append("missing_recipient")
                except Exception as e:
                    raise ValueError(f"Error in normalize_recipient: {e}") from e
                
                # Canonicalize issuer name
                try:
                    if issuer_cleaned:
                        result = canonicalize_department(issuer_cleaned)
                        if result is None:
                            raise ValueError("canonicalize_department returned None")
                        issuer_canonical, match_type, issuer_flags = result
                        all_flags.extend(issuer_flags)
                        cleaning_report.add_dept_match(match_type)
                    else:
                        issuer_canonical = "Unknown"
                        match_type = "unmatched"
                        issuer_flags = ["missing_department"]
                        all_flags.extend(issuer_flags)
                        cleaning_report.add_dept_match(match_type)
                except Exception as e:
                    raise ValueError(f"Error in canonicalize_department: {e}") from e
                
                # Clean amount (use amount_raw if available, otherwise convert amount_cad to string)
                try:
                    amount_raw_str = raw.amount_raw if raw.amount_raw else (str(raw.amount_cad) if raw.amount_cad is not None else None)
                    result = clean_amount(amount_raw_str)
                    if result is None:
                        raise ValueError("clean_amount returned None")
                    amount_cad, amount_flags = result
                    all_flags.extend(amount_flags)
                    amount_unknown = amount_cad is None
                except Exception as e:
                    raise ValueError(f"Error in clean_amount: {e}") from e
                
                # Clean date
                try:
                    result = clean_date(raw.award_date_raw)
                    if result is None:
                        raise ValueError("clean_date returned None")
                    award_date_obj, date_flags = result
                    all_flags.extend(date_flags)
                except Exception as e:
                    raise ValueError(f"Error in clean_date: {e}") from e
                
                # Extract fiscal year if date is available
                fiscal_year = None
                if award_date_obj:
                    fiscal_year = extract_fiscal_year(award_date_obj)
                
                # Extract region (use CSV mapping if source is csv_file)
                if source == "csv_file":
                    region = map_province_name_to_code(raw.region_raw)
                else:
                    region = self._extract_region(raw.region_raw)
                
                # Map recipient type (from CSV files or Open Canada raw data)
                recipient_type = None
                if raw.raw_data and raw.raw_data.get("recipient_type_raw"):
                    recipient_type = map_recipient_type(raw.raw_data.get("recipient_type_raw"))
                elif source == "csv_file" and raw.raw_data and raw.raw_data.get("recipient_type"):
                    recipient_type = map_recipient_type(raw.raw_data.get("recipient_type"))
                
                # Extract agreement_type from raw_data
                agreement_type = None
                if raw.raw_data:
                    agreement_type = raw.raw_data.get("agreement_type")
                
                # Generate deduplication hash (must be after cleaning)
                dedup_hash = self._generate_dedup_hash(raw)
                
                # Check if record should be quarantined
                should_quarantine_record, quarantine_reason = should_quarantine(all_flags)
                
                if should_quarantine_record:
                    # Send to quarantine queue
                    try:
                        quarantine_data = {
                            "source": source,
                            "raw_data": raw.raw_data,
                            "failure_reasons": [quarantine_reason] + all_flags,
                            "quarantine_reason": quarantine_reason,
                        }
                        # Add pipeline_run_id if available (passed from orchestrator)
                        if run_id:
                            quarantine_data["pipeline_run_id"] = run_id
                        self.supabase.table("quarantine_queue").insert(quarantine_data).execute()
                        cleaning_report.total_quarantined += 1
                        logger.debug(f"Quarantined record: {quarantine_reason}")
                    except Exception as e:
                        logger.warning(f"Failed to quarantine record: {e}")
                    continue
                
                # Calculate business relevance
                relevance_category, relevance_score, relevance_reasons = calculate_business_relevance(
                    description=description_cleaned,
                    amount_cad=amount_cad,
                    recipient_type=recipient_type,
                    funding_theme=None,  # Will be set after classification
                    issuer_canonical=issuer_canonical
                )
                
                # Add to cleaned records
                cleaned.append({
                    "source": source,
                    "source_record_id": raw.source_record_id,
                    "issuer_canonical": issuer_canonical,
                    "issuer_raw": issuer_cleaned,
                    "recipient_name": display_name or "Unknown",
                    "recipient_name_normalized": recipient_normalized,
                    "recipient_type": recipient_type,
                    "agreement_type": agreement_type,
                    "amount_cad": amount_cad,
                    "amount_unknown": amount_unknown,
                    "award_date": award_date_obj.isoformat() if award_date_obj else None,
                    "fiscal_year": fiscal_year,
                    "region": region,
                    "description": description_cleaned,
                    "program_name": raw.program_name,
                    "raw_data": raw.raw_data,
                    "quality_flags": all_flags,
                    "business_relevance": relevance_category,
                    "business_relevance_score": relevance_score,
                    "business_relevance_reasons": relevance_reasons,
                    "is_quarantined": False,
                    "dedup_hash": dedup_hash,
                })
                
                # Update report
                cleaning_report.add_flags(all_flags)
                
            except Exception as e:
                import traceback
                error_details = traceback.format_exc()
                error_count += 1
                # #region agent log - log first 10 errors and every 100th error with full traceback
                if error_count <= 10 or error_count % 100 == 0:
                    # Extract the last few lines of traceback to find where .lower() is called
                    tb_lines = error_details.split('\n')
                    # Find the line that mentions .lower()
                    lower_line = None
                    for line in tb_lines:
                        if '.lower()' in line or 'lower' in line.lower():
                            lower_line = line.strip()
                            break
                    # Get the file and line number from traceback
                    file_line = None
                    for i, line in enumerate(tb_lines):
                        if 'File "' in line and 'orchestrator.py' in line:
                            if i + 1 < len(tb_lines):
                                file_line = tb_lines[i].strip() + " -> " + tb_lines[i+1].strip()
                                break
                        elif 'File "' in line and ('cleaner.py' in line or 'orchestrator.py' in line):
                            if i + 1 < len(tb_lines):
                                file_line = tb_lines[i].strip() + " -> " + tb_lines[i+1].strip()
                                break
                    
#                     _safe_debug_log({"runId":"debug","hypothesisId":"B","location":"orchestrator.py:732","message":"Error cleaning grant","data":{"error_count":error_count,"error":str(e) # FIXME: Incomplete debug log call - commented out for production
                # #endregion
                logger.warning(f"Error cleaning grant (source_record_id: {raw.source_record_id if raw else 'unknown'}): {e}")
                logger.warning(f"Traceback: {error_details.split(chr(10))[-3]}")  # Show last meaningful line
                cleaning_report.total_quarantined += 1
                continue
        
        # #region agent log
#         _safe_debug_log({"runId":"debug","hypothesisId":"B","location":"orchestrator.py:742","message":"Cleaning summary","data":{"total_raw":len(raw_grants) # FIXME: Incomplete debug log call - commented out for production
        # #endregion
        
        cleaning_report.total_clean = len(cleaned)
        cleaning_report.print_summary()
        
        # Store cleaning report in pipeline_runs metadata
        try:
            if source and len(raw_grants) > 0:
                self.supabase.table("pipeline_runs").update({
                    "metadata": {"cleaning_report": cleaning_report.to_dict()}
                }).eq("source", source).order("started_at", desc=True).limit(1).execute()
        except Exception as e:
            logger.warning(f"Failed to store cleaning report: {e}")
        
        return cleaned
    
    def _normalize_issuer(self, issuer_raw: Optional[str]) -> str:
        """Normalize issuer/department name with common abbreviation expansion."""
        if not issuer_raw:
            return "Unknown"
        
        # Basic normalization
        normalized = issuer_raw.strip()
        
        # Common abbreviations
        replacements = {
            "DND": "Department of National Defence",
            "DND/CF": "Department of National Defence",
            "PSPC": "Public Services and Procurement Canada",
            "ISED": "Innovation, Science and Economic Development Canada",
            "NRC": "National Research Council",
            "NRCan": "Natural Resources Canada",
        }
        
        for abbrev, full in replacements.items():
            if abbrev in normalized.upper():
                return full
        
        return normalized
    
    def _extract_region(self, region_raw: Optional[str]) -> Optional[str]:
        """Extract standardized 2-letter province/territory code from region string."""
        if not region_raw:
            return None
        
        region_upper = region_raw.upper().strip()
        
        # Map common variations to standard codes
        region_map = {
            "ONTARIO": "ON",
            "ONT": "ON",
            "BRITISH COLUMBIA": "BC",
            "BC": "BC",
            "ALBERTA": "AB",
            "QUEBEC": "QC",
            "QUE": "QC",
            "MANITOBA": "MB",
            "SASKATCHEWAN": "SK",
            "NOVA SCOTIA": "NS",
            "NEW BRUNSWICK": "NB",
            "NEWFOUNDLAND": "NL",
            "PEI": "PE",
            "PRINCE EDWARD ISLAND": "PE",
            "YUKON": "YT",
            "NORTHWEST TERRITORIES": "NT",
            "NUNAVUT": "NU",
        }
        
        for key, code in region_map.items():
            if key in region_upper:
                return code
        
        # If it's already a 2-letter code, return it
        if len(region_upper) == 2:
            return region_upper
        
        return region_raw
    
    def _generate_dedup_hash(self, raw: RawGrantRecord) -> str:
        """
        Generate content-based deduplication hash.
        
        Uses a more robust approach:
        - Normalized department + recipient + amount bucket + fiscal year
        - Amount bucket = rounded to nearest 10,000 to handle small variations
        - Fiscal year extraction for better date matching
        """
        # Get normalized recipient name
        _, recipient_normalized = normalize_recipient(raw.recipient_name)
        
        # Get canonical department name
        dept_canonical, _, _ = canonicalize_department(raw.issuer_raw)
        dept_canonical = dept_canonical.lower()
        
        # Get amount bucket (round to nearest 10,000)
        amount_bucket = "unknown"
        if raw.amount_cad is not None:
            try:
                amount_value = float(raw.amount_cad)
                amount_bucket = str(round(amount_value / 10_000) * 10_000)
            except (ValueError, TypeError):
                pass
        
        # Get fiscal year
        fiscal_year = "unknown"
        if raw.award_date_raw:
            try:
                from dateutil import parser as date_parser
                parsed_date = date_parser.parse(raw.award_date_raw).date()
                fiscal_year = extract_fiscal_year(parsed_date)
            except Exception:
                pass
        
        # Build composite key
        key = f"{dept_canonical}|{recipient_normalized}|{amount_bucket}|{fiscal_year}"
        return hashlib.sha256(key.encode()).hexdigest()[:64]
    
    def _validate_grant(self, grant: dict) -> list[str]:
        """Validate grant and return quality flags. Flags annotate data quality, not block insertion."""
        # Use existing quality flags if available
        if "quality_flags" in grant and isinstance(grant["quality_flags"], list):
            return grant["quality_flags"]
            
        flags = []
        
        # Check recipient quality
        recipient = grant.get("recipient_name", "")
        if not recipient or recipient == "Unknown":
            flags.append("missing_recipient")
        elif len(recipient) < 3:
            flags.append("short_recipient")
        elif recipient.startswith("$"):
            flags.append("recipient_is_amount")  # Common scraping error
        
        # Check amount quality
        amount = grant.get("amount_cad")
        if amount is None:
            flags.append("missing_amount")
        elif amount <= 0:
            flags.append("invalid_amount")
        elif amount > 1_000_000_000:  # > $1B is suspicious
            flags.append("unusually_high_amount")
        
        # Check date quality
        if not grant.get("award_date"):
            flags.append("missing_date")
        else:
            try:
                from dateutil import parser
                d = parser.parse(grant["award_date"]).date()
                today = date.today()
                if d > today:
                    flags.append("future_date")
                elif d.year < 2000:
                    flags.append("very_old_date")
            except Exception:
                flags.append("unparseable_date")
        
        # Check description quality
        desc = grant.get("description", "")
        if not desc:
            flags.append("missing_description")
        elif len(desc) < 20:
            flags.append("short_description")
        elif desc.startswith("$"):
            flags.append("description_is_amount")
        
        # Check issuer quality
        if grant.get("issuer_canonical") == "Unknown":
            flags.append("missing_issuer")
        
        return flags
    
    async def _save_grants(
        self, cleaned_grants: list[dict], source: str, run_id: str, total_fetched: int = 0
    ) -> tuple[int, int, int, int, int]:
        """
        Save cleaned grants with 3-level deduplication:
          1. In-memory set (same batch)
          2. Batch DB lookup (avoid N+1)
          3. Upsert on conflict (update if better data)
        Returns: (saved_count, quarantined_count, records_new, records_existing, records_enriched)
        """
        import time
        self._last_progress_update_time = 0  # Initialize progress update timer
        saved_count = 0
        quarantined_count = 0
        seen_hashes: set[str] = set()
        
        # --- Level 1: In-memory dedup within this batch ---
        unique_grants = []
        for grant in cleaned_grants:
            h = grant["dedup_hash"]
            if h in seen_hashes:
                continue
            seen_hashes.add(h)
            unique_grants.append(grant)
        
        skipped_in_memory = len(cleaned_grants) - len(unique_grants)
        if skipped_in_memory > 0:
            logger.info(f"[DEDUP] Skipped {skipped_in_memory} in-memory duplicates")
        
        if not unique_grants:
            return 0, 0, 0, 0, 0
        
        # --- Level 2: Batch DB lookup (avoid N+1) ---
        all_hashes = [g["dedup_hash"] for g in unique_grants]
        existing_hashes: set[str] = set()
        
        # Query in batches of 50 (Supabase .in_() has limits)
        for i in range(0, len(all_hashes), 50):
            batch = all_hashes[i:i+50]
            try:
                response = self.supabase.table("grant_records").select("dedup_hash").in_(
                    "dedup_hash", batch
                ).execute()
                existing_hashes.update(row["dedup_hash"] for row in response.data)
            except Exception as e:
                logger.warning(f"Error checking existing hashes: {e}")
                # Fall back to individual checks if batch fails
                for h in batch:
                    try:
                        check = self.supabase.table("grant_records").select("id").eq(
                            "dedup_hash", h
                        ).limit(1).execute()
                        if check.data:
                            existing_hashes.add(h)
                    except Exception:
                        pass
        
        skipped_existing = 0
        new_grants = []
        update_grants = []
        total_processed = 0  # Track total processed (new + existing) for progress updates
        
        for grant in unique_grants:
            if grant["dedup_hash"] in existing_hashes:
                # Existing record — check if new data is richer (upsert candidate)
                update_grants.append(grant)
                skipped_existing += 1
                total_processed += 1  # Count existing records for progress
            else:
                new_grants.append(grant)
        
        # #region agent log
#         _safe_debug_log({"runId":"debug","hypothesisId":"F","location":"orchestrator.py:971","message":"After deduplication check","data":{"unique_grants_count":len(unique_grants) # FIXME: Incomplete debug log call - commented out for production
        # #endregion
        
        if skipped_existing > 0:
            logger.info(f"[DEDUP] Found {skipped_existing} existing records in DB")
        
        # If all records already exist, update progress immediately to show we're processing them
        if len(new_grants) == 0 and len(update_grants) > 0:
            try:
                self._update_pipeline_run(
                    run_id,
                    source,
                    total_fetched if total_fetched > 0 else len(cleaned_grants),
                    0,  # Start at 0, will update as we process
                    quarantined_count,
                    0,  # Not classified yet
                    "running",
                    records_found=total_fetched if total_fetched > 0 else len(cleaned_grants),
                    records_new=0,
                    records_existing=skipped_existing,
                    records_enriched=0,
                )
                # #region agent log
#                 _safe_debug_log({"runId":"debug","hypothesisId":"J","location":"orchestrator.py:1033","message":"Initial progress update for all-existing case","data":{"update_grants_count":len(update_grants) # FIXME: Incomplete debug log call - commented out for production
                # #endregion
            except Exception as e:
                # #region agent log
#                 _safe_debug_log({"runId":"debug","hypothesisId":"J","location":"orchestrator.py:1045","message":"Error in initial progress update","data":{"error":str(e) # FIXME: Incomplete debug log call - commented out for production
                # #endregion
                pass
        
        # --- Insert new records ---
        records_new = 0
        # #region agent log
#         _safe_debug_log({"runId":"debug","hypothesisId":"F","location":"orchestrator.py:1029","message":"Starting to process new_grants","data":{"new_grants_count":len(new_grants) # FIXME: Incomplete debug log call - commented out for production
        # #endregion
        for idx, grant in enumerate(new_grants):
            # #region agent log
            if idx % 500 == 0 or idx == len(new_grants) - 1:
                # _safe_debug_log({"runId":"debug","hypothesisId":"F","location":"orchestrator.py:1034","message":"Processing grant in loop","data":{"idx":idx,"total":len(new_grants)},"timestamp":int(datetime.now().timestamp()*1000)}) # Commented out for production
                pass
            # #endregion
            
            try:
                # Validate and add quality flags
                quality_flags = self._validate_grant(grant)
                grant["quality_flags"] = quality_flags
                
                # #region agent log
#                 _safe_debug_log({"runId":"debug","hypothesisId":"F","location":"orchestrator.py:990","message":"Quality flags generated","data":{"quality_flags":quality_flags,"recipient_name":grant.get("recipient_name","") # FIXME: Incomplete debug log call - commented out for production
                # #endregion
                
                # Check if record should be quarantined based on flags
                should_quarantine_record, quarantine_reason = should_quarantine(quality_flags)
                
                # #region agent log
#                 _safe_debug_log({"runId":"debug","hypothesisId":"F","location":"orchestrator.py:997","message":"Quarantine check result","data":{"should_quarantine":should_quarantine_record,"quarantine_reason":quarantine_reason,"quality_flags":quality_flags,"quarantine_flags_count":len([f for f in quality_flags if f in ["missing_recipient","missing_department","date_parse_failed","date_missing","amount_parse_failed","insufficient_data"]]) # FIXME: Incomplete debug log call - commented out for production
                # #endregion
                
                if should_quarantine_record:
                    # Send to quarantine queue
                    # #region agent log
#                     _safe_debug_log({"runId":"debug","hypothesisId":"F","location":"orchestrator.py:1001","message":"Quarantining grant","data":{"quarantine_reason":quarantine_reason,"quality_flags":quality_flags,"quarantined_count":quarantined_count+1},"timestamp":int(datetime.now() # FIXME: Incomplete debug log call - commented out for production
                    # #endregion
                    quarantine_data = {
                        "source": source,
                        "raw_data": grant.get("raw_data", {}),
                        "failure_reasons": [quarantine_reason] + quality_flags,
                        "quarantine_reason": quarantine_reason,
                    }
                    if run_id:
                        quarantine_data["pipeline_run_id"] = run_id
                    self.supabase.table("quarantine_queue").insert(quarantine_data).execute()
                    quarantined_count += 1
                    continue
                
                # Insert grant record
                # Ensure 'id' is not in the grant dict (let DB auto-generate)
                if "id" in grant:
                    del grant["id"]
                
                # Create a copy of grant dict for safe insertion
                # Remove procurement signal fields that might not exist in DB schema
                # These will be added later via UPDATE if the columns exist
                safe_grant = grant.copy()
                procurement_signal_fields = [
                    "agreement_type",
                    "procurement_signal_score",
                    "procurement_signal_category",
                    "procurement_signal_reasons",
                    "grant_duration_months"
                ]
                procurement_signal_data = {}
                for field in procurement_signal_fields:
                    if field in safe_grant:
                        procurement_signal_data[field] = safe_grant.pop(field)
                
                # #region agent log
#                 _safe_debug_log({"runId":"debug","hypothesisId":"F","location":"orchestrator.py:1022","message":"Attempting to insert grant","data":{"dedup_hash":grant.get("dedup_hash") # FIXME: Incomplete debug log call - commented out for production
                # #endregion
                
                # #region agent log
#                 _safe_debug_log({"runId":"debug","hypothesisId":"F","location":"orchestrator.py:1027","message":"About to execute insert","data":{"grant_keys":list(safe_grant.keys() # FIXME: Incomplete debug log call - commented out for production
                # #endregion
                
                try:
                    result = self.supabase.table("grant_records").insert(safe_grant).execute()
                    # #region agent log
#                     _safe_debug_log({"runId":"debug","hypothesisId":"F","location":"orchestrator.py:1051","message":"Insert execute() # FIXME: Incomplete debug log call - commented out for production
                    # #endregion
                    
                    # If insert succeeded, try to update with procurement signal fields (if columns exist)
                    if result.data and len(result.data) > 0 and procurement_signal_data:
                        inserted_id = result.data[0].get("id")
                        if inserted_id:
                            try:
                                # Try to update with procurement signal fields
                                update_data = {k: v for k, v in procurement_signal_data.items() if v is not None}
                                if update_data:
                                    self.supabase.table("grant_records").update(update_data).eq("id", inserted_id).execute()
                                    # #region agent log
#                                     _safe_debug_log({"runId":"debug","hypothesisId":"F","location":"orchestrator.py:1062","message":"Updated procurement signal fields","data":{"inserted_id":str(inserted_id) # FIXME: Incomplete debug log call - commented out for production
                                    # #endregion
                            except Exception as update_error:
                                # Columns might not exist - that's okay, log and continue
                                # #region agent log
#                                 _safe_debug_log({"runId":"debug","hypothesisId":"F","location":"orchestrator.py:1069","message":"Could not update procurement signal fields (columns may not exist) # FIXME: Incomplete debug log call - commented out for production
                                # #endregion
                                logger.debug(f"Could not update procurement signal fields (columns may not exist): {update_error}")
                    
                    saved_count += 1
                    records_new += 1
                    total_processed += 1  # Increment total processed (new + existing)
                    # #region agent log
#                     _safe_debug_log({"runId":"debug","hypothesisId":"F","location":"orchestrator.py:1077","message":"Successfully inserted grant","data":{"saved_count":saved_count,"records_new":records_new,"total_processed":total_processed},"timestamp":int(datetime.now() # FIXME: Incomplete debug log call - commented out for production
                    # #endregion
                    
                    # Update progress every 50 grants OR every 5 seconds (whichever comes first) to keep UI responsive
                    # Use total_processed_now (new + existing) so progress updates even when all records exist
                    current_time = time.time()
                    # Calculate current total: saved_count (new) + skipped_existing (existing already counted)
                    total_processed_now = saved_count + skipped_existing
                    should_update = (
                        total_processed_now % 50 == 0 or  # Every 50 grants processed (new or existing)
                        saved_count == len(new_grants) or  # At the end of new grants
                        (current_time - self._last_progress_update_time >= 5)  # Every 5 seconds
                    )
                    if should_update:
                        # #region agent log
#                         _safe_debug_log({"runId":"debug","hypothesisId":"H","location":"orchestrator.py:1152","message":"About to update progress","data":{"saved_count":saved_count,"total_processed_now":total_processed_now,"skipped_existing":skipped_existing,"len_unique_grants":len(unique_grants) # FIXME: Incomplete debug log call - commented out for production
                        # #endregion
                        try:
                            # Update records_cleaned to show total processed (new + existing) for accurate progress
                            self._update_pipeline_run(
                                run_id,
                                source,
                                total_fetched if total_fetched > 0 else len(cleaned_grants),
                                total_processed_now,  # Total processed (new + existing) for accurate progress
                                quarantined_count,
                                0,  # Not classified yet
                                "running",
                                records_found=total_fetched if total_fetched > 0 else len(cleaned_grants),
                                records_new=records_new,
                                records_existing=skipped_existing,
                                records_enriched=0,  # Will be updated at end
                            )
                            self._last_progress_update_time = current_time  # Track last update time
                            # #region agent log
#                             _safe_debug_log({"runId":"debug","hypothesisId":"H","location":"orchestrator.py:1170","message":"Progress update completed successfully","data":{"saved_count":saved_count,"total_processed_now":total_processed_now,"records_cleaned":total_processed_now},"timestamp":int(datetime.now() # FIXME: Incomplete debug log call - commented out for production
                            # #endregion
                        except Exception as update_error:
                            # Don't fail the save process if progress update fails
                            # #region agent log
#                             _safe_debug_log({"runId":"debug","hypothesisId":"H","location":"orchestrator.py:1167","message":"Error updating progress","data":{"error":str(update_error) # FIXME: Incomplete debug log call - commented out for production
                            # #endregion
                            logger.debug(f"Error updating progress: {update_error}")
                except Exception as insert_error:
                    error_str = str(insert_error).lower()
                    # #region agent log
#                     _safe_debug_log({"runId":"debug","hypothesisId":"F","location":"orchestrator.py:1043","message":"Exception during insert.execute() # FIXME: Incomplete debug log call - commented out for production
                    # #endregion
                    if "duplicate key" in error_str or "unique" in error_str or "duplicate" in error_str:
                        # Race condition — another process inserted it, treat as existing
                        # #region agent log
#                         _safe_debug_log({"runId":"debug","hypothesisId":"F","location":"orchestrator.py:1049","message":"Duplicate key - adding to update_grants","data":{},"timestamp":int(datetime.now() # FIXME: Incomplete debug log call - commented out for production
                        # #endregion
                        update_grants.append(grant)
                        continue
                    logger.warning(f"Error saving grant: {insert_error}")
                    # Quarantine on error
                    # #region agent log
#                     _safe_debug_log({"runId":"debug","hypothesisId":"F","location":"orchestrator.py:1057","message":"Quarantining due to insert error","data":{"error":str(insert_error) # FIXME: Incomplete debug log call - commented out for production
                    # #endregion
                    try:
                        quarantine_data = {
                            "source": source,
                            "raw_data": grant.get("raw_data", {}),
                            "failure_reasons": [str(insert_error)],
                            "quarantine_reason": "database_insert_error",
                        }
                        if run_id:
                            quarantine_data["pipeline_run_id"] = run_id
                        self.supabase.table("quarantine_queue").insert(quarantine_data).execute()
                        quarantined_count += 1
                    except Exception as quarantine_error:
                        # #region agent log
#                         _safe_debug_log({"runId":"debug","hypothesisId":"F","location":"orchestrator.py:1067","message":"Failed to quarantine (quarantine insert also failed) # FIXME: Incomplete debug log call - commented out for production
                        # #endregion
                        pass
            except Exception as e:
                # Outer exception handler for validation/quarantine check errors
                error_str = str(e).lower()
                # #region agent log
#                 _safe_debug_log({"runId":"debug","hypothesisId":"F","location":"orchestrator.py:1073","message":"Outer exception handler","data":{"error":str(e) # FIXME: Incomplete debug log call - commented out for production
                # #endregion
                logger.error(f"Unexpected error processing grant: {e}")
                import traceback
                logger.error(traceback.format_exc())
        
        # --- Upsert existing records (update if new data is richer) ---
        updated_count = 0
        # #region agent log
#         _safe_debug_log({"runId":"debug","hypothesisId":"I","location":"orchestrator.py:1258","message":"Starting to process update_grants","data":{"update_grants_count":len(update_grants) # FIXME: Incomplete debug log call - commented out for production
        # #endregion
        for idx, grant in enumerate(update_grants):
            # Update progress every 50 grants OR every 5 seconds for existing records too
            current_time = time.time()
            # Calculate total processed: saved_count (new) + how many existing we've processed so far
            existing_processed = idx + 1
            total_processed_so_far = saved_count + existing_processed
            should_update_existing = (
                total_processed_so_far % 50 == 0 or  # Every 50 total processed
                existing_processed == len(update_grants) or  # At the end of existing records
                (current_time - self._last_progress_update_time >= 5)  # Every 5 seconds
            )
            if should_update_existing:
                try:
                    self._update_pipeline_run(
                        run_id,
                        source,
                        total_fetched if total_fetched > 0 else len(cleaned_grants),
                        total_processed_so_far,  # Total processed (new + existing) for accurate progress
                        quarantined_count,
                        0,  # Not classified yet
                        "running",
                        records_found=total_fetched if total_fetched > 0 else len(cleaned_grants),
                        records_new=records_new,
                        records_existing=skipped_existing,
                        records_enriched=0,  # Will be updated at end
                    )
                    self._last_progress_update_time = current_time
                    # #region agent log
#                     _safe_debug_log({"runId":"debug","hypothesisId":"I","location":"orchestrator.py:1235","message":"Progress update for existing records","data":{"total_processed_so_far":total_processed_so_far,"existing_processed":existing_processed,"saved_count":saved_count},"timestamp":int(datetime.now() # FIXME: Incomplete debug log call - commented out for production
                    # #endregion
                except Exception as e:
                    # #region agent log
#                     _safe_debug_log({"runId":"debug","hypothesisId":"I","location":"orchestrator.py:1248","message":"Error updating progress for existing records","data":{"error":str(e) # FIXME: Incomplete debug log call - commented out for production
                    # #endregion
                    pass  # Don't fail if progress update fails
            
            # Process the grant update
            try:
                update_fields = {}
                # Only update fields that are currently NULL in DB
                if grant.get("description"):
                    update_fields["description"] = grant["description"]
                if grant.get("region"):
                    update_fields["region"] = grant["region"]
                if grant.get("award_date"):
                    update_fields["award_date"] = grant["award_date"]
                if grant.get("issuer_raw") and grant["issuer_raw"] != "Unknown":
                    update_fields["issuer_canonical"] = self._normalize_issuer(grant["issuer_raw"])
                    update_fields["issuer_raw"] = grant["issuer_raw"]
                
                if update_fields:
                    update_fields["updated_at"] = datetime.now().isoformat()
                    # Only update if current DB value is NULL
                    # Note: Supabase doesn't support .is_() chaining easily, so we'll update anyway
                    # The dedup_hash UNIQUE constraint prevents true duplicates
                    self.supabase.table("grant_records").update(
                        update_fields
                    ).eq("dedup_hash", grant["dedup_hash"]).execute()
                    updated_count += 1
            except Exception as e:
                logger.debug(f"Error enriching existing record: {e}")
                pass
        
        if updated_count > 0:
            logger.info(f"[DEDUP] Enriched {updated_count} existing records with new data")
        
        # Calculate records with issues (quality flags but not quarantined)
        records_with_issues = 0
        for g in new_grants:
            flags = g.get("quality_flags", [])
            if flags:
                should_quar, _ = should_quarantine(flags)
                if not should_quar:
                    records_with_issues += 1
        
        # #region agent log
#         _safe_debug_log({"runId":"debug","hypothesisId":"F","location":"orchestrator.py:1216","message":"_save_grants returning","data":{"saved_count":saved_count,"quarantined_count":quarantined_count,"records_new":saved_count,"records_existing":skipped_existing,"records_enriched":updated_count,"new_grants_count":len(new_grants) # FIXME: Incomplete debug log call - commented out for production
        # #endregion
        return saved_count, quarantined_count, saved_count, skipped_existing, updated_count
    
    async def _classify_grants(self, cleaned_grants: list[dict]) -> int:
        """
        Classify grants using the 6-dimension procurement signal + hybrid approach:

        Phase 1 — Procurement Signal Scoring (instant, no API):
          Score every unclassified record with the 6-dimension model.
          Only HIGH/MEDIUM signal grants proceed to LLM classification.
          LOW/NOISE grants get a default "Not Classified" theme.

        Phase 2 — Hybrid Classification (rule-based + LLM fallback):
          1. Skip already-classified records (funding_theme IS NOT NULL)
          2. Rule-based matching (instant, no API needed)
          3. LLM fallback only for unmatched records
          4. Auto-learns new keywords from LLM results

        Processes all unclassified records in batches of CLASSIFY_BATCH.
        Re-runs are essentially free: only new records get classified.
        """
        CLASSIFY_BATCH = 500  # records fetched from DB per iteration

        try:
            # --- Log how many records are already classified vs. pending ---
            total_resp = self.supabase.table("grant_records").select(
                "id", count="exact"
            ).eq("is_quarantined", False).execute()
            total_records = total_resp.count or 0

            classified_resp = self.supabase.table("grant_records").select(
                "id", count="exact"
            ).eq("is_quarantined", False).not_.is_("funding_theme", "null").execute()
            already_classified = classified_resp.count or 0

            pending = total_records - already_classified
            logger.info(
                f"[CLASSIFY] {already_classified} already classified, "
                f"{pending} pending classification (total {total_records})"
            )

            if pending == 0:
                logger.info("[CLASSIFY] Nothing to classify — all records already done.")
                return 0

            # ════════════════════════════════════════════════════════════════
            # Phase 1 — Procurement Signal Scoring
            # ════════════════════════════════════════════════════════════════
            logger.info("[SIGNAL] Running 6-dimension procurement signal scoring...")
            signal_stats = {"high": 0, "medium": 0, "low": 0, "noise": 0}
            skipped_for_llm = 0
            scored_count = 0

            # Score in batches
            offset = 0
            while True:
                score_resp = self.supabase.table("grant_records").select(
                    "id, agreement_type, recipient_name, recipient_type, "
                    "amount_cad, program_name, description, award_date, raw_data, "
                    "procurement_signal_score, issuer_canonical"
                ).is_("funding_theme", "null").eq(
                    "is_quarantined", False
                ).order("id").limit(CLASSIFY_BATCH).offset(offset).execute()

                if not score_resp.data:
                    break

                batch_count = len(score_resp.data)
                logger.info(f"[SIGNAL] Processing batch: offset={offset}, count={batch_count}")
                for g in score_resp.data:
                    # Skip if already scored
                    if g.get("procurement_signal_score") is not None:
                        cat = self._score_to_category(g["procurement_signal_score"])
                        signal_stats[cat] += 1
                        scored_count += 1
                        continue

                    # Parse dates for duration calculation
                    start_dt = None
                    end_dt = None
                    raw_data = g.get("raw_data") or {}

                    if g.get("award_date"):
                        try:
                            ad = g["award_date"]
                            if isinstance(ad, str):
                                start_dt = datetime.fromisoformat(ad.split("T")[0]).date()
                        except (ValueError, TypeError):
                            pass
                    elif raw_data.get("agreement_start_date"):
                        try:
                            start_dt = datetime.fromisoformat(
                                raw_data["agreement_start_date"].split("T")[0]
                            ).date()
                        except (ValueError, TypeError, AttributeError):
                            pass

                    if raw_data.get("agreement_end_date"):
                        try:
                            end_dt = datetime.fromisoformat(
                                raw_data["agreement_end_date"].split("T")[0]
                            ).date()
                        except (ValueError, TypeError, AttributeError):
                            pass

                    score, reasons, category, duration_months = calculate_procurement_signal_score(
                        agreement_type=g.get("agreement_type"),
                        recipient_name=g.get("recipient_name"),
                        recipient_type=g.get("recipient_type"),
                        amount_cad=float(g["amount_cad"]) if g.get("amount_cad") else None,
                        program_name=g.get("program_name"),
                        description=g.get("description"),
                        naics_code=raw_data.get("naics_code"),
                        start_date=start_dt,
                        end_date=end_dt,
                    )

                    signal_stats[category] += 1
                    scored_count += 1

                    # Persist the score
                    update_fields = {
                        "procurement_signal_score": score,
                        "procurement_signal_category": category,
                        "procurement_signal_reasons": reasons,
                        "grant_duration_months": duration_months,
                    }

                    # For LOW/NOISE, set a default theme and calculate business relevance
                    if category in ("low", "noise"):
                        skipped_for_llm += 1
                        
                        # Calculate business relevance for LOW/NOISE grants too
                        # This ensures consistency between procurement signal and business relevance
                        relevance_category, relevance_score, relevance_reasons = calculate_business_relevance(
                            description=g.get("description"),
                            amount_cad=float(g["amount_cad"]) if g.get("amount_cad") else None,
                            recipient_type=g.get("recipient_type"),
                            funding_theme=None,  # Not classified yet
                            issuer_canonical=g.get("issuer_canonical"),
                        )
                        
                        # Align business relevance with procurement signal:
                        # If procurement signal is low/noise, business relevance should be capped
                        if category == "noise" and relevance_category == "high":
                            # Noise signal + high relevance = inconsistency, cap at medium
                            relevance_category = "medium"
                            relevance_score = min(relevance_score, 0.65)
                            relevance_reasons.append("capped:procurement_signal_noise")
                        elif category == "low" and relevance_category == "high":
                            # Low signal + high relevance = inconsistency, cap at medium
                            relevance_category = "medium"
                            relevance_score = min(relevance_score, 0.65)
                            relevance_reasons.append("capped:procurement_signal_low")
                        
                        update_fields.update({
                            "funding_theme": "Not Classified",
                            "llm_confidence": 0.0,
                            "llm_classified_at": datetime.now().isoformat(),
                            "business_relevance": relevance_category,
                            "business_relevance_score": relevance_score,
                            "business_relevance_reasons": relevance_reasons,
                        })

                    try:
                        self.supabase.table("grant_records").update(
                            update_fields
                        ).eq("id", g["id"]).execute()
                    except Exception as e:
                        logger.warning(f"[SIGNAL] Error updating score for {g['id']}: {e}")

                offset += batch_count
                if batch_count < CLASSIFY_BATCH:
                    break

            logger.info(
                f"[SIGNAL] Scoring complete: {scored_count} scored — "
                f"HIGH={signal_stats['high']} MEDIUM={signal_stats['medium']} "
                f"LOW={signal_stats['low']} NOISE={signal_stats['noise']} "
                f"({skipped_for_llm} skipped LLM)"
            )

            # ════════════════════════════════════════════════════════════════
            # Phase 2 — Hybrid Classification (only HIGH + MEDIUM signal)
            # ════════════════════════════════════════════════════════════════
            total_updated = 0
            classifier = HybridClassifier(use_llm_fallback=True)
            classify_offset = 0

            while True:
                response = self.supabase.table("grant_records").select(
                    "id, source, issuer_canonical, recipient_name, amount_cad, "
                    "award_date, region, description, recipient_type, "
                    "agreement_type, raw_data, procurement_signal_category"
                ).is_("funding_theme", "null").eq(
                    "is_quarantined", False
                ).in_("procurement_signal_category", ["high", "medium"]).order("id").limit(
                    CLASSIFY_BATCH
                ).offset(classify_offset).execute()

                if not response.data:
                    break

                batch_size = len(response.data)
                logger.info(f"[CLASSIFY] Processing batch: offset={classify_offset}, count={batch_size}")

                # Convert to CleanedGrantRecord
                grants = []
                for g in response.data:
                    try:
                        award_date = None
                        if g.get("award_date"):
                            if isinstance(g["award_date"], str):
                                from dateutil import parser
                                award_date = parser.parse(g["award_date"].split("T")[0]).date()
                            elif hasattr(g["award_date"], "date"):
                                award_date = g["award_date"]

                        grant = CleanedGrantRecord(
                            id=g["id"],
                            source=g["source"],
                            issuer_canonical=g["issuer_canonical"],
                            recipient_name=g["recipient_name"],
                            amount_cad=float(g["amount_cad"]) if g.get("amount_cad") else None,
                            award_date=award_date,
                            region=g.get("region"),
                            description=g.get("description"),
                        )
                        grants.append(grant)
                    except Exception as e:
                        logger.warning(f"Error parsing grant for classification: {e}")
                        continue

                if not grants:
                    break

                # Classify this batch
                classifications = await classifier.classify_batch(grants, batch_size=25)

                # Update database with classifications + relevance + RFP predictions
                batch_updated = 0
                for classification in classifications:
                    try:
                        grant_data = next(
                            (g for g in response.data if g["id"] == classification.grant_id), {}
                        )

                        # Recalculate business relevance with funding_theme
                        relevance_category, relevance_score, relevance_reasons = calculate_business_relevance(
                            description=grant_data.get("description"),
                            amount_cad=grant_data.get("amount_cad"),
                            recipient_type=grant_data.get("recipient_type"),
                            funding_theme=classification.funding_theme,
                            issuer_canonical=grant_data.get("issuer_canonical"),
                        )
                        
                        # Align business relevance with procurement signal:
                        # If procurement signal is low/noise, business relevance should be capped
                        procurement_signal = grant_data.get("procurement_signal_category", "unknown")
                        if procurement_signal == "noise" and relevance_category == "high":
                            # Noise signal + high relevance = inconsistency, cap at medium
                            relevance_category = "medium"
                            relevance_score = min(relevance_score, 0.65)
                            relevance_reasons.append("capped:procurement_signal_noise")
                        elif procurement_signal == "low" and relevance_category == "high":
                            # Low signal + high relevance = inconsistency, cap at medium
                            relevance_category = "medium"
                            relevance_score = min(relevance_score, 0.65)
                            relevance_reasons.append("capped:procurement_signal_low")

                        # Generate RFP predictions
                        award_date_obj = None
                        if grant_data.get("award_date"):
                            try:
                                ad = grant_data["award_date"]
                                if isinstance(ad, str):
                                    award_date_obj = datetime.fromisoformat(ad.split("T")[0]).date()
                                elif isinstance(ad, date):
                                    award_date_obj = ad
                            except (ValueError, TypeError):
                                pass

                        rfp_forecast = predict_rfps(
                            grant_id=classification.grant_id,
                            funding_theme=classification.funding_theme,
                            amount_cad=float(grant_data.get("amount_cad") or 0),
                            award_date=award_date_obj,
                            description=grant_data.get("description"),
                            issuer_canonical=grant_data.get("issuer_canonical"),
                            business_relevance=relevance_category,
                            business_relevance_score=relevance_score,
                        )

                        update_data = {
                            "funding_theme": classification.funding_theme,
                            "procurement_category": classification.procurement_category,
                            "sector_tags": classification.sector_tags,
                            "llm_confidence": classification.confidence,
                            "llm_classified_at": datetime.now().isoformat(),
                            "quality_flags": classification.classification_flags,
                            "business_relevance": relevance_category,
                            "business_relevance_score": relevance_score,
                            "business_relevance_reasons": relevance_reasons,
                            "predicted_rfps": [p.to_dict() for p in rfp_forecast.predictions],
                            "rfp_forecast_summary": rfp_forecast.forecast_summary,
                            "rfp_forecast_confidence": rfp_forecast.forecast_confidence,
                            "predicted_rfp_count": rfp_forecast.total_predicted_rfps,
                        }

                        self.supabase.table("grant_records").update(update_data).eq(
                            "id", classification.grant_id
                        ).execute()
                        batch_updated += 1
                    except Exception as e:
                        logger.warning(f"Error updating classification: {e}")

                total_updated += batch_updated
                classify_offset += batch_size
                logger.info(
                    f"[CLASSIFY] Batch done: {batch_updated}/{batch_size} updated "
                    f"(total so far: {total_updated})"
                )

                # If we got fewer than the batch limit, there are no more
                if batch_size < CLASSIFY_BATCH:
                    break

            # Log final stats
            stats = classifier.get_stats()
            logger.info(
                f"[CLASSIFY] Complete — {total_updated} newly classified, "
                f"{already_classified} previously classified. "
                f"Signal filter saved {skipped_for_llm} LLM calls. Stats: {stats}"
            )
            return total_updated

        except Exception as e:
            logger.error(f"Error in classification: {e}")
            return 0
    
    @staticmethod
    def _score_to_category(score: int) -> str:
        """Convert a numeric procurement signal score to a category string."""
        if score >= 60:
            return "high"
        elif score >= 40:
            return "medium"
        elif score >= 20:
            return "low"
        return "noise"
    
    async def _periodic_status_update(self, run_id: str, source: str):
        """
        Background task to update pipeline status every 10 seconds during processing
        This ensures the frontend sees progress even during long operations
        """
        try:
            while True:
                await asyncio.sleep(10)  # Update every 10 seconds
                
                # Get current counts from database for this source
                # This gives us the most up-to-date counts
                grants_response = self.supabase.table("grant_records").select(
                    "id, funding_theme, llm_classified_at"
                ).eq("source", source).execute()
                
                total_grants = len(grants_response.data)
                classified_grants = sum(
                    1 for g in grants_response.data 
                    if g.get("funding_theme") or g.get("llm_classified_at")
                )
                
                # Update status with current progress
                # We don't know exact fetched/cleaned counts, so we estimate based on saved grants
                self._update_pipeline_run(
                    run_id,
                    source,
                    total_grants,  # Estimate: fetched ≈ saved (for now)
                    total_grants,  # Estimate: cleaned ≈ saved
                    0,  # Quarantined count would need separate query
                    classified_grants,
                    "running",
                )
        except asyncio.CancelledError:
            # Task was cancelled, that's expected
            pass
        except Exception as e:
            logger.warning(f"Error in periodic status update: {e}")
    
    def _update_pipeline_run(
        self,
        run_id: str,
        source: str,
        records_fetched: int,
        records_cleaned: int,
        records_quarantined: int,
        records_classified: int,
        status: str,
        error_message: Optional[str] = None,
        records_found: Optional[int] = None,
        records_new: Optional[int] = None,
        records_existing: Optional[int] = None,
        records_with_issues: Optional[int] = None,
        records_deduplicated: Optional[int] = None,
        records_enriched: Optional[int] = None,
    ):
        """Update pipeline run status in database with detailed progress tracking"""
        try:
            update_data = {
                "status": status,
                "records_fetched": records_fetched,
                "records_cleaned": records_cleaned,
                "records_quarantined": records_quarantined,
                "records_classified": records_classified,
            }
            
            # Add detailed tracking fields if provided
            if records_found is not None:
                update_data["records_found"] = records_found
            if records_new is not None:
                update_data["records_new"] = records_new
            if records_existing is not None:
                update_data["records_existing"] = records_existing
            if records_with_issues is not None:
                update_data["records_with_issues"] = records_with_issues
            if records_deduplicated is not None:
                update_data["records_deduplicated"] = records_deduplicated
            if records_enriched is not None:
                update_data["records_enriched"] = records_enriched
            
            if status == "completed":
                update_data["completed_at"] = datetime.now().isoformat()
            elif status == "failed":
                update_data["completed_at"] = datetime.now().isoformat()
                update_data["error_message"] = error_message
            
            # Find run by source (in sources array) and parent_run_id in metadata
            # Get all runs and filter in Python since Supabase doesn't support array contains easily
            runs = self.supabase.table("pipeline_runs").select("*").execute()
            
            # #region agent log
#             _safe_debug_log({"runId":"debug","hypothesisId":"H","location":"orchestrator.py:1649","message":"_update_pipeline_run: searching for run","data":{"run_id":run_id,"source":source,"total_runs":len(runs.data) # FIXME: Incomplete debug log call - commented out for production
            # #endregion
            
            # Find the run with matching source in sources array and parent_run_id
            found_run = None
            for run in runs.data:
                sources_list = run.get("sources", [])
                metadata = run.get("metadata", {})
                parent_run_id = metadata.get("parent_run_id")
                if source in sources_list and parent_run_id == run_id:
                    found_run = run
                    # #region agent log
#                     _safe_debug_log({"runId":"debug","hypothesisId":"H","location":"orchestrator.py:1656","message":"_update_pipeline_run: found matching run","data":{"run_id":run_id,"source":source,"found_run_id":run["id"],"records_cleaned":records_cleaned,"update_data":update_data},"timestamp":int(datetime.now() # FIXME: Incomplete debug log call - commented out for production
                    # #endregion
                    result = self.supabase.table("pipeline_runs").update(update_data).eq(
                        "id", run["id"]
                    ).execute()
                    # #region agent log
#                     _safe_debug_log({"runId":"debug","hypothesisId":"H","location":"orchestrator.py:1662","message":"_update_pipeline_run: update executed","data":{"run_id":run_id,"found_run_id":run["id"],"result_count":len(result.data) # FIXME: Incomplete debug log call - commented out for production
                    # #endregion
                    break
            
            if not found_run:
                # #region agent log
#                 _safe_debug_log({"runId":"debug","hypothesisId":"H","location":"orchestrator.py:1668","message":"_update_pipeline_run: no matching run found","data":{"run_id":run_id,"source":source,"total_runs":len(runs.data) # FIXME: Incomplete debug log call - commented out for production
                # #endregion
                logger.warning(f"Could not find pipeline run to update: run_id={run_id}, source={source}")
            
        except Exception as e:
            # #region agent log
#             _safe_debug_log({"runId":"debug","hypothesisId":"H","location":"orchestrator.py:1675","message":"_update_pipeline_run: exception","data":{"error":str(e) # FIXME: Incomplete debug log call - commented out for production
            # #endregion
            logger.error(f"Error updating pipeline run: {e}")
