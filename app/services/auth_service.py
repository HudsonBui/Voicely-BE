from passlib.context import CryptContext
from datetime import timedelta, datetime, timezone
from typing import Union, Any, Optional
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.config import settings
from app.models import User
from app.schemas.auth import TokenData


# Use a more reliable password hashing scheme
password_context = CryptContext(
    schemes=["pbkdf2_sha256"],
    deprecated="auto",
    pbkdf2_sha256__default_rounds=29000,
)

# Service functions for password hashing and verification
def get_hashed_password(password: str) -> str:
    """
    Hash a password using PBKDF2-SHA256 (more reliable than bcrypt).
    """
    return password_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.
    """
    return password_context.verify(plain_password, hashed_password)

# Service functions for JWT token creation
def create_access_token(subject: Union[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    if expires_delta is not None:
        expires_delta = datetime.now(timezone.utc) + expires_delta
    else:
        expires_delta = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode = {"exp": expires_delta, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, settings.ALGORITHM)
    return encoded_jwt

def create_refresh_token(subject: Union[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    if expires_delta is not None:
        expires_delta = datetime.now(timezone.utc) + expires_delta
    else:
        expires_delta = datetime.now(timezone.utc) + timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES)

    to_encode = {"exp": expires_delta, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.JWT_REFRESH_SECRET_KEY, settings.ALGORITHM)
    return encoded_jwt

def verify_token(token: str, secret_key: str) -> Optional[str]:
    try:
        payload = jwt.decode(token, secret_key, algorithms=[settings.ALGORITHM])
        print(payload)  # Debug print - remove in production
        email: str = payload.get("sub")
        if email is None:
            return None
        token_data = TokenData(email=email)
        return token_data.email
    except jwt.ExpiredSignatureError:
        # Token has expired
        print("Token has expired")  # Debug print - remove in production
        return None
    except JWTError as e:
        # Other JWT errors (invalid signature, malformed token, etc.)
        print(f"JWT Error: {e}")  # Debug print - remove in production
        return None

def get_token_expiration_info(token: str) -> dict:
    """
    Get token expiration information without validating the signature.
    Useful for debugging and informational purposes.
    """
    try:
        # Decode without verification to get payload info
        unverified_payload = jwt.get_unverified_claims(token)
        exp_timestamp = unverified_payload.get("exp")
        
        if exp_timestamp:
            exp_datetime = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
            current_time = datetime.now(timezone.utc)
            is_expired = current_time > exp_datetime
            
            return {
                "expires_at": exp_datetime.isoformat(),
                "is_expired": is_expired,
                "time_until_expiry": str(exp_datetime - current_time) if not is_expired else "Already expired"
            }
    except Exception as e:
        return {"error": f"Could not decode token: {str(e)}"}
    
    return {"error": "No expiration information found"}

def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.query(User).filter(User.email == email).first()

def create_user(db: Session, email: str, password: str) -> User:
    hashed_password = get_hashed_password(password)
    db_user = User(email=email, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    user = get_user_by_email(db, email)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


