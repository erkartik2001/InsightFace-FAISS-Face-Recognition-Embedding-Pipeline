# SQLAlchemy ORM models for the pipeline service

from sqlalchemy import (
    Column, Integer, String, Boolean,
    DateTime, Text
)
from sqlalchemy.sql import func

from app.database import Base


class IndexingState(Base):
    __tablename__ = "indexing_state"

    id = Column(Integer, primary_key=True, index=True)
    bucket_name = Column(
        String(255), unique=True, nullable=False, index=True
    )
    last_indexed = Column(Integer, default=0)
    total_files = Column(Integer, nullable=True)
    last_sync_date = Column(DateTime(timezone=True), nullable=True)

    def to_dict(self):
        return {
            "last_indexed": self.last_indexed,
            "total_files": self.total_files,
            "last_sync_date": (
                self.last_sync_date.strftime("%Y-%m-%d %H:%M:%S")
                if self.last_sync_date else None
            )
        }


class Bucket(Base):
    """
    Read-only mirror of the CRM's buckets table.
    The pipeline reads this to discover which buckets
    need indexing. CRM owns writes.
    """
    __tablename__ = "buckets"

    id = Column(Integer, primary_key=True, index=True)
    bucket_name = Column(
        String(255), unique=True, nullable=False, index=True
    )
    is_active = Column(Boolean, default=False)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )
    created_by = Column(String(255), nullable=True)


class SchedulerLog(Base):
    """
    Tracks every batch the scheduler processes.
    Provides a complete audit trail of automated indexing.
    """
    __tablename__ = "scheduler_logs"

    id = Column(Integer, primary_key=True, index=True)
    bucket_name = Column(
        String(255), nullable=False, index=True
    )
    batch_size = Column(Integer, default=0)
    processed = Column(Integer, default=0)
    skipped = Column(Integer, default=0)
    status = Column(
        String(50), nullable=False, default="running"
    )  # running, completed, failed, no_work
    message = Column(Text, nullable=True)
    started_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )
    completed_at = Column(
        DateTime(timezone=True), nullable=True
    )

    def to_dict(self):
        return {
            "id": self.id,
            "bucket_name": self.bucket_name,
            "batch_size": self.batch_size,
            "processed": self.processed,
            "skipped": self.skipped,
            "status": self.status,
            "message": self.message,
            "started_at": (
                self.started_at.strftime("%Y-%m-%d %H:%M:%S")
                if self.started_at else None
            ),
            "completed_at": (
                self.completed_at.strftime("%Y-%m-%d %H:%M:%S")
                if self.completed_at else None
            )
        }

