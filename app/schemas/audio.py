from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime

from app.schemas.pagination import PageOptionsDto

class AudioFileBase(BaseModel):
    filename: str
    original_filename: str
    file_size: int
    duration: Optional[float] = None
    format: str
    folder_id: Optional[int] = None

class AudioFileCreate(AudioFileBase):
    pass

class AudioFileUpdate(BaseModel):
    """
    Schema for updating audio file information.
    Only provided fields will be updated (partial updates supported).
    """
    transcription: Optional[str] = Field(
        default=None,
        max_length=50000,
        description="Updated transcription text",
    )
    original_filename: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=255,
        description="Updated original filename",
    )
    folder_id: Optional[int] = Field(
        default=None,
        description="ID of the folder to move the audio file to",
    )

    @field_validator("original_filename")
    @classmethod
    def validate_original_filename(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        value = value.strip()
        invalid_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
        if any(char in value for char in invalid_chars):
            raise ValueError("Filename contains invalid characters")
        if not value:
            raise ValueError("Filename cannot be empty")
        return value

    @field_validator("transcription")
    @classmethod
    def validate_transcription(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        value = value.strip()
        if not value:
            return None
        return value

class AudioFile(AudioFileBase):
    id: int
    user_id: int
    file_path: str
    status: str
    transcription: Optional[str] = None
    confidence_score: Optional[float] = None
    created_at: datetime
    updated_at: datetime
    is_summarize: bool = False
    
    class Config:
        from_attributes = True


class AudioSearchDto(PageOptionsDto):
    """
    Audio files search/filter request payload.
    Extends base pagination with audio-specific filters.
    """

    folder_id: Optional[int] = Field(
        default=None, description="Filter audio files by folder ID"
    )
    status: Optional[str] = Field(
        default=None, description="Filter by status (uploaded, processing, completed, failed)"
    )
    from_date: Optional[datetime] = Field(
        default=None, description="Filter audio files uploaded after this date"
    )
    to_date: Optional[datetime] = Field(
        default=None, description="Filter audio files uploaded before this date"
    )
    min_duration: Optional[float] = Field(default=None, description="Minimum duration in seconds")
    max_duration: Optional[float] = Field(default=None, description="Maximum duration in seconds")
    has_transcript: Optional[bool] = Field(
        default=None, description="Filter files with/without transcripts"
    )
    has_summary: Optional[bool] = Field(
        default=None, description="Filter files with/without summary notes"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "page": 1,
                "page_size": 20,
                "order": "DESC",
                "search": "interview",
                "status": "completed",
                "from_date": "2025-01-01T00:00:00",
                "to_date": "2025-12-31T23:59:59",
                "min_duration": 10.5,
                "max_duration": 300.0,
                "has_transcript": True,
                "has_summary": False,
            }
        }

class AudioUploadResponse(BaseModel):
    message: str
    audio_file: AudioFile
    upload_info: dict
