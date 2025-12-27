from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


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

