# FCM Push Notification Implementation Guide

## Overview
This guide provides a complete implementation for sending Firebase Cloud Messaging (FCM) push notifications to users when async worker tasks complete (e.g., transcript processing, note summarization). The system includes automatic cleanup of invalid tokens and multi-device support.

## System Components
- **FastAPI** - REST API endpoints
- **ARQ** - Background task processing
- **PostgreSQL** - Database storage
- **Firebase Admin SDK** - Push notification delivery
- **SQLAlchemy** - ORM

## 1. Database Schema

### UserDevice Table
Create a new table to manage multiple devices per user. Each user can have multiple active FCM tokens (e.g., iPhone, iPad, Android).

**Location**: Create new file `app/models/user_device_model.py`

```python
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.db.base import Base

class UserDevice(Base):
    __tablename__ = "user_devices"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    fcm_token = Column(String, unique=True, nullable=False, index=True)
    device_type = Column(String)  # "ios" or "android"
    device_name = Column(String)  # Optional: "iPhone 15 Pro", "iPad Air"
    is_active = Column(Boolean, default=True, nullable=False)
    last_login = Column(DateTime, default=func.now(), nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
```

### Alembic Migration
Create a new migration for the user_devices table:

```bash
alembic revision -m "add_user_devices_table"
```

**Migration file content**:
```python
def upgrade():
    op.create_table(
        'user_devices',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('fcm_token', sa.String(), nullable=False),
        sa.Column('device_type', sa.String(), nullable=True),
        sa.Column('device_name', sa.String(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('last_login', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('fcm_token')
    )
    op.create_index('ix_user_devices_user_id', 'user_devices', ['user_id'])
    op.create_index('ix_user_devices_fcm_token', 'user_devices', ['fcm_token'])

def downgrade():
    op.drop_index('ix_user_devices_fcm_token')
    op.drop_index('ix_user_devices_user_id')
    op.drop_table('user_devices')
```

## 2. Pydantic Schemas

**Location**: Create new file `app/schemas/notification.py`

```python
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class DeviceRegisterRequest(BaseModel):
    fcm_token: str = Field(..., description="Firebase Cloud Messaging token")
    device_type: str = Field(..., description="Device type: ios or android")
    device_name: Optional[str] = Field(None, description="Optional device name")

class DeviceResponse(BaseModel):
    id: int
    user_id: int
    fcm_token: str
    device_type: str
    device_name: Optional[str]
    is_active: bool
    last_login: datetime
    
    class Config:
        from_attributes = True

class NotificationPayload(BaseModel):
    title: str = Field(..., description="Notification title")
    body: str = Field(..., description="Notification body")
    data: Optional[dict] = Field(None, description="Additional data payload")
```

## 3. Firebase Admin SDK Setup

**Location**: Update or create `app/core/firebase_config.py`

```python
import firebase_admin
from firebase_admin import credentials, messaging
import os
from app.core.config import settings

# Initialize Firebase Admin SDK
def init_firebase():
    """Initialize Firebase Admin SDK with service account credentials"""
    if not firebase_admin._apps:
        # Path to your Firebase service account key JSON file
        cred_path = os.getenv("FIREBASE_CREDENTIALS_PATH", "voicely-firebase-adminsdk.json")
        
        if not os.path.exists(cred_path):
            raise FileNotFoundError(f"Firebase credentials not found at {cred_path}")
        
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)
        print("✅ Firebase Admin SDK initialized successfully")
    
    return firebase_admin.get_app()

# Call this in app startup (main.py)
```

**Update `app/main.py`** to initialize Firebase on startup:
```python
from app.core.firebase_config import init_firebase

@app.on_event("startup")
async def startup_event():
    init_firebase()
    # ... other startup logic
```

## 4. API Endpoints

### Register Device Endpoint
**Location**: Update `app/api/v1/endpoints/auth_endpoints.py`

Add a new endpoint for device registration (called after successful login):

```python
from app.models.user_device_model import UserDevice
from app.schemas.notification import DeviceRegisterRequest, DeviceResponse
from sqlalchemy.orm import Session
from datetime import datetime

@router.post("/register-device", response_model=DeviceResponse)
async def register_device(
    request: DeviceRegisterRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Register a device for push notifications.
    Called after successful login with FCM token from client.
    
    Edge cases handled:
    - Token already exists for another user -> reassign to current user
    - Token already exists for current user -> update last_login and ensure active
    - New token -> create new device record
    """
    # Check if token already exists
    existing_device = db.query(UserDevice).filter(
        UserDevice.fcm_token == request.fcm_token
    ).first()
    
    if existing_device:
        # Token exists - update ownership and activate
        existing_device.user_id = current_user.id
        existing_device.device_type = request.device_type
        existing_device.device_name = request.device_name
        existing_device.is_active = True
        existing_device.last_login = datetime.utcnow()
        db.commit()
        db.refresh(existing_device)
        return existing_device
    else:
        # New token - create new device
        new_device = UserDevice(
            user_id=current_user.id,
            fcm_token=request.fcm_token,
            device_type=request.device_type,
            device_name=request.device_name,
            is_active=True,
            last_login=datetime.utcnow()
        )
        db.add(new_device)
        db.commit()
        db.refresh(new_device)
        return new_device
```

### Update Logout Endpoint
**Location**: Update existing logout endpoint in `app/api/v1/endpoints/auth_endpoints.py`

```python
@router.post("/logout")
async def logout(
    fcm_token: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Logout user and deactivate device if FCM token provided.
    """
    if fcm_token:
        # Find and deactivate the device
        device = db.query(UserDevice).filter(
            UserDevice.fcm_token == fcm_token,
            UserDevice.user_id == current_user.id
        ).first()
        
        if device:
            device.is_active = False
            db.commit()
    
    # Perform other logout operations (invalidate JWT, etc.)
    return {"message": "Logged out successfully"}
```

### List User Devices Endpoint (Optional)
```python
@router.get("/devices", response_model=List[DeviceResponse])
async def list_devices(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all devices registered for the current user"""
    devices = db.query(UserDevice).filter(
        UserDevice.user_id == current_user.id
    ).all()
    return devices
```

## 5. Notification Service

**Location**: Create new file `app/services/notification_service.py`

```python
from firebase_admin import messaging
from sqlalchemy.orm import Session
from app.models.user_device_model import UserDevice
from typing import Optional, Dict, List
import logging

logger = logging.getLogger(__name__)

class NotificationService:
    """Service for sending push notifications via Firebase Cloud Messaging"""
    
    @staticmethod
    async def send_to_user(
        db: Session,
        user_id: int,
        title: str,
        body: str,
        data: Optional[Dict[str, str]] = None
    ) -> Dict[str, int]:
        """
        Send push notification to all active devices of a user.
        
        Handles edge cases:
        - Automatically deactivates tokens that are no longer valid
        - Skips inactive devices
        - Returns statistics about successful/failed sends
        
        Args:
            db: Database session
            user_id: Target user ID
            title: Notification title
            body: Notification body
            data: Optional additional data payload
            
        Returns:
            Dictionary with send statistics:
            {
                "total_devices": int,
                "successful": int,
                "failed": int,
                "deactivated": int
            }
        """
        # Get all active devices for the user
        devices = db.query(UserDevice).filter(
            UserDevice.user_id == user_id,
            UserDevice.is_active == True
        ).all()
        
        stats = {
            "total_devices": len(devices),
            "successful": 0,
            "failed": 0,
            "deactivated": 0
        }
        
        if not devices:
            logger.warning(f"No active devices found for user {user_id}")
            return stats
        
        # Prepare notification
        notification = messaging.Notification(
            title=title,
            body=body
        )
        
        # Send to each device
        for device in devices:
            message = messaging.Message(
                notification=notification,
                token=device.fcm_token,
                data=data or {}
            )
            
            try:
                # Attempt to send
                response = messaging.send(message)
                stats["successful"] += 1
                logger.info(f"✅ Notification sent to device {device.id}: {response}")
                
            except messaging.UnregisteredError:
                # EDGE CASE: Token is no longer valid (user uninstalled app)
                logger.warning(f"⚠️ Token {device.fcm_token} is unregistered. Deactivating device {device.id}")
                device.is_active = False
                stats["deactivated"] += 1
                
            except messaging.SenderIdMismatchError:
                # Token belongs to different Firebase project
                logger.error(f"❌ Token {device.fcm_token} sender ID mismatch. Deactivating device {device.id}")
                device.is_active = False
                stats["deactivated"] += 1
                
            except messaging.QuotaExceededError:
                # Rate limit exceeded
                logger.error(f"❌ FCM quota exceeded for device {device.id}")
                stats["failed"] += 1
                
            except messaging.InvalidArgumentError as e:
                # Invalid token format
                logger.error(f"❌ Invalid token for device {device.id}: {e}")
                device.is_active = False
                stats["deactivated"] += 1
                
            except Exception as e:
                # Other unexpected errors
                logger.error(f"❌ Unexpected error sending to device {device.id}: {e}")
                stats["failed"] += 1
        
        # Commit deactivations
        if stats["deactivated"] > 0:
            db.commit()
        
        logger.info(f"📊 Notification stats for user {user_id}: {stats}")
        return stats
    
    @staticmethod
    async def send_to_devices(
        tokens: List[str],
        title: str,
        body: str,
        data: Optional[Dict[str, str]] = None
    ) -> List[str]:
        """
        Send notification to specific device tokens (without database)
        Returns list of failed tokens
        """
        failed_tokens = []
        
        notification = messaging.Notification(title=title, body=body)
        
        for token in tokens:
            message = messaging.Message(
                notification=notification,
                token=token,
                data=data or {}
            )
            
            try:
                messaging.send(message)
            except Exception as e:
                logger.error(f"Failed to send to token {token}: {e}")
                failed_tokens.append(token)
        
        return failed_tokens
```

## 6. Worker Integration

### Update ARQ Workers
**Location**: Update workers in `app/worker.py` and individual task functions

Example for transcript completion:

```python
from app.services.notification_service import NotificationService
from app.models.audio_model import Audio
from app.models.user_model import User

async def process_transcription_task(ctx, audio_id: int):
    """
    ARQ worker task for processing audio transcription
    Sends notification when complete
    """
    db = get_db_session()  # Your DB session getter
    
    try:
        # 1. Perform transcription
        audio = db.query(Audio).filter(Audio.id == audio_id).first()
        if not audio:
            raise ValueError(f"Audio {audio_id} not found")
        
        # ... transcription logic ...
        
        # 2. Update status
        audio.status = "completed"
        db.commit()
        
        # 3. Send notification
        await NotificationService.send_to_user(
            db=db,
            user_id=audio.user_id,
            title="Transcription Complete ✅",
            body=f"Your audio '{audio.filename}' has been transcribed successfully",
            data={
                "type": "transcription_complete",
                "audio_id": str(audio_id),
                "status": "completed"
            }
        )
        
        logger.info(f"✅ Transcription completed for audio {audio_id}")
        
    except Exception as e:
        logger.error(f"❌ Transcription failed for audio {audio_id}: {e}")
        
        # Send failure notification
        if audio:
            await NotificationService.send_to_user(
                db=db,
                user_id=audio.user_id,
                title="Transcription Failed ❌",
                body=f"Failed to transcribe '{audio.filename}'",
                data={
                    "type": "transcription_failed",
                    "audio_id": str(audio_id),
                    "status": "failed"
                }
            )
        
        raise
    finally:
        db.close()
```

Example for note summarization:

```python
async def summarize_transcript_task(ctx, note_id: int):
    """
    ARQ worker task for summarizing transcripts
    Sends notification when complete
    """
    db = get_db_session()
    
    try:
        # 1. Perform summarization
        note = db.query(Note).filter(Note.id == note_id).first()
        if not note:
            raise ValueError(f"Note {note_id} not found")
        
        # ... summarization logic ...
        
        # 2. Update status
        note.status = "completed"
        db.commit()
        
        # 3. Send notification
        await NotificationService.send_to_user(
            db=db,
            user_id=note.user_id,
            title="Summary Ready 📝",
            body=f"Your note has been summarized",
            data={
                "type": "summarization_complete",
                "note_id": str(note_id),
                "status": "completed"
            }
        )
        
        logger.info(f"✅ Summarization completed for note {note_id}")
        
    except Exception as e:
        logger.error(f"❌ Summarization failed for note {note_id}: {e}")
        
        if note:
            await NotificationService.send_to_user(
                db=db,
                user_id=note.user_id,
                title="Summarization Failed ❌",
                body=f"Failed to summarize your note",
                data={
                    "type": "summarization_failed",
                    "note_id": str(note_id),
                    "status": "failed"
                }
            )
        
        raise
    finally:
        db.close()
```

## 7. Environment Configuration

**Location**: Update `.env` file

Add Firebase configuration:
```env
# Firebase Cloud Messaging
FIREBASE_CREDENTIALS_PATH=voicely-firebase-adminsdk.json
```

## 8. Complete Workflow

### 1. User Login Flow
```
1. Client app logs in -> receives JWT token
2. Client app gets FCM token from Firebase SDK
3. Client app calls POST /api/v1/auth/register-device with FCM token
4. Backend saves/updates device in user_devices table with is_active=true
```

### 2. Task Processing Flow
```
1. User submits async task (transcription/summarization)
2. API creates task record and enqueues ARQ worker
3. Worker processes task
4. Worker calls NotificationService.send_to_user()
5. Service queries all active devices for user
6. Service sends notification to each device via Firebase
7. If token is invalid (UnregisteredError):
   - Service sets is_active=false for that device
   - Database automatically cleaned
8. User receives notification on active devices
```

### 3. User Logout Flow
```
1. Client app calls POST /api/v1/auth/logout with FCM token
2. Backend finds device record with that token
3. Backend sets is_active=false
4. User no longer receives notifications on that device
```

### 4. Edge Case Handling
```
Automatic cleanup when:
- User uninstalls app -> Firebase returns UnregisteredError -> is_active=false
- User reinstalls app on same device -> New registration reactivates token
- User logs in on new device -> New device record created
- Token belongs to wrong Firebase project -> SenderIdMismatchError -> is_active=false
```

## 9. Testing

### Manual Testing Steps

1. **Test Device Registration**
```bash
curl -X POST http://localhost:8000/api/v1/auth/register-device \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "fcm_token": "YOUR_FCM_TOKEN",
    "device_type": "ios",
    "device_name": "iPhone 15 Pro"
  }'
```

2. **Test Notification Sending**
Create a test endpoint in `auth_endpoints.py`:
```python
@router.post("/test-notification")
async def test_notification(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Test endpoint to send notification"""
    stats = await NotificationService.send_to_user(
        db=db,
        user_id=current_user.id,
        title="Test Notification",
        body="This is a test message",
        data={"type": "test"}
    )
    return stats
```

3. **Test Logout**
```bash
curl -X POST http://localhost:8000/api/v1/auth/logout \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"fcm_token": "YOUR_FCM_TOKEN"}'
```

### Unit Tests
**Location**: Create `tests/test_notification_service.py`

```python
import pytest
from app.services.notification_service import NotificationService
from app.models.user_device_model import UserDevice

@pytest.mark.asyncio
async def test_send_to_user_success(db_session, test_user):
    # Create active device
    device = UserDevice(
        user_id=test_user.id,
        fcm_token="valid_token_123",
        device_type="ios",
        is_active=True
    )
    db_session.add(device)
    db_session.commit()
    
    # Send notification
    stats = await NotificationService.send_to_user(
        db=db_session,
        user_id=test_user.id,
        title="Test",
        body="Test message"
    )
    
    assert stats["total_devices"] == 1
    # Note: Will fail in test without Firebase setup
```

## 10. Security Considerations

1. **Token Security**
   - Never expose FCM tokens in API responses (except in device management endpoints)
   - Store tokens securely in database
   - Use HTTPS for all API communication

2. **User Authorization**
   - Always verify user owns the device before operations
   - Require JWT authentication for device registration
   - Validate FCM token format before storage

3. **Rate Limiting**
   - Implement rate limiting on notification endpoints
   - Handle FCM quota limits gracefully
   - Consider batching notifications for efficiency

4. **Data Privacy**
   - Don't send sensitive data in notification body
   - Use data payload for identifiers only
   - Client should fetch full data after receiving notification

## 11. Monitoring and Logging

**Best Practices**:
- Log all notification send attempts
- Track deactivation rates
- Monitor Firebase quota usage
- Alert on high failure rates
- Dashboard for active devices per user

**Example Logging**:
```python
logger.info(f"📲 Sending notification to user {user_id}: {title}")
logger.warning(f"⚠️ Deactivated {stats['deactivated']} invalid tokens")
logger.error(f"❌ Failed to send {stats['failed']} notifications")
```

## 12. Dependencies

Add to `requirements.txt`:
```txt
firebase-admin>=6.0.0
```

Install:
```bash
pip install firebase-admin
```

## 13. Firebase Setup

1. Go to Firebase Console (https://console.firebase.google.com)
2. Create/select your project
3. Navigate to Project Settings > Service Accounts
4. Click "Generate New Private Key"
5. Download the JSON file
6. Rename to `voicely-firebase-adminsdk.json`
7. Place in project root (add to .gitignore!)
8. Update FIREBASE_CREDENTIALS_PATH in .env

## Summary

This implementation provides:
- ✅ Multi-device support per user
- ✅ Automatic cleanup of invalid tokens
- ✅ Robust error handling
- ✅ Clean separation of concerns
- ✅ Easy integration with existing ARQ workers
- ✅ Comprehensive edge case coverage
- ✅ Security best practices

The system automatically handles device lifecycle management, ensuring clean database state and reliable notification delivery.
