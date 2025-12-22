import uuid
from typing import Optional

from fastapi import Request
from sqlalchemy.orm import Session

from app.common.response_common import ResponseCommon
from app.models.task_job_model import TaskJob


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
        if not hasattr(request.app.state, "arq_pool"):
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

            return ResponseCommon.success_response(
                data={
                    "job_id": job.id,
                    "task_type": job.task_type,
                    "status": job.status,
                    "result": job.result,
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
