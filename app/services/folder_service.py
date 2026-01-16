import logging
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from fastapi import status

from app.models import Folder, AudioFile, User
from app.schemas.folder import FolderCreate, FolderSearchDto, Folder as FolderSchema
from app.schemas.pagination import PageDto
from app.common.pagination_utils import PaginationHelper
from app.common.response_common import ResponseCommon

logger = logging.getLogger(__name__)


class FolderService:
    
    def create_folder(self, db: Session, user_id: int, folder_data: FolderCreate) -> ResponseCommon:
        """Create a new folder for a user"""
        try:
            # If is_default is True, unset other default folders
            if folder_data.is_default:
                db.query(Folder).filter(
                    Folder.user_id == user_id,
                    Folder.is_default == True
                ).update({"is_default": False})
            
            # Create new folder
            folder = Folder(
                user_id=user_id,
                name=folder_data.name,
                description=folder_data.description,
                color=folder_data.color,
                icon=folder_data.icon,
                is_default=folder_data.is_default
            )
            
            db.add(folder)
            db.commit()
            db.refresh(folder)
            
            # Add audio count
            folder_dict = {
                "id": folder.id,
                "user_id": folder.user_id,
                "name": folder.name,
                "description": folder.description,
                "color": folder.color,
                "icon": folder.icon,
                "is_default": folder.is_default,
                "created_at": folder.created_at,
                "updated_at": folder.updated_at,
                "audio_count": 0
            }
            
            return ResponseCommon.success_response(
                data=folder_dict,
                message="Folder created successfully",
                code=status.HTTP_201_CREATED
            )
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error creating folder: {str(e)}")
            return ResponseCommon.error_response(
                message=f"Failed to create folder: {str(e)}",
                code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def get_folder(self, db: Session, folder_id: int, user_id: int) -> ResponseCommon:
        """Get a specific folder by ID"""
        folder = db.query(Folder).filter(
            Folder.id == folder_id,
            Folder.user_id == user_id
        ).first()
        
        if not folder:
            return ResponseCommon.error_response(
                message="Folder not found",
                code=status.HTTP_404_NOT_FOUND
            )
        
        # Get audio count
        audio_count = db.query(func.count(AudioFile.id)).filter(
            AudioFile.folder_id == folder_id
        ).scalar()
        
        folder_dict = {
            "id": folder.id,
            "user_id": folder.user_id,
            "name": folder.name,
            "description": folder.description,
            "color": folder.color,
            "icon": folder.icon,
            "is_default": folder.is_default,
            "created_at": folder.created_at,
            "updated_at": folder.updated_at,
            "audio_count": audio_count or 0
        }
        
        return ResponseCommon.success_response(data=folder_dict)
    
    def list_folders(self, db: Session, user_id: int, skip: int = 0, limit: int = 100) -> ResponseCommon:
        """List all folders for a user"""
        folders = db.query(
            Folder,
            func.count(AudioFile.id).label('audio_count')
        ).outerjoin(
            AudioFile, AudioFile.folder_id == Folder.id
        ).filter(
            Folder.user_id == user_id
        ).group_by(Folder.id).order_by(Folder.created_at.desc()).offset(skip).limit(limit).all()
        
        folders_list = []
        for folder, audio_count in folders:
            folder_dict = {
                "id": folder.id,
                "user_id": folder.user_id,
                "name": folder.name,
                "description": folder.description,
                "color": folder.color,
                "icon": folder.icon,
                "is_default": folder.is_default,
                "created_at": folder.created_at,
                "updated_at": folder.updated_at,
                "audio_count": audio_count or 0
            }
            folders_list.append(folder_dict)
        
        return ResponseCommon.success_response(data=folders_list)

    def search_folders(
        self, db: Session, user_id: int, search_dto: FolderSearchDto
    ) -> PageDto[FolderSchema]:
        """
        Search and filter folders with pagination.

        Args:
            db: Database session
            user_id: Current user ID
            search_dto: Search criteria and pagination options

        Returns:
            PageDto containing folders and pagination metadata
        """
        try:
            audio_count_expr = func.count(AudioFile.id)
            query = db.query(
                Folder,
                audio_count_expr.label("audio_count"),
            ).outerjoin(
                AudioFile,
                and_(
                    AudioFile.folder_id == Folder.id,
                    AudioFile.user_id == user_id,
                ),
            ).filter(
                Folder.user_id == user_id
            ).group_by(Folder.id)

            if search_dto.search:
                search_term = f"%{search_dto.search}%"
                query = query.filter(
                    or_(
                        Folder.name.ilike(search_term),
                        Folder.description.ilike(search_term),
                    )
                )

            if search_dto.is_default is not None:
                query = query.filter(Folder.is_default == search_dto.is_default)

            if search_dto.color:
                query = query.filter(Folder.color == search_dto.color)

            if search_dto.has_audio is not None:
                if search_dto.has_audio:
                    query = query.having(audio_count_expr > 0)
                else:
                    query = query.having(audio_count_expr == 0)

            if search_dto.min_audio_count is not None:
                query = query.having(audio_count_expr >= search_dto.min_audio_count)

            if search_dto.max_audio_count is not None:
                query = query.having(audio_count_expr <= search_dto.max_audio_count)

            if search_dto.from_date:
                query = query.filter(Folder.created_at >= search_dto.from_date)

            if search_dto.to_date:
                query = query.filter(Folder.created_at <= search_dto.to_date)

            order_value = getattr(search_dto.order, "value", search_dto.order)
            if str(order_value).upper() == "ASC":
                query = query.order_by(Folder.created_at.asc())
            else:
                query = query.order_by(Folder.created_at.desc())

            if search_dto.is_dropdown:
                results = query.all()
                folders_with_count = self._build_folder_search_results(results)
                meta = PaginationHelper.create_meta(
                    page=1,
                    page_size=len(folders_with_count),
                    total_items=len(folders_with_count),
                )
                return PageDto(data=folders_with_count, meta=meta)

            total_items = db.query(func.count()).select_from(query.subquery()).scalar() or 0
            offset = (search_dto.page - 1) * search_dto.page_size
            results = query.offset(offset).limit(search_dto.page_size).all()

            folders_with_count = self._build_folder_search_results(results)
            meta = PaginationHelper.create_meta(
                page=search_dto.page,
                page_size=search_dto.page_size,
                total_items=total_items,
            )

            return PageDto(data=folders_with_count, meta=meta)
        except Exception as e:
            logger.error("Error searching folders: %s", str(e), exc_info=True)
            raise
    
    def update_folder(self, db: Session, folder_id: int, user_id: int, update_data: dict) -> ResponseCommon:
        """Update folder information"""
        folder = db.query(Folder).filter(
            Folder.id == folder_id,
            Folder.user_id == user_id
        ).first()
        
        if not folder:
            return ResponseCommon.error_response(
                message="Folder not found",
                code=status.HTTP_404_NOT_FOUND
            )
        
        try:
            # If setting as default, unset other defaults
            if update_data.get("is_default") == True:
                db.query(Folder).filter(
                    Folder.user_id == user_id,
                    Folder.id != folder_id,
                    Folder.is_default == True
                ).update({"is_default": False})
            
            # Update folder fields
            for field, value in update_data.items():
                if value is not None and hasattr(folder, field):
                    setattr(folder, field, value)
            
            db.commit()
            db.refresh(folder)
            
            # Get audio count
            audio_count = db.query(func.count(AudioFile.id)).filter(
                AudioFile.folder_id == folder_id
            ).scalar()
            
            folder_dict = {
                "id": folder.id,
                "user_id": folder.user_id,
                "name": folder.name,
                "description": folder.description,
                "color": folder.color,
                "icon": folder.icon,
                "is_default": folder.is_default,
                "created_at": folder.created_at,
                "updated_at": folder.updated_at,
                "audio_count": audio_count or 0
            }
            
            return ResponseCommon.success_response(
                data=folder_dict,
                message="Folder updated successfully"
            )
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error updating folder: {str(e)}")
            return ResponseCommon.error_response(
                message=f"Failed to update folder: {str(e)}",
                code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def delete_folder(self, db: Session, folder_id: int, user_id: int) -> ResponseCommon:
        """Delete a folder (audio files will be unassigned, not deleted)"""
        folder = db.query(Folder).filter(
            Folder.id == folder_id,
            Folder.user_id == user_id
        ).first()
        
        if not folder:
            return ResponseCommon.error_response(
                message="Folder not found",
                code=status.HTTP_404_NOT_FOUND
            )
        
        try:
            # Unassign audio files from this folder (set folder_id to NULL)
            db.query(AudioFile).filter(
                AudioFile.folder_id == folder_id
            ).update({"folder_id": None})
            
            # Delete the folder
            db.delete(folder)
            db.commit()
            
            return ResponseCommon.success_response(
                message="Folder deleted successfully"
            )
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error deleting folder: {str(e)}")
            return ResponseCommon.error_response(
                message=f"Failed to delete folder: {str(e)}",
                code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def move_audio_to_folder(
        self, 
        db: Session, 
        audio_id: int, 
        folder_id: Optional[int], 
        user_id: int
    ) -> ResponseCommon:
        """Move an audio file to a folder (or remove from folder if folder_id is None)"""
        # Check audio file exists and belongs to user
        audio = db.query(AudioFile).filter(
            AudioFile.id == audio_id,
            AudioFile.user_id == user_id
        ).first()
        
        if not audio:
            return ResponseCommon.error_response(
                message="Audio file not found",
                code=status.HTTP_404_NOT_FOUND
            )
        
        # If folder_id is provided, verify it exists and belongs to user
        if folder_id is not None:
            folder = db.query(Folder).filter(
                Folder.id == folder_id,
                Folder.user_id == user_id
            ).first()
            
            if not folder:
                return ResponseCommon.error_response(
                    message="Folder not found",
                    code=status.HTTP_404_NOT_FOUND
                )
        
        try:
            audio.folder_id = folder_id
            db.commit()
            db.refresh(audio)
            
            message = "Audio file moved to folder" if folder_id else "Audio file removed from folder"
            
            audio_dict = {
                "id": audio.id,
                "user_id": audio.user_id,
                "folder_id": audio.folder_id,
                "filename": audio.filename,
                "original_filename": audio.original_filename,
                "file_path": audio.file_path,
                "file_size": audio.file_size,
                "duration": audio.duration,
                "format": audio.format,
                "status": audio.status,
                "transcription": audio.transcription,
                "confidence_score": audio.confidence_score,
                "created_at": audio.created_at,
                "updated_at": audio.updated_at,
            }
            
            return ResponseCommon.success_response(
                data=audio_dict,
                message=message
            )
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error moving audio to folder: {str(e)}")
            return ResponseCommon.error_response(
                message=f"Failed to move audio: {str(e)}",
                code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def get_folder_audio_files(
        self, 
        db: Session, 
        folder_id: int, 
        user_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> ResponseCommon:
        """Get all audio files in a specific folder"""
        # Verify folder exists and belongs to user
        folder = db.query(Folder).filter(
            Folder.id == folder_id,
            Folder.user_id == user_id
        ).first()
        
        if not folder:
            return ResponseCommon.error_response(
                message="Folder not found",
                code=status.HTTP_404_NOT_FOUND
            )
        
        # Get audio files
        audio_files = db.query(AudioFile).filter(
            AudioFile.folder_id == folder_id
        ).order_by(AudioFile.created_at.desc()).offset(skip).limit(limit).all()
        
        audio_list = []
        for audio in audio_files:
            audio_dict = {
                "id": audio.id,
                "user_id": audio.user_id,
                "folder_id": audio.folder_id,
                "filename": audio.filename,
                "original_filename": audio.original_filename,
                "file_path": audio.file_path,
                "file_size": audio.file_size,
                "duration": audio.duration,
                "format": audio.format,
                "status": audio.status,
                "transcription": audio.transcription,
                "confidence_score": audio.confidence_score,
                "created_at": audio.created_at,
                "updated_at": audio.updated_at,
            }
            audio_list.append(audio_dict)
        
        return ResponseCommon.success_response(data=audio_list)

    @staticmethod
    def _build_folder_search_results(results):
        folders_with_count = []
        for folder, audio_count in results:
            folder_dict = {
                "id": folder.id,
                "user_id": folder.user_id,
                "name": folder.name,
                "description": folder.description,
                "color": folder.color,
                "icon": folder.icon,
                "is_default": folder.is_default,
                "created_at": folder.created_at,
                "updated_at": folder.updated_at,
                "audio_count": audio_count or 0,
            }
            folders_with_count.append(FolderSchema(**folder_dict))
        return folders_with_count


# Create service instance
folder_service = FolderService()
