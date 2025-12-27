from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Dict, List


class DeviceRegisterRequest(BaseModel):
    fcm_token: str = Field(..., description="Firebase Cloud Messaging token")
    device_type: str = Field(..., description="Device type: ios or android")
    device_name: Optional[str] = Field(None, description="Optional device name")


class DeviceResponse(BaseModel):
    id: int
    user_id: int
    fcm_token: str
    device_type: str
    device_name: Optional[str]
    is_active: bool
    last_login: datetime

    class Config:
        from_attributes = True


class NotificationPayload(BaseModel):
    title: str = Field(..., description="Notification title")
    body: str = Field(..., description="Notification body")
    data: Optional[Dict[str, str]] = Field(None, description="Additional data payload")


# Notification database schemas

class NotificationBase(BaseModel):
    title: str = Field(..., max_length=255, description="Notification title")
    body: str = Field(..., description="Notification body text")
    notification_type: str = Field(..., description="Type: audio_processed, note_created, task_completed, etc.")
    related_id: Optional[int] = Field(None, description="Related entity ID")
    data: Optional[Dict] = Field(None, description="Additional metadata")


class NotificationCreate(NotificationBase):
    user_id: int = Field(..., description="User ID to notify")


class NotificationResponse(NotificationBase):
    id: int
    user_id: int
    is_read: bool
    read_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class NotificationListResponse(BaseModel):
    notifications: List[NotificationResponse]
    total_count: int
    unread_count: int


class MarkAsReadRequest(BaseModel):
    notification_ids: List[int] = Field(..., description="List of notification IDs to mark as read")


class NotificationFilter(BaseModel):
    is_read: Optional[bool] = Field(None, description="Filter by read status")
    notification_type: Optional[str] = Field(None, description="Filter by type")
    skip: int = Field(0, ge=0, description="Pagination offset")
    limit: int = Field(20, ge=1, le=100, description="Items per page")
