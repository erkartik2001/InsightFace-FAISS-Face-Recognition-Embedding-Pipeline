# Global application state for the pipeline service

matcher = None
b2_storage = None
face_engine = None

# Sync state tracking (in-memory)
sync_in_progress = False
sync_job = None

# Scheduler state tracking
scheduler_running = False
scheduler_task = None  # asyncio.Task reference
scheduler_info = {
    "status": "stopped",       # stopped, running, paused
    "started_at": None,
    "stopped_at": None,
    "batch_size": 5000,
    "interval_seconds": 120,   # gap between batches
    "total_batches_completed": 0,
    "current_batch": None,     # info about batch being processed right now
    "last_error": None,
}
