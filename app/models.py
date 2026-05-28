# SQLAlchemy ORM models for the pipeline service
# Only IndexingState is needed here — User/Bucket are managed by the CRM

from sqlalchemy import (
    Column, Integer, String,
    DateTime
)

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
