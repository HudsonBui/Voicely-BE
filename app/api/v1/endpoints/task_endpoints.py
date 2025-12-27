from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session
import json

from app.api.deps import get_db, get_current_active_user
from app.models import User
from app.schemas.task_job import TaskSearchDto, TaskJobResponse
from app.schemas.pagination import ResponseCommon as ResponseCommonSchema, PageDto
from app.common.pagination_utils import PaginationHelper
from app.services.task_job_service import task_job_service

router = APIRouter()


@router.post("/search", response_model=ResponseCommonSchema[PageDto[TaskJobResponse]])
async def search_tasks(
    search_dto: TaskSearchDto,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Search and filter user's tasks with pagination.

    **Pagination:**
    - `page`: Current page number (default: 1)
    - `page_size`: Items per page (default: 10, max: 100)
    - `order`: Sort order - ASC or DESC (default: DESC)

    **Search:**
    - `search`: Search across task_type, status, and job_id

    **Filters:**
    - `status`: Filter by task status (pending, queued, processing, completed, failed)
    - `task_type`: Filter by task type (upload, transcribe, summarize)
    - `audio_id`: Filter by linked audio file ID
    - `from_date`: Filter tasks created after this date
    - `to_date`: Filter tasks created before this date
    - `active_only`: If true, only return active tasks (pending, queued, processing)
    """
    paginated_tasks = task_job_service.search_tasks(
        db=db,
        user_id=current_user.id,
        search_dto=search_dto,
    )

    return PaginationHelper.create_response(
        paginated_data=paginated_tasks,
        message="Tasks retrieved successfully",
    )


@router.get("/status/{job_id}")
async def get_task_status(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get the status of an async task job.
    """
    result = task_job_service.get_job_status(
        db=db,
        job_id=job_id,
        user_id=current_user.id,
    )

    return Response(
        content=json.dumps(result.to_json()),
        status_code=result.code,
        media_type="application/json",
    )
