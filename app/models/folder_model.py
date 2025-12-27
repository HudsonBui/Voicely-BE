from app.models.base_import import Base, Column, Integer, String, Boolean, DateTime, datetime, timezone, ForeignKey, relationship, Text


class Folder(Base):
    __tablename__ = "folders"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    color = Column(String(7), nullable=True)  # Hex color code, e.g., #FF5733
    icon = Column(String(50), nullable=True)  # Icon name/identifier
    is_default = Column(Boolean, default=False)  # Default folder for new uploads
    
    # Metadata
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    
    # Relationships
    user = relationship("User", back_populates="folders")
    audio_files = relationship("AudioFile", back_populates="folder")
    
    def __repr__(self):
        return f"<Folder(id={self.id}, name='{self.name}', user_id={self.user_id})>"

