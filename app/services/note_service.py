import os
from typing import Optional
from google import genai
from google.genai import types
from sqlalchemy.orm import Session
from sqlalchemy import or_, cast, func
from pgvector.sqlalchemy import Vector
from fastapi import status
import logging

from app.common.common_message import CommonMessage
from app.common.constants import AIPrompts
from app.common.pagination_utils import PaginationHelper
from app.models import AudioFile, Note, NoteChunk
from app.common.response_common import ResponseCommon
from app.schemas.note import Note as NoteSchema, NoteSearchDto
from app.schemas.pagination import PageDto, SortOrder
from app.services.embedding_service import (
    chunk_text, 
    generate_chunk_embeddings, 
    generate_query_embedding
)

logger = logging.getLogger(__name__)


# Initialize the GenAI client for Vertex AI
client = genai.Client(
    vertexai=True, 
    project=os.getenv('GOOGLE_CLOUD_PROJECT'), 
    location=os.getenv('GOOGLE_CLOUD_LOCATION')
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

        timeout_seconds = int(os.getenv("SUMMARY_TIMEOUT_SECONDS", "7200"))
        request_options = {"timeout": timeout_seconds}

        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=AIPrompts.SUMMARY_SYSTEM_PROMPT,
                    temperature=0.7,
                ),
                request_options=request_options,
            )
        except TypeError:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=AIPrompts.SUMMARY_SYSTEM_PROMPT,
                    temperature=0.7,
                ),
            )

        logger.info("🚀 ~ NoteService ~ summarize_audio_transcript ~ generated summary for audio_file_id=%s", audio_file_id)
        
        # Parse and validate Quill Delta JSON
        summary_json_text = response.text.strip()
        logger.info("🚀 ~ NoteService ~ summarize_audio_transcript ~ raw_json_response=%s", summary_json_text)
        
        # Validate JSON format
        import json
        try:
            summary_delta = json.loads(summary_json_text)
            if not isinstance(summary_delta, list):
                raise ValueError("Summary must be a JSON array (Quill Delta format)")
            logger.info("✅ Valid Quill Delta JSON with %d operations", len(summary_delta))
            # Store as JSON string for database
            summary_json = json.dumps(summary_delta, ensure_ascii=False)
        except json.JSONDecodeError as je:
            logger.error("Invalid JSON from Gemini: %s", je)
            return ResponseCommon.error_response(
                message="AI returned invalid JSON format",
                code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
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
        
        # Create note first
        note = Note(
            user_id=user_id,
            audio_file_id=audio_file_id,
            title=title,
            content=audio_file.transcription,
            summary=summary_json,  # Store Quill Delta JSON string
            category="transcription",
            tags="audio,transcription"
        )
        
        db.add(note)
        db.flush()  # Get note.id without committing
        
        # Generate chunks with embeddings for content
        if audio_file.transcription:
            content_chunks = chunk_text(
                audio_file.transcription,
                chunk_size=1500,  # Increased from 500 to reduce API calls
                chunk_overlap=200,  # Increased proportionally
                chunk_type="content"
            )
            
            if content_chunks:
                content_chunks_with_embeddings = generate_chunk_embeddings(content_chunks)
                
                # Save chunks to database
                for chunk_data in content_chunks_with_embeddings:
                    if chunk_data["embedding"]:  # Only save if embedding was generated
                        note_chunk = NoteChunk(
                            note_id=note.id,
                            chunk_text=chunk_data["chunk_text"],
                            chunk_index=chunk_data["chunk_index"],
                            chunk_type=chunk_data["chunk_type"],
                            embedding=chunk_data["embedding"],
                            start_char=chunk_data["start_char"],
                            end_char=chunk_data["end_char"],
                            token_count=chunk_data["token_count"]
                        )
                        db.add(note_chunk)
                
                logger.info("Created %d content chunks for note %s", len(content_chunks_with_embeddings), note.id)
        
        # Generate chunks with embeddings for summary
        if summary_json:
            summary_chunks = chunk_text(
                summary_json,
                chunk_size=1500,  # Increased from 500 to reduce API calls
                chunk_overlap=200,  # Increased proportionally
                chunk_type="summary"
            )
            
            if summary_chunks:
                summary_chunks_with_embeddings = generate_chunk_embeddings(summary_chunks)
                
                # Save chunks to database
                for chunk_data in summary_chunks_with_embeddings:
                    if chunk_data["embedding"]:  # Only save if embedding was generated
                        note_chunk = NoteChunk(
                            note_id=note.id,
                            chunk_text=chunk_data["chunk_text"],
                            chunk_index=chunk_data["chunk_index"],
                            chunk_type=chunk_data["chunk_type"],
                            embedding=chunk_data["embedding"],
                            start_char=chunk_data["start_char"],
                            end_char=chunk_data["end_char"],
                            token_count=chunk_data["token_count"]
                        )
                        db.add(note_chunk)
                
                logger.info("Created %d summary chunks for note %s", len(summary_chunks_with_embeddings), note.id)
        
        db.commit()
        db.refresh(note)
        
        logger.info("Created note %s with summary for audio %s", note.id, audio_file_id)
        
        return ResponseCommon.success_response(
            code=status.HTTP_201_CREATED,
            message=CommonMessage.SUMMARY_CREATED_SUCCESS,
            data={
                "audio_file_id": audio_file_id,
                "summary_json": summary_delta,  # Return the object (list), not the string
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




def search_notes(db: Session, user_id: int, search_dto: NoteSearchDto) -> PageDto[NoteSchema]:
    """
    Search and filter notes with pagination

    Args:
        db: Database session
        user_id: Current user ID
        search_dto: Search filters and pagination options

    Returns:
        PageDto with notes and pagination metadata
    """
    query = db.query(Note).filter(Note.user_id == user_id)

    if search_dto.search:
        search_term = f"%{search_dto.search}%"
        query = query.filter(
            or_(
                Note.title.ilike(search_term),
                Note.content.ilike(search_term),
                Note.summary.ilike(search_term),
                Note.tags.ilike(search_term),
            )
        )

    if search_dto.category is not None:
        query = query.filter(Note.category == search_dto.category)

    if search_dto.priority is not None:
        query = query.filter(Note.priority == search_dto.priority)

    if search_dto.is_favorite is not None:
        query = query.filter(Note.is_favorite == search_dto.is_favorite)

    if search_dto.is_archived is not None:
        query = query.filter(Note.is_archived == search_dto.is_archived)
    else:
        query = query.filter(Note.is_archived == False)

    if search_dto.is_shared is not None:
        query = query.filter(Note.is_shared == search_dto.is_shared)

    if search_dto.audio_file_id is not None:
        query = query.filter(Note.audio_file_id == search_dto.audio_file_id)

    if search_dto.tags:
        query = query.filter(Note.tags.ilike(f"%{search_dto.tags}%"))

    if search_dto.from_date:
        query = query.filter(Note.created_at >= search_dto.from_date)

    if search_dto.to_date:
        query = query.filter(Note.created_at <= search_dto.to_date)

    order_value = getattr(search_dto.order, "value", search_dto.order)
    if str(order_value).upper() == SortOrder.ASC.value:
        query = query.order_by(Note.updated_at.asc())
    else:
        query = query.order_by(Note.updated_at.desc())

    return PaginationHelper.paginate_query(
        query=query,
        page_options=search_dto,
        response_model=NoteSchema,
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
    page = (skip // limit) + 1 if limit > 0 else 1
    search_dto = NoteSearchDto(
        page=page,
        page_size=limit,
        order=SortOrder.DESC,
        search=search,
        category=category,
        is_favorite=is_favorite,
        is_archived=is_archived,
    )
    paginated = search_notes(db=db, user_id=user_id, search_dto=search_dto)

    return ResponseCommon.success_response(
        data={
            "notes": paginated.data,
            "total_count": paginated.meta.item_count,
            "page": paginated.meta.page,
            "page_size": paginated.meta.page_size,
        },
        message=CommonMessage.NOTES_LIST_RETRIEVED_SUCCESS
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
    
    # Convert to schema to trigger validators
    note_schema = NoteSchema.model_validate(note)
    
    return ResponseCommon.success_response(
        data=note_schema,
        message=CommonMessage.NOTE_RETRIEVED_SUCCESS
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
        db.flush()  # Get note.id without committing
        
        # Generate chunks with embeddings for content
        if note_data.get("content"):
            content_chunks = chunk_text(
                note_data["content"],
                chunk_size=1500,
                chunk_overlap=200,
                chunk_type="content"
            )
            
            if content_chunks:
                content_chunks_with_embeddings = generate_chunk_embeddings(content_chunks)
                
                for chunk_data in content_chunks_with_embeddings:
                    if chunk_data["embedding"]:
                        note_chunk = NoteChunk(
                            note_id=note.id,
                            chunk_text=chunk_data["chunk_text"],
                            chunk_index=chunk_data["chunk_index"],
                            chunk_type=chunk_data["chunk_type"],
                            embedding=chunk_data["embedding"],
                            start_char=chunk_data["start_char"],
                            end_char=chunk_data["end_char"],
                            token_count=chunk_data["token_count"]
                        )
                        db.add(note_chunk)
                
                logger.info("Generated %d content chunks for new note", len(content_chunks_with_embeddings))
        
        # Generate chunks with embeddings for summary
        if note_data.get("summary"):
            summary_chunks = chunk_text(
                note_data["summary"],
                chunk_size=1500,
                chunk_overlap=200,
                chunk_type="summary"
            )
            
            if summary_chunks:
                summary_chunks_with_embeddings = generate_chunk_embeddings(summary_chunks)
                
                for chunk_data in summary_chunks_with_embeddings:
                    if chunk_data["embedding"]:
                        note_chunk = NoteChunk(
                            note_id=note.id,
                            chunk_text=chunk_data["chunk_text"],
                            chunk_index=chunk_data["chunk_index"],
                            chunk_type=chunk_data["chunk_type"],
                            embedding=chunk_data["embedding"],
                            start_char=chunk_data["start_char"],
                            end_char=chunk_data["end_char"],
                            token_count=chunk_data["token_count"]
                        )
                        db.add(note_chunk)
                
                logger.info("Generated %d summary chunks for new note", len(summary_chunks_with_embeddings))
        
        db.commit()
        db.refresh(note)
        
        logger.info("Created note %s for user %s", note.id, user_id)
        note_schema = NoteSchema.model_validate(note)
        return ResponseCommon.success_response(
            code=status.HTTP_201_CREATED,
            data=note_schema,
            message=CommonMessage.NOTE_CREATED_SUCCESS
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
    # Query the database directly to get the SQLAlchemy model (not the Pydantic schema)
    note = db.query(Note).filter(
        Note.id == note_id,
        Note.user_id == user_id
    ).first()
    
    if not note:
        return ResponseCommon.error_response(
            message=CommonMessage.NOTE_NOT_FOUND,
            code=status.HTTP_404_NOT_FOUND
        )
    
    try:
        # Generate new chunks with embeddings if content or summary is updated
        if "content" in update_data and update_data["content"]:
            # Delete old content chunks
            db.query(NoteChunk).filter(
                NoteChunk.note_id == note_id,
                NoteChunk.chunk_type == "content"
            ).delete()
            
            # Create new content chunks
            content_chunks = chunk_text(
                update_data["content"],
                chunk_size=1500,
                chunk_overlap=200,
                chunk_type="content"
            )
            
            if content_chunks:
                content_chunks_with_embeddings = generate_chunk_embeddings(content_chunks)
                
                for chunk_data in content_chunks_with_embeddings:
                    if chunk_data["embedding"]:
                        note_chunk = NoteChunk(
                            note_id=note_id,
                            chunk_text=chunk_data["chunk_text"],
                            chunk_index=chunk_data["chunk_index"],
                            chunk_type=chunk_data["chunk_type"],
                            embedding=chunk_data["embedding"],
                            start_char=chunk_data["start_char"],
                            end_char=chunk_data["end_char"],
                            token_count=chunk_data["token_count"]
                        )
                        db.add(note_chunk)
                
                logger.info("Updated %d content chunks for note %s", len(content_chunks_with_embeddings), note_id)
        
        if "summary" in update_data and update_data["summary"]:
            # Delete old summary chunks
            db.query(NoteChunk).filter(
                NoteChunk.note_id == note_id,
                NoteChunk.chunk_type == "summary"
            ).delete()
            
            # Create new summary chunks
            summary_chunks = chunk_text(
                update_data["summary"],
                chunk_size=1500,
                chunk_overlap=200,
                chunk_type="summary"
            )
            
            if summary_chunks:
                summary_chunks_with_embeddings = generate_chunk_embeddings(summary_chunks)
                
                for chunk_data in summary_chunks_with_embeddings:
                    if chunk_data["embedding"]:
                        note_chunk = NoteChunk(
                            note_id=note_id,
                            chunk_text=chunk_data["chunk_text"],
                            chunk_index=chunk_data["chunk_index"],
                            chunk_type=chunk_data["chunk_type"],
                            embedding=chunk_data["embedding"],
                            start_char=chunk_data["start_char"],
                            end_char=chunk_data["end_char"],
                            token_count=chunk_data["token_count"]
                        )
                        db.add(note_chunk)
                
                logger.info("Updated %d summary chunks for note %s", len(summary_chunks_with_embeddings), note_id)
        
        # Update only provided fields
        for field, value in update_data.items():
            if value is not None and hasattr(note, field):
                setattr(note, field, value)
        
        db.commit()
        db.refresh(note)
        
        logger.info("Updated note %s", note_id)
        note_schema = NoteSchema.model_validate(note)
        return ResponseCommon.success_response(
            data=note_schema,
            message=CommonMessage.NOTE_UPDATED_SUCCESS
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
    # Query the database directly to get the SQLAlchemy model (not the Pydantic schema)
    note = db.query(Note).filter(
        Note.id == note_id,
        Note.user_id == user_id
    ).first()
    
    if not note:
        return ResponseCommon.error_response(
            message=CommonMessage.NOTE_NOT_FOUND,
            code=status.HTTP_404_NOT_FOUND
        )
    
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
        message=CommonMessage.NOTE_CATEGORIES_RETRIEVED_SUCCESS
    )


def get_note_priorities() -> ResponseCommon:
    """
    Get list of available priority levels.
    
    Returns:
        List of priority strings
    """
    return ResponseCommon.success_response(
        data=["low", "normal", "high", "urgent"],
        message=CommonMessage.NOTE_PRIORITIES_RETRIEVED_SUCCESS
    )


def semantic_search_notes(
    db: Session,
    user_id: int,
    query: str,
    limit: int = 10,
    search_in: str = "both",  # "content", "summary", or "both"
    similarity_threshold: float = 0.5
) -> ResponseCommon:
    """
    Search notes using semantic similarity based on chunk embeddings.
    Uses RAG approach: searches through chunks and returns parent notes.
    
    Args:
        db: Database session
        user_id: User ID
        query: Search query text
        limit: Maximum number of results to return
        search_in: Where to search - "content", "summary", or "both"
        similarity_threshold: Minimum similarity score (0-1)
        
    Returns:
        List of notes with similarity scores, ordered by relevance
    """
    # Generate query embedding
    query_embedding = generate_query_embedding(query)
    
    if not query_embedding:
        return ResponseCommon.error_response(
            message="Failed to generate query embedding",
            code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    try:
        # Cast embedding to vector type for pgvector cosine_distance function
        embedding_vector = cast(query_embedding, Vector(768))
        
        # Build query to search through chunks
        chunk_query = db.query(
            NoteChunk.note_id,
            func.max(1 - func.cosine_distance(NoteChunk.embedding, embedding_vector)).label('max_similarity')
        ).join(
            Note, NoteChunk.note_id == Note.id
        ).filter(
            Note.user_id == user_id,
            Note.is_archived == False
        )
        
        # Filter by chunk_type based on search_in parameter
        if search_in == "content":
            chunk_query = chunk_query.filter(NoteChunk.chunk_type == "content")
        elif search_in == "summary":
            chunk_query = chunk_query.filter(NoteChunk.chunk_type == "summary")
        # If "both", no filter needed
        
        # Group by note_id and get the maximum similarity for each note
        chunk_query = chunk_query.group_by(NoteChunk.note_id).having(
            func.max(1 - func.cosine_distance(NoteChunk.embedding, embedding_vector)) >= similarity_threshold
        ).order_by(
            func.max(1 - func.cosine_distance(NoteChunk.embedding, embedding_vector)).desc()
        ).limit(limit)
        
        # Execute chunk query to get note_ids with similarities
        chunk_results = chunk_query.all()
        
        if not chunk_results:
            logger.info("Semantic search found 0 notes for user %s", user_id)
            return ResponseCommon.success_response(
                data={
                    "results": [],
                    "total_count": 0,
                    "query": query,
                    "search_in": search_in
                },
                message="No relevant notes found"
            )
        
        # Get the actual Note objects
        note_ids = [result.note_id for result in chunk_results]
        notes = db.query(Note).filter(Note.id.in_(note_ids)).all()
        
        # Create a mapping of note_id to similarity score
        similarity_map = {result.note_id: float(result.max_similarity) for result in chunk_results}
        
        # Sort notes by similarity score and format results
        notes_with_scores = [
            {
                "note": NoteSchema.model_validate(note),
                "similarity_score": similarity_map[note.id]
            }
            for note in sorted(notes, key=lambda n: similarity_map[n.id], reverse=True)
        ]
        
        logger.info(
            "Semantic search found %d notes for user %s (threshold=%.2f)",
            len(notes_with_scores),
            user_id,
            similarity_threshold
        )
        
        return ResponseCommon.success_response(
            data={
                "results": notes_with_scores,
                "total_count": len(notes_with_scores),
                "query": query,
                "search_in": search_in
            },
            message=CommonMessage.SEMANTIC_SEARCH_COMPLETED
        )
        
    except Exception as e:
        logger.error("Semantic search failed: %s", e, exc_info=True)
        return ResponseCommon.error_response(
            message="Semantic search failed",
            code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
