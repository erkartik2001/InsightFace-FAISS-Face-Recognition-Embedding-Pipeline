"""
Scheduler Service — Automated Batch Indexing

Runs as an asyncio background task. Continuously checks
all registered buckets for remaining (un-indexed) images
and processes them in configurable batches (default 5000).

Lifecycle:
  start_scheduler()  → launches the background loop
  stop_scheduler()   → cancels the background task gracefully
  get_status()       → returns current scheduler state

Each completed batch is logged to the scheduler_logs table.
"""

import asyncio
import os
from datetime import datetime

import app.app_state as app_state
from app.database import SessionLocal
from app.models import (
    Bucket, IndexingState, SchedulerLog
)
from app.services.indexing_service import IndexingService


BATCH_SIZE = int(os.getenv("SCHEDULER_BATCH_SIZE", "5000"))
INTERVAL_SECONDS = int(
    os.getenv("SCHEDULER_INTERVAL_SECONDS", "120")
)


async def _scheduler_loop():
    """
    Main scheduler loop.
    Runs forever until cancelled. Each iteration:
      1. Query all registered buckets from DB
      2. For each bucket, check remaining files
      3. If remaining > 0, index a batch of BATCH_SIZE
      4. Log the batch result to scheduler_logs
      5. Sleep for INTERVAL_SECONDS before next cycle
    """

    batch_size = app_state.scheduler_info["batch_size"]
    interval = app_state.scheduler_info["interval_seconds"]

    print(
        f"[Scheduler] Started — batch_size={batch_size}, "
        f"interval={interval}s"
    )

    while True:
        try:
            # ------------------------------------------
            # 1. Get all registered buckets from DB
            # ------------------------------------------
            db = SessionLocal()
            try:
                buckets = db.query(Bucket).all()
                bucket_names = [
                    b.bucket_name for b in buckets
                ]
            finally:
                db.close()

            if not bucket_names:
                # No buckets registered — just wait
                app_state.scheduler_info["current_batch"] = {
                    "status": "idle",
                    "message": "No buckets registered"
                }
                await asyncio.sleep(interval)
                continue

            # ------------------------------------------
            # 2. Process each bucket
            # ------------------------------------------
            work_done = False

            for bucket_name in bucket_names:

                # Check if scheduler was stopped
                if not app_state.scheduler_running:
                    return

                # Get current indexing state
                service = IndexingService()
                bucket_state = service.get_bucket_state(
                    bucket_name
                )

                last_indexed = bucket_state.get(
                    "last_indexed", 0
                )
                total_files = bucket_state.get(
                    "total_files"
                )

                # If we don't know total_files yet, or
                # there are remaining files — do a batch
                needs_work = (
                    total_files is None
                    or last_indexed < total_files
                )

                if not needs_work:
                    continue

                # ------------------------------------------
                # 3. Run a batch for this bucket
                # ------------------------------------------
                work_done = True

                app_state.scheduler_info["current_batch"] = {
                    "bucket": bucket_name,
                    "status": "running",
                    "started_at": datetime.now().strftime(
                        "%Y-%m-%d %H:%M:%S"
                    ),
                    "processed": 0,
                    "skipped": 0,
                }

                # Create scheduler log entry
                db = SessionLocal()
                log_entry = SchedulerLog(
                    bucket_name=bucket_name,
                    batch_size=batch_size,
                    status="running",
                    started_at=datetime.now()
                )
                db.add(log_entry)
                db.commit()
                log_id = log_entry.id
                db.close()

                # Run indexing in a thread to avoid
                # blocking the async event loop
                try:
                    await asyncio.to_thread(
                        _run_batch,
                        service, batch_size,
                        bucket_name, log_id
                    )
                except Exception as e:
                    print(
                        f"[Scheduler] Batch failed "
                        f"for {bucket_name}: {e}"
                    )
                    _update_log(
                        log_id, "failed",
                        0, 0, str(e)
                    )
                    app_state.scheduler_info[
                        "last_error"
                    ] = str(e)

            # ------------------------------------------
            # 4. If no work was done on any bucket, idle
            # ------------------------------------------
            if not work_done:
                app_state.scheduler_info["current_batch"] = {
                    "status": "idle",
                    "message": "All buckets fully indexed"
                }

        except asyncio.CancelledError:
            print("[Scheduler] Cancelled — stopping")
            raise

        except Exception as e:
            print(f"[Scheduler] Error in loop: {e}")
            app_state.scheduler_info["last_error"] = str(e)

        # ------------------------------------------
        # 5. Wait before next cycle
        # ------------------------------------------
        try:
            await asyncio.sleep(interval)
        except asyncio.CancelledError:
            print("[Scheduler] Cancelled during sleep")
            raise


def _run_batch(
    service, batch_size, bucket_name, log_id
):
    """
    Runs a single indexing batch synchronously
    (called via asyncio.to_thread).
    """

    try:
        # Set up sync_job for live progress tracking
        app_state.sync_in_progress = True
        app_state.sync_job = {
            "status": "running",
            "bucket": bucket_name,
            "batch_size": batch_size,
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

        # Use existing IndexingService.run_indexing
        service.run_indexing(
            batch_size=batch_size,
            bucket_name=bucket_name
        )

        # Read results from sync_job
        processed = app_state.sync_job.get("processed", 0)
        skipped = app_state.sync_job.get("skipped", 0)
        status = app_state.sync_job.get("status", "completed")
        error = app_state.sync_job.get("error")
        message = app_state.sync_job.get("message")

        if status == "completed" and processed == 0 and message:
            # "No new files to index"
            _update_log(
                log_id, "no_work", 0, 0, message
            )
        elif status == "failed":
            _update_log(
                log_id, "failed",
                processed, skipped,
                error or "Unknown error"
            )
        else:
            _update_log(
                log_id, "completed",
                processed, skipped,
                f"Batch completed: {processed} processed"
            )
            app_state.scheduler_info[
                "total_batches_completed"
            ] += 1

        # Update current_batch info
        app_state.scheduler_info["current_batch"] = {
            "bucket": bucket_name,
            "status": status,
            "processed": processed,
            "skipped": skipped,
            "completed_at": datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
        }

    except Exception as e:
        _update_log(
            log_id, "failed", 0, 0, str(e)
        )
        raise


def _update_log(
    log_id, status, processed, skipped, message
):
    """Update a scheduler_log entry in the DB."""

    db = SessionLocal()
    try:
        log = db.query(SchedulerLog).filter(
            SchedulerLog.id == log_id
        ).first()

        if log:
            log.status = status
            log.processed = processed
            log.skipped = skipped
            log.message = message
            log.completed_at = datetime.now()
            db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


# =============================================
# PUBLIC API
# =============================================

async def start_scheduler(
    batch_size=None, interval_seconds=None
):
    """Start the scheduler background task."""

    if app_state.scheduler_running:
        return {
            "success": False,
            "message": "Scheduler is already running"
        }

    # Apply config overrides
    if batch_size:
        app_state.scheduler_info["batch_size"] = batch_size
    else:
        app_state.scheduler_info["batch_size"] = BATCH_SIZE

    if interval_seconds:
        app_state.scheduler_info[
            "interval_seconds"
        ] = interval_seconds
    else:
        app_state.scheduler_info[
            "interval_seconds"
        ] = INTERVAL_SECONDS

    # Reset state
    app_state.scheduler_running = True
    app_state.scheduler_info["status"] = "running"
    app_state.scheduler_info["started_at"] = (
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )
    app_state.scheduler_info["stopped_at"] = None
    app_state.scheduler_info["last_error"] = None
    app_state.scheduler_info["current_batch"] = None
    app_state.scheduler_info[
        "total_batches_completed"
    ] = 0

    # Launch background task
    app_state.scheduler_task = asyncio.create_task(
        _scheduler_loop()
    )

    # Handle task completion/cancellation
    def _on_done(task):
        app_state.scheduler_running = False
        app_state.scheduler_info["status"] = "stopped"
        app_state.scheduler_info["stopped_at"] = (
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        app_state.sync_in_progress = False
        print("[Scheduler] Task finished")

    app_state.scheduler_task.add_done_callback(_on_done)

    return {
        "success": True,
        "message": "Scheduler started",
        "scheduler": app_state.scheduler_info
    }


async def stop_scheduler():
    """Stop the scheduler background task."""

    if not app_state.scheduler_running:
        return {
            "success": False,
            "message": "Scheduler is not running"
        }

    app_state.scheduler_running = False

    if app_state.scheduler_task:
        app_state.scheduler_task.cancel()
        try:
            await app_state.scheduler_task
        except asyncio.CancelledError:
            pass

    app_state.scheduler_info["status"] = "stopped"
    app_state.scheduler_info["stopped_at"] = (
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )
    app_state.sync_in_progress = False

    return {
        "success": True,
        "message": "Scheduler stopped",
        "scheduler": app_state.scheduler_info
    }


def get_scheduler_status():
    """Get current scheduler status."""

    return {
        "success": True,
        "scheduler": app_state.scheduler_info
    }


def get_scheduler_logs(limit=50):
    """Get recent scheduler log entries from DB."""

    db = SessionLocal()
    try:
        logs = (
            db.query(SchedulerLog)
            .order_by(SchedulerLog.id.desc())
            .limit(limit)
            .all()
        )
        return [log.to_dict() for log in logs]
    finally:
        db.close()
