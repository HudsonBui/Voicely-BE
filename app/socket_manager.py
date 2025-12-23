import socketio
from urllib.parse import parse_qs
from jose import jwt, JWTError

from app.core.redis_config import REDIS_SETTINGS
from app.config import settings
from app.db.session import SessionLocal
from app.models.chatbot_model import ChatbotSession
from app.services.auth_service import get_user_by_email
from app.services.chatbot_service import chatbot_service


redis_url = f"redis://{REDIS_SETTINGS.host}:{REDIS_SETTINGS.port}/{REDIS_SETTINGS.database}"
mgr = socketio.AsyncRedisManager(redis_url)
sio = socketio.AsyncServer(async_mode="asgi", client_manager=mgr, cors_allowed_origins="*")


def _get_token_from_environ(environ) -> str:
    query_string = environ.get("QUERY_STRING", "")
    if query_string:
        parsed = parse_qs(query_string)
        token_list = parsed.get("token", [])
        if token_list:
            return token_list[0]

    auth_header = environ.get("HTTP_AUTHORIZATION")
    if auth_header and auth_header.lower().startswith("bearer "):
        return auth_header.split(" ", 1)[1]

    headers = environ.get("headers") or []
    for key, value in headers:
        header_name = key.decode("utf-8").lower()
        if header_name == "authorization":
            header_value = value.decode("utf-8")
            if header_value.lower().startswith("bearer "):
                return header_value.split(" ", 1)[1]

    return ""


def _authenticate_socket_user(environ):
    token = _get_token_from_environ(environ)
    if not token:
        return None

    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.ALGORITHM])
        email = payload.get("sub")
        if not email:
            return None
    except JWTError:
        return None

    db = SessionLocal()
    try:
        return get_user_by_email(db, email=email)
    finally:
        db.close()


@sio.event
async def connect(sid, environ):
    user = _authenticate_socket_user(environ)
    if not user:
        return False
    await sio.save_session(sid, {"user_id": user.id})


@sio.event
async def join_session(sid, data):
    session_id = data.get("session_id") if isinstance(data, dict) else None
    if not session_id:
        await sio.emit("error", {"code": 400, "msg": "Thiếu session_id"}, room=sid)
        return

    socket_session = await sio.get_session(sid)
    user_id = socket_session.get("user_id") if socket_session else None
    if not user_id:
        await sio.emit("error", {"code": 401, "msg": "Unauthorized"}, room=sid)
        return

    db = SessionLocal()
    try:
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
            await sio.emit("error", {"code": 404, "msg": "Session not found"}, room=sid)
            return
    finally:
        db.close()

    await sio.enter_room(sid, session_id)
    await sio.emit("room_joined", {"session_id": session_id}, room=sid)


@sio.event
async def join_room(sid, data):
    await join_session(sid, data)


@sio.event
async def user_message(sid, data):
    session_id = data.get("session_id") if isinstance(data, dict) else None
    content = data.get("content") if isinstance(data, dict) else None

    if not session_id or not content:
        await sio.emit("error", {"code": 400, "msg": "Thiếu session_id hoặc content"}, room=sid)
        return

    socket_session = await sio.get_session(sid)
    user_id = socket_session.get("user_id") if socket_session else None
    if not user_id:
        await sio.emit("error", {"code": 401, "msg": "Unauthorized"}, room=sid)
        return

    await sio.emit("message_ack", {"status": "received"}, room=sid)
    await sio.emit("typing_start", {"sender": "ai"}, room=session_id)

    db = SessionLocal()
    try:
        result = await chatbot_service.process_message(
            db=db,
            user_id=user_id,
            session_id=session_id,
            message=content,
        )
        payload = {
            "message_id": result["message_id"],
            "role": "assistant",
            "content": result["response"],
            "intent": result["intent"],
            "audio_references": result.get("audio_references", []),
            "note_references": result.get("note_references", []),
            "suggested_questions": result.get("suggested_questions", []),
        }
        await sio.emit("ai_response", payload, room=session_id)
    except Exception as exc:
        await sio.emit("error", {"code": 500, "msg": str(exc)}, room=sid)
    finally:
        db.close()
        await sio.emit("typing_stop", {"sender": "ai"}, room=session_id)


@sio.event
async def disconnect(sid):
    return
