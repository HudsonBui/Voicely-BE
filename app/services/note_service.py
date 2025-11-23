import os
from typing import Optional
from google import genai
from google.genai import types
from sqlalchemy.orm import Session
from sqlalchemy import desc, or_
from fastapi import status
import logging

from app.common.command_message import CommonMessage
from app.common.constants import AIPrompts
from app.models import AudioFile, Note
from app.common.response_common import ResponseCommon

logger = logging.getLogger(__name__)


# Initialize the GenAI client for Vertex AI
client = genai.Client(
    vertexai=True, 
    project=os.getenv('GOOGLE_CLOUD_PROJECT'), 
    location='asia-southeast1'
)


def summarize_audio_transcript(
    db: Session,
    audio_file_id: int,
    user_id: int
) -> ResponseCommon:
    """
    Summarize an audio file's transcription and create a note.
    """
    audio_file = db.query(AudioFile).filter(
        AudioFile.id == audio_file_id,
        AudioFile.user_id == user_id
    ).first()
    
    if not audio_file:
        return ResponseCommon.error_response(
            message=CommonMessage.AUDIO_NOT_FOUND,
            code=status.HTTP_404_NOT_FOUND
        )
    
    if not audio_file.transcription:
        return ResponseCommon.error_response(
            message=CommonMessage.AUDIO_NOT_TRANSCRIBED,
            code=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        user_prompt = AIPrompts.SUMMARY_USER_PROMPT.format(content=audio_file.transcription)
        
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=AIPrompts.SUMMARY_SYSTEM_PROMPT,
                temperature=0.3,
                max_output_tokens=2048,
            )
        )
        
        summary_html = response.text.strip()
        logger.info("Successfully generated summary (%s chars)", len(summary_html))
        
    except Exception as e:
        logger.error("Failed to generate summary: %s", e, exc_info=True)
        return ResponseCommon.error_response(
            message=CommonMessage.SUMMARY_GENERATION_FAILED,
            code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    try:
        title = audio_file.original_filename.rsplit('.', 1)[0][:100]
        if not title:
            title = f"Note from {audio_file.created_at.strftime('%Y-%m-%d %H:%M')}"
        
        note = Note(
            user_id=user_id,
            audio_file_id=audio_file_id,
            title=title,
            content=audio_file.transcription,
            summary=summary_html,
            category="transcription",
            tags="audio,transcription"
        )
        
        db.add(note)
        db.commit()
        db.refresh(note)
        
        logger.info("Created note %s with summary for audio %s", note.id, audio_file_id)
        
        return ResponseCommon.success_response(
            code=status.HTTP_201_CREATED,
            message=CommonMessage.SUMMARY_CREATED_SUCCESS,
            data={
                "audio_file_id": audio_file_id,
                "summary_html": summary_html,
                "note_id": note.id
            }
        )
        
    except Exception as e:
        db.rollback()
        logger.error("Failed to create note: %s", e, exc_info=True)
        return ResponseCommon.error_response(
            message=CommonMessage.NOTE_CREATE_FAILED,
            code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )




def get_notes_list(
    db: Session,
    user_id: int,
    skip: int = 0,
    limit: int = 20,
    category: Optional[str] = None,
    is_favorite: Optional[bool] = None,
    is_archived: Optional[bool] = None,
    search: Optional[str] = None
) -> ResponseCommon:
    """
    Get a paginated list of notes for a user with optional filters.
    
    Args:
        db: Database session
        user_id: User ID
        skip: Number of records to skip
        limit: Maximum number of records to return
        category: Filter by category
        is_favorite: Filter by favorite status
        is_archived: Filter by archived status
        search: Search in title, content, and summary
        
    Returns:
        Dictionary with notes list and pagination info
    """
    query = db.query(Note).filter(Note.user_id == user_id)
    
    # Apply filters
    if category:
        query = query.filter(Note.category == category)
    
    if is_favorite is not None:
        query = query.filter(Note.is_favorite == is_favorite)
    
    if is_archived is not None:
        query = query.filter(Note.is_archived == is_archived)
    else:
        # Default: don't show archived notes unless explicitly requested
        query = query.filter(Note.is_archived == False)
    
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            or_(
                Note.title.ilike(search_pattern),
                Note.content.ilike(search_pattern),
                Note.summary.ilike(search_pattern),
                Note.tags.ilike(search_pattern)
            )
        )
    
    # Get total count
    total_count = query.count()
    
    # Get paginated results
    notes = query.order_by(desc(Note.updated_at)).offset(skip).limit(limit).all()
    
    return ResponseCommon.success_response(
        data={
            "notes": notes,
            "total_count": total_count,
            "page": (skip // limit) + 1 if limit > 0 else 1,
            "page_size": limit
        },
        message="Notes retrieved successfully"
    )


def get_note_by_id(db: Session, note_id: int, user_id: int) -> ResponseCommon:
    """
    Get a single note by ID.
    
    Args:
        db: Database session
        note_id: Note ID
        user_id: User ID (for ownership verification)
        
    Returns:
        Note object
        
    Raises:
        HTTPException: If note not found or user doesn't own it
    """
    note = db.query(Note).filter(
        Note.id == note_id,
        Note.user_id == user_id
    ).first()
    
    if not note:
        return ResponseCommon.error_response(
            message=CommonMessage.NOTE_NOT_FOUND,
            code=status.HTTP_404_NOT_FOUND
        )
    
    return ResponseCommon.success_response(
        data=note,
        message="Note retrieved successfully"
    )


def create_note(db: Session, user_id: int, note_data: dict) -> ResponseCommon:
    """
    Create a new note.
    
    Args:
        db: Database session
        user_id: User ID
        note_data: Dictionary containing note fields
        
    Returns:
        Created note object
        
    Raises:
        HTTPException: If creation fails
    """
    try:
        # Verify audio file exists and belongs to user if provided
        if note_data.get("audio_file_id"):
            audio_file = db.query(AudioFile).filter(
                AudioFile.id == note_data["audio_file_id"],
                AudioFile.user_id == user_id
            ).first()
            
            if not audio_file:
                return ResponseCommon.error_response(
                    message=CommonMessage.AUDIO_NOT_FOUND,
                    code=status.HTTP_404_NOT_FOUND
                )
        
        # Create note
        note = Note(
            user_id=user_id,
            **note_data
        )
        
        db.add(note)
        db.commit()
        db.refresh(note)
        
        logger.info("Created note %s for user %s", note.id, user_id)
        return ResponseCommon.success_response(
            code=status.HTTP_201_CREATED,
            data=note,
            message="Note created successfully"
        )
        
    except Exception as e:
        db.rollback()
        logger.error("Failed to create note: %s", e, exc_info=True)
        return ResponseCommon.error_response(
            message=CommonMessage.NOTE_CREATE_FAILED,
            code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


def update_note(db: Session, note_id: int, user_id: int, update_data: dict) -> ResponseCommon:
    """
    Update a note.
    
    Args:
        db: Database session
        note_id: Note ID
        user_id: User ID (for ownership verification)
        update_data: Dictionary containing fields to update
        
    Returns:
        Updated note object
        
    Raises:
        HTTPException: If note not found or update fails
    """
    note_response = get_note_by_id(db, note_id, user_id)
    if not note_response.success:
        return note_response

    note = note_response.data
    
    try:
        # Update only provided fields
        for field, value in update_data.items():
            if value is not None and hasattr(note, field):
                setattr(note, field, value)
        
        db.commit()
        db.refresh(note)
        
        logger.info("Updated note %s", note_id)
        return ResponseCommon.success_response(
            data=note,
            message="Note updated successfully"
        )
        
    except Exception as e:
        db.rollback()
        logger.error("Failed to update note %s: %s", note_id, e, exc_info=True)
        return ResponseCommon.error_response(
            message=CommonMessage.NOTE_UPDATE_FAILED,
            code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


def delete_note(db: Session, note_id: int, user_id: int) -> ResponseCommon:
    """
    Delete a note.
    
    Args:
        db: Database session
        note_id: Note ID
        user_id: User ID (for ownership verification)
        
    Returns:
        Success message
        
    Raises:
        HTTPException: If note not found or deletion fails
    """
    note_response = get_note_by_id(db, note_id, user_id)
    if not note_response.success:
        return note_response

    note = note_response.data
    
    try:
        db.delete(note)
        db.commit()
        
        logger.info("Deleted note %s", note_id)
        return ResponseCommon.success_response(
            message=CommonMessage.NOTE_DELETED_SUCCESS
        )
        
    except Exception as e:
        db.rollback()
        logger.error("Failed to delete note %s: %s", note_id, e, exc_info=True)
        return ResponseCommon.error_response(
            message=CommonMessage.NOTE_DELETE_FAILED,
            code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


def get_note_categories(db: Session, user_id: int) -> ResponseCommon:
    """
    Get all unique categories used by the user.
    
    Args:
        db: Database session
        user_id: User ID
        
    Returns:
        List of category strings
    """
    categories = db.query(Note.category).filter(
        Note.user_id == user_id,
        Note.category.isnot(None)
    ).distinct().all()
    
    return ResponseCommon.success_response(
        data=[cat[0] for cat in categories if cat[0]],
        message="Note categories retrieved successfully"
    )


def get_note_priorities() -> ResponseCommon:
    """
    Get list of available priority levels.
    
    Returns:
        List of priority strings
    """
    return ResponseCommon.success_response(
        data=["low", "normal", "high", "urgent"],
        message="Note priorities retrieved successfully"
    )
