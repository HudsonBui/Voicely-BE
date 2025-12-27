from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth_enpoints,
    user_endpoints,
    audio_endpoints,
    transcript_endpoints,
    note_endpoints,
    task_endpoints,
    chatbot_endpoints,
    folder_endpoints,
    notification_endpoints,
)

api_router = APIRouter()

api_router.include_router(auth_enpoints.router, prefix="/auth", tags=["authentication"])
api_router.include_router(user_endpoints.router, prefix="/users", tags=["users"])
api_router.include_router(audio_endpoints.router, prefix="/audio", tags=["audio"])
api_router.include_router(transcript_endpoints.router, prefix="/transcript", tags=["transcription"])
api_router.include_router(note_endpoints.router, prefix="/notes", tags=["notes"])
api_router.include_router(task_endpoints.router, prefix="/tasks", tags=["tasks"])
api_router.include_router(chatbot_endpoints.router, prefix="/chatbot", tags=["chatbot"])
api_router.include_router(folder_endpoints.router, prefix="/folders", tags=["folders"])
api_router.include_router(notification_endpoints.router, prefix="/notifications", tags=["notifications"])
