# Add is_summarize Field to Audio Search Endpoint

## Overview
This guide provides instructions for adding an `is_summarize` field to the `audio/search` endpoint. This field will indicate whether an audio file has been summarized (i.e., has an associated note).

## Objective
Modify the POST `/audio/search` endpoint to include an `is_summarize` boolean field in the response that indicates whether each audio file has been summarized by checking if a note exists for that audio file.

## Implementation Steps

### 1. Update Audio Response Schema

**File:** `app/schemas/audio.py`

Add the `is_summarize` field to the `AudioFile` schema:

```python
class AudioFile(AudioFileBase):
    id: int
    user_id: int
    file_path: str
    status: str
    transcription: Optional[str] = None
    confidence_score: Optional[float] = None
    created_at: datetime
    updated_at: datetime
    is_summarize: bool = False  # Add this field
    
    class Config:
        from_attributes = True
```

**Explanation:**
- Add `is_summarize` as a boolean field with a default value of `False`
- This field will be computed and set in the service layer

### 2. Update Audio Service Logic

**File:** `app/services/audio_service.py`

Modify the `search_audio_files` method to populate the `is_summarize` field by checking if notes exist for each audio file.

**Option A: Using SQL Join (Recommended - More Efficient)**

```python
from sqlalchemy import exists
from app.models.note_model import Note

def search_audio_files(
    self, db: Session, user_id: int, search_dto: AudioSearchDto
) -> PageDto[AudioFileSchema]:
    """
    Search and filter audio files with pagination
    """
    # Build the base query with note existence check
    note_exists_subquery = db.query(Note.id).filter(
        Note.audio_file_id == AudioFileModel.id
    ).exists()
    
    query = db.query(
        AudioFileModel,
        note_exists_subquery.label('has_note')
    ).filter(AudioFileModel.user_id == user_id)

    # Apply existing filters
    if search_dto.search:
        search_term = f"%{search_dto.search}%"
        query = query.filter(AudioFileModel.filename.ilike(search_term))

    if search_dto.status:
        query = query.filter(AudioFileModel.status == search_dto.status)

    if search_dto.from_date:
        query = query.filter(AudioFileModel.created_at >= search_dto.from_date)

    if search_dto.to_date:
        query = query.filter(AudioFileModel.created_at <= search_dto.to_date)

    if search_dto.min_duration is not None:
        query = query.filter(AudioFileModel.duration >= search_dto.min_duration)

    if search_dto.max_duration is not None:
        query = query.filter(AudioFileModel.duration <= search_dto.max_duration)

    if search_dto.has_transcript is not None:
        if search_dto.has_transcript:
            query = query.filter(AudioFileModel.transcription.isnot(None))
        else:
            query = query.filter(AudioFileModel.transcription.is_(None))

    # Apply ordering
    order_value = getattr(search_dto.order, "value", search_dto.order)
    if str(order_value).upper() == "ASC":
        query = query.order_by(AudioFileModel.created_at.asc())
    else:
        query = query.order_by(AudioFileModel.created_at.desc())

    # Get total count
    total = query.count()
    
    # Apply pagination
    offset = (search_dto.page - 1) * search_dto.page_size
    results = query.offset(offset).limit(search_dto.page_size).all()
    
    # Convert to schema objects with is_summarize field
    audio_files = []
    for audio_file, has_note in results:
        audio_dict = {
            "id": audio_file.id,
            "user_id": audio_file.user_id,
            "filename": audio_file.filename,
            "original_filename": audio_file.original_filename,
            "file_path": audio_file.file_path,
            "file_size": audio_file.file_size,
            "duration": audio_file.duration,
            "format": audio_file.format,
            "status": audio_file.status,
            "transcription": audio_file.transcription,
            "confidence_score": audio_file.confidence_score,
            "created_at": audio_file.created_at,
            "updated_at": audio_file.updated_at,
            "is_summarize": bool(has_note)
        }
        audio_files.append(AudioFileSchema(**audio_dict))
    
    # Create pagination response
    return PageDto(
        data=audio_files,
        total=total,
        page=search_dto.page,
        page_size=search_dto.page_size
    )
```

**Option B: Using Relationship (Simpler but Less Efficient)**

```python
def search_audio_files(
    self, db: Session, user_id: int, search_dto: AudioSearchDto
) -> PageDto[AudioFileSchema]:
    """
    Search and filter audio files with pagination
    """
    query = db.query(AudioFileModel).filter(AudioFileModel.user_id == user_id)

    # ... (keep all existing filters) ...

    # Get paginated results
    paginated = PaginationHelper.paginate_query(
        query=query,
        page_options=search_dto,
        response_model=AudioFileSchema,
    )
    
    # Add is_summarize field to each item
    for audio_file in paginated.data:
        # Check if notes exist for this audio file
        note_exists = db.query(Note).filter(
            Note.audio_file_id == audio_file.id
        ).first() is not None
        audio_file.is_summarize = note_exists
    
    return paginated
```

### 3. Optional: Add Filter for Summarized Status

If you want to allow filtering by summarization status, update the search DTO:

**File:** `app/schemas/audio.py`

```python
class AudioSearchDto(PageOptionsDto):
    """
    Audio files search/filter request payload.
    """
    status: Optional[str] = Field(...)
    from_date: Optional[datetime] = Field(...)
    to_date: Optional[datetime] = Field(...)
    min_duration: Optional[float] = Field(...)
    max_duration: Optional[float] = Field(...)
    has_transcript: Optional[bool] = Field(...)
    has_summary: Optional[bool] = Field(  # Add this field
        default=None, 
        description="Filter files with/without summary notes"
    )
```

Then update the service to filter by this field:

**File:** `app/services/audio_service.py`

```python
# Add this filter in the search_audio_files method
if search_dto.has_summary is not None:
    from app.models.note_model import Note
    
    if search_dto.has_summary:
        # Only audio files that have notes
        query = query.filter(
            db.query(Note.id).filter(
                Note.audio_file_id == AudioFileModel.id
            ).exists()
        )
    else:
        # Only audio files without notes
        query = query.filter(
            ~db.query(Note.id).filter(
                Note.audio_file_id == AudioFileModel.id
            ).exists()
        )
```

### 4. Update API Documentation

**File:** `app/api/v1/endpoints/audio_endpoints.py`

Update the endpoint docstring to document the new field:

```python
@router.post("/search", response_model=ResponseCommonSchema[PageDto[AudioFileSchema]])
async def search_audio_files(
    search_dto: AudioSearchDto,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Search and filter audio files with pagination.

    - **page**: Current page number (default: 1)
    - **page_size**: Items per page (default: 10)
    - **order**: Sort order - ASC or DESC (default: DESC)
    - **search**: Search in filename
    - **status**: Filter by processing status
    - **from_date**: Filter files uploaded after date
    - **to_date**: Filter files uploaded before date
    - **min_duration**: Minimum duration in seconds
    - **max_duration**: Maximum duration in seconds
    - **has_transcript**: Filter files with/without transcripts
    - **has_summary**: Filter files with/without summary notes (optional)
    
    Response includes:
    - **is_summarize**: Boolean indicating if the audio has been summarized
    """
    # ... existing implementation ...
```

## Testing Checklist

- [ ] Verify `is_summarize` is `true` for audio files with notes
- [ ] Verify `is_summarize` is `false` for audio files without notes
- [ ] Test pagination still works correctly
- [ ] Test all existing filters still work
- [ ] Test the optional `has_summary` filter (if implemented)
- [ ] Verify performance with large datasets
- [ ] Test API documentation is updated correctly

## Database Considerations

**Important:** The `is_summarize` field is computed at query time based on the relationship between `audio_files` and `notes` tables. No database migration is needed as this is not a stored field.

### Relationship Check
The implementation relies on the existing relationship:
- `AudioFile.notes` (one-to-many relationship with Note model)
- `Note.audio_file_id` (foreign key to AudioFile)

Make sure these relationships exist in the models.

## Performance Notes

- **Option A (SQL Join)**: More efficient for large datasets as it performs the check in a single database query
- **Option B (Relationship)**: Simpler to implement but may cause N+1 queries if not careful with eager loading

For production, **Option A is recommended** for better performance.

## Example Response

After implementation, the response should look like:

```json
{
  "success": true,
  "message": "Audio files retrieved successfully",
  "data": {
    "data": [
      {
        "id": 1,
        "filename": "recording_2024_01_15.mp3",
        "original_filename": "My Recording.mp3",
        "file_size": 2048000,
        "duration": 120.5,
        "format": "mp3",
        "user_id": 5,
        "file_path": "/uploads/audio/...",
        "status": "completed",
        "transcription": "Hello world...",
        "confidence_score": 0.95,
        "created_at": "2024-01-15T10:30:00Z",
        "updated_at": "2024-01-15T10:35:00Z",
        "is_summarize": true  // New field
      },
      {
        "id": 2,
        "filename": "recording_2024_01_16.mp3",
        "original_filename": "Another Recording.mp3",
        "file_size": 1024000,
        "duration": 60.0,
        "format": "mp3",
        "user_id": 5,
        "file_path": "/uploads/audio/...",
        "status": "completed",
        "transcription": "Test audio...",
        "confidence_score": 0.92,
        "created_at": "2024-01-16T09:00:00Z",
        "updated_at": "2024-01-16T09:05:00Z",
        "is_summarize": false  // New field
      }
    ],
    "total": 2,
    "page": 1,
    "page_size": 10
  }
}
```

## Related Files

- `app/models/audio_model.py` - AudioFile model
- `app/models/note_model.py` - Note model
- `app/schemas/audio.py` - Audio schemas
- `app/services/audio_service.py` - Audio service logic
- `app/api/v1/endpoints/audio_endpoints.py` - Audio endpoints
