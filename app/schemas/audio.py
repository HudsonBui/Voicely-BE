from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class AudioFileBase(BaseModel):
    filename: str
    original_filename: str
    file_size: int
    duration: Optional[float] = None
    format: str

class AudioFileCreate(AudioFileBase):
    pass

class AudioFileUpdate(BaseModel):
    transcription: Optional[str] = None
    confidence_score: Optional[float] = None
    status: Optional[str] = None
    duration: Optional[float] = None

class AudioFile(AudioFileBase):
    id: int
    user_id: int
    file_path: str
    status: str
    transcription: Optional[str] = None
    confidence_score: Optional[float] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class AudioUploadResponse(BaseModel):
    message: str
    audio_file: AudioFile
    upload_info: dict