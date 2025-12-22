# Voicely AI Chatbot Implementation Guide

**Objective:** Build a complete, real-time AI chatbot system for Voicely-BE using **WebSockets**, **FastAPI**, **Redis**, and **PostgreSQL (pgvector)**. This system will enable users to interact with their audio recordings, transcripts, and notes through natural language.

---

## 1. Architecture & Tech Stack

The system extends the existing Voicely-BE architecture.

*   **Backend:** FastAPI (Async)
*   **Real-time Communication:** `python-socketio` (Socket.IO) with `uvicorn` as the ASGI runner.
*   **Message Broker:** Redis (using `RedisManager` for Socket.IO scaling and `ARQ` for heavy tasks).
*   **Database:** PostgreSQL + `pgvector` for semantic search (RAG).
*   **AI/LLM:** Google Gemini (via `google-genai` SDK) or LangChain.
*   **Worker:** `ARQ` (existing) for offloading heavy RAG/Summarization tasks to prevent blocking the socket loop.

### Socket Event Flow
1.  **Client** connects and joins a `session_room`.
2.  **Client** emits `user_message`.
3.  **Server** acknowledges, emits `typing_start`.
4.  **Server** (optionally offloads to Worker) -> classifies intent -> performs RAG -> generates response.
5.  **Server** emits `typing_stop`.
6.  **Server** emits `ai_response` (final text + references).

---

## 2. Implementation Steps

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

Create `app/models/chatbot_model.py`. This maps strictly to the proposal's schema.

```python
from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
from app.db.session import Base

class ChatbotSession(Base):
    __tablename__ = "chatbot_sessions"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, unique=True, index=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(200), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    messages = relationship("ChatbotMessage", back_populates="session", cascade="all, delete-orphan")
    user = relationship("User", back_populates="chatbot_sessions")

class ChatbotMessage(Base):
    __tablename__ = "chatbot_messages"

    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(String, unique=True, index=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, ForeignKey("chatbot_sessions.session_id", ondelete="CASCADE"), nullable=False)
    role = Column(String(20), nullable=False) # 'user', 'assistant'
    content = Column(Text, nullable=False)
    
    # Metadata for RAG
    intent = Column(String(50), nullable=True)
    references = Column(JSON, nullable=True) # Stores audio_ids, note_ids used
    
    created_at = Column(DateTime, server_default=func.now())

    session = relationship("ChatbotSession", back_populates="messages")
```

**Action:** Run `alembic revision --autogenerate -m "add_chatbot_tables"` and `alembic upgrade head`.

### Step 3: RAG Service (`app/services/rag_service.py`)

Implement the logic to search `NoteChunk` vectors.

```python
from app.models.note_chunk_model import NoteChunk
from app.services.embedding_service import generate_embedding # Function to call Gemini embedding API

def search_context(db, user_id, query_text, limit=5):
    query_vector = generate_embedding(query_text)
    
    # PGVector search syntax (requires pgvector extension installed)
    results = db.query(NoteChunk).order_by(
        NoteChunk.embedding.cosine_distance(query_vector)
    ).limit(limit).all()
    
    # Filter by user ownership logic here or in query
    return results
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

## 4. Development Workflow for Copilot

1.  **Install Libraries:** Update `requirements.txt` and rebuild Docker.
2.  **Migration:** Generate and apply the `chatbot_sessions` and `chatbot_messages` migration.
3.  **Services:**
    *   Create `ChatbotService` to handle `Intent Classification` -> `RAG` -> `Generation`.
    *   Ensure `RAGService` correctly queries `pgvector` using `app/models/note_chunk_model.py`.
4.  **Sockets:** Implement `app/socket_manager.py` with the events defined above.
5.  **Integration:** Update `app/main.py` to wrap the FastAPI app with Socket.IO.
6.  **Testing:** Use a socket.io client tool (like Firecamp or a simple HTML/JS script) to connect to `ws://localhost:8000`, join a room, and send a message.

## 5. Security & Auth

*   **Handshake Auth:** Validate the JWT token during the Socket.IO handshake.
*   **Room Protection:** Ensure `user_id` from the token matches the owner of `session_id` before allowing `join_room`.

## 6. Future Expansion (Async Workers)

For heavy RAG queries (> 5 seconds):
1.  `socket_manager` receives message.
2.  Enqueues job to `ARQ` (`await request.app.state.arq_pool.enqueue_job(...)`).
3.  Worker processes AI logic.
4.  Worker connects to Redis and emits the result back to the specific `session_id` room using `socketio.AsyncRedisManager` (external emitter pattern).
