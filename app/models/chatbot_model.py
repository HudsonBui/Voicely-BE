import uuid
from sqlalchemy import Text
from sqlalchemy.dialects.postgresql import JSONB

from app.models.base_import import (
    Base,
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    relationship,
    datetime,
    timezone,
)


class ChatbotSession(Base):
    __tablename__ = "chatbot_sessions"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, unique=True, index=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(200), nullable=True)
    total_messages = Column(Integer, default=0)
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    messages = relationship("ChatbotMessage", back_populates="session", cascade="all, delete-orphan")
    user = relationship("User", back_populates="chatbot_sessions")


class ChatbotMessage(Base):
    __tablename__ = "chatbot_messages"

    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(String, unique=True, index=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(
        String,
        ForeignKey("chatbot_sessions.session_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)

    intent = Column(String(50), nullable=True)
    entities = Column(JSONB, nullable=True)

    retrieved_chunks = Column(JSONB, nullable=True)
    retrieved_audio_ids = Column(JSONB, nullable=True)
    retrieved_note_ids = Column(JSONB, nullable=True)

    response_time_ms = Column(Integer, nullable=True)
    confidence_score = Column(Float, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    session = relationship("ChatbotSession", back_populates="messages")
