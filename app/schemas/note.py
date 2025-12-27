from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Any
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)

from app.schemas.pagination import PageOptionsDto

class NoteBase(BaseModel):
    title: str
    content: Optional[str] = None
    summary: Optional[Any] = None
    category: Optional[str] = "general"
    priority: Optional[str] = "normal"
    is_favorite: Optional[bool] = False
    color: Optional[str] = "#FFFFFF"
    tags: Optional[str] = None
    audio_timestamp: Optional[float] = None
    audio_transcript_excerpt: Optional[str] = None
    is_shared: Optional[bool] = False

    @field_validator("summary")
    @classmethod
    def parse_summary(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                logger.warning("Failed to parse summary JSON string")
                return v
        return v

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


class NoteSearchDto(PageOptionsDto):
    """
    Notes search/filter request payload.
    Extends base pagination with note-specific filters.
    """

    category: Optional[str] = Field(default=None, description="Filter by category")
    priority: Optional[str] = Field(default=None, description="Filter by priority (low, normal, high)")
    is_favorite: Optional[bool] = Field(default=None, description="Filter favorite notes")
    is_archived: Optional[bool] = Field(default=None, description="Filter archived notes")
    is_shared: Optional[bool] = Field(default=None, description="Filter shared notes")
    tags: Optional[str] = Field(default=None, description="Filter by tags (comma-separated)")
    from_date: Optional[datetime] = Field(default=None, description="Filter notes created after this date")
    to_date: Optional[datetime] = Field(default=None, description="Filter notes created before this date")
    audio_file_id: Optional[int] = Field(default=None, description="Filter by linked audio file")

    class Config:
        json_schema_extra = {
            "example": {
                "page": 1,
                "page_size": 10,
                "order": "DESC",
                "search": "meeting",
                "category": "work",
                "priority": "high",
                "is_favorite": True,
                "is_archived": False,
                "is_shared": False,
                "tags": "work,urgent",
                "audio_file_id": 123,
                "from_date": "2025-01-01T00:00:00",
                "to_date": "2025-12-31T23:59:59",
            }
        }

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
    summary_json: Any  # Quill Delta JSON format (can be object or string)
    note_id: int
    message: str

    @field_validator("summary_json")
    @classmethod
    def parse_summary_json(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return v
        return v


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
