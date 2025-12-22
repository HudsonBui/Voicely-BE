from app.models.base_import import Base, Column, Integer, String, Boolean, DateTime, datetime, timezone, Text, Float, ForeignKey, relationship
from pgvector.sqlalchemy import Vector

class Note(Base):
    __tablename__ = "notes"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    audio_file_id = Column(Integer, ForeignKey("audio_files.id"), nullable=True)
    
    # Content
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)  # AI-generated summary
    
    # Categorization
    category = Column(String(50), default="general")  # meeting, lecture, personal, etc.
    priority = Column(String(20), default="normal")   # low, normal, high, urgent
    
    # Metadata
    is_favorite = Column(Boolean, default=False)
    is_archived = Column(Boolean, default=False)
    color = Column(String(7), default="#FFFFFF")      # Hex color for UI
    tags = Column(String(500), nullable=True)         # JSON array of tags
    
    # Audio-related fields
    audio_timestamp = Column(Float, nullable=True)    # Link to specific audio moment
    audio_transcript_excerpt = Column(Text, nullable=True)  # Related transcript portion
    
    # Collaboration (future feature)
    is_shared = Column(Boolean, default=False)
    shared_with = Column(Text, nullable=True)         # JSON array of user IDs
    
    # Timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    
    # Relationships
    user = relationship("User", back_populates="notes")
    audio_file = relationship("AudioFile", back_populates="notes")
    chunks = relationship("NoteChunk", back_populates="note", cascade="all, delete-orphan")