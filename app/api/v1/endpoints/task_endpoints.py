from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session
import json

from app.api.deps import get_db, get_current_active_user
from app.models import User
from app.services.task_job_service import task_job_service

router = APIRouter()


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
