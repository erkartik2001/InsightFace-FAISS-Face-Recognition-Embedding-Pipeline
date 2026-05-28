from fastapi import APIRouter
from fastapi import HTTPException

from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import threading

from app.services.indexing_service import (
    IndexingService
)
from app.services.scheduler_service import (
    start_scheduler,
    stop_scheduler,
    get_scheduler_status,
    get_scheduler_logs
)

import app.app_state as app_state


router = APIRouter()


# =========================================
# SCHEDULER ENDPOINTS
# =========================================

class SchedulerStartRequest(BaseModel):
    batch_size: Optional[int] = None
    interval_seconds: Optional[int] = None


@router.post("/scheduler/start")
async def scheduler_start(
    request: SchedulerStartRequest = SchedulerStartRequest()
):
    """
    Start the automated indexing scheduler.
    It will continuously check all registered buckets
    and index remaining images in batches.
    """

    result = await start_scheduler(
        batch_size=request.batch_size,
        interval_seconds=request.interval_seconds
    )

    return result


@router.post("/scheduler/stop")
async def scheduler_stop():
    """
    Stop the automated indexing scheduler.
    """

    result = await stop_scheduler()
    return result


@router.get("/scheduler/status")
async def scheduler_status():
    """
    Get current scheduler status + live batch info.
    """

    status = get_scheduler_status()

    # Also include current sync progress if a batch
    # is being processed right now
    status["sync_in_progress"] = app_state.sync_in_progress
    status["sync_job"] = app_state.sync_job

    return status


@router.get("/scheduler/logs")
async def scheduler_logs(limit: int = 50):
    """
    Get recent scheduler batch logs from the DB.
    Shows audit trail of completed/failed batches.
    """

    logs = get_scheduler_logs(limit=limit)

    return {
        "success": True,
        "logs": logs
    }


# =========================================
# LEGACY: MANUAL START INDEXING
# (kept for backward compatibility)
# =========================================

class IndexRequest(BaseModel):
    count: int
    bucket_name: str | None = None


@router.post("/start-indexing")
async def start_indexing(request: IndexRequest):
    """
    Start batch indexing for a given bucket (manual).
    Kept for backward compatibility. Prefer using
    the scheduler endpoints instead.
    """

    if app_state.sync_in_progress:

        return {
            "success": False,
            "message": "Sync already in progress",
            "sync_job": app_state.sync_job
        }

    bucket_name = request.bucket_name

    if not bucket_name:
        import os
        bucket_name = os.getenv(
            "B2_BUCKET_NAME", "icf-bucket"
        )

    app_state.sync_in_progress = True

    app_state.sync_job = {
        "status": "starting",
        "bucket": bucket_name,
        "batch_size": request.count,
        "processed": 0,
        "skipped": 0,
        "total_files": None,
        "remaining": None,
        "started_at": datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        ),
        "completed_at": None,
        "error": None,
        "message": None
    }

    service = IndexingService()

    thread = threading.Thread(
        target=service.run_indexing,
        args=(request.count, bucket_name),
        daemon=True
    )

    thread.start()

    return {
        "success": True,
        "message": "Indexing started in background",
        "sync_job": app_state.sync_job
    }


# =========================================
# SYNC STATUS (poll this for live progress)
# =========================================

@router.get("/sync-status")
async def sync_status():
    """
    Poll indexing progress (works with both
    manual indexing and scheduler batches).
    """

    return {
        "success": True,
        "in_progress": app_state.sync_in_progress,
        "sync_job": app_state.sync_job
    }


# =========================================
# SYNC LOGS (per-bucket stats)
# =========================================

@router.get("/sync-logs")
async def sync_logs():
    """
    Get per-bucket sync statistics from DB.
    """

    service = IndexingService()
    logs = service.get_sync_logs()

    return {
        "success": True,
        "logs": logs
    }


# =========================================
# INDEXING STATE (for a specific bucket)
# =========================================

@router.get("/indexing-state/{bucket_name}")
async def get_indexing_state(bucket_name: str):
    """
    Get indexing state for a specific bucket.
    """

    service = IndexingService()
    state = service.get_bucket_state(bucket_name)

    return {
        "success": True,
        "bucket_name": bucket_name,
        "state": state
    }

