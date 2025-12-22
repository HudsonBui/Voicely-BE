from sqlalchemy import JSON

from app.models.base_import import (
    Base,
    Column,
    Integer,
    String,
    DateTime,
    Text,
    ForeignKey,
    relationship,
    datetime,
    timezone,
)


class TaskJob(Base):
    __tablename__ = "task_jobs"

    id = Column(String, primary_key=True, index=True)
    task_type = Column(String, nullable=False, index=True)
    status = Column(String, default="pending", index=True)
    result = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    audio_id = Column(Integer, ForeignKey("audio_files.id", ondelete="CASCADE"), nullable=True)
    metadata_json = Column("metadata", JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    user = relationship("User", back_populates="task_jobs")
    audio_file = relationship("AudioFile", back_populates="task_jobs")
