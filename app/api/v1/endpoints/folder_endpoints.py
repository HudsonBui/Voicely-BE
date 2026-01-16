from fastapi import APIRouter, Depends, status
from fastapi.responses import Response
from sqlalchemy.orm import Session
import json

from app.api.deps import get_db, get_current_active_user
from app.models import User
from app.schemas.folder import FolderCreate, FolderUpdate, MoveAudioToFolder, Folder, FolderSearchDto
from app.schemas.pagination import ResponseCommon as ResponseCommonSchema, PageDto
from app.common.pagination_utils import PaginationHelper
from app.services.folder_service import folder_service

router = APIRouter()


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_folder(
    folder_data: FolderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Create a new folder for organizing audio files.
    
    - **name**: Folder name (required)
    - **description**: Optional description
    - **color**: Hex color code (e.g., #FF5733)
    - **icon**: Icon identifier
    - **is_default**: Set as default folder for new uploads
    """
    response = folder_service.create_folder(
        db=db,
        user_id=current_user.id,
        folder_data=folder_data
    )
    
    return Response(
        content=json.dumps(response.to_json(), default=str),
        status_code=response.code,
        media_type="application/json",
    )


@router.get("/", deprecated=True)
async def list_folders(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    List all folders for the authenticated user.
    
    Returns folders with audio file count.

    ⚠️ DEPRECATED: Use POST /folders/search instead.
    """
    response = folder_service.list_folders(
        db=db,
        user_id=current_user.id,
        skip=skip,
        limit=limit
    )
    
    return Response(
        content=json.dumps(response.to_json(), default=str),
        status_code=response.code,
        media_type="application/json",
    )


@router.post("/search", response_model=ResponseCommonSchema[PageDto[Folder]])
async def search_folders(
    search_dto: FolderSearchDto,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Search and filter folders with pagination.

    - **page**: Current page number (default: 1)
    - **page_size**: Items per page (default: 10)
    - **order**: Sort order - ASC or DESC (default: DESC)
    - **search**: Search in folder name and description
    - **is_default**: Filter default folders
    - **color**: Filter by color (hex code)
    - **has_audio**: Filter folders with/without audio files
    - **min_audio_count**: Minimum number of audio files
    - **max_audio_count**: Maximum number of audio files
    - **from_date**: Filter folders created after date
    - **to_date**: Filter folders created before date
    - **is_dropdown**: Return all items without pagination

    Response includes:
    - **data**: Array of folders with audio_count
    - **meta**: Pagination metadata (page, page_size, item_count, page_count, etc.)
    """
    paginated_folders = folder_service.search_folders(
        db=db,
        user_id=current_user.id,
        search_dto=search_dto,
    )

    return PaginationHelper.create_response(
        paginated_data=paginated_folders,
        message="Folders retrieved successfully",
    )


@router.get("/{folder_id}")
async def get_folder(
    folder_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get a specific folder by ID.
    
    Returns folder details with audio count.
    """
    response = folder_service.get_folder(
        db=db,
        folder_id=folder_id,
        user_id=current_user.id
    )
    
    return Response(
        content=json.dumps(response.to_json(), default=str),
        status_code=response.code,
        media_type="application/json",
    )


@router.put("/{folder_id}")
async def update_folder(
    folder_id: int,
    update_data: FolderUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Update folder information.
    
    Only provided fields will be updated (partial updates supported).
    """
    update_dict = update_data.model_dump(exclude_unset=True)
    
    response = folder_service.update_folder(
        db=db,
        folder_id=folder_id,
        user_id=current_user.id,
        update_data=update_dict
    )
    
    return Response(
        content=json.dumps(response.to_json(), default=str),
        status_code=response.code,
        media_type="application/json",
    )


@router.delete("/{folder_id}")
async def delete_folder(
    folder_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Delete a folder.
    
    Audio files in the folder will be unassigned (not deleted).
    """
    response = folder_service.delete_folder(
        db=db,
        folder_id=folder_id,
        user_id=current_user.id
    )
    
    return Response(
        content=json.dumps(response.to_json(), default=str),
        status_code=response.code,
        media_type="application/json",
    )


@router.get("/{folder_id}/audio")
async def get_folder_audio_files(
    folder_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get all audio files in a specific folder.
    
    Returns paginated list of audio files.
    """
    response = folder_service.get_folder_audio_files(
        db=db,
        folder_id=folder_id,
        user_id=current_user.id,
        skip=skip,
        limit=limit
    )
    
    return Response(
        content=json.dumps(response.to_json(), default=str),
        status_code=response.code,
        media_type="application/json",
    )


@router.post("/move-audio")
async def move_audio_to_folder(
    move_data: MoveAudioToFolder,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Move an audio file to a folder.
    
    - **audio_id**: ID of audio file to move
    - **folder_id**: Target folder ID (null to remove from folder)
    """
    response = folder_service.move_audio_to_folder(
        db=db,
        audio_id=move_data.audio_id,
        folder_id=move_data.folder_id,
        user_id=current_user.id
    )
    
    return Response(
        content=json.dumps(response.to_json(), default=str),
        status_code=response.code,
        media_type="application/json",
    )
