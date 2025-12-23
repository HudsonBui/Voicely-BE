from pydantic import BaseModel, Field
from typing import Optional, List, Any
from datetime import datetime


class ChatbotSessionCreate(BaseModel):
    title: Optional[str] = None


class ChatbotSessionResponse(BaseModel):
    session_id: str
    title: Optional[str] = None
    total_messages: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ChatbotMessageCreate(BaseModel):
    message: str = Field(..., min_length=1)


class ChatbotMessageResponse(BaseModel):
    message_id: str
    response: str
    intent: str
    audio_references: List[Any] = []
    note_references: List[Any] = []
    suggested_questions: List[str] = []


class ChatbotMessageHistoryItem(BaseModel):
    message_id: str
    role: str
    content: str
    intent: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ChatbotMessageHistoryResponse(BaseModel):
    session_id: str
    messages: List[ChatbotMessageHistoryItem]
    total: int
    limit: int
    offset: int
