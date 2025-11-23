from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List

from app.api.deps import get_db, get_current_active_user
from app.models import User
from app.schemas.audio import AudioFile as AudioFileSchema, AudioUploadResponse
from app.services.audio_service import audio_service

router = APIRouter()

@router.post("/upload", response_model=AudioUploadResponse)
async def upload_audio_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Upload an audio file for the authenticated user.
    
    Supported formats: WAV, MP3, M4A, AAC, FLAC, OGG
    Maximum file size: 50MB
    """
    
    # Validate file
    validation_result = audio_service.validate_audio_file(file)
    if not validation_result.success:
        raise HTTPException(
            status_code=validation_result.code,
            detail=validation_result.message
        )
    
    # Save file
    try:
        save_result = audio_service.save_uploaded_file(file, current_user)
        if not save_result.success:
            raise HTTPException(
                status_code=save_result.code,
                detail=save_result.message
            )

        file_path = save_result.data["file_path"]
        file_format = save_result.data["file_format"]
        
        # Create database record
        create_result = audio_service.create_audio_record(
            db=db,
            file=file,
            user=current_user,
            file_path=file_path,
            file_format=file_format
        )
        if not create_result.success:
            raise HTTPException(
                status_code=create_result.code,
                detail=create_result.message
            )

        audio_file = create_result.data
        
        return AudioUploadResponse(
            message="Audio file uploaded successfully",
            audio_file=audio_file,
            upload_info={
                "file_size_mb": round(audio_file.file_size / (1024 * 1024), 2),
                "format": audio_file.format,
                "duration_seconds": audio_file.duration,
                "status": audio_file.status
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process audio upload: {str(e)}"
        )

@router.get("/files", response_model=List[AudioFileSchema])
def get_audio_files(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get all audio files for the authenticated user.
    """
    audio_files_response = audio_service.get_user_audio_files(
        db=db, 
        user=current_user, 
        skip=skip, 
        limit=limit
    )
    if not audio_files_response.success:
        raise HTTPException(
            status_code=audio_files_response.code,
            detail=audio_files_response.message
        )
    return audio_files_response.data

@router.get("/files/{audio_id}", response_model=AudioFileSchema)
def get_audio_file(
    audio_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get a specific audio file by ID for the authenticated user.
    """
    audio_file_response = audio_service.get_audio_file_by_id(
        db=db,
        audio_id=audio_id,
        user=current_user
    )
    
    if not audio_file_response.success:
        raise HTTPException(
            status_code=audio_file_response.code,
            detail=audio_file_response.message
        )
    
    return audio_file_response.data

@router.delete("/files/{audio_id}")
def delete_audio_file(
    audio_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Delete a specific audio file by ID for the authenticated user.
    """
    audio_file_response = audio_service.get_audio_file_by_id(
        db=db,
        audio_id=audio_id,
        user=current_user
    )
    
    if not audio_file_response.success:
        raise HTTPException(
            status_code=audio_file_response.code,
            detail=audio_file_response.message
        )
    
    delete_response = audio_service.delete_audio_file(
        db=db,
        audio_file=audio_file_response.data
    )
    
    if not delete_response.success:
        raise HTTPException(
            status_code=delete_response.code,
            detail=delete_response.message
        )
    
    return {"message": delete_response.message}

@router.get("/files/{audio_id}/download")
def download_audio_file(
    audio_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Download a specific audio file by ID for the authenticated user.
    """
    from fastapi.responses import FileResponse
    import os
    
    audio_file_response = audio_service.get_audio_file_by_id(
        db=db,
        audio_id=audio_id,
        user=current_user
    )
    
    if not audio_file_response.success:
        raise HTTPException(
            status_code=audio_file_response.code,
            detail=audio_file_response.message
        )

    audio_file = audio_file_response.data
    
    if not os.path.exists(audio_file.file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audio file not found on disk"
        )
    
    return FileResponse(
        path=audio_file.file_path,
        filename=audio_file.original_filename,
        media_type=f"audio/{audio_file.format}"
    )
