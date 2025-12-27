import uuid
import json
from typing import Optional

from fastapi import Request
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.common.response_common import ResponseCommon
from app.common.pagination_utils import PaginationHelper
from app.models.task_job_model import TaskJob
from app.schemas.pagination import PageDto
from app.schemas.task_job import TaskSearchDto, TaskJobResponse


class TaskJobService:
    """Service for managing async task jobs."""

    async def create_and_queue_job(
        self,
        request: Request,
        db: Session,
        task_type: str,
        task_function: str,
        user_id: int,
        audio_id: Optional[int] = None,
        metadata: Optional[dict] = None,
        **kwargs,
    ) -> ResponseCommon:
        """Create a task job record and enqueue it to the ARQ worker."""
        if request is None or not hasattr(request.app.state, "arq_pool"):
            return ResponseCommon.error_response(
                message="ARQ pool not initialized",
                code=500,
            )

        try:
            job_id = str(uuid.uuid4())
            new_job = TaskJob(
                id=job_id,
                task_type=task_type,
                status="pending",
                user_id=user_id,
                audio_id=audio_id,
                metadata_json=metadata,
            )
            db.add(new_job)
            db.commit()
            db.refresh(new_job)
        except Exception as exc:
            db.rollback()
            return ResponseCommon.error_response(
                message=f"Failed to create task job: {str(exc)}",
                code=500,
            )

        job_kwargs = dict(kwargs)
        job_kwargs["user_id"] = user_id
        if audio_id is not None:
            job_kwargs["audio_id"] = audio_id

        try:
            await request.app.state.arq_pool.enqueue_job(
                task_function,
                job_id,
                **job_kwargs,
                _job_id=job_id,
            )
            new_job.status = "queued"
            db.commit()
        except Exception as exc:
            db.rollback()
            try:
                new_job.status = "failed"
                new_job.error_message = str(exc)
                db.commit()
            except Exception:
                db.rollback()
            return ResponseCommon.error_response(
                message=f"Failed to queue task job: {str(exc)}",
                code=500,
            )

        return ResponseCommon.success_response(
            data={
                "job_id": job_id,
                "task_type": task_type,
                "status": "queued",
            },
            message="Task queued successfully. Use job_id to check status.",
        )

    def search_tasks(
        self, db: Session, user_id: int, search_dto: TaskSearchDto
    ) -> PageDto[TaskJobResponse]:
        """
        Search and filter user's tasks with pagination

        Args:
            db: Database session
            user_id: Current user ID
            search_dto: Search filters and pagination options

        Returns:
            PageDto with tasks and pagination metadata
        """
        query = db.query(TaskJob).filter(TaskJob.user_id == user_id)

        if search_dto.search:
            search_term = f"%{search_dto.search}%"
            query = query.filter(
                or_(
                    TaskJob.task_type.ilike(search_term),
                    TaskJob.status.ilike(search_term),
                    TaskJob.id.ilike(search_term),
                )
            )

        if search_dto.status is not None:
            query = query.filter(TaskJob.status == search_dto.status)

        if search_dto.task_type is not None:
            query = query.filter(TaskJob.task_type == search_dto.task_type)

        if search_dto.audio_id is not None:
            query = query.filter(TaskJob.audio_id == search_dto.audio_id)

        if search_dto.active_only:
            query = query.filter(TaskJob.status.in_(["pending", "queued", "processing"]))

        if search_dto.from_date:
            query = query.filter(TaskJob.created_at >= search_dto.from_date)

        if search_dto.to_date:
            query = query.filter(TaskJob.created_at <= search_dto.to_date)

        order_value = getattr(search_dto.order, "value", search_dto.order)
        if str(order_value).upper() == "ASC":
            query = query.order_by(TaskJob.created_at.asc())
        else:
            query = query.order_by(TaskJob.created_at.desc())

        return PaginationHelper.paginate_query(
            query=query,
            page_options=search_dto,
            response_model=TaskJobResponse,
        )

    def get_job_status(self, db: Session, job_id: str, user_id: int) -> ResponseCommon:
        """Get job status by job_id."""
        try:
            job = (
                db.query(TaskJob)
                .filter(TaskJob.id == job_id, TaskJob.user_id == user_id)
                .first()
            )

            if not job:
                return ResponseCommon.error_response(message="Job not found", code=404)

            # Parse result from JSON string to dict if present
            result_data = None
            if job.result:
                try:
                    result_data = json.loads(job.result)
                except (json.JSONDecodeError, TypeError):
                    # If parsing fails, return as-is
                    result_data = job.result

            return ResponseCommon.success_response(
                data={
                    "job_id": job.id,
                    "task_type": job.task_type,
                    "status": job.status,
                    "result": result_data,
                    "error_message": job.error_message,
                    "created_at": job.created_at,
                    "updated_at": job.updated_at,
                },
                message="Job status retrieved successfully",
            )

        except Exception as exc:
            return ResponseCommon.error_response(
                message=f"Failed to get job status: {str(exc)}",
                code=500,
            )


task_job_service = TaskJobService()
