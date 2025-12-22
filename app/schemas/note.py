from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class NoteBase(BaseModel):
    title: str
    content: Optional[str] = None
    summary: Optional[str] = None
    category: Optional[str] = "general"
    priority: Optional[str] = "normal"
    is_favorite: Optional[bool] = False
    color: Optional[str] = "#FFFFFF"
    tags: Optional[str] = None
    audio_timestamp: Optional[float] = None
    audio_transcript_excerpt: Optional[str] = None
    is_shared: Optional[bool] = False

class NoteCreate(NoteBase):
    audio_file_id: Optional[int] = None

class NoteUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    summary: Optional[str] = None
    category: Optional[str] = None
    priority: Optional[str] = None
    is_favorite: Optional[bool] = None
    is_archived: Optional[bool] = None
    color: Optional[str] = None
    tags: Optional[str] = None
    audio_timestamp: Optional[float] = None
    audio_transcript_excerpt: Optional[str] = None
    is_shared: Optional[bool] = None
    shared_with: Optional[str] = None

class Note(NoteBase):
    id: int
    user_id: int
    audio_file_id: Optional[int] = None
    is_archived: bool
    shared_with: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class NoteWithAudio(Note):
    audio_file: Optional[dict] = None  # AudioFile info if linked

class NotesListResponse(BaseModel):
    notes: List[Note]
    total_count: int
    page: int
    page_size: int

# Response models for different operations
class NoteCreateResponse(BaseModel):
    message: str
    note: Note

class NoteCategoriesResponse(BaseModel):
    categories: List[str]

class NotePrioritiesResponse(BaseModel):
    priorities: List[str]

# Summary request/response
class SummarizeTranscriptRequest(BaseModel):
    audio_file_id: int

class SummarizeTranscriptResponse(BaseModel):
    audio_file_id: int
    summary_json: str  # Quill Delta JSON format string
    note_id: int
    message: str


# Semantic search request/response
class SemanticSearchRequest(BaseModel):
    query: str
    limit: Optional[int] = 10
    search_in: Optional[str] = "both"  # "content", "summary", or "both"
    similarity_threshold: Optional[float] = 0.5


class NoteWithSimilarity(BaseModel):
    note: Note
    similarity_score: float


class SemanticSearchResponse(BaseModel):
    results: List[NoteWithSimilarity]
    total_count: int
    query: str
    search_in: str
    message: str
