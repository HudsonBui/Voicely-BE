from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session
from typing import Optional
import json

from app.api.deps import get_db, get_current_active_user
from app.models import User
from app.common.common_message import CommonMessage
from app.schemas.note import (
    Note,
    NoteCreate,
    NoteUpdate,
    NoteSearchDto,
    NotesListResponse,
    NoteCreateResponse,
    NoteCategoriesResponse,
    NotePrioritiesResponse,
    SummarizeTranscriptRequest,
    SummarizeTranscriptResponse,
    SemanticSearchRequest,
    SemanticSearchResponse
)
from app.schemas.pagination import ResponseCommon as ResponseCommonSchema, PageDto
from app.common.pagination_utils import PaginationHelper
from app.common.response_common import ResponseCommon
from app.services.note_service import (
    summarize_audio_transcript,
    get_notes_list,
    get_note_by_id,
    create_note,
    update_note,
    delete_note,
    get_note_categories,
    get_note_priorities,
    semantic_search_notes,
    search_notes as search_notes_service
)
from app.services.task_job_service import task_job_service

router = APIRouter()


@router.post("/search", response_model=ResponseCommonSchema[PageDto[Note]])
async def search_notes(
    search_dto: NoteSearchDto,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Search and filter notes with pagination.

    - **page**: Current page number (default: 1)
    - **page_size**: Items per page (default: 10)
    - **order**: Sort order - ASC or DESC (default: DESC)
    - **search**: Search in title, content, summary, tags
    - **category**: Filter by category
    - **priority**: Filter by priority
    - **is_favorite**: Filter favorite notes
    - **is_archived**: Filter archived notes
    - **is_shared**: Filter shared notes
    - **tags**: Filter by tags
    - **from_date**: Filter notes created after date
    - **to_date**: Filter notes created before date
    - **audio_file_id**: Filter by linked audio file
    """
    paginated_notes = search_notes_service(
        db=db,
        user_id=current_user.id,
        search_dto=search_dto,
    )

    return PaginationHelper.create_response(
        paginated_data=paginated_notes,
        message="Notes retrieved successfully",
    )


@router.get("", deprecated=True)
async def list_notes(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of records to return"),
    category: Optional[str] = Query(None, description="Filter by category"),
    is_favorite: Optional[bool] = Query(None, description="Filter by favorite status"),
    is_archived: Optional[bool] = Query(None, description="Filter by archived status"),
    search: Optional[str] = Query(None, description="Search in title, content, and tags"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get a paginated list of notes with optional filters.
    
    By default, archived notes are not shown unless is_archived=true is specified.

    Deprecated: Use POST /notes/search instead.
    """
    result = get_notes_list(
        db=db,
        user_id=current_user.id,
        skip=skip,
        limit=limit,
        category=category,
        is_favorite=is_favorite,
        is_archived=is_archived,
        search=search
    )
    
    if not result.success:
        return Response(
            content=json.dumps(result.to_json()),
            status_code=result.code,
            media_type="application/json"
        )
    
    return result.to_json()


@router.get("/categories")
async def list_categories(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get all unique categories used by the current user.
    """
    categories_response = get_note_categories(db=db, user_id=current_user.id)
    if not categories_response.success:
        return Response(
            content=json.dumps(categories_response.to_json()),
            status_code=categories_response.code,
            media_type="application/json"
        )
    return categories_response.to_json()


@router.get("/priorities")
async def list_priorities():
    """
    Get list of available priority levels.
    """
    priorities_response = get_note_priorities()
    if not priorities_response.success:
        return Response(
            content=json.dumps(priorities_response.to_json()),
            status_code=priorities_response.code,
            media_type="application/json"
        )
    return priorities_response.to_json()


@router.get("/{note_id}")
async def get_note(
    note_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get a single note by ID.
    """
    note_response = get_note_by_id(db=db, note_id=note_id, user_id=current_user.id)
    if not note_response.success:
        return Response(
            content=json.dumps(note_response.to_json()),
            status_code=note_response.code,
            media_type="application/json"
        )
    note_schema = Note.model_validate(note_response.data)
    return ResponseCommon.success_response(
        data=note_schema,
        message=CommonMessage.NOTE_RETRIEVED_SUCCESS,
    ).to_json()


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_new_note(
    note_data: NoteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Create a new note.
    
    Can optionally link to an audio file by providing audio_file_id.
    """
    create_response = create_note(
        db=db,
        user_id=current_user.id,
        note_data=note_data.model_dump(exclude_unset=True)
    )
    
    if not create_response.success:
        return Response(
            content=json.dumps(create_response.to_json()),
            status_code=create_response.code,
            media_type="application/json"
        )

    return create_response.to_json()


@router.put("/{note_id}")
async def update_existing_note(
    note_id: int,
    update_data: NoteUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Update a note.
    
    Only provided fields will be updated. Null/missing fields are ignored.
    """
    update_response = update_note(
        db=db,
        note_id=note_id,
        user_id=current_user.id,
        update_data=update_data.model_dump(exclude_unset=True)
    )
    
    if not update_response.success:
        return Response(
            content=json.dumps(update_response.to_json()),
            status_code=update_response.code,
            media_type="application/json"
        )
    
    return update_response.to_json()


@router.delete("/{note_id}", status_code=status.HTTP_200_OK)
async def delete_existing_note(
    note_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Delete a note permanently.
    """
    delete_response = delete_note(db=db, note_id=note_id, user_id=current_user.id)
    if not delete_response.success:
        return Response(
            content=json.dumps(delete_response.to_json()),
            status_code=delete_response.code,
            media_type="application/json"
        )
    return delete_response.to_json()


@router.post("/summarize-transcript")
async def summarize_transcript(
    request: SummarizeTranscriptRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Generate an AI summary of an audio file's transcription and create a note.
    
    This endpoint:
    1. Retrieves the audio file by ID
    2. Checks if it has been transcribed
    3. Generates an HTML summary using Vertex AI Gemini
    4. Creates a new note with the summary
    
    Args:
        request: Contains audio_file_id
        
    Returns:
        Summary HTML and the created note ID
    """
    
    result = summarize_audio_transcript(
        db=db,
        audio_file_id=request.audio_file_id,
        user_id=current_user.id
    )
    
    if not result.success:
        return Response(
            content=json.dumps(result.to_json()),
            status_code=result.code,
            media_type="application/json"
        )

    return result.to_json()


@router.post("/summarize-transcript-async")
async def summarize_transcript_async(
    request: Request,
    summarize_request: SummarizeTranscriptRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Summarize audio transcript asynchronously.
    Returns job_id for status polling.
    """
    result = await task_job_service.create_and_queue_job(
        request=request,
        db=db,
        task_type="summarize",
        task_function="handle_summarization",
        user_id=current_user.id,
        audio_id=summarize_request.audio_file_id,
    )

    return result.to_json()


@router.post("/semantic-search")
async def search_notes_by_semantic(
    request: SemanticSearchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Search notes using semantic similarity based on vector embeddings.
    
    This endpoint uses AI embeddings to find notes that are semantically similar
    to your search query, even if they don't contain the exact keywords.
    
    Args:
        request: Contains query text and search parameters
            - query: The search query text
            - limit: Maximum number of results (default: 10)
            - search_in: Where to search - "content", "summary", or "both" (default: "both")
            - similarity_threshold: Minimum similarity score 0-1 (default: 0.5)
        
    Returns:
        List of notes with similarity scores, ordered by relevance
    """
    
    result = semantic_search_notes(
        db=db,
        user_id=current_user.id,
        query=request.query,
        limit=request.limit,
        search_in=request.search_in,
        similarity_threshold=request.similarity_threshold
    )
    
    if not result.success:
        return Response(
            content=json.dumps(result.to_json()),
            status_code=result.code,
            media_type="application/json"
        )
    
    return result.to_json()
