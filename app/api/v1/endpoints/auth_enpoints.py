
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
import json

from app.api.deps import get_db, get_current_active_user
from app.schemas.auth import UserLogin, UserCreate, Token, User as UserSchema, RefreshTokenRequest
from app.services.auth_service import (
    authenticate_user, 
    create_user, 
    get_user_by_email,
    create_access_token, 
    create_refresh_token,
    verify_token,
    get_token_expiration_info
)
from app.models import User
from app.config import settings

from app.common.response_common import ResponseCommon
from app.common.common_message import CommonMessage

router = APIRouter()
security = HTTPBearer()

@router.post('/register')
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    # Check if user already exists
    existing_user = get_user_by_email(db, email=user_data.email)
    if existing_user:
        error_response = ResponseCommon.error_response(
            message="Email already registered",
            code=status.HTTP_400_BAD_REQUEST
        )
        return Response(
            content=json.dumps(error_response.to_json()),
            status_code=error_response.code,
            media_type="application/json"
        )
    
    # Create new user
    user = create_user(db, email=user_data.email, password=user_data.password)
    response = ResponseCommon.success_response(
        data={
            "id": user.id,
            "email": user.email,
            "is_active": user.is_active,
            "created_at": user.created_at
        },
        message=CommonMessage.USER_REGISTERED_SUCCESS
    )
    return response.to_json()

@router.post('/login')
def login(user_data: UserLogin, db: Session = Depends(get_db)):
    # Authenticate user
    user = authenticate_user(db, email=user_data.email, password=user_data.password)
    if not user:
        error_response = ResponseCommon.error_response(
            message="Incorrect email or password",
            code=status.HTTP_401_UNAUTHORIZED
        )
        return Response(
            content=json.dumps(error_response.to_json()),
            status_code=error_response.code,
            media_type="application/json",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    if not user.is_active:
        error_response = ResponseCommon.error_response(
            message="Inactive user",
            code=status.HTTP_400_BAD_REQUEST
        )
        return Response(
            content=json.dumps(error_response.to_json()),
            status_code=error_response.code,
            media_type="application/json"
        )
    
    # Create access and refresh tokens
    access_token = create_access_token(subject=user.email)
    refresh_token = create_refresh_token(subject=user.email)
    
    response = ResponseCommon.success_response(
        data={
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
        },
        message=CommonMessage.LOGIN_SUCCESS
    )
    return response.to_json()

@router.post('/refresh')
def refresh_token(refresh_data: RefreshTokenRequest, db: Session = Depends(get_db)):
    # Verify refresh token
    email = verify_token(refresh_data.refresh_token, settings.JWT_REFRESH_SECRET_KEY)
    if not email:
        error_response = ResponseCommon.error_response(
            message="Invalid refresh token",
            code=status.HTTP_401_UNAUTHORIZED
        )
        return Response(
            content=json.dumps(error_response.to_json()),
            status_code=error_response.code,
            media_type="application/json"
        )
    
    # Get user
    user = get_user_by_email(db, email=email)
    if not user or not user.is_active:
        error_response = ResponseCommon.error_response(
            message="User not found or inactive",
            code=status.HTTP_401_UNAUTHORIZED
        )
        return Response(
            content=json.dumps(error_response.to_json()),
            status_code=error_response.code,
            media_type="application/json"
        )
    
    # Create new tokens
    access_token = create_access_token(subject=user.email)
    new_refresh_token = create_refresh_token(subject=user.email)
    
    response = ResponseCommon.success_response(
        data={
            "access_token": access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer"
        },
        message=CommonMessage.TOKEN_REFRESHED_SUCCESS
    )
    return response.to_json()

@router.get('/me')
def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    response = ResponseCommon.success_response(
        data={
            "id": current_user.id,
            "email": current_user.email,
            "is_active": current_user.is_active,
            "created_at": current_user.created_at
        },
        message=CommonMessage.USER_INFO_RETRIEVED_SUCCESS
    )
    return response.to_json()

@router.post('/logout')
def logout():
    # In a real application, you might want to blacklist the token
    # For now, we'll just return a success message
    response = ResponseCommon.success_response(
        message=CommonMessage.LOGOUT_SUCCESS
    )
    return response.to_json()
