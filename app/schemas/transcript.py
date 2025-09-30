from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

class TranscriptRequest(BaseModel):
    audio_id: int
    language_code: Optional[str] = "en-US"

class WordInfo(BaseModel):
    word: str
    start_time: float
    end_time: float
    confidence: float

class TranscriptSegment(BaseModel):
    transcript: str
    confidence: float
    words: List[WordInfo] = []

class TranscriptResponse(BaseModel):
    audio_id: int
    transcript: str
    confidence: float
    language_code: str
    segments: List[TranscriptSegment]
    word_count: int
    duration_transcribed: Optional[float]
    status: str
    processed_at: datetime

class SupportedLanguage(BaseModel):
    code: str
    name: str

class TranscriptStatus(BaseModel):
    audio_id: int
    status: str  # uploaded, processing, completed, failed
    transcript: Optional[str] = None
    confidence: Optional[float] = None
    created_at: datetime
    updated_at: datetime