import os
import uuid
from datetime import datetime, timezone
from typing import Optional
from fastapi import UploadFile, status
from sqlalchemy.orm import Session
import shutil
from pathlib import Path
import subprocess

from app.models import AudioFile as AudioFileModel, Note, User
from app.schemas.audio import AudioFileCreate, AudioFile as AudioFileSchema, AudioSearchDto
from app.common.pagination_utils import PaginationHelper
from app.common.common_message import CommonMessage
from app.common.response_common import ResponseCommon
from app.schemas.pagination import PageDto, PageMetaDto
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class AudioService:
    def __init__(self):
        self.upload_dir = Path("uploads/audio")
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.allowed_formats = {
            'audio/wav': 'wav',
            'audio/mpeg': 'mp3', 
            'audio/mp3': 'mp3',
            'audio/x-wav': 'wav',
            'audio/wave': 'wav',
            'audio/mp4': 'm4a',
            'audio/aac': 'aac',
            'audio/flac': 'flac',
            'audio/ogg': 'ogg'
        }
        self.max_file_size = 200 * 1024 * 1024  # 200MB limit

    def validate_audio_file(self, file: UploadFile) -> ResponseCommon:
        """Validate uploaded audio file"""

        logger.info("Triggered Audio Validation Service ~ validate_audio_file")
        
        # Check file size
        if hasattr(file, 'size') and file.size > self.max_file_size:
            return ResponseCommon.error_response(
                message=CommonMessage.AUDIO_FILE_TOO_LARGE,
                code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
            )
        
        # Check content type
        content_type = file.content_type
        if content_type not in self.allowed_formats:
            return ResponseCommon.error_response(
                message=CommonMessage.AUDIO_FILE_INVALID_FORMAT,
                code=status.HTTP_400_BAD_REQUEST
            )
        
        # Additional validation could include:
        # - File header validation
        # - Duration limits
        # - Sample rate checks
        
        return ResponseCommon.success_response()

    def save_uploaded_file(self, file: UploadFile, user: User) -> ResponseCommon:
        """Save uploaded file to disk and return file path and format"""
        
        logger.info("Triggered Audio Save Service ~ save_uploaded_file")
        
        # Generate unique filename
        file_extension = self.allowed_formats.get(file.content_type, 'unknown')
        unique_filename = f"{user.id}_{uuid.uuid4().hex}.{file_extension}"
        file_path = self.upload_dir / unique_filename
        
        # Save file
        try:
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
        except Exception:
            return ResponseCommon.error_response(
                message=CommonMessage.AUDIO_FILE_SAVE_FAILED,
                code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        return ResponseCommon.success_response(
            code=status.HTTP_201_CREATED,
            message=CommonMessage.AUDIO_UPLOADED_SUCCESS,
            data={
                "file_path": str(file_path),
                "file_format": file_extension
            }
        )

    def get_audio_duration(self, file_path: str) -> Optional[float]:
        """Get audio duration using ffprobe (if available)"""
        try:
            # Using ffprobe to get duration
            result = subprocess.run([
                'ffprobe', '-v', 'quiet', '-show_entries', 
                'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', 
                file_path
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                duration = float(result.stdout.strip())
                return duration
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, ValueError, FileNotFoundError):
            # ffprobe not available or failed, return None
            pass
        
        return None

    def create_audio_record(
        self, 
        db: Session, 
        file: UploadFile, 
        user: User, 
        file_path: str, 
        file_format: str,
        folder_id: Optional[int] = None
    ) -> ResponseCommon:
        """Create audio file record in database"""
        
        # Get file size
        file_size = 0
        if hasattr(file, 'size'):
            file_size = file.size
        else:
            try:
                file_size = os.path.getsize(file_path)
            except OSError:
                file_size = 0
        
        # Get duration if possible
        duration = self.get_audio_duration(file_path)
        
        # Create database record
        audio_data = AudioFileCreate(
            filename=Path(file_path).name,
            original_filename=file.filename or "unknown",
            file_size=file_size,
            duration=duration,
            format=file_format,
            folder_id=folder_id
        )
        
        audio_file = AudioFileModel(
            user_id=user.id,
            folder_id=audio_data.folder_id,
            filename=audio_data.filename,
            original_filename=audio_data.original_filename,
            file_path=file_path,
            file_size=audio_data.file_size,
            duration=audio_data.duration,
            format=audio_data.format,
            status="uploaded"
        )
        
        try:
            db.add(audio_file)
            db.commit()
            db.refresh(audio_file)
        except Exception:
            db.rollback()
            return ResponseCommon.error_response(
                message=CommonMessage.AUDIO_FILE_SAVE_FAILED,
                code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        audio_schema = AudioFileSchema.model_validate(audio_file)
        return ResponseCommon.success_response(
            code=status.HTTP_201_CREATED,
            message=CommonMessage.AUDIO_UPLOADED_SUCCESS,
            data=audio_schema
        )

    def update_audio_file(
        self,
        db: Session,
        audio_id: int,
        user_id: int,
        update_data: dict
    ) -> ResponseCommon:
        """
        Update audio file information.

        Args:
            db: Database session
            audio_id: ID of the audio file to update
            user_id: ID of the current user
            update_data: Dictionary of fields to update

        Returns:
            ResponseCommon with updated audio file or error
        """
        audio_file = db.query(AudioFileModel).filter(
            AudioFileModel.id == audio_id,
            AudioFileModel.user_id == user_id
        ).first()

        if not audio_file:
            return ResponseCommon.error_response(
                message=CommonMessage.AUDIO_NOT_FOUND,
                code=status.HTTP_404_NOT_FOUND
            )

        allowed_fields = {"transcription", "original_filename", "folder_id"}
        has_values = any(
            field in allowed_fields and value is not None
            for field, value in update_data.items()
        )
        if not has_values:
            return ResponseCommon.error_response(
                message=CommonMessage.AUDIO_UPDATE_NO_FIELDS,
                code=status.HTTP_400_BAD_REQUEST
            )

        updated = False
        transcription_updated = False
        changes = []

        for field, value in update_data.items():
            if value is None or field not in allowed_fields:
                continue

            if field == "original_filename":
                if audio_file.original_filename != value:
                    audio_file.original_filename = value
                    base_name = value.rsplit(".", 1)[0]
                    audio_file.filename = f"{base_name}.{audio_file.format}"
                    changes.append(field)
                    updated = True
            else:
                if getattr(audio_file, field) != value:
                    setattr(audio_file, field, value)
                    changes.append(field)
                    updated = True
                    if field == "transcription":
                        transcription_updated = True

        try:
            if transcription_updated:
                deleted_count = db.query(Note).filter(
                    Note.audio_file_id == audio_id
                ).delete(synchronize_session=False)
                if deleted_count:
                    logger.info(
                        "Deleted %d note(s) for audio %s due to transcription update",
                        deleted_count,
                        audio_id,
                    )

            if updated:
                audio_file.updated_at = datetime.now(timezone.utc)
                db.commit()
                db.refresh(audio_file)
            else:
                db.commit()

            note_exists = db.query(Note.id).filter(
                Note.audio_file_id == audio_file.id
            ).first() is not None
            audio_schema = self._build_audio_search_results([(audio_file, note_exists)])[0]

            if changes:
                logger.info(
                    "User %s updated audio %s: %s",
                    user_id,
                    audio_id,
                    ", ".join(changes),
                )

            return ResponseCommon.success_response(
                data=audio_schema,
                message=CommonMessage.AUDIO_UPDATED_SUCCESS
            )
        except Exception as exc:
            db.rollback()
            logger.error("Error updating audio file %s: %s", audio_id, str(exc), exc_info=True)
            return ResponseCommon.error_response(
                message=CommonMessage.AUDIO_FILE_SAVE_FAILED,
                code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def search_audio_files(
        self, db: Session, user_id: int, search_dto: AudioSearchDto
    ) -> PageDto[AudioFileSchema]:
        """
        Search and filter audio files with pagination

        Args:
            db: Database session
            user_id: Current user ID
            search_dto: Search filters and pagination options

        Returns:
            PageDto with audio files and pagination metadata
        """
        note_exists_subquery = db.query(Note.id).filter(
            Note.audio_file_id == AudioFileModel.id
        ).exists()

        query = db.query(
            AudioFileModel,
            note_exists_subquery.label("has_note"),
        ).filter(AudioFileModel.user_id == user_id)

        if search_dto.folder_id is not None:
            query = query.filter(AudioFileModel.folder_id == search_dto.folder_id)

        if search_dto.search:
            search_term = f"%{search_dto.search}%"
            query = query.filter(AudioFileModel.filename.ilike(search_term))

        if search_dto.status:
            query = query.filter(AudioFileModel.status == search_dto.status)

        if search_dto.from_date:
            query = query.filter(AudioFileModel.created_at >= search_dto.from_date)

        if search_dto.to_date:
            query = query.filter(AudioFileModel.created_at <= search_dto.to_date)

        if search_dto.min_duration is not None:
            query = query.filter(AudioFileModel.duration >= search_dto.min_duration)

        if search_dto.max_duration is not None:
            query = query.filter(AudioFileModel.duration <= search_dto.max_duration)

        if search_dto.has_transcript is not None:
            if search_dto.has_transcript:
                query = query.filter(AudioFileModel.transcription.isnot(None))
            else:
                query = query.filter(AudioFileModel.transcription.is_(None))

        if search_dto.has_summary is not None:
            if search_dto.has_summary:
                query = query.filter(note_exists_subquery)
            else:
                query = query.filter(~note_exists_subquery)

        order_value = getattr(search_dto.order, "value", search_dto.order)
        if str(order_value).upper() == "ASC":
            query = query.order_by(AudioFileModel.created_at.asc())
        else:
            query = query.order_by(AudioFileModel.created_at.desc())

        if search_dto.is_dropdown:
            results = query.all()
            audio_files = self._build_audio_search_results(results)
            meta = PageMetaDto(
                page=1,
                page_size=len(audio_files),
                item_count=len(audio_files),
                page_count=1,
                has_previous_page=False,
                has_next_page=False,
            )
            return PageDto(data=audio_files, meta=meta)

        total_items = query.count()
        offset = (search_dto.page - 1) * search_dto.page_size
        results = query.offset(offset).limit(search_dto.page_size).all()

        meta = PaginationHelper.create_meta(
            page=search_dto.page,
            page_size=search_dto.page_size,
            total_items=total_items,
        )
        audio_files = self._build_audio_search_results(results)
        return PageDto(data=audio_files, meta=meta)

    def _build_audio_search_results(self, results):
        audio_files = []
        for audio_file, has_note in results:
            audio_dict = {
                "id": audio_file.id,
                "user_id": audio_file.user_id,
                "folder_id": audio_file.folder_id,
                "filename": audio_file.filename,
                "original_filename": audio_file.original_filename,
                "file_path": audio_file.file_path,
                "file_size": audio_file.file_size,
                "duration": audio_file.duration,
                "format": audio_file.format,
                "status": audio_file.status,
                "transcription": audio_file.transcription,
                "confidence_score": audio_file.confidence_score,
                "created_at": audio_file.created_at,
                "updated_at": audio_file.updated_at,
                "is_summarize": bool(has_note),
            }
            audio_files.append(AudioFileSchema(**audio_dict))
        return audio_files

    def get_user_audio_files(self, db: Session, user: User, skip: int = 0, limit: int = 100) -> ResponseCommon:
        """Get audio files for a user"""
        page = (skip // limit) + 1 if limit > 0 else 1
        search_dto = AudioSearchDto(page=page, page_size=limit)
        paginated = self.search_audio_files(db=db, user_id=user.id, search_dto=search_dto)
        return ResponseCommon.success_response(
            data=paginated.data,
            message=CommonMessage.AUDIO_LIST_RETRIEVED_SUCCESS
        )

    def get_audio_file_by_id(self, db: Session, audio_id: int, user: User) -> ResponseCommon:
        """Get specific audio file by ID for a user"""
        audio_file = db.query(AudioFileModel).filter(
            AudioFileModel.id == audio_id,
            AudioFileModel.user_id == user.id
        ).first()

        if not audio_file:
            return ResponseCommon.error_response(
                message=CommonMessage.AUDIO_NOT_FOUND,
                code=status.HTTP_404_NOT_FOUND
            )

        return ResponseCommon.success_response(
            data=audio_file,
            message=CommonMessage.AUDIO_RETRIEVED_SUCCESS
        )

    def delete_audio_file(self, db: Session, audio_id: int, user_id: int) -> ResponseCommon:
        """Delete audio file from database and filesystem"""
        audio_file = db.query(AudioFileModel).filter(
            AudioFileModel.id == audio_id,
            AudioFileModel.user_id == user_id
        ).first()

        if not audio_file:
            return ResponseCommon.error_response(
                message=CommonMessage.AUDIO_NOT_FOUND,
                code=status.HTTP_404_NOT_FOUND
            )

        try:
            # Delete from filesystem
            if os.path.exists(audio_file.file_path):
                os.remove(audio_file.file_path)

            # Delete from database
            db.delete(audio_file)
            db.commit()
            return ResponseCommon.success_response(
                message=CommonMessage.AUDIO_DELETED_SUCCESS
            )
        except Exception:
            db.rollback()
            return ResponseCommon.error_response(
                message=CommonMessage.AUDIO_FILE_SAVE_FAILED,
                code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

audio_service = AudioService()
