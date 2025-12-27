from datetime import datetime
import logging
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import func, cast
from pgvector.sqlalchemy import Vector

from app.models.note_chunk_model import NoteChunk
from app.models.note_model import Note
from app.models.audio_model import AudioFile
from app.services.embedding_service import generate_query_embedding

logger = logging.getLogger(__name__)


class RAGContextService:
    """Service for building RAG context from user's content."""

    def semantic_search_with_filters(
        self,
        db: Session,
        user_id: int,
        query: str,
        entities: dict,
        limit: int = 5,
    ) -> list:
        """Search with semantic understanding and filters."""
        query_embedding = generate_query_embedding(query)
        if not query_embedding:
            logger.error("Failed to generate query embedding")
            return []

        query_obj = (
            db.query(NoteChunk)
            .join(Note, NoteChunk.note_id == Note.id)
            .outerjoin(AudioFile, Note.audio_file_id == AudioFile.id)
            .filter(Note.user_id == user_id, Note.is_archived == False)
        )

        date_range = entities.get("date_range") or {}
        start_date = self._parse_date(date_range.get("start"))
        end_date = self._parse_date(date_range.get("end"))
        if start_date:
            query_obj = query_obj.filter(Note.created_at >= start_date)
        if end_date:
            query_obj = query_obj.filter(Note.created_at <= end_date)

        categories = entities.get("categories") or []
        if categories:
            query_obj = query_obj.filter(Note.category.in_(categories))

        audio_ids = entities.get("audio_ids") or []
        if audio_ids:
            query_obj = query_obj.filter(Note.audio_file_id.in_(audio_ids))

        keywords = entities.get("keywords") or []
        if keywords:
            pattern = f"%{' '.join(keywords)}%"
            query_obj = query_obj.filter(NoteChunk.chunk_text.ilike(pattern))

        # Cast embedding to vector type for pgvector cosine_distance function
        embedding_vector = cast(query_embedding, Vector(768))
        
        chunks = (
            query_obj.order_by(func.cosine_distance(NoteChunk.embedding, embedding_vector))
            .limit(limit)
            .all()
        )

        return chunks

    def build_context(self, chunks: list, max_tokens: int = 3000) -> str:
        """Build context string from chunks, respecting token limit."""
        max_chars = max_tokens * 4
        context_parts = []
        total_chars = 0

        for chunk in chunks:
            note = chunk.note
            audio_name = note.audio_file.original_filename if note.audio_file else "N/A"
            chunk_text = (
                "---\n"
                f"Nguồn: {note.title}\n"
                f"Audio: {audio_name}\n"
                f"Ngày: {note.created_at.strftime('%Y-%m-%d')}\n"
                f"Nội dung: {chunk.chunk_text}\n"
                "---\n"
            )
            if total_chars + len(chunk_text) > max_chars:
                break
            context_parts.append(chunk_text)
            total_chars += len(chunk_text)

        return "\n".join(context_parts)

    def get_related_audio_files(self, chunks: list) -> list:
        """Extract unique audio files from chunks."""
        audio_files = []
        seen_ids = set()
        for chunk in chunks:
            if chunk.note.audio_file and chunk.note.audio_file.id not in seen_ids:
                audio_files.append(chunk.note.audio_file)
                seen_ids.add(chunk.note.audio_file.id)
        return audio_files

    def get_related_notes(self, chunks: list) -> list:
        """Extract unique notes from chunks."""
        notes = []
        seen_ids = set()
        for chunk in chunks:
            if chunk.note.id not in seen_ids:
                notes.append(chunk.note)
                seen_ids.add(chunk.note.id)
        return notes

    def _parse_date(self, value: Optional[str]) -> Optional[datetime]:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None


rag_context_service = RAGContextService()
