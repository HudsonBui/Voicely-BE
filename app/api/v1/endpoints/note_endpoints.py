from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.api.deps import get_db, get_current_active_user
from app.models import User
from app.common.command_message import CommonMessage
from app.schemas.note import (
    Note,
    NoteCreate,
    NoteUpdate,
    NotesListResponse,
    NoteCreateResponse,
    NoteCategoriesResponse,
    NotePrioritiesResponse,
    SummarizeTranscriptRequest,
    SummarizeTranscriptResponse,
    SemanticSearchRequest,
    SemanticSearchResponse
)
from app.services.note_service import (
    summarize_audio_transcript,
    get_notes_list,
    get_note_by_id,
    create_note,
    update_note,
    delete_note,
    get_note_categories,
    get_note_priorities,
    semantic_search_notes
)

router = APIRouter()


@router.get("", response_model=NotesListResponse)
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
        raise HTTPException(
            status_code=result.code,
            detail=result.message
        )
    
    return NotesListResponse(**result.data)


@router.get("/categories", response_model=NoteCategoriesResponse)
async def list_categories(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get all unique categories used by the current user.
    """
    categories_response = get_note_categories(db=db, user_id=current_user.id)
    if not categories_response.success:
        raise HTTPException(
            status_code=categories_response.code,
            detail=categories_response.message
        )
    return NoteCategoriesResponse(categories=categories_response.data)


@router.get("/priorities", response_model=NotePrioritiesResponse)
async def list_priorities():
    """
    Get list of available priority levels.
    """
    priorities_response = get_note_priorities()
    if not priorities_response.success:
        raise HTTPException(
            status_code=priorities_response.code,
            detail=priorities_response.message
        )
    return NotePrioritiesResponse(priorities=priorities_response.data)


@router.get("/{note_id}", response_model=Note)
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
        raise HTTPException(
            status_code=note_response.code,
            detail=note_response.message
        )
    return note_response.data


@router.post("", response_model=NoteCreateResponse, status_code=status.HTTP_201_CREATED)
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
        raise HTTPException(
            status_code=create_response.code,
            detail=create_response.message
        )

    return NoteCreateResponse(
        message=create_response.message or "Note created successfully",
        note=create_response.data
    )


@router.put("/{note_id}", response_model=Note)
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
        raise HTTPException(
            status_code=update_response.code,
            detail=update_response.message
        )
    
    return update_response.data


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
        raise HTTPException(
            status_code=delete_response.code,
            detail=delete_response.message
        )
    return {"message": delete_response.message}


@router.post("/summarize-transcript", response_model=SummarizeTranscriptResponse)
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
        raise HTTPException(
            status_code=result.code,
            detail=result.message
        )

    data = result.data or {}
    
    return SummarizeTranscriptResponse(
        audio_file_id=data.get("audio_file_id"),
        summary_html=data.get("summary_html", ""),
        note_id=data.get("note_id"),
        message=result.message or CommonMessage.SUMMARY_CREATED_SUCCESS
    )


@router.post("/semantic-search", response_model=SemanticSearchResponse)
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
        raise HTTPException(
            status_code=result.code,
            detail=result.message
        )
    
    data = result.data or {}
    
    return SemanticSearchResponse(
        results=data.get("results", []),
        total_count=data.get("total_count", 0),
        query=data.get("query", ""),
        search_in=data.get("search_in", "both"),
        message=result.message or "Semantic search completed"
    )
