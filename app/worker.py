import json
import logging
from typing import Optional

from sqlalchemy.orm import Session

from app.core.redis_config import REDIS_SETTINGS
from app.db.session import SessionLocal
from app.models import AudioFile
from app.models.task_job_model import TaskJob

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("arq.worker")


async def handle_audio_upload(
    ctx,
    job_id: str,
    file_info: dict,
    user_id: int,
    audio_id: Optional[int] = None,
):
    """
    Background task for processing uploaded audio files.
    """
    db: Session = SessionLocal()
    job_record = None
    audio_file = None
    try:
        logger.info("Starting audio upload processing for job: %s", job_id)

        job_record = db.query(TaskJob).filter(TaskJob.id == job_id).first()
        if not job_record:
            logger.error("Job %s not found in database", job_id)
            return

        if audio_id is not None:
            audio_file = (
                db.query(AudioFile)
                .filter(AudioFile.id == audio_id, AudioFile.user_id == user_id)
                .first()
            )

        job_record.status = "processing"
        if audio_file:
            audio_file.status = "processing"
        db.commit()

        result = {
            "file_name": file_info.get("file_name"),
            "file_path": file_info.get("file_path"),
            "format": file_info.get("file_format") or file_info.get("format"),
            "processed": True,
        }

        job_record.status = "completed"
        job_record.result = json.dumps(result)
        if audio_file:
            audio_file.status = "completed"
        db.commit()

        logger.info("Completed audio upload processing for job: %s", job_id)
    except Exception as exc:
        logger.error("Error processing audio upload job %s: %s", job_id, str(exc))
        db.rollback()
        if job_record:
            job_record.status = "failed"
            job_record.error_message = str(exc)
        if audio_file:
            audio_file.status = "failed"
        if job_record or audio_file:
            db.commit()
    finally:
        db.close()


async def handle_transcription(
    ctx,
    job_id: str,
    audio_id: int,
    language_code: str,
    user_id: int,
):
    """
    Background task for transcribing audio files.
    """
    db: Session = SessionLocal()
    job_record = None
    audio_file = None
    try:
        logger.info("Starting transcription for job: %s, audio_id: %s", job_id, audio_id)

        job_record = db.query(TaskJob).filter(TaskJob.id == job_id).first()
        if not job_record:
            logger.error("Job %s not found in database", job_id)
            return

        audio_file = (
            db.query(AudioFile)
            .filter(AudioFile.id == audio_id, AudioFile.user_id == user_id)
            .first()
        )
        if not audio_file:
            raise Exception(f"Audio file not found: {audio_id}")

        if audio_file.transcription and audio_file.status == "completed":
            job_record.status = "completed"
            job_record.result = audio_file.transcription
            db.commit()
            logger.info("Transcription already completed for audio_id: %s", audio_id)
            return

        job_record.status = "processing"
        audio_file.status = "processing"
        db.commit()

        from app.services.transcript_service import transcript_service

        transcription_response = transcript_service.transcribe_audio(
            audio_file=audio_file,
            language_code=language_code,
        )
        if not transcription_response.success:
            raise Exception(transcription_response.message)

        update_response = transcript_service.update_audio_file_transcription(
            db=db,
            audio_file=audio_file,
            transcription_result=transcription_response.data or {},
        )
        if not update_response.success:
            raise Exception(update_response.message)

        job_record.status = "completed"
        if transcription_response.data:
            job_record.result = transcription_response.data.get("transcript")
        db.commit()

        logger.info("Completed transcription for job: %s", job_id)
    except Exception as exc:
        logger.error("Error processing transcription job %s: %s", job_id, str(exc))
        db.rollback()
        if job_record:
            job_record.status = "failed"
            job_record.error_message = str(exc)
        if audio_file:
            audio_file.status = "failed"
        if job_record or audio_file:
            db.commit()
    finally:
        db.close()


async def handle_summarization(ctx, job_id: str, audio_id: int, user_id: int):
    """
    Background task for summarizing transcripts.
    """
    db: Session = SessionLocal()
    job_record = None
    try:
        logger.info("Starting summarization for job: %s, audio_id: %s", job_id, audio_id)

        job_record = db.query(TaskJob).filter(TaskJob.id == job_id).first()
        if not job_record:
            logger.error("Job %s not found in database", job_id)
            return

        job_record.status = "processing"
        db.commit()

        from app.services.note_service import summarize_audio_transcript

        summary_response = summarize_audio_transcript(
            db=db,
            audio_file_id=audio_id,
            user_id=user_id,
        )
        if not summary_response.success:
            raise Exception(summary_response.message)

        job_record.status = "completed"
        job_record.result = json.dumps(summary_response.data)
        db.commit()

        logger.info("Completed summarization for job: %s", job_id)
    except Exception as exc:
        logger.error("Error processing summarization job %s: %s", job_id, str(exc))
        db.rollback()
        if job_record:
            job_record.status = "failed"
            job_record.error_message = str(exc)
            db.commit()
    finally:
        db.close()


async def handle_chatbot_message(
    ctx,
    job_id: str,
    session_id: str,
    message: str,
    user_id: int,
):
    """Background task for processing chatbot messages."""
    db: Session = SessionLocal()
    job_record = None
    try:
        logger.info("Starting chatbot processing for job: %s", job_id)

        job_record = db.query(TaskJob).filter(TaskJob.id == job_id).first()
        if not job_record:
            logger.error("Job %s not found in database", job_id)
            return

        job_record.status = "processing"
        db.commit()

        from app.services.chatbot_service import chatbot_service

        result = await chatbot_service.process_message(
            db=db,
            user_id=user_id,
            session_id=session_id,
            message=message,
        )

        job_record.status = "completed"
        job_record.result = json.dumps(result, ensure_ascii=False)
        db.commit()

        logger.info("Completed chatbot processing for job: %s", job_id)
    except Exception as exc:
        logger.error("Error processing chatbot job %s: %s", job_id, str(exc))
        db.rollback()
        if job_record:
            job_record.status = "failed"
            job_record.error_message = str(exc)
            db.commit()
    finally:
        db.close()


class WorkerSettings:
    """ARQ Worker configuration."""

    functions = [
        handle_audio_upload,
        handle_transcription,
        handle_summarization,
        handle_chatbot_message,
    ]
    redis_settings = REDIS_SETTINGS
    max_jobs = 10
    job_timeout = 3600
    keep_result = 3600
