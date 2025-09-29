
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session

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

router = APIRouter()
security = HTTPBearer()

@router.post('/register', response_model=UserSchema)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    # Check if user already exists
    existing_user = get_user_by_email(db, email=user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    user = create_user(db, email=user_data.email, password=user_data.password)
    return user

@router.post('/login', response_model=Token)
def login(user_data: UserLogin, db: Session = Depends(get_db)):
    # Authenticate user
    user = authenticate_user(db, email=user_data.email, password=user_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    # Create access and refresh tokens
    access_token = create_access_token(subject=user.email)
    refresh_token = create_refresh_token(subject=user.email)
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

@router.post('/refresh', response_model=Token)
def refresh_token(refresh_data: RefreshTokenRequest, db: Session = Depends(get_db)):
    # Verify refresh token
    email = verify_token(refresh_data.refresh_token, settings.JWT_REFRESH_SECRET_KEY)
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    # Get user
    user = get_user_by_email(db, email=email)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    
    # Create new tokens
    access_token = create_access_token(subject=user.email)
    new_refresh_token = create_refresh_token(subject=user.email)
    
    return {
        "access_token": access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer"
    }

@router.get('/me', response_model=UserSchema)
def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    return current_user

@router.post('/logout')
def logout():
    # In a real application, you might want to blacklist the token
    # For now, we'll just return a success message
    return {"message": "Successfully logged out"}
