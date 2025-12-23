# Voicely AI Chatbot Implementation Guide

**Objective:** Build a complete, real-time AI chatbot system for Voicely-BE using **WebSockets**, **FastAPI**, **Redis**, and **PostgreSQL (pgvector)**. This system will enable users to interact with their audio recordings, transcripts, and notes through natural language.

---

## Table of Contents

1. [Business Use Cases](#business-use-cases)
2. [Architecture & Tech Stack](#architecture--tech-stack)
3. [Processing Pipeline](#processing-pipeline)
4. [Database Schema](#database-schema)
5. [REST API Endpoints](#rest-api-endpoints)
6. [WebSocket Events](#websocket-events)
7. [Implementation Steps](#implementation-steps)
8. [Services Implementation](#services-implementation)
9. [Integration Points](#integration-points)
10. [Implementation Plan](#implementation-plan)
11. [Security & Auth](#security--auth)
12. [Success Metrics](#success-metrics)

---

## 1. Business Use Cases

### Primary Use Cases for Voicely Chatbot

#### 1.1 **Intelligent Search & Retrieval** 🔍
**User Query**: "Find all meetings about project X from last week"
- Search across transcripts using semantic understanding
- Filter by date, category, keywords
- Return relevant audio files with timestamps

#### 1.2 **Content Summarization** 📝
**User Query**: "Summarize the key points from today's meeting"
- Generate concise summaries from audio transcripts
- Extract action items and decisions
- Create structured notes automatically

#### 1.3 **Question Answering** 💬
**User Query**: "What did John say about the budget?"
- Search specific content within transcripts
- Provide direct answers with audio timestamp references
- Context-aware responses based on conversation history

#### 1.4 **Audio Management Assistant** 🎧
**User Query**: "Delete all recordings older than 30 days"
**User Query**: "Archive my lecture notes from March"
- Help manage audio library through natural language
- Batch operations on audio files and notes
- Smart categorization and organization

#### 1.5 **Productivity Intelligence** 📊
**User Query**: "How much time have I spent in meetings this month?"
**User Query**: "What are my most common meeting topics?"
- Analytics on audio usage patterns
- Insights from transcript content analysis
- Productivity recommendations

---

## 2. Architecture & Tech Stack

The system extends the existing Voicely-BE architecture.

*   **Backend:** FastAPI (Async)
*   **Real-time Communication:** `python-socketio` (Socket.IO) with `uvicorn` as the ASGI runner.
*   **Message Broker:** Redis (using `RedisManager` for Socket.IO scaling and `ARQ` for heavy tasks).
*   **Database:** PostgreSQL + `pgvector` for semantic search (RAG).
*   **AI/LLM:** Google Gemini (via `google-genai` SDK) or LangChain.
*   **Worker:** `ARQ` (existing) for offloading heavy RAG/Summarization tasks to prevent blocking the socket loop.

### Key Design Principles

1. **Async-First**: Long AI processing tasks run in background workers
2. **RAG-Enabled**: Use existing note chunks and embeddings for semantic search
3. **Context-Aware**: Maintain conversation history for better responses
4. **Real-time**: WebSocket communication for instant responses
5. **Multi-Modal**: Handle both text and audio references

### Socket Event Flow
1.  **Client** connects and joins a `session_room`.
2.  **Client** emits `user_message`.
3.  **Server** acknowledges, emits `typing_start`.
4.  **Server** (optionally offloads to Worker) -> classifies intent -> performs RAG -> generates response.
5.  **Server** emits `typing_stop`.
6.  **Server** emits `ai_response` (final text + references).

---

## 3. Processing Pipeline

### Voicely Chatbot Pipeline (6 Stages)

```
User Query: "Summarize yesterday's meeting about marketing"
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│  Stage 1: Input Validation & Session Management             │
│  • Validate user authentication                              │
│  • Load/create conversation session                          │
│  • Create chat message record                                │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  Stage 2: Intent Classification                             │
│  • Determine user intent:                                    │
│    - Search/Retrieval                                        │
│    - Summarization                                           │
│    - Question Answering                                      │
│    - Management Action (delete, archive, etc.)               │
│    - Analytics/Insights                                      │
│    - General Chat                                            │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  Stage 3: Entity Extraction                                  │
│  • Extract query parameters:                                 │
│    - Date/time ranges: "yesterday", "last week"              │
│    - Keywords: "marketing", "budget"                         │
│    - Categories: "meeting", "lecture"                        │
│    - Audio IDs or references                                 │
│    - Person names                                            │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  Stage 4: Context Retrieval (RAG)                            │
│  • Semantic search on note_chunks using embeddings           │
│  • Filter by user_id, date_range, category                   │
│  • Retrieve top K relevant chunks                            │
│  • Get associated audio files and transcripts                │
│  • Build context from conversation history                   │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  Stage 5: Action Execution                                   │
│  Based on intent:                                            │
│                                                              │
│  [Search] → Return filtered audio files/notes                │
│  [Summarize] → Generate AI summary from chunks               │
│  [Q&A] → Generate answer with audio timestamp refs           │
│  [Manage] → Execute database operations                      │
│  [Analytics] → Query aggregations and stats                  │
│  [Chat] → General AI conversation                            │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  Stage 6: Response Formatting & Delivery                    │
│  • Format response with:                                     │
│    - Text answer                                             │
│    - Audio file references with timestamps                   │
│    - Note IDs                                                │
│    - Suggested follow-up questions                           │
│  • Update conversation history                               │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
                   Return to User
```

### Pipeline Flow Logic

```python
# Pseudo-code for pipeline
async def process_chat_message(user_id, message, session_id):
    # Stage 1: Validation
    session = get_or_create_session(user_id, session_id)
    chat_message = create_message_record(session, message)
    
    # Stage 2: Intent Classification
    intent = classify_intent(message, conversation_history)
    # Returns: "search" | "summarize" | "question" | "manage" | "analytics" | "chat"
    
    # Stage 3: Entity Extraction
    entities = extract_entities(message, intent)
    # Returns: {date_range, keywords, categories, audio_ids, etc.}
    
    # Stage 4: RAG Retrieval
    if intent in ["search", "summarize", "question", "analytics"]:
        chunks = semantic_search(message, entities, user_id)
        audio_files = get_related_audio_files(chunks, entities)
        notes = get_related_notes(chunks, entities)
        context = build_rag_context(chunks, audio_files, notes)
    
    # Stage 5: Action Execution
    if intent == "search":
        result = format_search_results(audio_files, notes, entities)
    elif intent == "summarize":
        result = generate_summary(context, entities)
    elif intent == "question":
        result = answer_question(message, context, conversation_history)
    elif intent == "manage":
        result = execute_management_action(entities, user_id)
    elif intent == "analytics":
        result = generate_analytics(entities, user_id)
    else:  # chat
        result = general_chat_response(message, conversation_history)
    
    # Stage 6: Response Formatting
    response = format_response(result, intent)
    update_conversation_history(session, message, response)
    
    return response
```

---

## 4. Database Schema

### New Tables for Chatbot

#### 4.1 **chatbot_sessions**
Stores conversation sessions for context continuity.

```sql
CREATE TABLE chatbot_sessions (
    id SERIAL PRIMARY KEY,
    session_id UUID UNIQUE NOT NULL DEFAULT gen_random_uuid(),
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(200),  -- Auto-generated from first message
    total_messages INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_session_user_id (user_id),
    INDEX idx_session_active (is_active)
);
```

#### 4.2 **chatbot_messages**
Stores individual messages in conversations with full metadata.

```sql
CREATE TABLE chatbot_messages (
    id SERIAL PRIMARY KEY,
    message_id UUID UNIQUE NOT NULL DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES chatbot_sessions(session_id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL,  -- 'user' | 'assistant' | 'system'
    content TEXT NOT NULL,
    
    -- Intent & Entities
    intent VARCHAR(50),  -- 'search' | 'summarize' | 'question' | etc.
    entities JSONB,  -- Extracted entities
    
    -- RAG Context
    retrieved_chunks JSONB,  -- IDs of chunks used
    retrieved_audio_ids JSONB,  -- IDs of audio files referenced
    retrieved_note_ids JSONB,  -- IDs of notes referenced
    
    -- Response metadata
    response_time_ms INTEGER,
    confidence_score FLOAT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_message_session (session_id),
    INDEX idx_message_created (created_at)
);
```

### Existing Tables to Leverage

- ✅ **users**: User authentication and profiles
- ✅ **audio_files**: Audio recordings with transcripts
- ✅ **notes**: Summarized notes from audio
- ✅ **note_chunks**: Chunked content with embeddings (for RAG)

---

## 5. REST API Endpoints

### Chatbot API Specification

#### 5.1 Create Chat Session

```http
POST /api/v1/chatbot/sessions
Authorization: Bearer <token>
Content-Type: application/json

{}

Response 201:
{
  "success": true,
  "message": "Session created successfully",
  "data": {
    "session_id": "uuid-here",
    "title": null,
    "created_at": "2024-12-22T10:00:00Z"
  }
}
```

#### 5.2 Send Message (Sync)

```http
POST /api/v1/chatbot/sessions/{session_id}/messages
Authorization: Bearer <token>
Content-Type: application/json

{
  "message": "Find all meetings from last week"
}

Response 200:
{
  "success": true,
  "message": "Message processed",
  "data": {
    "message_id": "uuid-here",
    "response": "I found 5 meetings from last week...",
    "intent": "search",
    "audio_references": [
      {
        "audio_id": 123,
        "title": "Team Meeting",
        "timestamp": 120,
        "excerpt": "Discussed project timeline..."
      }
    ],
    "note_references": [
      {
        "note_id": 456,
        "title": "Meeting Summary"
      }
    ],
    "suggested_questions": [
      "Would you like a summary of these meetings?",
      "Show me action items from these meetings"
    ]
  }
}
```

#### 5.3 Send Message (Async) - For Long Processing

```http
POST /api/v1/chatbot/sessions/{session_id}/messages-async
Authorization: Bearer <token>
Content-Type: application/json

{
  "message": "Summarize all my meetings this month"
}

Response 202:
{
  "success": true,
  "message": "Message is being processed",
  "data": {
    "job_id": "uuid-here",
    "status": "queued"
  }
}

# Poll status:
GET /api/v1/tasks/status/{job_id}
```

#### 5.4 Get Session History

```http
GET /api/v1/chatbot/sessions/{session_id}/messages?limit=20&offset=0
Authorization: Bearer <token>

Response 200:
{
  "success": true,
  "data": {
    "session_id": "uuid-here",
    "messages": [
      {
        "message_id": "uuid-1",
        "role": "user",
        "content": "Find all meetings from last week",
        "created_at": "2024-12-22T10:00:00Z"
      },
      {
        "message_id": "uuid-2",
        "role": "assistant",
        "content": "I found 5 meetings...",
        "intent": "search",
        "created_at": "2024-12-22T10:00:02Z"
      }
    ],
    "total": 10,
    "limit": 20,
    "offset": 0
  }
}
```

#### 5.5 List All Sessions

```http
GET /api/v1/chatbot/sessions?limit=20&offset=0
Authorization: Bearer <token>

Response 200:
{
  "success": true,
  "data": {
    "sessions": [
      {
        "session_id": "uuid-1",
        "title": "Project Discussion",
        "total_messages": 15,
        "is_active": true,
        "created_at": "2024-12-20T10:00:00Z",
        "updated_at": "2024-12-22T10:00:00Z"
      }
    ],
    "total": 5,
    "limit": 20,
    "offset": 0
  }
}
```

#### 5.6 Delete Session

```http
DELETE /api/v1/chatbot/sessions/{session_id}
Authorization: Bearer <token>

Response 200:
{
  "success": true,
  "message": "Session deleted successfully"
}
```

---

## 6. WebSocket Events

## 7. Implementation Steps

### Step 1: Add Dependencies

Add the following to `requirements.txt`:

```txt
python-socketio==5.11.0
redis==5.0.0  # Already exists, ensure compatibility
google-genai==1.0.0 # Or latest version
langchain==0.1.0 # Optional, but recommended for RAG chains
langchain-google-genai
```

### Step 2: Database Schema (SQLAlchemy Models)

Create `app/models/chatbot_model.py`. This maps to the database schema.

```python
from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey, DateTime, Float
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.db.base import Base

class ChatbotSession(Base):
    __tablename__ = "chatbot_sessions"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, unique=True, index=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(200), nullable=True)
    total_messages = Column(Integer, default=0)
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    messages = relationship("ChatbotMessage", back_populates="session", cascade="all, delete-orphan")
    user = relationship("User", back_populates="chatbot_sessions")

class ChatbotMessage(Base):
    __tablename__ = "chatbot_messages"

    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(String, unique=True, index=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, ForeignKey("chatbot_sessions.session_id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(20), nullable=False)  # 'user' | 'assistant' | 'system'
    content = Column(Text, nullable=False)
    
    # Intent & Entities
    intent = Column(String(50), nullable=True)
    entities = Column(JSONB, nullable=True)
    
    # RAG Context
    retrieved_chunks = Column(JSONB, nullable=True)
    retrieved_audio_ids = Column(JSONB, nullable=True)
    retrieved_note_ids = Column(JSONB, nullable=True)
    
    # Response metadata
    response_time_ms = Column(Integer, nullable=True)
    confidence_score = Column(Float, nullable=True)
    
    created_at = Column(DateTime, server_default=func.now(), index=True)

    session = relationship("ChatbotSession", back_populates="messages")
```

Update `app/models/user_model.py` to add the relationship:

```python
# In User model, add:
chatbot_sessions = relationship("ChatbotSession", back_populates="user", cascade="all, delete-orphan")
```

**Action:** Run `alembic revision --autogenerate -m "add_chatbot_tables"` and `alembic upgrade head`.

### Step 3: Core Services Implementation

Create the following services to handle the chatbot pipeline.

#### 3.1 Intent Classification Service (`app/services/intent_service.py`)

```python
from google import genai
from google.genai import types
import json
from app.core.config import settings

class IntentService:
    """Service for classifying user intent in chatbot messages"""
    
    INTENT_SYSTEM_PROMPT = """You are an intent classifier for a voice recording and note-taking application.
    
Available intents:
- search: User wants to find audio files, transcripts, or notes
- summarize: User wants a summary of audio/transcript content
- question: User asks a specific question about their recordings
- manage: User wants to delete, archive, categorize, or organize files
- analytics: User asks for statistics, insights, or usage patterns
- chat: General conversation or unclear intent

Extract entities when applicable:
- date_range: time periods mentioned
- keywords: important search terms
- categories: meeting, lecture, personal, etc.
- audio_ids: specific file references
- actions: delete, archive, categorize, etc.
- person_names: names mentioned

Respond ONLY with valid JSON in this format:
{
  "intent": "search|summarize|question|manage|analytics|chat",
  "confidence": 0.0-1.0,
  "entities": {
    "date_range": {"start": "YYYY-MM-DD", "end": "YYYY-MM-DD"},
    "keywords": ["keyword1", "keyword2"],
    "categories": ["meeting"],
    "audio_ids": [123],
    "actions": ["delete", "archive"],
    "person_names": ["John"]
  }
}
"""
    
    def __init__(self):
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
    
    def classify_intent(
        self,
        message: str,
        conversation_history: list = None
    ) -> dict:
        """Classify user intent and extract entities"""
        
        # Build context from conversation history
        context = ""
        if conversation_history:
            context = "\n".join([
                f"{msg['role']}: {msg['content']}" 
                for msg in conversation_history[-3:]  # Last 3 messages
            ])
        
        user_prompt = f"""Message: {message}

Recent conversation context:
{context if context else "None"}

Classify intent and extract entities as JSON."""
        
        try:
            response = self.client.models.generate_content(
                model='gemini-2.0-flash-exp',
                contents=[
                    types.Content(
                        role="user",
                        parts=[types.Part(text=self.INTENT_SYSTEM_PROMPT)]
                    ),
                    types.Content(
                        role="user",
                        parts=[types.Part(text=user_prompt)]
                    )
                ]
            )
            
            result = json.loads(response.text)
            return result
            
        except Exception as e:
            # Fallback to chat intent on error
            return {
                "intent": "chat",
                "confidence": 0.5,
                "entities": {},
                "error": str(e)
            }

# Initialize global instance
intent_service = IntentService()
```

#### 3.2 RAG Context Service (`app/services/rag_context_service.py`)

```python
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from app.models.note_chunk_model import NoteChunk
from app.models.note_model import Note
from app.models.audio_model import AudioFile
from app.services.embedding_service import generate_embedding
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class RAGContextService:
    """Service for building RAG context from user's content"""
    
    def semantic_search_with_filters(
        self,
        db: Session,
        user_id: int,
        query: str,
        entities: dict,
        limit: int = 5
    ) -> list:
        """Search with semantic understanding and filters"""
        
        try:
            # Generate query embedding
            query_embedding = generate_embedding(query)
            
            # Build base query
            query_obj = db.query(NoteChunk)\
                .join(Note)\
                .join(AudioFile)\
                .filter(Note.user_id == user_id)
            
            # Apply date range filter
            if entities.get("date_range"):
                start_date = entities["date_range"].get("start")
                end_date = entities["date_range"].get("end")
                
                if start_date:
                    query_obj = query_obj.filter(AudioFile.created_at >= start_date)
                if end_date:
                    query_obj = query_obj.filter(AudioFile.created_at <= end_date)
            
            # Apply category filter
            if entities.get("categories"):
                query_obj = query_obj.filter(
                    AudioFile.category.in_(entities["categories"])
                )
            
            # Apply audio_id filter
            if entities.get("audio_ids"):
                query_obj = query_obj.filter(
                    AudioFile.id.in_(entities["audio_ids"])
                )
            
            # Apply semantic search using pgvector
            chunks = query_obj.order_by(
                NoteChunk.embedding.cosine_distance(query_embedding)
            ).limit(limit).all()
            
            return chunks
            
        except Exception as e:
            logger.error(f"Error in semantic search: {e}")
            return []
    
    def build_context(
        self,
        chunks: list,
        max_tokens: int = 3000
    ) -> str:
        """Build context string from chunks, respecting token limit"""
        
        # Rough estimate: 4 chars = 1 token
        max_chars = max_tokens * 4
        
        context_parts = []
        total_chars = 0
        
        for chunk in chunks:
            chunk_text = f"""---
Source: {chunk.note.title}
Audio: {chunk.note.audio_file.original_filename if chunk.note.audio_file else 'N/A'}
Date: {chunk.note.created_at.strftime('%Y-%m-%d')}
Content: {chunk.content}
---
"""
            if total_chars + len(chunk_text) > max_chars:
                break
            
            context_parts.append(chunk_text)
            total_chars += len(chunk_text)
        
        return "\n".join(context_parts)
    
    def get_related_audio_files(
        self,
        chunks: list,
        entities: dict
    ) -> list:
        """Extract unique audio files from chunks"""
        
        audio_files = []
        seen_ids = set()
        
        for chunk in chunks:
            if chunk.note.audio_file and chunk.note.audio_file.id not in seen_ids:
                audio_files.append(chunk.note.audio_file)
                seen_ids.add(chunk.note.audio_file.id)
        
        return audio_files
    
    def get_related_notes(
        self,
        chunks: list
    ) -> list:
        """Extract unique notes from chunks"""
        
        notes = []
        seen_ids = set()
        
        for chunk in chunks:
            if chunk.note.id not in seen_ids:
                notes.append(chunk.note)
                seen_ids.add(chunk.note.id)
        
        return notes

# Initialize global instance
rag_context_service = RAGContextService()
```

#### 3.3 Main Chatbot Service (`app/services/chatbot_service.py`)

```python
from sqlalchemy.orm import Session
from app.models.chatbot_model import ChatbotSession, ChatbotMessage
from app.services.intent_service import intent_service
from app.services.rag_context_service import rag_context_service
from google import genai
from google.genai import types
from app.core.config import settings
import uuid
import time
import logging

logger = logging.getLogger(__name__)

class ChatbotService:
    """Main chatbot orchestration service"""
    
    def __init__(self):
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
    
    async def process_message(
        self,
        db: Session,
        user_id: int,
        session_id: str,
        message: str
    ) -> dict:
        """Main pipeline for processing chatbot messages"""
        
        start_time = time.time()
        
        try:
            # Stage 1: Get or create session
            session = self._get_or_create_session(db, user_id, session_id)
            
            # Get conversation history
            history = self._get_conversation_history(db, session_id)
            
            # Stage 2: Intent Classification
            intent_result = intent_service.classify_intent(message, history)
            intent = intent_result["intent"]
            entities = intent_result.get("entities", {})
            confidence = intent_result.get("confidence", 0.0)
            
            # Stage 3 & 4: RAG Retrieval (if needed)
            chunks = []
            audio_files = []
            notes = []
            context = ""
            
            if intent in ["search", "summarize", "question", "analytics"]:
                chunks = rag_context_service.semantic_search_with_filters(
                    db, user_id, message, entities
                )
                audio_files = rag_context_service.get_related_audio_files(chunks, entities)
                notes = rag_context_service.get_related_notes(chunks)
                context = rag_context_service.build_context(chunks)
            
            # Stage 5: Action Execution
            if intent == "search":
                result = self._handle_search(audio_files, notes, entities)
            elif intent == "summarize":
                result = self._handle_summarization(context, message, history)
            elif intent == "question":
                result = self._handle_question(context, message, history)
            elif intent == "manage":
                result = self._handle_management(db, user_id, entities)
            elif intent == "analytics":
                result = self._handle_analytics(db, user_id, entities)
            else:  # chat
                result = self._handle_chat(message, history)
            
            # Stage 6: Save message and response
            response_time = int((time.time() - start_time) * 1000)
            
            # Save user message
            user_msg = ChatbotMessage(
                message_id=str(uuid.uuid4()),
                session_id=session_id,
                role="user",
                content=message,
                intent=intent,
                entities=entities,
                created_at=func.now()
            )
            db.add(user_msg)
            
            # Save assistant response
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
                created_at=func.now()
            )
            db.add(assistant_msg)
            
            # Update session
            session.total_messages += 2
            session.updated_at = func.now()
            
            db.commit()
            
            return {
                "message_id": assistant_msg.message_id,
                "response": result["text"],
                "intent": intent,
                "audio_references": result.get("audio_references", []),
                "note_references": result.get("note_references", []),
                "suggested_questions": result.get("suggested_questions", [])
            }
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            db.rollback()
            raise
    
    def _get_or_create_session(
        self,
        db: Session,
        user_id: int,
        session_id: str = None
    ) -> ChatbotSession:
        """Get existing or create new session"""
        
        if session_id:
            session = db.query(ChatbotSession).filter(
                ChatbotSession.session_id == session_id
            ).first()
            if session:
                return session
        
        # Create new session
        session = ChatbotSession(
            session_id=str(uuid.uuid4()),
            user_id=user_id,
            is_active=True
        )
        db.add(session)
        db.commit()
        
        return session
    
    def _get_conversation_history(
        self,
        db: Session,
        session_id: str,
        limit: int = 10
    ) -> list:
        """Get recent conversation history"""
        
        messages = db.query(ChatbotMessage).filter(
            ChatbotMessage.session_id == session_id
        ).order_by(
            ChatbotMessage.created_at.desc()
        ).limit(limit).all()
        
        return [
            {"role": msg.role, "content": msg.content}
            for msg in reversed(messages)
        ]
    
    def _handle_search(
        self,
        audio_files: list,
        notes: list,
        entities: dict
    ) -> dict:
        """Handle search intent"""
        
        audio_refs = [
            {
                "audio_id": audio.id,
                "title": audio.original_filename,
                "duration": audio.duration,
                "created_at": audio.created_at.isoformat()
            }
            for audio in audio_files
        ]
        
        note_refs = [
            {
                "note_id": note.id,
                "title": note.title
            }
            for note in notes
        ]
        
        count = len(audio_files)
        
        if count == 0:
            text = "I couldn't find any recordings matching your criteria."
        elif count == 1:
            text = f"I found 1 recording: {audio_files[0].original_filename}"
        else:
            text = f"I found {count} recordings matching your search."
        
        return {
            "text": text,
            "audio_references": audio_refs,
            "note_references": note_refs,
            "suggested_questions": [
                "Would you like a summary of these recordings?",
                "Show me the most recent one"
            ]
        }
    
    def _handle_summarization(
        self,
        context: str,
        question: str,
        history: list
    ) -> dict:
        """Handle summarization intent"""
        
        system_prompt = """You are a helpful assistant for a voice recording app.
Generate a concise summary from the provided context.
Extract key points, action items, and important decisions.
Format the response in markdown with clear sections."""
        
        user_prompt = f"""Context from recordings:
{context}

User request: {question}

Provide a comprehensive summary."""
        
        response = self.client.models.generate_content(
            model='gemini-2.0-flash-exp',
            contents=[
                types.Content(role="user", parts=[types.Part(text=system_prompt)]),
                types.Content(role="user", parts=[types.Part(text=user_prompt)])
            ]
        )
        
        return {
            "text": response.text,
            "suggested_questions": [
                "Can you elaborate on the action items?",
                "What were the main decisions made?"
            ]
        }
    
    def _handle_question(
        self,
        context: str,
        question: str,
        history: list
    ) -> dict:
        """Handle Q&A intent"""
        
        system_prompt = """You are a helpful assistant for a voice recording app.
Answer questions based ONLY on the provided context from the user's recordings.
If the answer is not in the context, say "I don't have information about that in your recordings."
Always cite which recording/note the information comes from."""
        
        user_prompt = f"""Context from user's recordings:
{context}

Question: {question}

Provide a helpful answer with references to the source recordings."""
        
        response = self.client.models.generate_content(
            model='gemini-2.0-flash-exp',
            contents=[
                types.Content(role="user", parts=[types.Part(text=system_prompt)]),
                types.Content(role="user", parts=[types.Part(text=user_prompt)])
            ]
        )
        
        return {
            "text": response.text,
            "suggested_questions": [
                "Tell me more about this topic",
                "Are there any related recordings?"
            ]
        }
    
    def _handle_management(
        self,
        db: Session,
        user_id: int,
        entities: dict
    ) -> dict:
        """Handle management actions"""
        
        # This would implement actual deletion/archival logic
        # For now, return a confirmation message
        
        actions = entities.get("actions", [])
        
        if "delete" in actions:
            text = "I can help you delete recordings. Please confirm which recordings you'd like to delete."
        elif "archive" in actions:
            text = "I can help you archive recordings. Please specify which ones."
        else:
            text = "I can help you manage your recordings. What would you like to do?"
        
        return {
            "text": text,
            "suggested_questions": [
                "Delete recordings older than 30 days",
                "Archive all meeting recordings from last month"
            ]
        }
    
    def _handle_analytics(
        self,
        db: Session,
        user_id: int,
        entities: dict
    ) -> dict:
        """Handle analytics intent"""
        
        # This would implement actual analytics queries
        # For now, return placeholder
        
        text = "I can provide analytics about your recordings. What insights are you looking for?"
        
        return {
            "text": text,
            "suggested_questions": [
                "How many meetings did I have this month?",
                "What are my most common topics?"
            ]
        }
    
    def _handle_chat(
        self,
        message: str,
        history: list
    ) -> dict:
        """Handle general chat intent"""
        
        system_prompt = """You are a friendly assistant for a voice recording and note-taking app.
Help users understand what you can do and guide them to useful features."""
        
        response = self.client.models.generate_content(
            model='gemini-2.0-flash-exp',
            contents=[
                types.Content(role="user", parts=[types.Part(text=system_prompt)]),
                types.Content(role="user", parts=[types.Part(text=message)])
            ]
        )
        
        return {
            "text": response.text,
            "suggested_questions": [
                "Find my recent meetings",
                "Summarize today's recordings",
                "What topics did I discuss this week?"
            ]
        }

# Initialize global instance
chatbot_service = ChatbotService()
```

### Step 4: Socket Manager (`app/socket_manager.py`)

This is the core of the real-time system.

```python
import socketio
from app.core.redis_config import REDIS_SETTINGS

# Initialize Socket.IO server
# client_manager connects to Redis to handle scaling/broadcasting
mgr = socketio.AsyncRedisManager(f'redis://{REDIS_SETTINGS.host}:{REDIS_SETTINGS.port}/0')
sio = socketio.AsyncServer(async_mode='asgi', client_manager=mgr, cors_allowed_origins='*')

@sio.event
async def connect(sid, environ):
    print(f"Client connected: {sid}")
    # Extract token from query string or headers for auth
    # user = await authenticate_socket_user(environ) 
    # await sio.save_session(sid, {'user_id': user.id})

@sio.event
async def join_room(sid, data):
    """
    data: {'session_id': 'uuid...'}
    """
    session_id = data.get('session_id')
    # Validate session access
    await sio.enter_room(sid, session_id)
    await sio.emit('room_joined', {'session_id': session_id}, room=sid)

@sio.event
async def user_message(sid, data):
    """
    data: {'session_id': '...', 'content': '...'}
    """
    session_id = data['session_id']
    content = data['content']
    
    # 1. Ack receipt
    await sio.emit('message_ack', {'status': 'received'}, room=sid)
    
    # 2. Emit typing indicator
    await sio.emit('typing_start', {'sender': 'ai'}, room=session_id)
    
    # 3. Process (Ideally, offload this to ARQ if it takes > 2-3 seconds)
    try:
        # Pseudo-code:
        # response_text, refs = await chatbot_service.generate_response(user_id, content)
        
        # Save to DB
        # await save_message_to_db(...)
        
        response_payload = {
            'message_id': 'new-uuid',
            'role': 'assistant',
            'content': "Here is the summary of your meeting...", 
            'references': [{'audio_id': 1, 'timestamp': 120}] 
        }
        
        await sio.emit('ai_response', response_payload, room=session_id)
        
    except Exception as e:
        await sio.emit('error', {'message': str(e)}, room=sid)
    finally:
        await sio.emit('typing_stop', room=session_id)

@sio.event
async def disconnect(sid):
    print(f"Client disconnected: {sid}")
```

### Step 5: Mount Socket.IO to FastAPI (`app/main.py`)

Integrate the socket app into the main application.

```python
from app.socket_manager import sio
import socketio

# Existing app definition
# app = FastAPI(...)

# Mount socket app
socket_app = socketio.ASGIApp(sio, app)

# NOTE: When running uvicorn, point to 'app.main:socket_app' 
# OR keep 'app.main:app' and mount it differently if using sub-path.
# Standard way for root handling:
app.mount("/ws", socket_app) # This might require path stripping or direct ASGI wrapping
# Better approach: Wrap the entire app
# final_app = socketio.ASGIApp(sio, app)
```

**Recommendation:** For clean separation, often the `socket_app` wraps the `fastapi_app`.
Update `main.py` to expose `socketio_app` as the entry point or use `mount`.

```python
# In app/main.py
app = FastAPI()
# ... include routers ...

# Create the ASGI app that combines Socket.IO and FastAPI
sio_app = socketio.ASGIApp(sio, other_asgi_app=app)
```

Then in `docker-compose.yml`, update the command:
`command: > uvicorn app.main:sio_app --host 0.0.0.0 --port 8000`

---

## 3. Detailed Event Contract

### Client -> Server Events

| Event Name | Payload | Description |
| :--- | :--- | :--- |
| `join_session` | `{ "session_id": "uuid" }` | User joins a specific chat session room. |
| `user_message` | `{ "session_id": "uuid", "content": "Hello" }` | User sends a text message. |
| `typing_start` | `{ "session_id": "uuid" }` | User starts typing (optional UI feature). |

### Server -> Client Events

| Event Name | Payload | Description |
| :--- | :--- | :--- |
| `ai_response` | `{ "id": "uuid", "content": "markdown text", "refs": [...] }` | The AI's full response. |
| `typing_start` | `{ "sender": "ai" }` | AI is "thinking" or generating. |
| `typing_stop` | `{ "sender": "ai" }` | AI finished processing. |
| `error` | `{ "code": 500, "msg": "..." }` | Error notification. |
| `stream_chunk` | `{ "chunk": "word" }` | (Optional) If streaming tokens. |

---

---

## 8. Services Implementation

See **Step 3** above for the complete implementation of:
- `IntentService` - Intent classification and entity extraction
- `RAGContextService` - Semantic search with filters
- `ChatbotService` - Main orchestration service

---

## 9. Integration Points

### 9.1 Audio File Integration

**Capability**: Reference specific audio files in responses

```python
# When chatbot needs to reference audio
from app.services.audio_service import audio_service

audio_file = audio_service.get_audio_file_by_id(db, audio_id, user)
response_data = {
    "audio_id": audio_file.id,
    "title": audio_file.original_filename,
    "duration": audio_file.duration,
    "transcript_excerpt": audio_file.transcription[:200] if audio_file.transcription else "",
    "playback_url": f"/api/v1/audio/{audio_file.id}/stream"
}
```

### 9.2 Transcript Search Integration

**Capability**: Search within transcripts using semantic understanding

```python
# Semantic search in transcripts
from app.services.embedding_service import generate_embedding
from app.services.note_service import semantic_search_notes

query_embedding = generate_embedding(user_query)
relevant_chunks = semantic_search_notes(
    db=db,
    user_id=user_id,
    query_embedding=query_embedding,
    limit=5
)
```

### 9.3 Note Summarization Integration

**Capability**: Reuse existing summarization logic

```python
# Leverage existing summarization
from app.services.note_service import summarize_audio_transcript

summary_response = summarize_audio_transcript(
    db=db,
    audio_file_id=audio_id,
    user_id=user_id
)
```

### 9.4 Async Task Integration

**Capability**: Use ARQ for long-running AI operations

```python
# Queue chatbot AI processing
from app.services.task_job_service import task_job_service

result = await task_job_service.create_and_queue_job(
    request=request,
    db=db,
    task_type="chatbot_message",
    task_function="handle_chatbot_message",
    user_id=current_user.id,
    session_id=session_id,
    message=message
)
```

---

## 10. Implementation Plan

### Phase 1: Foundation (Week 1-2)

#### Tasks:
1. **Database Setup**
   - Create migration for new chatbot tables
   - Add indexes for performance
   - Update models in `app/models/`

2. **Core Services**
   - Create `app/services/chatbot_service.py`
   - Create `app/services/intent_service.py`
   - Create `app/services/rag_context_service.py`

3. **Basic REST Endpoints**
   - `POST /api/v1/chatbot/sessions` - Create new chat session
   - `POST /api/v1/chatbot/sessions/{session_id}/messages` - Send message
   - `GET /api/v1/chatbot/sessions` - List user sessions
   - `GET /api/v1/chatbot/sessions/{session_id}` - Get session history

4. **WebSocket Setup**
   - Implement `app/socket_manager.py`
   - Mount Socket.IO to FastAPI
   - Add authentication middleware

### Phase 2: RAG Integration (Week 3)

#### Tasks:
1. **Semantic Search Enhancement**
   - Enhance existing `semantic_search_notes()` function
   - Add multi-criteria filtering (date, category, etc.)
   - Implement hybrid search (semantic + keyword)

2. **Context Builder**
   - Implement context window management
   - Add conversation history compression
   - Optimize chunk selection

3. **Intent Classification**
   - Build intent classifier using Gemini
   - Create intent-specific prompts
   - Add entity extraction for each intent type

### Phase 3: Action Handlers (Week 4)

#### Tasks:
1. **Search Handler**
   - Implement semantic search across transcripts
   - Return audio files with timestamps
   - Add faceted search (filters)

2. **Summarization Handler**
   - Generate summaries from retrieved chunks
   - Create structured output (bullet points, key points)
   - Extract action items automatically

3. **Q&A Handler**
   - Answer questions from transcript context
   - Provide audio timestamp references
   - Handle multi-turn conversations

4. **Management Handler**
   - Parse management commands (delete, archive, categorize)
   - Execute database operations
   - Confirm actions with user

### Phase 4: Advanced Features (Week 5-6)

#### Tasks:
1. **Analytics Handler**
   - Aggregate audio usage statistics
   - Generate insights from transcript content
   - Create visualization data

2. **Async Processing**
   - Move heavy AI calls to ARQ workers
   - Implement streaming responses (Server-Sent Events)
   - Add progress indicators

3. **REST API Endpoints**
   - Implement all remaining endpoints
   - Add pagination and filtering
   - Create comprehensive error handling

### Phase 5: Polish & Optimization (Week 7-8)

#### Tasks:
1. **Performance Optimization**
   - Add response caching
   - Optimize database queries
   - Implement connection pooling

2. **Error Handling**
   - Add comprehensive error messages
   - Implement fallback responses
   - Create retry logic

3. **Testing**
   - Unit tests for each service
   - Integration tests for endpoints
   - WebSocket connection testing
   - Load testing for concurrent users

4. **Documentation**
   - API documentation (OpenAPI/Swagger)
   - User guide for chatbot features
   - Developer documentation

---

## 11. Development Workflow

1.  **Install Libraries:** Update `requirements.txt` and rebuild Docker.
2.  **Migration:** Generate and apply the `chatbot_sessions` and `chatbot_messages` migration.
3.  **Services:**
    *   Create `ChatbotService` to handle `Intent Classification` -> `RAG` -> `Generation`.
    *   Ensure `RAGService` correctly queries `pgvector` using `app/models/note_chunk_model.py`.
4.  **Sockets:** Implement `app/socket_manager.py` with the events defined above.
5.  **Integration:** Update `app/main.py` to wrap the FastAPI app with Socket.IO.
6.  **Testing:** Use a socket.io client tool (like Firecamp or a simple HTML/JS script) to connect to `ws://localhost:8000`, join a room, and send a message.

---

## 12. Security & Auth

*   **Handshake Auth:** Validate the JWT token during the Socket.IO handshake.
*   **Room Protection:** Ensure `user_id` from the token matches the owner of `session_id` before allowing `join_room`.
*   **API Authentication:** Use existing JWT authentication for REST endpoints.
*   **Input Validation:** Sanitize and validate all user inputs.
*   **Rate Limiting:** Implement rate limits to prevent abuse.

---

## 13. Success Metrics

### Technical Metrics
- **Response Time**: < 2s for sync requests, < 30s for async
- **Intent Accuracy**: > 90% correct classification
- **RAG Relevance**: > 80% relevant chunks retrieved
- **Uptime**: > 99.5% availability

### Business Metrics
- **User Engagement**: % of users who try chatbot
- **Daily Active Chat Sessions**: Number per day
- **Query Success Rate**: % of queries that get useful answers
- **Average Session Length**: Messages per session

---

## 14. Future Expansion (Async Workers)

For heavy RAG queries (> 5 seconds):
1.  `socket_manager` receives message.
2.  Enqueues job to `ARQ` (`await request.app.state.arq_pool.enqueue_job(...)`).
3.  Worker processes AI logic.
4.  Worker connects to Redis and emits the result back to the specific `session_id` room using `socketio.AsyncRedisManager` (external emitter pattern).

---

## Conclusion

This implementation guide provides a complete roadmap for building the Voicely AI Chatbot system. The system combines:

1. **Real-time communication** via WebSockets for instant interaction
2. **REST API** for traditional request-response operations
3. **RAG-powered search** for accurate, context-aware responses
4. **Intent classification** for understanding user needs
5. **Async processing** for handling heavy AI workloads

By following the phased implementation plan, you'll build a robust chatbot that transforms Voicely from a passive recording tool into an intelligent assistant that helps users find, understand, and manage their audio content effectively.

**Estimated Timeline**: 8 weeks for full implementation  
**Resource Requirements**: 1-2 backend developers  
**Dependencies**: Existing Gemini AI, pgvector, ARQ worker setup
