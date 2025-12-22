# Voicely AI Chatbot System - Implementation Proposal

## Executive Summary

This document proposes a comprehensive AI chatbot system for Voicely-BE, inspired by the multi-stage chatbot architecture but tailored specifically for voice recording and note-taking use cases. The chatbot will help users interact with their audio recordings, transcripts, and notes through natural language conversations.

---

## Table of Contents

1. [Business Use Cases](#business-use-cases)
2. [Architecture Overview](#architecture-overview)
3. [Processing Pipeline](#processing-pipeline)
4. [Database Schema](#database-schema)
5. [Implementation Plan](#implementation-plan)
6. [API Endpoints](#api-endpoints)
7. [Integration Points](#integration-points)

---

## Business Use Cases

### Primary Use Cases for Voicely Chatbot

#### 1. **Intelligent Search & Retrieval** 🔍
**User Query**: "Find all meetings about project X from last week"
- Search across transcripts using semantic understanding
- Filter by date, category, keywords
- Return relevant audio files with timestamps

#### 2. **Content Summarization** 📝
**User Query**: "Summarize the key points from today's meeting"
- Generate concise summaries from audio transcripts
- Extract action items and decisions
- Create structured notes automatically

#### 3. **Question Answering** 💬
**User Query**: "What did John say about the budget?"
- Search specific content within transcripts
- Provide direct answers with audio timestamp references
- Context-aware responses based on conversation history

#### 4. **Audio Management Assistant** 🎧
**User Query**: "Delete all recordings older than 30 days"
**User Query**: "Archive my lecture notes from March"
- Help manage audio library through natural language
- Batch operations on audio files and notes
- Smart categorization and organization

#### 5. **Productivity Intelligence** 📊
**User Query**: "How much time have I spent in meetings this month?"
**User Query**: "What are my most common meeting topics?"
- Analytics on audio usage patterns
- Insights from transcript content analysis
- Productivity recommendations

#### 6. **Multi-lingual Support** 🌍
**User Query**: "Translate the summary to Vietnamese"
- Detect user's preferred language
- Translate responses automatically
- Support multi-language audio transcription queries

---

## Architecture Overview

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                    VOICELY CHATBOT SYSTEM                    │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              │               │               │
              ▼               ▼               ▼
    ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
    │   FastAPI    │  │  ARQ Worker  │  │    Redis     │
    │   Chatbot    │  │  (Async AI   │  │   (Queue)    │
    │   Endpoints  │  │  Processing) │  │              │
    └──────────────┘  └──────────────┘  └──────────────┘
              │               │               │
              └───────────────┼───────────────┘
                              │
                              ▼
              ┌───────────────────────────────┐
              │        PostgreSQL              │
              │  • Users                       │
              │  • Audio Files                 │
              │  • Transcripts                 │
              │  • Notes & Note Chunks         │
              │  • Chatbot Sessions            │
              │  • Chatbot Messages            │
              │  • Token Usage                 │
              └───────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              │               │               │
              ▼               ▼               ▼
    ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
    │ Google Cloud │  │  Gemini AI   │  │  pgvector    │
    │   Storage    │  │   (GenAI)    │  │  (Semantic   │
    │   (Audio)    │  │              │  │   Search)    │
    └──────────────┘  └──────────────┘  └──────────────┘
```

### Key Design Principles

1. **Async-First**: Long AI processing tasks run in background workers
2. **RAG-Enabled**: Use existing note chunks and embeddings for semantic search
3. **Context-Aware**: Maintain conversation history for better responses
4. **Token-Efficient**: Track and limit AI token usage per user
5. **Multi-Modal**: Handle both text and audio references

---

## Processing Pipeline

### Voicely Chatbot Pipeline (6 Stages)

```
User Query: "Summarize yesterday's meeting about marketing"
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│  Stage 1: Input Validation & Session Management             │
│  • Validate user authentication                              │
│  • Load/create conversation session                          │
│  • Detect language                                           │
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
│  • Translate if needed (multi-lingual)                       │
│  • Update conversation history                               │
│  • Track token usage                                         │
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
    language = detect_language(message)
    chat_message = create_message_record(session, message, language)
    
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
    response = format_response(result, language, intent)
    update_conversation_history(session, message, response)
    track_token_usage(chat_message, tokens_used)
    
    return response
```

---

## Database Schema

### New Tables for Chatbot

#### 1. **chatbot_sessions**
Stores conversation sessions for context continuity.

```sql
CREATE TABLE chatbot_sessions (
    id SERIAL PRIMARY KEY,
    session_id UUID UNIQUE NOT NULL DEFAULT gen_random_uuid(),
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(200),  -- Auto-generated from first message
    language VARCHAR(10) DEFAULT 'en',
    total_messages INTEGER DEFAULT 0,
    total_tokens_used INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_session_user_id (user_id),
    INDEX idx_session_active (is_active)
);
```

#### 2. **chatbot_messages**
Stores individual messages in conversations.

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
    
    -- Token tracking
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    model_name VARCHAR(100),
    
    -- Response metadata
    response_time_ms INTEGER,
    confidence_score FLOAT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_message_session (session_id),
    INDEX idx_message_created (created_at)
);
```

#### 3. **chatbot_token_limits**
User-specific token limits and usage tracking.

```sql
CREATE TABLE chatbot_token_limits (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    monthly_token_limit INTEGER DEFAULT 100000,  -- Tokens per month
    current_month_usage INTEGER DEFAULT 0,
    last_reset_date DATE DEFAULT CURRENT_DATE,
    
    -- Soft limits per request
    max_tokens_per_request INTEGER DEFAULT 4000,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_token_user (user_id)
);
```

#### 4. **chatbot_feedback**
User feedback on chatbot responses for improvement.

```sql
CREATE TABLE chatbot_feedback (
    id SERIAL PRIMARY KEY,
    message_id UUID NOT NULL REFERENCES chatbot_messages(message_id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
    feedback_text TEXT,
    is_helpful BOOLEAN,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_feedback_message (message_id),
    INDEX idx_feedback_user (user_id)
);
```

### Existing Tables to Leverage

- ✅ **users**: User authentication and profiles
- ✅ **audio_files**: Audio recordings with transcripts
- ✅ **notes**: Summarized notes from audio
- ✅ **note_chunks**: Chunked content with embeddings (for RAG)

---

## Implementation Plan

### Phase 1: Foundation (Week 1-2)

#### Tasks:
1. **Database Setup**
   - Create migration for new chatbot tables
   - Add indexes for performance
   - Update models in `app/models/`

2. **Core Services**
   - Create `app/services/chatbot_service.py`
   - Create `app/services/intent_service.py`
   - Create `app/services/entity_extraction_service.py`

3. **Basic Endpoints**
   - `POST /api/v1/chatbot/sessions` - Create new chat session
   - `POST /api/v1/chatbot/sessions/{session_id}/messages` - Send message
   - `GET /api/v1/chatbot/sessions` - List user sessions
   - `GET /api/v1/chatbot/sessions/{session_id}` - Get session history

### Phase 2: RAG Integration (Week 3)

#### Tasks:
1. **Semantic Search Enhancement**
   - Enhance existing `semantic_search_notes()` function
   - Add multi-criteria filtering (date, category, etc.)
   - Implement hybrid search (semantic + keyword)

2. **Context Builder**
   - Create `app/services/rag_context_service.py`
   - Implement context window management
   - Add conversation history compression

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

2. **Multi-lingual Support**
   - Integrate language detection
   - Add response translation
   - Support multi-language transcripts

3. **Async Processing**
   - Move heavy AI calls to ARQ workers
   - Implement streaming responses (Server-Sent Events)
   - Add progress indicators

4. **Token Management**
   - Implement token tracking per user
   - Add usage limits and warnings
   - Create token optimization strategies

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
   - Load testing for concurrent users

4. **Documentation**
   - API documentation (OpenAPI/Swagger)
   - User guide for chatbot features
   - Developer documentation

---

## API Endpoints

### Chatbot API Specification

#### 1. Create Chat Session

```http
POST /api/v1/chatbot/sessions
Authorization: Bearer <token>
Content-Type: application/json

{
  "language": "en"  // Optional
}

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

#### 2. Send Message (Sync)

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
        "title": "Team Meeting - Dec 15",
        "timestamp": 120.5,
        "excerpt": "We discussed the marketing campaign..."
      }
    ],
    "note_references": [
      {
        "note_id": 456,
        "title": "Marketing Notes",
        "excerpt": "Key decisions made..."
      }
    ],
    "suggested_questions": [
      "Would you like a summary of these meetings?",
      "Show me action items from these meetings"
    ],
    "tokens_used": 1250
  }
}
```

#### 3. Send Message (Async) - For Long Processing

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

#### 4. Get Session History

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
        "content": "Find meetings...",
        "created_at": "2024-12-22T10:00:00Z"
      },
      {
        "message_id": "uuid-2",
        "role": "assistant",
        "content": "I found 5 meetings...",
        "intent": "search",
        "created_at": "2024-12-22T10:00:05Z"
      }
    ],
    "total": 10,
    "limit": 20,
    "offset": 0
  }
}
```

#### 5. List All Sessions

```http
GET /api/v1/chatbot/sessions?limit=20&offset=0
Authorization: Bearer <token>

Response 200:
{
  "success": true,
  "data": {
    "sessions": [
      {
        "session_id": "uuid-here",
        "title": "Audio Management Discussion",
        "total_messages": 15,
        "last_message_at": "2024-12-22T10:00:00Z",
        "created_at": "2024-12-20T09:00:00Z"
      }
    ],
    "total": 5,
    "limit": 20,
    "offset": 0
  }
}
```

#### 6. Delete Session

```http
DELETE /api/v1/chatbot/sessions/{session_id}
Authorization: Bearer <token>

Response 200:
{
  "success": true,
  "message": "Session deleted successfully"
}
```

#### 7. Provide Feedback

```http
POST /api/v1/chatbot/messages/{message_id}/feedback
Authorization: Bearer <token>
Content-Type: application/json

{
  "rating": 5,
  "is_helpful": true,
  "feedback_text": "Great response!"
}

Response 201:
{
  "success": true,
  "message": "Feedback recorded"
}
```

#### 8. Get Token Usage

```http
GET /api/v1/chatbot/token-usage
Authorization: Bearer <token>

Response 200:
{
  "success": true,
  "data": {
    "monthly_limit": 100000,
    "current_usage": 15000,
    "remaining": 85000,
    "percentage_used": 15.0,
    "reset_date": "2025-01-01"
  }
}
```

---

## Integration Points

### 1. Audio File Integration

**Capability**: Reference specific audio files in responses

```python
# When chatbot needs to reference audio
from app.services.audio_service import audio_service

audio_file = audio_service.get_audio_file_by_id(db, audio_id, user)
response_data = {
    "audio_id": audio_file.id,
    "title": audio_file.original_filename,
    "duration": audio_file.duration,
    "transcript_excerpt": audio_file.transcription[:200],
    "playback_url": f"/api/v1/audio/{audio_file.id}/stream"
}
```

### 2. Transcript Search Integration

**Capability**: Search within transcripts using semantic understanding

```python
# Semantic search in transcripts
from app.services.embedding_service import generate_query_embedding

query_embedding = generate_query_embedding(user_query)
relevant_chunks = semantic_search_notes(
    db=db,
    user_id=user_id,
    query_embedding=query_embedding,
    limit=5
)
```

### 3. Note Summarization Integration

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

### 4. Async Task Integration

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

### 5. Token Tracking Integration

**Capability**: Track AI token usage across all services

```python
# Centralized token tracking
def track_chatbot_tokens(
    db: Session,
    user_id: int,
    message_id: str,
    input_tokens: int,
    output_tokens: int,
    model_name: str
):
    # Update chatbot_messages
    # Update chatbot_token_limits
    # Check limits
    pass
```

---

## Sample Implementation Code

### Intent Classifier Service

```python
# app/services/intent_service.py
from google import genai
from google.genai import types
import json

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
    
    def __init__(self, genai_client):
        self.client = genai_client
    
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
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=self.INTENT_SYSTEM_PROMPT,
                    temperature=0.3,
                    response_mime_type="application/json"
                )
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

# Usage
intent_service = IntentService(client)
result = intent_service.classify_intent(
    "Find all meetings from last week",
    conversation_history=[...]
)
```

### RAG Context Builder

```python
# app/services/rag_context_service.py
from sqlalchemy.orm import Session
from app.models import NoteChunk, Note, AudioFile
from app.services.embedding_service import generate_query_embedding
from pgvector.sqlalchemy import Vector
from datetime import datetime, timedelta

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
        
        # Generate query embedding
        query_embedding = generate_query_embedding(query)
        
        # Build base query
        query_obj = db.query(NoteChunk).join(Note).join(AudioFile).filter(
            Note.user_id == user_id
        )
        
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
                Note.category.in_(entities["categories"])
            )
        
        # Apply audio_id filter
        if entities.get("audio_ids"):
            query_obj = query_obj.filter(
                AudioFile.id.in_(entities["audio_ids"])
            )
        
        # Semantic search with cosine similarity
        chunks = query_obj.order_by(
            NoteChunk.embedding.cosine_distance(query_embedding)
        ).limit(limit).all()
        
        return chunks
    
    def build_context(
        self,
        chunks: list,
        max_tokens: int = 3000
    ) -> str:
        """Build context string from chunks, respecting token limit"""
        
        context_parts = []
        total_chars = 0
        max_chars = max_tokens * 4  # Rough estimate: 1 token ≈ 4 chars
        
        for chunk in chunks:
            chunk_text = f"""
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

# Usage
rag_service = RAGContextService()
chunks = rag_service.semantic_search_with_filters(
    db, user_id, query, entities
)
context = rag_service.build_context(chunks)
```

### Main Chatbot Service

```python
# app/services/chatbot_service.py
from sqlalchemy.orm import Session
from app.models import ChatbotSession, ChatbotMessage
from app.services.intent_service import intent_service
from app.services.rag_context_service import RAGContextService
from google import genai
import uuid

class ChatbotService:
    """Main chatbot orchestration service"""
    
    def __init__(self, genai_client):
        self.client = genai_client
        self.rag_service = RAGContextService()
    
    async def process_message(
        self,
        db: Session,
        user_id: int,
        session_id: str,
        message: str
    ) -> dict:
        """Main pipeline for processing chatbot messages"""
        
        # Stage 1: Load session
        session = db.query(ChatbotSession).filter(
            ChatbotSession.session_id == session_id,
            ChatbotSession.user_id == user_id
        ).first()
        
        if not session:
            raise ValueError("Session not found")
        
        # Get conversation history
        history = self._get_conversation_history(db, session_id, limit=10)
        
        # Stage 2: Classify intent
        intent_result = intent_service.classify_intent(message, history)
        intent = intent_result["intent"]
        entities = intent_result["entities"]
        
        # Stage 3 & 4: RAG retrieval (if applicable)
        context = ""
        retrieved_chunks = []
        if intent in ["search", "summarize", "question"]:
            chunks = self.rag_service.semantic_search_with_filters(
                db, user_id, message, entities, limit=5
            )
            context = self.rag_service.build_context(chunks)
            retrieved_chunks = [chunk.id for chunk in chunks]
        
        # Stage 5: Execute action based on intent
        if intent == "search":
            response = self._handle_search(db, user_id, entities, chunks)
        elif intent == "summarize":
            response = self._handle_summarize(message, context, history)
        elif intent == "question":
            response = self._handle_question(message, context, history)
        elif intent == "manage":
            response = self._handle_manage(db, user_id, entities)
        elif intent == "analytics":
            response = self._handle_analytics(db, user_id, entities)
        else:  # chat
            response = self._handle_chat(message, history)
        
        # Save message to database
        self._save_message(
            db, session_id, "user", message, intent, entities, retrieved_chunks
        )
        self._save_message(
            db, session_id, "assistant", response["text"], intent, {}
        )
        
        return response
    
    def _handle_question(
        self,
        question: str,
        context: str,
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
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.7
            )
        )
        
        return {
            "text": response.text,
            "intent": "question"
        }

chatbot_service = ChatbotService(client)
```

---

## Comparison with Reference Chatbot System

### Similarities
- ✅ Multi-stage pipeline architecture
- ✅ Intent classification and entity extraction
- ✅ RAG-based retrieval for context
- ✅ Token tracking and limits
- ✅ Conversation history management
- ✅ Multi-lingual support
- ✅ Async processing for heavy tasks

### Key Differences

| Aspect | Reference System | Voicely System |
|--------|-----------------|----------------|
| **Domain** | Generic chatbot for businesses | Voice recording & note-taking specific |
| **RAG Source** | Uploaded documents | User's own audio transcripts & notes |
| **Primary Intents** | Customer support, FAQ | Search, summarize, Q&A on recordings |
| **Third-party** | External DB integration | Audio/transcript-specific integrations |
| **Rule-based** | Keyword matching | Audio metadata filtering |
| **Special Words** | Customer service phrases | Audio management commands |
| **Multi-tenancy** | Company schemas | User-isolated data |

---

## Success Metrics

### Technical Metrics
- **Response Time**: < 2s for sync requests, < 30s for async
- **Intent Accuracy**: > 90% correct classification
- **RAG Relevance**: > 80% relevant chunks retrieved
- **Token Efficiency**: < 2000 tokens average per request

### Business Metrics
- **User Engagement**: % of users who try chatbot
- **Daily Active Chat Sessions**: Number per day
- **Query Success Rate**: % of queries that get useful answers
- **User Satisfaction**: Average rating on responses

---

## Conclusion

This chatbot system will transform Voicely from a passive recording tool into an intelligent assistant that helps users:

1. **Find content faster** through natural language search
2. **Understand recordings better** with AI-powered summaries
3. **Extract insights** from their audio library
4. **Manage content easily** through conversational commands
5. **Get more value** from their recorded content

By leveraging the existing infrastructure (RAG, embeddings, async processing) and following the proven multi-stage architecture, we can build a robust, scalable chatbot that provides genuine value to Voicely users.

---

## Next Steps

1. **Review & Approve**: Review this proposal and provide feedback
2. **Database Migration**: Create chatbot tables
3. **Phase 1 Implementation**: Build foundation (sessions, messages, basic endpoints)
4. **Testing**: Test with real user scenarios
5. **Iterate**: Refine based on user feedback
6. **Scale**: Optimize and expand features

**Estimated Timeline**: 8 weeks for full implementation
**Resource Requirements**: 1-2 backend developers
**Dependencies**: Existing Gemini AI, pgvector, ARQ worker setup
