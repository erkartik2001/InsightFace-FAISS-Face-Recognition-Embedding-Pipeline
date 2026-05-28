from fastapi import APIRouter
from fastapi import HTTPException

from pydantic import BaseModel
from datetime import datetime
import threading

from app.services.indexing_service import (
    IndexingService
)

import app.app_state as app_state


router = APIRouter()


class IndexRequest(BaseModel):

    count: int
    bucket_name: str | None = None


# =========================================
# START INDEXING (non-blocking)
# =========================================

@router.post("/start-indexing")
async def start_indexing(request: IndexRequest):
    """
    Start batch indexing for a given bucket.
    This is called by the CRM service (no auth needed,
    internal service-to-service call).
    """

    # -----------------------------
    # CHECK IF ALREADY RUNNING
    # -----------------------------

    if app_state.sync_in_progress:

        return {
            "success": False,
            "message": "Sync already in progress",
            "sync_job": app_state.sync_job
        }

    # -----------------------------
    # DETERMINE BUCKET
    # -----------------------------

    bucket_name = request.bucket_name

    if not bucket_name:
        import os
        bucket_name = os.getenv(
            "B2_BUCKET_NAME", "icf-bucket"
        )

    # -----------------------------
    # INIT SYNC JOB STATE
    # -----------------------------

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

    # -----------------------------
    # START BACKGROUND THREAD
    # -----------------------------

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
# SYNC STATUS (poll this after starting)
# =========================================

@router.get("/sync-status")
async def sync_status():
    """
    Poll indexing progress.
    Called by the CRM service to check status.
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
