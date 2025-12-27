from app.models.base_import import Base, Column, Integer, String, Boolean, DateTime, datetime, timezone, relationship


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    
    # Relationships
    audio_files = relationship("AudioFile", back_populates="user")
    folders = relationship("Folder", back_populates="user")
    notes = relationship("Note", back_populates="user")
    task_jobs = relationship("TaskJob", back_populates="user")
    chatbot_sessions = relationship(
        "ChatbotSession",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    devices = relationship("UserDevice", back_populates="user", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")
