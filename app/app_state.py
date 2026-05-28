# Global application state for the pipeline service

matcher = None
b2_storage = None
face_engine = None

# Sync state tracking (in-memory)
sync_in_progress = False
sync_job = None
