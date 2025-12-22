from pydantic import BaseModel
from typing import Optional, Any
from datetime import datetime


class TaskJobResponse(BaseModel):
    job_id: str
    task_type: str
    status: str
    message: str

    class Config:
        from_attributes = True


class TaskJobStatusResponse(BaseModel):
    job_id: str
    task_type: str
    status: str
    result: Optional[Any] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
