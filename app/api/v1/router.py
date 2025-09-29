from fastapi import APIRouter

from app.api.v1.endpoints import auth_enpoints, user_endpoints, audio_endpoints

api_router = APIRouter()

api_router.include_router(auth_enpoints.router, prefix="/auth", tags=["authentication"])
api_router.include_router(user_endpoints.router, prefix="/users", tags=["users"])
api_router.include_router(audio_endpoints.router, prefix="/audio", tags=["audio"])