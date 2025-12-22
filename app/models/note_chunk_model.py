from app.models.base_import import Base, Column, Integer, String, DateTime, datetime, timezone, Text, ForeignKey, relationship
from pgvector.sqlalchemy import Vector

class NoteChunk(Base):
    """
    Model for storing chunks of note content with embeddings for RAG.
    Each note can have multiple chunks for better semantic search accuracy.
    """
    __tablename__ = "note_chunks"
    
    id = Column(Integer, primary_key=True, index=True)
    note_id = Column(Integer, ForeignKey("notes.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Chunk content and metadata
    chunk_text = Column(Text, nullable=False)
    chunk_index = Column(Integer, nullable=False)  # Order of chunk in original text
    chunk_type = Column(String(20), nullable=False, default="content")  # "content" or "summary"
    
    # Vector embedding for the chunk
    embedding = Column(Vector(768), nullable=False)  # 768 dimensions for text-embedding-005
    
    # Metadata for context
    start_char = Column(Integer, nullable=True)  # Starting character position in original text
    end_char = Column(Integer, nullable=True)    # Ending character position in original text
    token_count = Column(Integer, nullable=True)  # Approximate token count of chunk
    
    # Timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    note = relationship("Note", back_populates="chunks")
