from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status, Query, Request, Form
from fastapi.responses import Response
from sqlalchemy.orm import Session
from typing import List, Optional
import json

from app.api.deps import get_db, get_current_active_user
from app.models import Note, User
from app.schemas.audio import AudioFile as AudioFileSchema, AudioFileUpdate, AudioSearchDto, AudioUploadResponse
from app.schemas.pagination import ResponseCommon as ResponseCommonSchema, PageDto
from app.common.pagination_utils import PaginationHelper
from app.common.common_message import CommonMessage
from app.common.response_common import ResponseCommon
from app.services.audio_service import audio_service
from app.services.task_job_service import task_job_service
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("audio_endpoints")

router = APIRouter()

@router.post("/upload")
async def upload_audio_file(
    file: UploadFile = File(...),
    folder_id: Optional[int] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Upload an audio file for the authenticated user.
    
    Supported formats: WAV, MP3, M4A, AAC, FLAC, OGG
    Maximum file size: 200MB
    """
    logger.info('Triggered endpoint: audio/upload')
    
    # Validate file
    validation_result = audio_service.validate_audio_file(file)
    if not validation_result.success:
        return Response(
            content=json.dumps(validation_result.to_json()),
            status_code=validation_result.code,
            media_type="application/json"
        )
    
    # Save file
    try:
        save_result = audio_service.save_uploaded_file(file, current_user)
        if not save_result.success:
            logger.error(f"Failed to save uploaded file: {save_result.message}")
            return Response(
                content=json.dumps(save_result.to_json()),
                status_code=save_result.code,
                media_type="application/json"
            )

        file_path = save_result.data["file_path"]
        file_format = save_result.data["file_format"]
        
        # Create database record
        create_result = audio_service.create_audio_record(
            db=db,
            file=file,
            user=current_user,
            file_path=file_path,
            file_format=file_format,
            folder_id=folder_id
        )
        if not create_result.success:
            logger.error(f"Failed to create audio record in DB: {create_result.message}")
            return Response(
                content=json.dumps(create_result.to_json()),
                status_code=create_result.code,
                media_type="application/json"
            )

        return create_result.to_json()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Exception during audio upload processing: {str(e)}")
        from app.common.response_common import ResponseCommon
        error_response = ResponseCommon.error_response(
            message=f"Failed to process audio upload: {str(e)}",
            code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
        return Response(
            content=json.dumps(error_response.to_json()),
            status_code=error_response.code,
            media_type="application/json"
        )

@router.post("/upload-async")
async def upload_audio_file_async(
    request: Request,
    file: UploadFile = File(...),
    folder_id: Optional[int] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Upload audio file with async processing.
    Returns job_id immediately for status polling.
    """
    logger.info("Triggered endpoint: audio/upload-async")

    validation_result = audio_service.validate_audio_file(file)
    if not validation_result.success:
        return Response(
            content=json.dumps(validation_result.to_json()),
            status_code=validation_result.code,
            media_type="application/json",
        )

    try:
        save_result = audio_service.save_uploaded_file(file, current_user)
        if not save_result.success:
            logger.error("Failed to save uploaded file: %s", save_result.message)
            return Response(
                content=json.dumps(save_result.to_json()),
                status_code=save_result.code,
                media_type="application/json",
            )

        file_path = save_result.data["file_path"]
        file_format = save_result.data["file_format"]

        create_result = audio_service.create_audio_record(
            db=db,
            file=file,
            user=current_user,
            file_path=file_path,
            file_format=file_format,
            folder_id=folder_id,
        )
        if not create_result.success:
            logger.error("Failed to create audio record in DB: %s", create_result.message)
            return Response(
                content=json.dumps(create_result.to_json()),
                status_code=create_result.code,
                media_type="application/json",
            )

        audio_file = create_result.data
        file_info = {
            "file_path": file_path,
            "file_format": file_format,
            "file_name": file.filename,
        }

        result = await task_job_service.create_and_queue_job(
            request=request,
            db=db,
            task_type="upload",
            task_function="handle_audio_upload",
            user_id=current_user.id,
            audio_id=audio_file.id,
            file_info=file_info,
        )

        return result.to_json()
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Exception during async audio upload processing: %s", str(exc))
        from app.common.response_common import ResponseCommon

        error_response = ResponseCommon.error_response(
            message=f"Failed to process async audio upload: {str(exc)}",
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
        return Response(
            content=json.dumps(error_response.to_json()),
            status_code=error_response.code,
            media_type="application/json",
        )

@router.post("/search", response_model=ResponseCommonSchema[PageDto[AudioFileSchema]])
async def search_audio_files(
    search_dto: AudioSearchDto,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Search and filter audio files with pagination.

    - **page**: Current page number (default: 1)
    - **page_size**: Items per page (default: 10)
    - **order**: Sort order - ASC or DESC (default: DESC)
    - **search**: Search in filename
    - **status**: Filter by processing status
    - **from_date**: Filter files uploaded after date
    - **to_date**: Filter files uploaded before date
    - **min_duration**: Minimum duration in seconds
    - **max_duration**: Maximum duration in seconds
    - **has_transcript**: Filter files with/without transcripts
    - **has_summary**: Filter files with/without summary notes

    Response includes:
    - **is_summarize**: Boolean indicating if the audio has been summarized
    """
    paginated_files = audio_service.search_audio_files(
        db=db,
        user_id=current_user.id,
        search_dto=search_dto,
    )

    return PaginationHelper.create_response(
        paginated_data=paginated_files,
        message="Audio files retrieved successfully",
    )


@router.put("/{audio_id}", response_model=ResponseCommonSchema[AudioFileSchema])
async def update_audio_file(
    audio_id: int,
    update_data: AudioFileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Update audio file information.

    This endpoint allows users to:
    - Edit the transcription text if it's incorrect
    - Update the original filename

    Only the provided fields will be updated (partial updates supported).
    """
    logger.info("Updating audio file %s for user %s", audio_id, current_user.id)

    update_dict = update_data.model_dump(exclude_unset=True)
    if not update_dict:
        from app.common.response_common import ResponseCommon

        error_response = ResponseCommon.error_response(
            message=CommonMessage.AUDIO_UPDATE_NO_FIELDS,
            code=status.HTTP_400_BAD_REQUEST,
        )
        return Response(
            content=json.dumps(error_response.to_json()),
            status_code=error_response.code,
            media_type="application/json",
        )

    update_response = audio_service.update_audio_file(
        db=db,
        audio_id=audio_id,
        user_id=current_user.id,
        update_data=update_dict,
    )

    if not update_response.success:
        return Response(
            content=json.dumps(update_response.to_json()),
            status_code=update_response.code,
            media_type="application/json",
        )

    return update_response.to_json()


@router.get("/files", deprecated=True)
def get_audio_files(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get all audio files for the authenticated user.

    Deprecated: Use POST /audio/search instead.
    """
    audio_files_response = audio_service.get_user_audio_files(
        db=db, 
        user=current_user, 
        skip=skip, 
        limit=limit
    )
    if not audio_files_response.success:
        return Response(
            content=json.dumps(audio_files_response.to_json()),
            status_code=audio_files_response.code,
            media_type="application/json"
        )
    return audio_files_response.to_json()

@router.get("/files/{audio_id}")
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
        return Response(
            content=json.dumps(audio_file_response.to_json()),
            status_code=audio_file_response.code,
            media_type="application/json"
        )

    audio_file = audio_file_response.data
    note_exists = db.query(Note).filter(Note.audio_file_id == audio_file.id).first() is not None
    audio_schema = AudioFileSchema.model_validate(
        {
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
            "is_summarize": bool(note_exists),
        }
    )

    return ResponseCommon.success_response(
        data=audio_schema,
        message=CommonMessage.AUDIO_RETRIEVED_SUCCESS,
    ).to_json()

@router.delete("/files/{audio_id}")
def delete_audio_file(
    audio_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Delete a specific audio file by ID for the authenticated user.
    """
    delete_response = audio_service.delete_audio_file(
        db=db,
        audio_id=audio_id,
        user_id=current_user.id
    )
    
    if not delete_response.success:
        return Response(
            content=json.dumps(delete_response.to_json()),
            status_code=delete_response.code,
            media_type="application/json"
        )
    
    return delete_response.to_json()

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
        return Response(
            content=json.dumps(audio_file_response.to_json()),
            status_code=audio_file_response.code,
            media_type="application/json"
        )

    audio_file = audio_file_response.data
    
    if not os.path.exists(audio_file.file_path):
        from app.common.response_common import ResponseCommon
        from app.common.common_message import CommonMessage
        error_response = ResponseCommon.error_response(
            message=CommonMessage.AUDIO_FILE_NOT_FOUND_ON_DISK,
            code=status.HTTP_404_NOT_FOUND
        )
        return Response(
            content=json.dumps(error_response.to_json()),
            status_code=error_response.code,
            media_type="application/json"
        )
    
    return FileResponse(
        path=audio_file.file_path,
        filename=audio_file.original_filename,
        media_type=f"audio/{audio_file.format}"
    )
