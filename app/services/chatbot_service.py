import os
import time
import uuid
import logging
from typing import Optional, List

from google import genai
from google.genai import types
from sqlalchemy.orm import Session

from app.models.chatbot_model import ChatbotSession, ChatbotMessage
from app.services.intent_service import intent_service
from app.services.rag_context_service import rag_context_service

logger = logging.getLogger(__name__)


class ChatbotService:
    """Main chatbot orchestration service."""

    def __init__(self):
        self.client = genai.Client(
            vertexai=True,
            project=os.getenv("GOOGLE_CLOUD_PROJECT"),
            location=os.getenv("GOOGLE_CLOUD_LOCATION"),
        )
        self.model_name = os.getenv("CHATBOT_RESPONSE_MODEL", "gemini-2.5-flash")

    async def process_message(
        self,
        db: Session,
        user_id: int,
        session_id: str,
        message: str,
    ) -> dict:
        """Main pipeline for processing chatbot messages."""
        start_time = time.time()

        try:
            session = self._get_session(db, user_id, session_id)
            history = self._get_conversation_history(db, session_id)

            intent_result = intent_service.classify_intent(message, history)
            intent = intent_result.get("intent", "chat")
            if intent not in {"search", "summarize", "question", "manage", "analytics", "chat"}:
                intent = "chat"
            entities = intent_result.get("entities", {}) or {}
            if not isinstance(entities, dict):
                entities = {}
            confidence = intent_result.get("confidence", 0.0)
            try:
                confidence = float(confidence)
            except (TypeError, ValueError):
                confidence = 0.0

            chunks = []
            audio_files = []
            notes = []
            context = ""

            if intent in ["search", "summarize", "question", "analytics"]:
                chunks = rag_context_service.semantic_search_with_filters(
                    db, user_id, message, entities
                )
                audio_files = rag_context_service.get_related_audio_files(chunks)
                notes = rag_context_service.get_related_notes(chunks)
                context = rag_context_service.build_context(chunks)

            if intent == "search":
                result = self._handle_search(audio_files, notes)
            elif intent == "summarize":
                result = self._handle_summarization(context, message)
            elif intent == "question":
                result = self._handle_question(context, message)
            elif intent == "manage":
                result = self._handle_management(entities)
            elif intent == "analytics":
                result = self._handle_analytics(context, message)
            else:
                result = self._handle_chat(message)

            response_time = int((time.time() - start_time) * 1000)

            if "audio_references" not in result:
                result["audio_references"] = [
                    {
                        "audio_id": audio.id,
                        "title": audio.original_filename,
                        "duration": audio.duration,
                        "created_at": audio.created_at.isoformat() if audio.created_at else None,
                    }
                    for audio in audio_files
                ]
            if "note_references" not in result:
                result["note_references"] = [{"note_id": note.id, "title": note.title} for note in notes]

            user_msg = ChatbotMessage(
                message_id=str(uuid.uuid4()),
                session_id=session_id,
                role="user",
                content=message,
                intent=intent,
                entities=entities,
            )
            db.add(user_msg)

            assistant_msg = ChatbotMessage(
                message_id=str(uuid.uuid4()),
                session_id=session_id,
                role="assistant",
                content=result["text"],
                intent=intent,
                retrieved_chunks=[c.id for c in chunks] if chunks else None,
                retrieved_audio_ids=[a.id for a in audio_files] if audio_files else None,
                retrieved_note_ids=[n.id for n in notes] if notes else None,
                response_time_ms=response_time,
                confidence_score=confidence,
            )
            db.add(assistant_msg)

            if not session.title:
                session.title = message.strip()[:200]
            session.total_messages = (session.total_messages or 0) + 2

            db.commit()
        except Exception:
            db.rollback()
            raise

        return {
            "message_id": assistant_msg.message_id,
            "response": result["text"],
            "intent": intent,
            "audio_references": result.get("audio_references", []),
            "note_references": result.get("note_references", []),
            "suggested_questions": result.get("suggested_questions", []),
        }

    def create_session(self, db: Session, user_id: int, title: Optional[str] = None) -> ChatbotSession:
        session = ChatbotSession(
            session_id=str(uuid.uuid4()),
            user_id=user_id,
            title=title,
            is_active=True,
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        return session

    def get_session(self, db: Session, user_id: int, session_id: str) -> ChatbotSession:
        return self._get_session(db, user_id, session_id)

    def list_sessions(self, db: Session, user_id: int, limit: int, offset: int) -> dict:
        query = db.query(ChatbotSession).filter(
            ChatbotSession.user_id == user_id,
            ChatbotSession.is_active == True,
        )
        total = query.count()
        sessions = (
            query.order_by(ChatbotSession.updated_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        return {"sessions": sessions, "total": total, "limit": limit, "offset": offset}

    def get_session_messages(
        self, db: Session, user_id: int, session_id: str, limit: int, offset: int
    ) -> dict:
        session = self._get_session(db, user_id, session_id)
        query = db.query(ChatbotMessage).filter(ChatbotMessage.session_id == session.session_id)
        total = query.count()
        messages = (
            query.order_by(ChatbotMessage.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        
        # Build rich message data with references
        enriched_messages = [
            self._build_message_with_references(db, msg)
            for msg in reversed(messages)
        ]
        
        return {
            "session": session,
            "messages": enriched_messages,
            "total": total,
            "limit": limit,
            "offset": offset,
        }
    
    def _build_message_with_references(
        self,
        db: Session,
        message: ChatbotMessage
    ) -> dict:
        """
        Build rich message response with audio and note references.
        
        Args:
            db: Database session
            message: ChatbotMessage model instance
            
        Returns:
            Dictionary with complete message data including references
        """
        from app.models.audio_model import AudioFile
        from app.models.note_model import Note
        
        result = {
            "message_id": message.message_id,
            "role": message.role,
            "response": message.content,
            "intent": message.intent,
            "created_at": message.created_at.isoformat() if message.created_at else None,
        }
        
        # Only add references for assistant messages
        if message.role == "assistant":
            # Build audio_references
            audio_references = []
            if message.retrieved_audio_ids:
                audio_files = db.query(AudioFile).filter(
                    AudioFile.id.in_(message.retrieved_audio_ids)
                ).all()
                
                audio_references = [
                    {
                        "audio_id": audio.id,
                        "title": audio.original_filename,
                        "duration": audio.duration,
                        "created_at": audio.created_at.isoformat() if audio.created_at else None,
                    }
                    for audio in audio_files
                ]
            
            # Build note_references
            note_references = []
            if message.retrieved_note_ids:
                notes = db.query(Note).filter(
                    Note.id.in_(message.retrieved_note_ids)
                ).all()
                
                note_references = [
                    {
                        "note_id": note.id,
                        "title": note.title
                    }
                    for note in notes
                ]
            
            result["audio_references"] = audio_references
            result["note_references"] = note_references
        
        return result

    def delete_session(self, db: Session, user_id: int, session_id: str) -> None:
        session = self._get_session(db, user_id, session_id)
        db.delete(session)
        db.commit()

    def _get_session(self, db: Session, user_id: int, session_id: str) -> ChatbotSession:
        session = (
            db.query(ChatbotSession)
            .filter(
                ChatbotSession.session_id == session_id,
                ChatbotSession.user_id == user_id,
                ChatbotSession.is_active == True,
            )
            .first()
        )
        if not session:
            raise ValueError("Session not found")
        return session

    def _get_conversation_history(self, db: Session, session_id: str, limit: int = 10) -> list:
        messages = (
            db.query(ChatbotMessage)
            .filter(ChatbotMessage.session_id == session_id)
            .order_by(ChatbotMessage.created_at.desc())
            .limit(limit)
            .all()
        )
        return [{"role": msg.role, "content": msg.content} for msg in reversed(messages)]

    def _handle_search(self, audio_files: list, notes: list) -> dict:
        audio_refs = [
            {
                "audio_id": audio.id,
                "title": audio.original_filename,
                "duration": audio.duration,
                "created_at": audio.created_at.isoformat() if audio.created_at else None,
            }
            for audio in audio_files
        ]
        note_refs = [{"note_id": note.id, "title": note.title} for note in notes]

        count = len(audio_files)
        if count == 0:
            text = "Mình chưa tìm thấy bản ghi âm phù hợp với yêu cầu của bạn."
        elif count == 1:
            text = f"Mình tìm thấy 1 bản ghi âm: {audio_files[0].original_filename}"
        else:
            text = f"Mình tìm thấy {count} bản ghi âm phù hợp."

        return {
            "text": text,
            "audio_references": audio_refs,
            "note_references": note_refs,
            "suggested_questions": [
                "Bạn có muốn tóm tắt các bản ghi này không?",
                "Cho mình xem bản gần nhất.",
            ],
        }

    def _handle_summarization(self, context: str, question: str) -> dict:
        if not context:
            return {
                "text": "Mình chưa tìm thấy dữ liệu liên quan để tóm tắt. Bạn có thể nói rõ hơn không?",
                "suggested_questions": [
                    "Tóm tắt cuộc họp hôm qua",
                    "Tóm tắt bản ghi âm gần nhất",
                ],
            }

        system_prompt = (
            "Bạn là trợ lý cho ứng dụng ghi âm. "
            "Hãy tóm tắt ngắn gọn, rõ ràng bằng tiếng Việt dựa trên ngữ cảnh được cung cấp. "
            "Nêu ý chính, quyết định và action items nếu có."
        )
        user_prompt = f"""Ngữ cảnh từ bản ghi:
{context}

Yêu cầu của người dùng: {question}

Hãy tóm tắt đầy đủ."""

        summary_text = self._generate_response(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            fallback="Mình gặp lỗi khi tạo tóm tắt. Bạn vui lòng thử lại nhé.",
        )

        return {
            "text": summary_text,
            "suggested_questions": [
                "Bạn có thể liệt kê action items không?",
                "Những quyết định quan trọng là gì?",
            ],
        }

    def _handle_question(self, context: str, question: str) -> dict:
        if not context:
            return {
                "text": "Mình không tìm thấy thông tin trong dữ liệu của bạn. Bạn có thể nói rõ hơn không?",
                "suggested_questions": [
                    "Tìm bản ghi âm về ngân sách",
                    "Bạn có bản ghi nào về cuộc họp gần đây không?",
                ],
            }

        system_prompt = (
            "Bạn là trợ lý cho ứng dụng ghi âm. "
            "Chỉ trả lời dựa trên ngữ cảnh được cung cấp. "
            "Nếu không có thông tin, hãy nói rõ. Trả lời bằng tiếng Việt."
        )
        user_prompt = f"""Ngữ cảnh từ bản ghi:
{context}

Câu hỏi: {question}

Trả lời ngắn gọn và chính xác."""

        answer_text = self._generate_response(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            fallback="Mình gặp lỗi khi trả lời. Bạn thử hỏi lại theo cách khác nhé.",
        )

        return {
            "text": answer_text,
            "suggested_questions": [
                "Có bản ghi nào liên quan khác không?",
                "Bạn có thể trích dẫn thêm chi tiết không?",
            ],
        }

    def _handle_management(self, entities: dict) -> dict:
        actions = entities.get("actions", [])
        if "delete" in actions:
            text = "Mình có thể hỗ trợ xóa bản ghi âm. Bạn xác nhận muốn xóa bản nào?"
        elif "archive" in actions:
            text = "Mình có thể lưu trữ bản ghi âm. Bạn muốn lưu trữ bản nào?"
        else:
            text = "Bạn muốn mình giúp quản lý bản ghi âm như thế nào?"

        return {
            "text": text,
            "suggested_questions": [
                "Xóa các bản ghi âm cũ hơn 30 ngày",
                "Lưu trữ các bản ghi cuộc họp tháng trước",
            ],
        }

    def _handle_analytics(self, context: str, question: str) -> dict:
        if not context:
            return {
                "text": "Mình cần thêm dữ liệu để tạo thống kê. Bạn có thể chỉ rõ phạm vi thời gian không?",
                "suggested_questions": [
                    "Thống kê số cuộc họp trong tháng này",
                    "Chủ đề phổ biến trong tuần này",
                ],
            }

        system_prompt = (
            "Bạn là trợ lý phân tích cho ứng dụng ghi âm. "
            "Từ ngữ cảnh, hãy đưa ra thống kê hoặc insight bằng tiếng Việt."
        )
        user_prompt = f"""Ngữ cảnh:
{context}

Yêu cầu: {question}

Hãy trả lời ngắn gọn, dễ hiểu."""

        analytics_text = self._generate_response(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            fallback="Mình chưa thể tạo thống kê lúc này. Bạn thử lại sau nhé.",
        )

        return {
            "text": analytics_text,
            "suggested_questions": [
                "Có xu hướng nào nổi bật không?",
                "So sánh với tháng trước giúp mình",
            ],
        }

    def _handle_chat(self, message: str) -> dict:
        system_prompt = (
            "Bạn là trợ lý thân thiện cho ứng dụng ghi âm và ghi chú. "
            "Trả lời bằng tiếng Việt và hướng người dùng tới các tính năng hữu ích."
        )

        chat_text = self._generate_response(
            system_prompt=system_prompt,
            user_prompt=message,
            fallback="Mình ở đây để giúp bạn tìm và tóm tắt các bản ghi âm. Bạn muốn bắt đầu với yêu cầu nào?",
        )

        return {
            "text": chat_text,
            "suggested_questions": [
                "Tìm các cuộc họp gần đây",
                "Tóm tắt bản ghi hôm nay",
                "Tôi đã nói về những chủ đề gì tuần này?",
            ],
        }

    def _generate_response(self, system_prompt: str, user_prompt: str, fallback: str) -> str:
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=[
                    types.Content(role="user", parts=[types.Part(text=system_prompt)]),
                    types.Content(role="user", parts=[types.Part(text=user_prompt)]),
                ],
            )
            return response.text
        except Exception as exc:
            logger.error("Chatbot generation failed: %s", exc, exc_info=True)
            return fallback


chatbot_service = ChatbotService()
