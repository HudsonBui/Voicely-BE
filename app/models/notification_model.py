from sqlalchemy import JSON
from sqlalchemy.sql import func

from app.models.base_import import (
    Base,
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    Text,
    ForeignKey,
    relationship,
)


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    notification_type = Column(String(50), nullable=False)  # audio_processed, note_created, task_completed, etc.
    related_id = Column(Integer, nullable=True)  # ID of related entity (audio_id, note_id, etc.)
    data = Column(JSON, nullable=True)  # Additional metadata
    is_read = Column(Boolean, default=False, nullable=False, index=True)
    read_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False, index=True)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # Relationship
    user = relationship("User", back_populates="notifications")

    def __repr__(self):
        return f"<Notification(id={self.id}, user_id={self.user_id}, type='{self.notification_type}', read={self.is_read})>"

