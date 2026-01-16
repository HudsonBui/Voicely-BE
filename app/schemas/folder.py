from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

from app.schemas.pagination import PageOptionsDto


class FolderBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Folder name")
    description: Optional[str] = Field(None, max_length=1000, description="Folder description")
    color: Optional[str] = Field(None, pattern="^#[0-9A-Fa-f]{6}$", description="Hex color code")
    icon: Optional[str] = Field(None, max_length=50, description="Icon identifier")
    is_default: bool = Field(default=False, description="Set as default folder")


class FolderCreate(FolderBase):
    """Schema for creating a new folder"""
    pass


class FolderUpdate(BaseModel):
    """Schema for updating a folder (all fields optional for partial updates)"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    color: Optional[str] = Field(None, pattern="^#[0-9A-Fa-f]{6}$")
    icon: Optional[str] = Field(None, max_length=50)
    is_default: Optional[bool] = None


class Folder(FolderBase):
    """Schema for folder response"""
    id: int
    user_id: int
    audio_count: int = Field(default=0, description="Number of audio files in folder")
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class FolderWithAudio(Folder):
    """Schema for folder with audio files list"""
    audio_files: List = Field(default_factory=list)


class MoveAudioToFolder(BaseModel):
    """Schema for moving audio file to folder"""
    audio_id: int
    folder_id: Optional[int] = Field(None, description="Folder ID (null to remove from folder)")


class FolderSearchDto(PageOptionsDto):
    """
    Folders search/filter request payload.
    Extends base pagination with folder-specific filters.
    """

    is_default: Optional[bool] = Field(
        default=None,
        description="Filter default folders",
    )
    color: Optional[str] = Field(
        default=None,
        description="Filter by color (hex code)",
    )
    has_audio: Optional[bool] = Field(
        default=None,
        description="Filter folders with/without audio files",
    )
    min_audio_count: Optional[int] = Field(
        default=None,
        description="Minimum number of audio files",
    )
    max_audio_count: Optional[int] = Field(
        default=None,
        description="Maximum number of audio files",
    )
    from_date: Optional[datetime] = Field(
        default=None,
        description="Filter folders created after this date",
    )
    to_date: Optional[datetime] = Field(
        default=None,
        description="Filter folders created before this date",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "page": 1,
                "page_size": 10,
                "order": "DESC",
                "search": "work",
                "is_default": False,
                "color": "#FF5733",
                "has_audio": True,
                "min_audio_count": 1,
                "max_audio_count": 100,
                "from_date": "2025-01-01T00:00:00",
                "to_date": "2025-12-31T23:59:59",
            }
        }
