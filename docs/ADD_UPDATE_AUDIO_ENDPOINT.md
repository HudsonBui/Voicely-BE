# Add Update Audio Endpoint

## Overview
This guide provides instructions for creating a PUT endpoint to update audio file information, primarily for editing transcripts when users find them inaccurate. The endpoint can also be extended to update other fields like the audio filename.

## Objective
Create a PUT `/audio/{audio_id}` endpoint that allows users to:
1. Update the transcript text if it's incorrect
2. Update the original filename (optional, for future use)
3. Update other editable fields as needed

## Use Case
When a user reviews an audio file's transcript and finds it doesn't match the actual audio content, they can manually correct the transcript through this endpoint.

## Important Business Rule
**When the transcription is updated, all related notes (summaries) must be deleted.**

Rationale: Notes/summaries are generated based on the audio's transcription. If the transcription changes, the existing summary is no longer accurate and should be removed. The user can regenerate a new summary based on the corrected transcription.

## Implementation Steps

### 1. Update Audio Schema for Updates

**File:** `app/schemas/audio.py`

Modify the `AudioFileUpdate` schema to support the fields users can edit:

```python
class AudioFileUpdate(BaseModel):
    """
    Schema for updating audio file information.
    Only provided fields will be updated (partial updates supported).
    """
    transcription: Optional[str] = Field(
        default=None, 
        description="Updated transcription text"
    )
    original_filename: Optional[str] = Field(
        default=None,
        description="Updated original filename",
        min_length=1,
        max_length=255
    )
    # Note: confidence_score, status, duration should not be user-editable
    # They are managed by the system
```

**Key Points:**
- Use `Optional` for all fields to support partial updates
- Only include fields that users should be allowed to edit
- System-managed fields (status, confidence_score, duration) should not be editable by users
- Use Field validators to ensure data integrity

### 2. Add Update Method to Audio Service

**File:** `app/services/audio_service.py`

Add a new method to handle audio file updates:

```python
def update_audio_file(
    self,
    db: Session,
    audio_id: int,
    user_id: int,
    update_data: dict
) -> ResponseCommon:
    """
    Update audio file information
    
    Args:
        db: Database session
        audio_id: ID of the audio file to update
        user_id: ID of the current user (for authorization)
        update_data: Dictionary of fields to update
        
    Returns:
        ResponseCommon with updated audio file or error
    """
    # Get the audio file
    audio_file = db.query(AudioFileModel).filter(
        AudioFileModel.id == audio_id,
        AudioFileModel.user_id == user_id
    ).first()
    
    if not audio_file:
        return ResponseCommon.error_response(
            message=f"Audio file with ID {audio_id} not found or you don't have permission to access it",
            code=status.HTTP_404_NOT_FOUND
        )
    
    # Validate and update fields
    try:
        # Filter out None values and system-managed fields
        allowed_fields = {'transcription', 'original_filename'}
        transcription_updated = False
        
        for field, value in update_data.items():
            if value is not None and field in allowed_fields:
                if field == 'original_filename':
                    # Update both original_filename and filename
                    audio_file.original_filename = value
                    # Generate new filename while keeping the extension
                    file_extension = audio_file.format
                    audio_file.filename = f"{value.rsplit('.', 1)[0]}.{file_extension}"
                elif field == 'transcription':
                    # Mark that transcription is being updated
                    transcription_updated = True
                    setattr(audio_file, field, value)
                else:
                    setattr(audio_file, field, value)
        
        # CRITICAL: If transcription is updated, delete all related notes
        # because the summary is based on the old transcription and is no longer valid
        if transcription_updated:
            deleted_count = db.query(Note).filter(
                Note.audio_file_id == audio_id
            ).delete(synchronize_session=False)
            
            if deleted_count > 0:
                logger.info(f"Deleted {deleted_count} note(s) for audio {audio_id} due to transcription update")
        
        # Update the updated_at timestamp
        from datetime import datetime, timezone
        audio_file.updated_at = datetime.now(timezone.utc)
        
        db.commit()
        db.refresh(audio_file)
        
        # Convert to schema
        audio_schema = AudioFileSchema.from_orm(audio_file)
        
        return ResponseCommon.success_response(
            data=audio_schema,
            message="Audio file updated successfully"
        )
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating audio file {audio_id}: {str(e)}")
        return ResponseCommon.error_response(
            message=f"Failed to update audio file: {str(e)}",
            code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
```

**Alternative Implementation (More Strict):**

If you want to prevent users from updating certain fields entirely:

```python
def update_audio_file(
    self,
    db: Session,
    audio_id: int,
    user_id: int,
    update_data: dict
) -> ResponseCommon:
    """Update audio file with validation"""
    
    # Get audio file
    audio_file = db.query(AudioFileModel).filter(
        AudioFileModel.id == audio_id,
        AudioFileModel.user_id == user_id
    ).first()
    
    if not audio_file:
        return ResponseCommon.error_response(
            message="Audio file not found",
            code=status.HTTP_404_NOT_FOUND
        )
    
    # Track if transcription is being updated
    transcription_updated = False
    
    # Only allow specific fields to be updated
    if 'transcription' in update_data and update_data['transcription'] is not None:
        transcription_updated = True
        audio_file.transcription = update_data['transcription']
    
    # Delete related notes if transcription was updated
    # The summary is based on the transcription, so it's no longer valid
    if transcription_updated:
        deleted_count = db.query(Note).filter(
            Note.audio_file_id == audio_id
        ).delete(synchronize_session=False)
        logger.info(f"Deleted {deleted_count} note(s) for audio {audio_id} due to transcription update")
    
    if 'original_filename' in update_data and update_data['original_filename'] is not None:
        new_filename = update_data['original_filename']
        
        # Validate filename
        if not new_filename or len(new_filename) > 255:
            return ResponseCommon.error_response(
                message="Invalid filename",
                code=status.HTTP_400_BAD_REQUEST
            )
        
        audio_file.original_filename = new_filename
        # Update filename field as well
        audio_file.filename = f"{new_filename.rsplit('.', 1)[0]}.{audio_file.format}"
    
    try:
        from datetime import datetime, timezone
        audio_file.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(audio_file)
        
        return ResponseCommon.success_response(
            data=AudioFileSchema.from_orm(audio_file),
            message="Audio file updated successfully"
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating audio: {str(e)}")
        return ResponseCommon.error_response(
            message=f"Update failed: {str(e)}",
            code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
```

### 3. Create the Update Endpoint

**File:** `app/api/v1/endpoints/audio_endpoints.py`

Add the new PUT endpoint:

```python
from app.schemas.audio import AudioFileUpdate

@router.put("/{audio_id}", response_model=ResponseCommonSchema[AudioFileSchema])
async def update_audio_file(
    audio_id: int,
    update_data: AudioFileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Update audio file information.
    
    This endpoint allows users to:
    - Edit the transcription text if it's incorrect
    - Update the original filename
    
    Only the provided fields will be updated (partial updates supported).
    
    Args:
        audio_id: ID of the audio file to update
        update_data: Fields to update (transcription, original_filename)
        
    Returns:
        Updated audio file information
        
    Raises:
        404: Audio file not found or no permission
        400: Invalid update data
        500: Server error during update
    """
    logger.info(f"Updating audio file {audio_id} for user {current_user.id}")
    
    # Convert to dict and exclude unset fields for partial updates
    update_dict = update_data.model_dump(exclude_unset=True)
    
    # Check if there's anything to update
    if not update_dict:
        from app.common.response_common import ResponseCommon
        error_response = ResponseCommon.error_response(
            message="No fields provided for update",
            code=status.HTTP_400_BAD_REQUEST
        )
        return Response(
            content=json.dumps(error_response.to_json()),
            status_code=error_response.code,
            media_type="application/json"
        )
    
    # Call service to update
    update_response = audio_service.update_audio_file(
        db=db,
        audio_id=audio_id,
        user_id=current_user.id,
        update_data=update_dict
    )
    
    if not update_response.success:
        return Response(
            content=json.dumps(update_response.to_json()),
            status_code=update_response.code,
            media_type="application/json"
        )
    
    return update_response.to_json()
```

### 4. Add Common Messages (Optional)

**File:** `app/common/common_message.py`

Add relevant success/error messages:

```python
# Audio update messages
AUDIO_UPDATED_SUCCESS = "Audio file updated successfully"
AUDIO_NOT_FOUND = "Audio file not found"
AUDIO_UPDATE_NO_PERMISSION = "You don't have permission to update this audio file"
AUDIO_UPDATE_NO_FIELDS = "No fields provided for update"
AUDIO_UPDATE_INVALID_FILENAME = "Invalid filename provided"
```

Then use them in the service:

```python
return ResponseCommon.success_response(
    data=audio_schema,
    message=CommonMessage.AUDIO_UPDATED_SUCCESS
)
```

### 5. Add Validation (Optional but Recommended)

Add validators to the schema for better data validation:

**File:** `app/schemas/audio.py`

```python
from pydantic import BaseModel, Field, field_validator

class AudioFileUpdate(BaseModel):
    transcription: Optional[str] = Field(default=None, max_length=50000)
    original_filename: Optional[str] = Field(default=None, min_length=1, max_length=255)
    
    @field_validator('original_filename')
    @classmethod
    def validate_filename(cls, v):
        if v is not None:
            # Remove leading/trailing whitespace
            v = v.strip()
            
            # Check for invalid characters
            invalid_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
            if any(char in v for char in invalid_chars):
                raise ValueError('Filename contains invalid characters')
            
            if not v:
                raise ValueError('Filename cannot be empty')
                
        return v
    
    @field_validator('transcription')
    @classmethod
    def validate_transcription(cls, v):
        if v is not None:
            v = v.strip()
            if not v:
                return None  # Empty transcription is allowed
        return v
```

## Testing the Endpoint

### Test Cases

1. **Update Transcription Only**
```bash
curl -X PUT "http://localhost:8000/api/v1/audio/1" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "transcription": "This is the corrected transcription text"
  }'
```

2. **Update Filename Only**
```bash
curl -X PUT "http://localhost:8000/api/v1/audio/1" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "original_filename": "New Audio Name.mp3"
  }'
```

3. **Update Both Fields**
```bash
curl -X PUT "http://localhost:8000/api/v1/audio/1" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "transcription": "Corrected transcript",
    "original_filename": "Updated Name.mp3"
  }'
```

4. **Test Authorization** - Try to update another user's audio
```bash
curl -X PUT "http://localhost:8000/api/v1/audio/999" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "transcription": "Should fail"
  }'
```

### Testing Checklist

- [ ] Can update transcription successfully
- [ ] Can update original_filename successfully
- [ ] Can update both fields simultaneously
- [ ] Partial updates work (only provided fields are updated)
- [ ] Returns 404 when audio doesn't exist
- [ ] Returns 404 when trying to update another user's audio
- [ ] Returns 400 when no fields are provided
- [ ] Returns 400 when invalid data is provided
- [ ] Filename validation works correctly
- [ ] `updated_at` timestamp is updated
- [ ] Original file on disk is not affected (only metadata changes)
- [ ] Works correctly with audio files that have/don't have transcriptions
- [ ] **Related notes are deleted when transcription is updated**
- [ ] **Notes are NOT deleted when only filename is updated**
- [ ] **Multiple notes associated with the audio are all deleted**
- [ ] **Audio without notes can still be updated without errors**

## Security Considerations

1. **Authorization**: Ensure users can only update their own audio files
2. **Validation**: Validate all input fields to prevent injection attacks
3. **Field Restrictions**: Don't allow users to update system-managed fields (status, confidence_score, file_path, etc.)
4. **Filename Sanitization**: If allowing filename updates, sanitize input to prevent path traversal
5. **Audit Trail**: Consider logging update operations for audit purposes
6. **Cascade Delete**: When deleting related notes, ensure only notes belonging to this audio are deleted (not accidentally deleting other users' notes)

## Data Integrity Considerations

### Note Deletion on Transcription Update

When the transcription is updated, the implementation automatically deletes all related notes. This is necessary because:

1. **Data Consistency**: Notes/summaries are generated from the transcription. If the transcription changes, the summary is no longer accurate.
2. **User Experience**: Showing outdated summaries could mislead users.
3. **Re-generation**: Users can regenerate summaries after correcting the transcription.

**Implementation Details:**
- Only transcription updates trigger note deletion
- Filename updates do NOT delete notes (the content hasn't changed)
- All notes associated with the audio file are deleted in a single query
- Deletion is logged for audit purposes
- The operation is atomic (within the same transaction)

**Warning to Users:**
Consider adding a warning in the API documentation or client application that updating the transcription will delete existing summaries.

## Example Implementation with Logging

If you want to track who changed what:

```python
def update_audio_file(self, db: Session, audio_id: int, user_id: int, update_data: dict) -> ResponseCommon:
    # ... existing code ...
    
    # Log the changes
    changes = []
    transcription_updated = False
    
    for field, new_value in update_data.items():
        if field in allowed_fields and new_value is not None:
            old_value = getattr(audio_file, field)
            if old_value != new_value:
                changes.append(f"{field}: '{old_value}' -> '{new_value}'")
                if field == 'transcription':
                    transcription_updated = True
                setattr(audio_file, field, new_value)
    
    if changes:
        logger.info(f"User {user_id} updated audio {audio_id}: {', '.join(changes)}")
    
    # Delete notes if transcription was updated
    if transcription_updated:
        deleted_count = db.query(Note).filter(
            Note.audio_file_id == audio_id
        ).delete(synchronize_session=False)
        if deleted_count > 0:
            logger.warning(f"User {user_id} updated transcription for audio {audio_id}, deleted {deleted_count} related note(s)")
    
    # ... rest of code ...
```

## Expected Response Format

**Success Response (200 OK):**
```json
{
  "success": true,
  "message": "Audio file updated successfully",
  "data": {
    "id": 1,
    "user_id": 5,
    "filename": "updated_recording.mp3",
    "original_filename": "Updated Recording.mp3",
    "file_path": "/uploads/audio/abc123.mp3",
    "file_size": 2048000,
    "duration": 120.5,
    "format": "mp3",
    "status": "completed",
    "transcription": "This is the corrected transcription",
    "confidence_score": 0.95,
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T14:25:00Z"
  }
}
```

**Error Response - Not Found (404):**
```json
{
  "success": false,
  "message": "Audio file with ID 999 not found or you don't have permission to access it",
  "code": 404
}
```

**Error Response - No Fields (400):**
```json
{
  "success": false,
  "message": "No fields provided for update",
  "code": 400
}
```

## Future Enhancements

Consider these potential extensions:

1. **Version History**: Keep track of transcript changes
2. **Batch Updates**: Allow updating multiple audio files at once
3. **Re-transcription**: Trigger a new transcription job if user requests it
4. **Tag Management**: Add ability to add/remove tags
5. **Notes Field**: Allow users to add personal notes about the audio

## Related Files

- `app/models/audio_model.py` - AudioFile model definition
- `app/schemas/audio.py` - Audio schemas (add AudioFileUpdate)
- `app/services/audio_service.py` - Audio service (add update_audio_file method)
- `app/api/v1/endpoints/audio_endpoints.py` - Audio endpoints (add PUT endpoint)
- `app/common/common_message.py` - Common messages (add update messages)

## References

For similar implementation patterns, see:
- `app/api/v1/endpoints/note_endpoints.py` - Update note endpoint example
- `app/services/note_service.py` - Update service pattern example
