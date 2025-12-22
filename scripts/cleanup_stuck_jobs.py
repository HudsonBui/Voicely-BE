from datetime import datetime, timedelta, timezone

from app.db.session import SessionLocal
from app.models.task_job_model import TaskJob


def main() -> None:
    db = SessionLocal()
    try:
        timeout = datetime.now(timezone.utc) - timedelta(hours=2)

        stuck_jobs = (
            db.query(TaskJob)
            .filter(TaskJob.status == "processing", TaskJob.updated_at < timeout)
            .all()
        )

        for job in stuck_jobs:
            job.status = "failed"
            job.error_message = "Job timeout - exceeded maximum processing time"

        db.commit()
        print(f"Cleaned up {len(stuck_jobs)} stuck jobs")
    finally:
        db.close()


if __name__ == "__main__":
    main()
