"""
API routes for pipeline operations
"""
import logging
import uuid
from typing import Optional, Union, Dict, Any

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Request
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.database.client import get_supabase_client

# Configure logging
logger = logging.getLogger(__name__)

# Rate limiter instance
limiter = Limiter(key_func=get_remote_address)

router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])


class PipelineRunRequest(BaseModel):
    """Request to run pipeline"""
    sources: list[str] = ["open_canada"]
    run_classification: bool = True
    incremental: bool = True  # Default to incremental fetching
    hours_lookback: int = 6   # Default to 6 hours lookback for incremental fetches
    csv_file_path: Optional[str] = None  # Optional path to CSV file for csv_file source


class PipelineRunResponse(BaseModel):
    """Response for pipeline run"""
    run_id: str
    status: str
    message: str


class PipelineStatusResponse(BaseModel):
    """Pipeline run status with detailed progress tracking"""
    id: str
    source: str
    started_at: str
    completed_at: Optional[str]
    status: Optional[str]
    records_fetched: int
    records_cleaned: int
    records_quarantined: int
    records_classified: int
    records_found: Optional[int] = None
    records_new: Optional[int] = None
    records_existing: Optional[int] = None
    records_with_issues: Optional[int] = None
    records_deduplicated: Optional[int] = None
    records_enriched: Optional[int] = None
    error_message: Optional[str]
    metadata: dict


async def run_pipeline_background(
    run_id: str,
    sources: list[str],
    run_classification: bool,
    incremental: bool = True,
    hours_lookback: int = 6,
    csv_file_path: Optional[str] = None,
):
    """
    Background task to run the pipeline
    This will be called asynchronously so it doesn't block the API response
    """
    logger.info(f"[PIPELINE_BG] Background task started for run_id={run_id}, sources={sources}")
    
    try:
        supabase = get_supabase_client()
        
        # Find all pipeline runs with this parent_run_id in metadata
        # The actual records have different IDs (source_run_id) with parent_run_id in metadata
        logger.info(f"[PIPELINE_BG] Finding pipeline runs with parent_run_id={run_id}")
        runs_response = supabase.table("pipeline_runs").select("*").execute()
        
        matching_runs = [
            run for run in runs_response.data
            if run.get("metadata", {}).get("parent_run_id") == run_id
        ]
        
        if not matching_runs:
            logger.warning(f"[PIPELINE_BG] No pipeline runs found with parent_run_id={run_id}")
            # Try direct ID match as fallback
            direct_response = supabase.table("pipeline_runs").select("*").eq("id", run_id).execute()
            if direct_response.data:
                matching_runs = direct_response.data
                logger.info(f"[PIPELINE_BG] Found {len(matching_runs)} run(s) by direct ID match")
            else:
                logger.error(f"[PIPELINE_BG] No pipeline runs found for run_id={run_id}, cannot update status")
                return
        else:
            logger.info(f"[PIPELINE_BG] Found {len(matching_runs)} pipeline run(s) to update")
        
        # Update each matching run to "running" status
        for run in matching_runs:
            run_record_id = run["id"]
            logger.info(f"[PIPELINE_BG] Updating pipeline run {run_record_id} to 'running' status")
            supabase.table("pipeline_runs").update({
                "status": "running"
            }).eq("id", run_record_id).execute()
        
        logger.info(f"[PIPELINE_BG] Status updated to 'running' for {len(matching_runs)} run(s)")
        
        # Import and call PipelineOrchestrator().run()
        logger.info(f"[PIPELINE_BG] Importing PipelineOrchestrator...")
        from app.pipeline.orchestrator import PipelineOrchestrator
        
        # Prepare metadata
        metadata = {}
        if csv_file_path:
            metadata["csv_file_path"] = csv_file_path
        
        logger.info(f"[PIPELINE_BG] Creating orchestrator instance...")
        orchestrator = PipelineOrchestrator()
        orchestrator.run_metadata = metadata
        
        logger.info(f"[PIPELINE_BG] Starting orchestrator.run() with run_id={run_id}, sources={sources}, run_classification={run_classification}")
        await orchestrator.run(
            sources=sources,
            run_classification=run_classification,
            run_id=run_id,
            incremental=incremental,
            hours_lookback=hours_lookback,
        )
        
        logger.info(f"[PIPELINE_BG] Orchestrator.run() completed successfully for run_id={run_id}")
        # Don't override status here - let the orchestrator control it
        # The orchestrator will set status to "completed" or "failed" based on actual results
        
    except Exception as e:
        logger.error(f"[PIPELINE_BG] Exception in background task for run_id={run_id}: {e}", exc_info=True)
        
        # Update status to failed - find runs by parent_run_id in metadata
        try:
            supabase = get_supabase_client()
            
            # Find all runs with this parent_run_id
            runs_response = supabase.table("pipeline_runs").select("*").execute()
            matching_runs = [
                run for run in runs_response.data
                if run.get("metadata", {}).get("parent_run_id") == run_id
            ]
            
            if not matching_runs:
                # Try direct ID match as fallback
                direct_response = supabase.table("pipeline_runs").select("*").eq("id", run_id).execute()
                if direct_response.data:
                    matching_runs = direct_response.data
            
            # Update each matching run to failed status
            for run in matching_runs:
                run_record_id = run["id"]
                logger.error(f"[PIPELINE_BG] Updating pipeline run {run_record_id} to 'failed' status")
                supabase.table("pipeline_runs").update({
                    "status": "failed",
                    "error_message": str(e),
                    "completed_at": "now()",
                }).eq("id", run_record_id).execute()
                
        except Exception as update_error:
            logger.error(f"[PIPELINE_BG] Failed to update status to 'failed': {update_error}", exc_info=True)


@router.post("/run", response_model=PipelineRunResponse)
@limiter.limit("10/minute")
async def run_pipeline(
    request: Request,
    run_request: PipelineRunRequest,
    background_tasks: BackgroundTasks,
):
    """
    Trigger a pipeline run
    Returns immediately with run_id, pipeline runs in background
    """
    try:
        # Validation: ensure at least one source is provided
        if not run_request.sources or len(run_request.sources) == 0:
            logger.warning("[PIPELINE_API] No sources provided in request")
            raise HTTPException(status_code=400, detail="At least one source must be provided")
        
        logger.info(f"[PIPELINE_API] Pipeline run requested: sources={run_request.sources}, run_classification={run_request.run_classification}, incremental={run_request.incremental}")
        
        supabase = get_supabase_client()
        
        # Create pipeline run record
        run_id = str(uuid.uuid4())
        logger.info(f"[PIPELINE_API] Created parent run_id={run_id}")
        
        source_run_ids = []
        # Create run record for each source (single loop - removed duplicate)
        for source in run_request.sources:
            source_run_id = str(uuid.uuid4())
            source_run_ids.append(source_run_id)
            run_data = {
                "id": source_run_id,
                "sources": [source],  # Use sources array instead of source
                "status": "running",
                "records_fetched": 0,
                "records_cleaned": 0,
                "records_quarantined": 0,
                "records_classified": 0,
                "metadata": {
                    "run_classification": run_request.run_classification,
                    "parent_run_id": run_id,
                    "source": source,  # Keep in metadata for backward compatibility
                },
            }
            
            logger.info(f"[PIPELINE_API] Creating pipeline run record: source_run_id={source_run_id}, source={source}, parent_run_id={run_id}")
            supabase.table("pipeline_runs").insert(run_data).execute()
        
        logger.info(f"[PIPELINE_API] Created {len(source_run_ids)} pipeline run record(s): {source_run_ids}")
        
        # Add background task
        logger.info(f"[PIPELINE_API] Adding background task for run_id={run_id}")
        background_tasks.add_task(
            run_pipeline_background,
            run_id=run_id,
            sources=run_request.sources,
            run_classification=run_request.run_classification,
            incremental=run_request.incremental,
            hours_lookback=run_request.hours_lookback,
            csv_file_path=run_request.csv_file_path,
        )
        
        logger.info(f"[PIPELINE_API] Background task added successfully. Returning response with run_id={run_id}")
        
        return PipelineRunResponse(
            run_id=run_id,
            status="started",
            message="Pipeline started in background",
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[PIPELINE_API] Failed to start pipeline: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to start pipeline: {str(e)}")


@router.get("/status/{run_id}", response_model=list[PipelineStatusResponse])
@limiter.limit("100/minute")
async def get_pipeline_status(request: Request, run_id: str):
    """
    Get pipeline run status by run_id
    Returns all runs associated with this run_id (one per source)
    """
    try:
        supabase = get_supabase_client()
        
        # Find runs with this run_id in metadata
        response = supabase.table("pipeline_runs").select("*").execute()
        
        # Filter by parent_run_id in metadata
        matching_runs = [
            run for run in response.data
            if run.get("metadata", {}).get("parent_run_id") == run_id
        ]
        
        if not matching_runs:
            # Try direct ID match
            direct_response = supabase.table("pipeline_runs").select("*").eq("id", run_id).execute()
            if direct_response.data:
                matching_runs = direct_response.data
        
        if not matching_runs:
            raise HTTPException(status_code=404, detail="Pipeline run not found")
        
        # Derive source from sources array for backward compatibility
        for run in matching_runs:
            if "source" not in run and "sources" in run:
                sources_list = run.get("sources", [])
                if sources_list:
                    run["source"] = sources_list[0]  # Use first source for backward compatibility
        
        return matching_runs
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch pipeline status: {str(e)}")


@router.get("/history", response_model=list[PipelineStatusResponse])
@limiter.limit("100/minute")
async def get_pipeline_history(request: Request):
    """
    Get last 10 pipeline runs ordered by started_at DESC
    """
    try:
        supabase = get_supabase_client()
        
        response = supabase.table("pipeline_runs").select("*").order(
            "started_at", desc=True
        ).limit(10).execute()
        
        # Derive source from sources array for backward compatibility
        for run in response.data:
            if "source" not in run and "sources" in run:
                sources_list = run.get("sources", [])
                if sources_list:
                    run["source"] = sources_list[0]  # Use first source for backward compatibility
        
        return response.data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch pipeline history: {str(e)}")
