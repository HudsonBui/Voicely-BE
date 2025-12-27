from app.models.base_import import Base, Column, Integer, String, Boolean, DateTime, datetime, timezone, Text, Float, ForeignKey, relationship

class AudioFile(Base):
    __tablename__ = "audio_files"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    folder_id = Column(Integer, ForeignKey("folders.id"), nullable=True)
    filename = Column(String, nullable=False)
    original_filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_size = Column(Integer, nullable=False)  # in bytes
    duration = Column(Float, nullable=True)  # in seconds
    format = Column(String, nullable=False)  # mp3, wav, etc.
    
    # Processing status
    status = Column(String, default="uploaded")  # uploaded, processing, completed, failed
    
    # Speech-to-text results
    transcription = Column(Text, nullable=True)
    confidence_score = Column(Float, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    
    # Relationships
    user = relationship("User", back_populates="audio_files")
    folder = relationship("Folder", back_populates="audio_files")
    notes = relationship("Note", back_populates="audio_file")
    task_jobs = relationship("TaskJob", back_populates="audio_file")
