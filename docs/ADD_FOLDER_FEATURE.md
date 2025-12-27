# Add Folder Feature for Audio Organization

## Overview
This guide provides instructions for implementing a folder system to organize audio files. Users can create folders and assign audio files to them for better organization and management.

## Objective
Create a complete folder management system that allows users to:
1. Create, read, update, and delete folders
2. Organize audio files into folders
3. Move audio files between folders
4. List audio files within a specific folder
5. Search and filter folders

## Database Schema

### Folder Model
The folder belongs to a user and can contain multiple audio files.

**Relationships:**
- One user → Many folders
- One folder → Many audio files
- Each audio file can optionally belong to one folder

## Implementation Steps

### 1. Create Folder Model

**File:** `app/models/folder_model.py`

```python
from app.models.base_import import Base, Column, Integer, String, Boolean, DateTime, datetime, timezone, ForeignKey, relationship, Text

class Folder(Base):
    __tablename__ = "folders"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    color = Column(String(7), nullable=True)  # Hex color code, e.g., #FF5733
    icon = Column(String(50), nullable=True)  # Icon name/identifier
    is_default = Column(Boolean, default=False)  # Default folder for new uploads
    
    # Metadata
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    
    # Relationships
    user = relationship("User", back_populates="folders")
    audio_files = relationship("AudioFile", back_populates="folder")
    
    def __repr__(self):
        return f"<Folder(id={self.id}, name='{self.name}', user_id={self.user_id})>"
```

**Key Features:**
- `name`: Folder name (required)
- `description`: Optional description
- `color`: UI color for the folder
- `icon`: Icon identifier for UI
- `is_default`: Flag to mark default folder for auto-organization

### 2. Update AudioFile Model

**File:** `app/models/audio_model.py`

Add folder relationship to the AudioFile model:

```python
class AudioFile(Base):
    __tablename__ = "audio_files"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    folder_id = Column(Integer, ForeignKey("folders.id"), nullable=True)  # Add this field
    filename = Column(String, nullable=False)
    # ... existing fields ...
    
    # Relationships
    user = relationship("User", back_populates="audio_files")
    folder = relationship("Folder", back_populates="audio_files")  # Add this relationship
    notes = relationship("Note", back_populates="audio_file")
    task_jobs = relationship("TaskJob", back_populates="audio_file")
```

### 3. Update User Model

**File:** `app/models/user_model.py`

Add folders relationship:

```python
class User(Base):
    __tablename__ = "users"
    
    # ... existing fields ...
    
    # Relationships
    audio_files = relationship("AudioFile", back_populates="user")
    folders = relationship("Folder", back_populates="user")  # Add this
    notes = relationship("Note", back_populates="user")
    task_jobs = relationship("TaskJob", back_populates="user")
    # ... other relationships ...
```

### 4. Update Models __init__.py

**File:** `app/models/__init__.py`

```python
from app.models.user_model import User
from app.models.audio_model import AudioFile
from app.models.folder_model import Folder  # Add this import
from app.models.note_model import Note
# ... other imports ...
```

### 5. Create Folder Schemas

**File:** `app/schemas/folder.py`

```python
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime

class FolderBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Folder name")
    description: Optional[str] = Field(None, max_length=1000, description="Folder description")
    color: Optional[str] = Field(None, pattern="^#[0-9A-Fa-f]{6}$", description="Hex color code")
    icon: Optional[str] = Field(None, max_length=50, description="Icon identifier")
    is_default: bool = Field(default=False, description="Set as default folder")

class FolderCreate(FolderBase):
    """Schema for creating a new folder"""
    pass

class FolderUpdate(BaseModel):
    """Schema for updating a folder (all fields optional for partial updates)"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    color: Optional[str] = Field(None, pattern="^#[0-9A-Fa-f]{6}$")
    icon: Optional[str] = Field(None, max_length=50)
    is_default: Optional[bool] = None

class Folder(FolderBase):
    """Schema for folder response"""
    id: int
    user_id: int
    audio_count: int = Field(default=0, description="Number of audio files in folder")
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class FolderWithAudio(Folder):
    """Schema for folder with audio files list"""
    audio_files: list = Field(default_factory=list)

class MoveAudioToFolder(BaseModel):
    """Schema for moving audio file to folder"""
    audio_id: int
    folder_id: Optional[int] = Field(None, description="Folder ID (null to remove from folder)")
```

### 6. Create Database Migration

**File:** `alembic/versions/XXXXXXXX_add_folders_table.py`

```python
"""add folders table

Revision ID: XXXXXXXX
Revises: <previous_revision>
Create Date: 2025-12-27

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = 'XXXXXXXX'
down_revision = '<previous_revision>'
branch_labels = None
depends_on = None

def upgrade():
    # Create folders table
    op.create_table(
        'folders',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('color', sa.String(length=7), nullable=True),
        sa.Column('icon', sa.String(length=50), nullable=True),
        sa.Column('is_default', sa.Boolean(), nullable=True, default=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )
    op.create_index(op.f('ix_folders_id'), 'folders', ['id'], unique=False)
    op.create_index(op.f('ix_folders_user_id'), 'folders', ['user_id'], unique=False)
    
    # Add folder_id to audio_files table
    op.add_column('audio_files', sa.Column('folder_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_audio_files_folder_id',
        'audio_files', 'folders',
        ['folder_id'], ['id'],
        ondelete='SET NULL'
    )
    op.create_index(op.f('ix_audio_files_folder_id'), 'audio_files', ['folder_id'], unique=False)

def downgrade():
    # Remove folder_id from audio_files
    op.drop_index(op.f('ix_audio_files_folder_id'), table_name='audio_files')
    op.drop_constraint('fk_audio_files_folder_id', 'audio_files', type_='foreignkey')
    op.drop_column('audio_files', 'folder_id')
    
    # Drop folders table
    op.drop_index(op.f('ix_folders_user_id'), table_name='folders')
    op.drop_index(op.f('ix_folders_id'), table_name='folders')
    op.drop_table('folders')
```

### 7. Create Folder Service

**File:** `app/services/folder_service.py`

```python
import logging
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import status

from app.models import Folder, AudioFile, User
from app.schemas.folder import FolderCreate, FolderUpdate, Folder as FolderSchema
from app.common.response_common import ResponseCommon
from app.common.common_message import CommonMessage

logger = logging.getLogger(__name__)

class FolderService:
    
    def create_folder(self, db: Session, user_id: int, folder_data: FolderCreate) -> ResponseCommon:
        """Create a new folder for a user"""
        try:
            # If is_default is True, unset other default folders
            if folder_data.is_default:
                db.query(Folder).filter(
                    Folder.user_id == user_id,
                    Folder.is_default == True
                ).update({"is_default": False})
            
            # Create new folder
            folder = Folder(
                user_id=user_id,
                name=folder_data.name,
                description=folder_data.description,
                color=folder_data.color,
                icon=folder_data.icon,
                is_default=folder_data.is_default
            )
            
            db.add(folder)
            db.commit()
            db.refresh(folder)
            
            # Add audio count
            folder_dict = {
                **folder.__dict__,
                "audio_count": 0
            }
            
            return ResponseCommon.success_response(
                data=folder_dict,
                message="Folder created successfully",
                code=status.HTTP_201_CREATED
            )
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error creating folder: {str(e)}")
            return ResponseCommon.error_response(
                message=f"Failed to create folder: {str(e)}",
                code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def get_folder(self, db: Session, folder_id: int, user_id: int) -> ResponseCommon:
        """Get a specific folder by ID"""
        folder = db.query(Folder).filter(
            Folder.id == folder_id,
            Folder.user_id == user_id
        ).first()
        
        if not folder:
            return ResponseCommon.error_response(
                message="Folder not found",
                code=status.HTTP_404_NOT_FOUND
            )
        
        # Get audio count
        audio_count = db.query(func.count(AudioFile.id)).filter(
            AudioFile.folder_id == folder_id
        ).scalar()
        
        folder_dict = {
            **folder.__dict__,
            "audio_count": audio_count or 0
        }
        
        return ResponseCommon.success_response(data=folder_dict)
    
    def list_folders(self, db: Session, user_id: int, skip: int = 0, limit: int = 100) -> ResponseCommon:
        """List all folders for a user"""
        folders = db.query(
            Folder,
            func.count(AudioFile.id).label('audio_count')
        ).outerjoin(
            AudioFile, AudioFile.folder_id == Folder.id
        ).filter(
            Folder.user_id == user_id
        ).group_by(Folder.id).order_by(Folder.created_at.desc()).offset(skip).limit(limit).all()
        
        folders_list = []
        for folder, audio_count in folders:
            folder_dict = {
                **folder.__dict__,
                "audio_count": audio_count or 0
            }
            folders_list.append(folder_dict)
        
        return ResponseCommon.success_response(data=folders_list)
    
    def update_folder(self, db: Session, folder_id: int, user_id: int, update_data: dict) -> ResponseCommon:
        """Update folder information"""
        folder = db.query(Folder).filter(
            Folder.id == folder_id,
            Folder.user_id == user_id
        ).first()
        
        if not folder:
            return ResponseCommon.error_response(
                message="Folder not found",
                code=status.HTTP_404_NOT_FOUND
            )
        
        try:
            # If setting as default, unset other defaults
            if update_data.get("is_default") == True:
                db.query(Folder).filter(
                    Folder.user_id == user_id,
                    Folder.id != folder_id,
                    Folder.is_default == True
                ).update({"is_default": False})
            
            # Update folder fields
            for field, value in update_data.items():
                if value is not None and hasattr(folder, field):
                    setattr(folder, field, value)
            
            db.commit()
            db.refresh(folder)
            
            # Get audio count
            audio_count = db.query(func.count(AudioFile.id)).filter(
                AudioFile.folder_id == folder_id
            ).scalar()
            
            folder_dict = {
                **folder.__dict__,
                "audio_count": audio_count or 0
            }
            
            return ResponseCommon.success_response(
                data=folder_dict,
                message="Folder updated successfully"
            )
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error updating folder: {str(e)}")
            return ResponseCommon.error_response(
                message=f"Failed to update folder: {str(e)}",
                code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def delete_folder(self, db: Session, folder_id: int, user_id: int) -> ResponseCommon:
        """Delete a folder (audio files will be unassigned, not deleted)"""
        folder = db.query(Folder).filter(
            Folder.id == folder_id,
            Folder.user_id == user_id
        ).first()
        
        if not folder:
            return ResponseCommon.error_response(
                message="Folder not found",
                code=status.HTTP_404_NOT_FOUND
            )
        
        try:
            # Unassign audio files from this folder (set folder_id to NULL)
            db.query(AudioFile).filter(
                AudioFile.folder_id == folder_id
            ).update({"folder_id": None})
            
            # Delete the folder
            db.delete(folder)
            db.commit()
            
            return ResponseCommon.success_response(
                message="Folder deleted successfully"
            )
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error deleting folder: {str(e)}")
            return ResponseCommon.error_response(
                message=f"Failed to delete folder: {str(e)}",
                code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def move_audio_to_folder(
        self, 
        db: Session, 
        audio_id: int, 
        folder_id: Optional[int], 
        user_id: int
    ) -> ResponseCommon:
        """Move an audio file to a folder (or remove from folder if folder_id is None)"""
        # Check audio file exists and belongs to user
        audio = db.query(AudioFile).filter(
            AudioFile.id == audio_id,
            AudioFile.user_id == user_id
        ).first()
        
        if not audio:
            return ResponseCommon.error_response(
                message="Audio file not found",
                code=status.HTTP_404_NOT_FOUND
            )
        
        # If folder_id is provided, verify it exists and belongs to user
        if folder_id is not None:
            folder = db.query(Folder).filter(
                Folder.id == folder_id,
                Folder.user_id == user_id
            ).first()
            
            if not folder:
                return ResponseCommon.error_response(
                    message="Folder not found",
                    code=status.HTTP_404_NOT_FOUND
                )
        
        try:
            audio.folder_id = folder_id
            db.commit()
            db.refresh(audio)
            
            message = f"Audio file moved to folder" if folder_id else "Audio file removed from folder"
            
            return ResponseCommon.success_response(
                data=audio,
                message=message
            )
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error moving audio to folder: {str(e)}")
            return ResponseCommon.error_response(
                message=f"Failed to move audio: {str(e)}",
                code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def get_folder_audio_files(
        self, 
        db: Session, 
        folder_id: int, 
        user_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> ResponseCommon:
        """Get all audio files in a specific folder"""
        # Verify folder exists and belongs to user
        folder = db.query(Folder).filter(
            Folder.id == folder_id,
            Folder.user_id == user_id
        ).first()
        
        if not folder:
            return ResponseCommon.error_response(
                message="Folder not found",
                code=status.HTTP_404_NOT_FOUND
            )
        
        # Get audio files
        audio_files = db.query(AudioFile).filter(
            AudioFile.folder_id == folder_id
        ).order_by(AudioFile.created_at.desc()).offset(skip).limit(limit).all()
        
        return ResponseCommon.success_response(data=audio_files)

# Create service instance
folder_service = FolderService()
```

### 8. Create Folder Endpoints

**File:** `app/api/v1/endpoints/folder_endpoints.py`

```python
from fastapi import APIRouter, Depends, status
from fastapi.responses import Response
from sqlalchemy.orm import Session
import json

from app.api.deps import get_db, get_current_active_user
from app.models import User
from app.schemas.folder import FolderCreate, FolderUpdate, MoveAudioToFolder
from app.services.folder_service import folder_service

router = APIRouter()

@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_folder(
    folder_data: FolderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Create a new folder for organizing audio files.
    
    - **name**: Folder name (required)
    - **description**: Optional description
    - **color**: Hex color code (e.g., #FF5733)
    - **icon**: Icon identifier
    - **is_default**: Set as default folder for new uploads
    """
    response = folder_service.create_folder(
        db=db,
        user_id=current_user.id,
        folder_data=folder_data
    )
    
    return Response(
        content=json.dumps(response.to_json()),
        status_code=response.code,
        media_type="application/json",
    )

@router.get("/")
async def list_folders(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    List all folders for the authenticated user.
    
    Returns folders with audio file count.
    """
    response = folder_service.list_folders(
        db=db,
        user_id=current_user.id,
        skip=skip,
        limit=limit
    )
    
    return Response(
        content=json.dumps(response.to_json()),
        status_code=response.code,
        media_type="application/json",
    )

@router.get("/{folder_id}")
async def get_folder(
    folder_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get a specific folder by ID.
    
    Returns folder details with audio count.
    """
    response = folder_service.get_folder(
        db=db,
        folder_id=folder_id,
        user_id=current_user.id
    )
    
    return Response(
        content=json.dumps(response.to_json()),
        status_code=response.code,
        media_type="application/json",
    )

@router.put("/{folder_id}")
async def update_folder(
    folder_id: int,
    update_data: FolderUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Update folder information.
    
    Only provided fields will be updated (partial updates supported).
    """
    update_dict = update_data.model_dump(exclude_unset=True)
    
    response = folder_service.update_folder(
        db=db,
        folder_id=folder_id,
        user_id=current_user.id,
        update_data=update_dict
    )
    
    return Response(
        content=json.dumps(response.to_json()),
        status_code=response.code,
        media_type="application/json",
    )

@router.delete("/{folder_id}")
async def delete_folder(
    folder_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Delete a folder.
    
    Audio files in the folder will be unassigned (not deleted).
    """
    response = folder_service.delete_folder(
        db=db,
        folder_id=folder_id,
        user_id=current_user.id
    )
    
    return Response(
        content=json.dumps(response.to_json()),
        status_code=response.code,
        media_type="application/json",
    )

@router.get("/{folder_id}/audio")
async def get_folder_audio_files(
    folder_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get all audio files in a specific folder.
    
    Returns paginated list of audio files.
    """
    response = folder_service.get_folder_audio_files(
        db=db,
        folder_id=folder_id,
        user_id=current_user.id,
        skip=skip,
        limit=limit
    )
    
    return Response(
        content=json.dumps(response.to_json()),
        status_code=response.code,
        media_type="application/json",
    )

@router.post("/move-audio")
async def move_audio_to_folder(
    move_data: MoveAudioToFolder,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Move an audio file to a folder.
    
    - **audio_id**: ID of audio file to move
    - **folder_id**: Target folder ID (null to remove from folder)
    """
    response = folder_service.move_audio_to_folder(
        db=db,
        audio_id=move_data.audio_id,
        folder_id=move_data.folder_id,
        user_id=current_user.id
    )
    
    return Response(
        content=json.dumps(response.to_json()),
        status_code=response.code,
        media_type="application/json",
    )
```

### 9. Register Router

**File:** `app/api/v1/api.py`

Add the folder router:

```python
from app.api.v1.endpoints import (
    audio_endpoints,
    auth_enpoints,
    note_endpoints,
    folder_endpoints,  # Add this
    # ... other endpoints
)

api_router = APIRouter()

api_router.include_router(
    auth_enpoints.router,
    prefix="/auth",
    tags=["Authentication"]
)

api_router.include_router(
    audio_endpoints.router,
    prefix="/audio",
    tags=["Audio"]
)

api_router.include_router(
    folder_endpoints.router,  # Add this
    prefix="/folders",
    tags=["Folders"]
)

# ... other routers
```

### 10. Update Common Messages (Optional)

**File:** `app/common/common_message.py`

Add folder-related messages:

```python
# Folder messages
FOLDER_CREATED_SUCCESS = "Folder created successfully"
FOLDER_UPDATED_SUCCESS = "Folder updated successfully"
FOLDER_DELETED_SUCCESS = "Folder deleted successfully"
FOLDER_NOT_FOUND = "Folder not found"
FOLDER_ALREADY_EXISTS = "Folder with this name already exists"
AUDIO_MOVED_TO_FOLDER = "Audio file moved to folder successfully"
AUDIO_REMOVED_FROM_FOLDER = "Audio file removed from folder successfully"
```

## API Endpoints Summary

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/folders/` | Create a new folder |
| GET | `/folders/` | List all folders |
| GET | `/folders/{folder_id}` | Get folder by ID |
| PUT | `/folders/{folder_id}` | Update folder |
| DELETE | `/folders/{folder_id}` | Delete folder |
| GET | `/folders/{folder_id}/audio` | Get audio files in folder |
| POST | `/folders/move-audio` | Move audio to folder |

## Example Usage

### Create a Folder

```bash
curl -X POST "http://localhost:8000/api/v1/folders/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Work Recordings",
    "description": "Audio files from work meetings",
    "color": "#3B82F6",
    "icon": "briefcase",
    "is_default": false
  }'
```

### List Folders

```bash
curl -X GET "http://localhost:8000/api/v1/folders/?skip=0&limit=10" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Move Audio to Folder

```bash
curl -X POST "http://localhost:8000/api/v1/folders/move-audio" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "audio_id": 123,
    "folder_id": 5
  }'
```

### Remove Audio from Folder

```bash
curl -X POST "http://localhost:8000/api/v1/folders/move-audio" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "audio_id": 123,
    "folder_id": null
  }'
```

## Testing Checklist

- [ ] Can create folders with valid data
- [ ] Cannot create folder with empty name
- [ ] Can list all user's folders
- [ ] Can get specific folder by ID
- [ ] Can update folder name, description, color, icon
- [ ] Can set/unset default folder
- [ ] Only one folder can be default at a time
- [ ] Can delete folder
- [ ] Audio files are unassigned (not deleted) when folder is deleted
- [ ] Can move audio file to folder
- [ ] Can remove audio file from folder
- [ ] Can get all audio files in a folder
- [ ] Cannot access another user's folders
- [ ] Cannot move audio to another user's folder
- [ ] Proper error messages for invalid requests

## Database Migration Steps

1. **Create migration file:**
   ```bash
   alembic revision -m "add folders table"
   ```

2. **Edit the generated file** with the upgrade/downgrade code above

3. **Run migration:**
   ```bash
   alembic upgrade head
   ```

4. **Verify tables created:**
   ```bash
   # Connect to database and check
   psql -d your_database
   \dt folders
   \d audio_files  # Check for folder_id column
   ```

## Optional Enhancements

### 1. Folder Statistics
Add endpoint to get folder statistics:
- Total audio files
- Total duration
- Total file size
- Last upload date

### 2. Default Folder Auto-Assignment
When uploading audio, automatically assign to default folder:

```python
# In audio upload service
default_folder = db.query(Folder).filter(
    Folder.user_id == user.id,
    Folder.is_default == True
).first()

audio_file.folder_id = default_folder.id if default_folder else None
```

### 3. Bulk Operations
Add endpoints for:
- Move multiple audio files to folder
- Delete multiple folders at once

### 4. Folder Sharing (Future)
Add fields for sharing folders with other users:
- `is_shared: Boolean`
- `shared_with: JSON` (list of user IDs)

### 5. Nested Folders (Advanced)
Add parent-child relationship:
- `parent_folder_id: Integer` (self-referential foreign key)

## Security Considerations

1. **Authorization**: Always verify folder belongs to current user
2. **Validation**: Validate all input data (name length, color format, etc.)
3. **SQL Injection**: Use SQLAlchemy ORM (already protected)
4. **Cascade Delete**: Folders delete only unassigns audio (safe)
5. **Rate Limiting**: Consider adding rate limits for folder creation

## Performance Notes

- Folders table indexed on `user_id` for fast lookups
- Audio files indexed on `folder_id` for fast filtering
- Use `.count()` for audio count instead of loading all files
- Consider caching folder list for frequently accessed data

## Related Files

- `app/models/folder_model.py` - Folder model
- `app/models/audio_model.py` - AudioFile model (add folder_id)
- `app/models/user_model.py` - User model (add folders relationship)
- `app/schemas/folder.py` - Folder schemas
- `app/services/folder_service.py` - Folder business logic
- `app/api/v1/endpoints/folder_endpoints.py` - Folder API endpoints
- `alembic/versions/XXXXXXXX_add_folders_table.py` - Database migration
