from pydantic import BaseModel, Field
from typing import Optional, Any
from datetime import datetime

from app.schemas.pagination import PageOptionsDto

class TaskJobResponse(BaseModel):
    """Individual task job response"""
    job_id: str = Field(..., alias="id")
    task_type: str
    status: str
    result: Optional[Any] = None
    error_message: Optional[str] = None
    audio_id: Optional[int] = None
    metadata: Optional[dict] = Field(None, alias="metadata_json")
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        populate_by_name = True


class TaskJobStatusResponse(BaseModel):
    """Task job status response (backward compatibility)"""
    job_id: str
    task_type: str
    status: str
    result: Optional[Any] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TaskSearchDto(PageOptionsDto):
    """
    Task search/filter request payload.
    Extends base pagination with task-specific filters.
    """

    status: Optional[str] = Field(
        default=None,
        description="Filter by status (pending, queued, processing, completed, failed)",
    )
    task_type: Optional[str] = Field(
        default=None,
        description="Filter by task type (upload, transcribe, summarize)",
    )
    audio_id: Optional[int] = Field(
        default=None,
        description="Filter by linked audio file ID",
    )
    from_date: Optional[datetime] = Field(
        default=None,
        description="Filter tasks created after this date",
    )
    to_date: Optional[datetime] = Field(
        default=None,
        description="Filter tasks created before this date",
    )
    active_only: bool = Field(
        default=False,
        description="If true, only return active tasks (pending, queued, processing)",
    )

    class Config:
        use_enum_values = True
        json_schema_extra = {
            "example": {
                "page": 1,
                "page_size": 10,
                "order": "DESC",
                "status": "processing",
                "task_type": "transcribe",
                "audio_id": 123,
                "active_only": True,
                "from_date": "2025-12-01T00:00:00Z",
                "to_date": "2025-12-31T23:59:59Z",
            }
        }
