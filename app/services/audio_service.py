import os
import uuid
from typing import Optional
from fastapi import UploadFile, status
from sqlalchemy.orm import Session
import shutil
from pathlib import Path
import subprocess

from app.models import AudioFile, User
from app.schemas.audio import AudioFileCreate
from app.common.common_message import CommonMessage
from app.common.response_common import ResponseCommon
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
        self.max_file_size = 70 * 1024 * 1024  # 70MB limit

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
        file_format: str
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
            format=file_format
        )
        
        audio_file = AudioFile(
            user_id=user.id,
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
        
        return ResponseCommon.success_response(
            code=status.HTTP_201_CREATED,
            message=CommonMessage.AUDIO_UPLOADED_SUCCESS,
            data=audio_file
        )

    def get_user_audio_files(self, db: Session, user: User, skip: int = 0, limit: int = 100) -> ResponseCommon:
        """Get audio files for a user"""
        audio_files = db.query(AudioFile).filter(
            AudioFile.user_id == user.id
        ).offset(skip).limit(limit).all()
        return ResponseCommon.success_response(
            data=audio_files,
            message=CommonMessage.AUDIO_LIST_RETRIEVED_SUCCESS
        )

    def get_audio_file_by_id(self, db: Session, audio_id: int, user: User) -> ResponseCommon:
        """Get specific audio file by ID for a user"""
        audio_file = db.query(AudioFile).filter(
            AudioFile.id == audio_id,
            AudioFile.user_id == user.id
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

    def delete_audio_file(self, db: Session, audio_file: AudioFile) -> ResponseCommon:
        """Delete audio file from database and filesystem"""
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
