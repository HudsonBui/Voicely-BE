# Pagination Standardization Guide

## Overview
This guide provides a comprehensive approach to standardizing pagination across all list/search endpoints in the FastAPI application. The implementation follows a consistent pattern using POST requests with complex filter payloads and standardized response wrappers.

## Goals
- ✅ Consistent pagination structure across all list endpoints
- ✅ Support complex filtering with multiple criteria
- ✅ Provide rich metadata for client-side pagination UI
- ✅ Use POST requests for search/list operations (to support complex payloads)
- ✅ Standardize field naming conventions (snake_case)

## System Architecture

### Request Flow
```
Client → POST /api/v1/{resource}/search → Endpoint → Service → Database → Response Wrapper → Client
```

## 1. Base Pagination Schema

### Create Base Pagination DTO
**Location**: Create new file `app/schemas/pagination.py`

```python
from pydantic import BaseModel, Field
from typing import Optional, List, TypeVar, Generic
from enum import Enum

class SortOrder(str, Enum):
    """Sort order enumeration"""
    ASC = "ASC"
    DESC = "DESC"

class PageOptionsDto(BaseModel):
    """
    Base pagination and filtering options.
    All list/search endpoints should extend this class.
    """
    page: int = Field(default=1, ge=1, description="Current page number (starts at 1)")
    page_size: int = Field(default=10, ge=1, le=100, description="Number of items per page")
    order: SortOrder = Field(default=SortOrder.DESC, description="Sort order (ASC or DESC)")
    search: Optional[str] = Field(default=None, description="General search keyword")
    is_dropdown: bool = Field(default=False, description="If true, return all items without pagination")
    
    class Config:
        use_enum_values = True

class PageMetaDto(BaseModel):
    """
    Pagination metadata returned with paginated responses
    """
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Items per page")
    item_count: int = Field(..., description="Total items matching filters")
    page_count: int = Field(..., description="Total number of pages")
    has_previous_page: bool = Field(..., description="Whether there is a previous page")
    has_next_page: bool = Field(..., description="Whether there is a next page")

T = TypeVar('T')

class PageDto(BaseModel, Generic[T]):
    """
    Generic paginated response wrapper
    """
    data: List[T] = Field(..., description="Array of items for current page")
    meta: PageMetaDto = Field(..., description="Pagination metadata")

class ResponseCommon(BaseModel, Generic[T]):
    """
    Standard API response wrapper
    """
    code: int = Field(default=200, description="HTTP status code")
    success: bool = Field(default=True, description="Whether request was successful")
    message: str = Field(default="SUCCESSFULLY", description="Response message")
    data: Optional[T] = Field(default=None, description="Response data")
```

### Pagination Helper Functions
**Location**: Create new file `app/common/pagination_utils.py`

```python
from typing import List, TypeVar, Type
from sqlalchemy.orm import Query
from sqlalchemy import func
from app.schemas.pagination import PageDto, PageMetaDto, PageOptionsDto, ResponseCommon
from math import ceil

T = TypeVar('T')

class PaginationHelper:
    """Helper class for creating paginated responses"""
    
    @staticmethod
    def create_meta(
        page: int,
        page_size: int,
        total_items: int
    ) -> PageMetaDto:
        """
        Create pagination metadata
        
        Args:
            page: Current page number
            page_size: Items per page
            total_items: Total number of items
            
        Returns:
            PageMetaDto with calculated values
        """
        page_count = ceil(total_items / page_size) if page_size > 0 else 0
        
        return PageMetaDto(
            page=page,
            page_size=page_size,
            item_count=total_items,
            page_count=page_count,
            has_previous_page=page > 1,
            has_next_page=page < page_count
        )
    
    @staticmethod
    def paginate_query(
        query: Query,
        page_options: PageOptionsDto,
        response_model: Type[T]
    ) -> PageDto[T]:
        """
        Apply pagination to a SQLAlchemy query
        
        Args:
            query: SQLAlchemy query object
            page_options: Pagination options from request
            response_model: Pydantic model for response items
            
        Returns:
            PageDto with paginated data and metadata
        """
        # If dropdown mode, return all items
        if page_options.is_dropdown:
            items = query.all()
            return PageDto(
                data=[response_model.from_orm(item) for item in items],
                meta=PageMetaDto(
                    page=1,
                    page_size=len(items),
                    item_count=len(items),
                    page_count=1,
                    has_previous_page=False,
                    has_next_page=False
                )
            )
        
        # Get total count
        total_items = query.count()
        
        # Calculate offset
        offset = (page_options.page - 1) * page_options.page_size
        
        # Apply pagination
        items = query.offset(offset).limit(page_options.page_size).all()
        
        # Create metadata
        meta = PaginationHelper.create_meta(
            page=page_options.page,
            page_size=page_options.page_size,
            total_items=total_items
        )
        
        # Convert to response models
        data = [response_model.from_orm(item) for item in items]
        
        return PageDto(data=data, meta=meta)
    
    @staticmethod
    def create_response(
        paginated_data: PageDto[T],
        message: str = "SUCCESSFULLY",
        code: int = 200
    ) -> ResponseCommon[PageDto[T]]:
        """
        Wrap paginated data in ResponseCommon
        
        Args:
            paginated_data: PageDto containing data and metadata
            message: Success message
            code: HTTP status code
            
        Returns:
            ResponseCommon wrapper
        """
        return ResponseCommon(
            code=code,
            success=True,
            message=message,
            data=paginated_data
        )
```

## 2. Entity-Specific Schemas

### Example: Notes Search Schema
**Location**: Update `app/schemas/note.py`

```python
from app.schemas.pagination import PageOptionsDto
from pydantic import Field
from typing import Optional
from datetime import datetime

class NoteSearchDto(PageOptionsDto):
    """
    Notes search/filter request payload.
    Extends base pagination with note-specific filters.
    """
    # Inherited from PageOptionsDto:
    # - page: int
    # - page_size: int
    # - order: SortOrder
    # - search: str (searches in title, content, summary)
    # - is_dropdown: bool
    
    # Note-specific filters
    category: Optional[str] = Field(default=None, description="Filter by category")
    priority: Optional[str] = Field(default=None, description="Filter by priority (low, normal, high)")
    is_favorite: Optional[bool] = Field(default=None, description="Filter favorite notes")
    is_archived: Optional[bool] = Field(default=None, description="Filter archived notes")
    is_shared: Optional[bool] = Field(default=None, description="Filter shared notes")
    tags: Optional[str] = Field(default=None, description="Filter by tags (comma-separated)")
    from_date: Optional[datetime] = Field(default=None, description="Filter notes created after this date")
    to_date: Optional[datetime] = Field(default=None, description="Filter notes created before this date")
    audio_file_id: Optional[int] = Field(default=None, description="Filter by linked audio file")
    
    class Config:
        json_schema_extra = {
            "example": {
                "page": 1,
                "page_size": 10,
                "order": "DESC",
                "search": "meeting",
                "category": "work",
                "priority": "high",
                "is_favorite": True,
                "from_date": "2025-01-01T00:00:00",
                "to_date": "2025-12-31T23:59:59"
            }
        }
```

### Example: Audio Search Schema
**Location**: Update `app/schemas/audio.py`

```python
from app.schemas.pagination import PageOptionsDto
from pydantic import Field
from typing import Optional
from datetime import datetime

class AudioSearchDto(PageOptionsDto):
    """
    Audio files search/filter request payload.
    Extends base pagination with audio-specific filters.
    """
    # Audio-specific filters
    status: Optional[str] = Field(default=None, description="Filter by status (pending, processing, completed, failed)")
    from_date: Optional[datetime] = Field(default=None, description="Filter audio files uploaded after this date")
    to_date: Optional[datetime] = Field(default=None, description="Filter audio files uploaded before this date")
    min_duration: Optional[float] = Field(default=None, description="Minimum duration in seconds")
    max_duration: Optional[float] = Field(default=None, description="Maximum duration in seconds")
    has_transcript: Optional[bool] = Field(default=None, description="Filter files with/without transcripts")
    
    class Config:
        json_schema_extra = {
            "example": {
                "page": 1,
                "page_size": 20,
                "order": "DESC",
                "search": "interview",
                "status": "completed",
                "from_date": "2025-01-01T00:00:00",
                "has_transcript": True
            }
        }
```

## 3. Update Endpoints

### Example: Notes Search Endpoint
**Location**: Update `app/api/v1/endpoints/note_endpoints.py`

**BEFORE:**
```python
@router.get("/", response_model=NotesListResponse)
async def get_notes(
    skip: int = Query(0),
    limit: int = Query(10),
    category: Optional[str] = None,
    is_archived: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    notes = note_service.get_user_notes(db, current_user.id, skip, limit, category, is_archived)
    total = note_service.count_user_notes(db, current_user.id, category, is_archived)
    
    return NotesListResponse(
        notes=notes,
        total_count=total,
        page=skip // limit + 1,
        page_size=limit
    )
```

**AFTER:**
```python
from app.schemas.pagination import ResponseCommon, PageDto
from app.schemas.note import NoteSearchDto, Note

@router.post("/search", response_model=ResponseCommon[PageDto[Note]])
async def search_notes(
    search_dto: NoteSearchDto,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Search and filter notes with pagination.
    
    - **page**: Current page number (default: 1)
    - **page_size**: Items per page (default: 10)
    - **order**: Sort order - ASC or DESC (default: DESC)
    - **search**: Search in title, content, summary
    - **category**: Filter by category
    - **priority**: Filter by priority
    - **is_favorite**: Filter favorite notes
    - **is_archived**: Filter archived notes
    - **from_date**: Filter notes created after date
    - **to_date**: Filter notes created before date
    """
    paginated_notes = await note_service.search_notes(
        db=db,
        user_id=current_user.id,
        search_dto=search_dto
    )
    
    return PaginationHelper.create_response(
        paginated_data=paginated_notes,
        message="Notes retrieved successfully"
    )
```

### Example: Audio Files Search Endpoint
**Location**: Update `app/api/v1/endpoints/audio_endpoints.py`

**BEFORE:**
```python
@router.get("/files", response_model=AudioFilesListResponse)
async def get_audio_files(
    skip: int = Query(0),
    limit: int = Query(10),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    files = audio_service.get_user_audio_files(db, current_user.id, skip, limit)
    total = audio_service.count_user_audio_files(db, current_user.id)
    
    return AudioFilesListResponse(
        files=files,
        total_count=total,
        page=skip // limit + 1,
        page_size=limit
    )
```

**AFTER:**
```python
from app.schemas.pagination import ResponseCommon, PageDto
from app.schemas.audio import AudioSearchDto, AudioFile

@router.post("/search", response_model=ResponseCommon[PageDto[AudioFile]])
async def search_audio_files(
    search_dto: AudioSearchDto,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
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
    - **has_transcript**: Filter files with/without transcripts
    """
    paginated_files = await audio_service.search_audio_files(
        db=db,
        user_id=current_user.id,
        search_dto=search_dto
    )
    
    return PaginationHelper.create_response(
        paginated_data=paginated_files,
        message="Audio files retrieved successfully"
    )
```

## 4. Update Service Layer

### Example: Note Service
**Location**: Update `app/services/note_service.py`

```python
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from app.models.note_model import Note
from app.schemas.note import NoteSearchDto, Note as NoteSchema
from app.schemas.pagination import PageDto
from app.common.pagination_utils import PaginationHelper

class NoteService:
    
    async def search_notes(
        self,
        db: Session,
        user_id: int,
        search_dto: NoteSearchDto
    ) -> PageDto[NoteSchema]:
        """
        Search and filter notes with pagination
        
        Args:
            db: Database session
            user_id: Current user ID
            search_dto: Search filters and pagination options
            
        Returns:
            PageDto with notes and pagination metadata
        """
        # Base query - filter by user
        query = db.query(Note).filter(Note.user_id == user_id)
        
        # Apply general search (if provided)
        if search_dto.search:
            search_term = f"%{search_dto.search}%"
            query = query.filter(
                or_(
                    Note.title.ilike(search_term),
                    Note.content.ilike(search_term),
                    Note.summary.ilike(search_term)
                )
            )
        
        # Apply specific filters
        if search_dto.category is not None:
            query = query.filter(Note.category == search_dto.category)
        
        if search_dto.priority is not None:
            query = query.filter(Note.priority == search_dto.priority)
        
        if search_dto.is_favorite is not None:
            query = query.filter(Note.is_favorite == search_dto.is_favorite)
        
        if search_dto.is_archived is not None:
            query = query.filter(Note.is_archived == search_dto.is_archived)
        
        if search_dto.is_shared is not None:
            query = query.filter(Note.is_shared == search_dto.is_shared)
        
        if search_dto.audio_file_id is not None:
            query = query.filter(Note.audio_file_id == search_dto.audio_file_id)
        
        if search_dto.tags:
            # Simple tag search (can be enhanced with array operations)
            query = query.filter(Note.tags.ilike(f"%{search_dto.tags}%"))
        
        # Date range filters
        if search_dto.from_date:
            query = query.filter(Note.created_at >= search_dto.from_date)
        
        if search_dto.to_date:
            query = query.filter(Note.created_at <= search_dto.to_date)
        
        # Apply ordering
        if search_dto.order.value == "ASC":
            query = query.order_by(Note.created_at.asc())
        else:
            query = query.order_by(Note.created_at.desc())
        
        # Apply pagination and return
        return PaginationHelper.paginate_query(
            query=query,
            page_options=search_dto,
            response_model=NoteSchema
        )
```

### Example: Audio Service
**Location**: Update `app/services/audio_service.py`

```python
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from app.models.audio_model import Audio
from app.schemas.audio import AudioSearchDto, AudioFile as AudioFileSchema
from app.schemas.pagination import PageDto
from app.common.pagination_utils import PaginationHelper

class AudioService:
    
    async def search_audio_files(
        self,
        db: Session,
        user_id: int,
        search_dto: AudioSearchDto
    ) -> PageDto[AudioFileSchema]:
        """
        Search and filter audio files with pagination
        
        Args:
            db: Database session
            user_id: Current user ID
            search_dto: Search filters and pagination options
            
        Returns:
            PageDto with audio files and pagination metadata
        """
        # Base query
        query = db.query(Audio).filter(Audio.user_id == user_id)
        
        # Apply general search
        if search_dto.search:
            search_term = f"%{search_dto.search}%"
            query = query.filter(Audio.filename.ilike(search_term))
        
        # Apply specific filters
        if search_dto.status:
            query = query.filter(Audio.status == search_dto.status)
        
        if search_dto.from_date:
            query = query.filter(Audio.created_at >= search_dto.from_date)
        
        if search_dto.to_date:
            query = query.filter(Audio.created_at <= search_dto.to_date)
        
        if search_dto.min_duration is not None:
            query = query.filter(Audio.duration >= search_dto.min_duration)
        
        if search_dto.max_duration is not None:
            query = query.filter(Audio.duration <= search_dto.max_duration)
        
        if search_dto.has_transcript is not None:
            if search_dto.has_transcript:
                query = query.filter(Audio.transcript.isnot(None))
            else:
                query = query.filter(Audio.transcript.is_(None))
        
        # Apply ordering
        if search_dto.order.value == "ASC":
            query = query.order_by(Audio.created_at.asc())
        else:
            query = query.order_by(Audio.created_at.desc())
        
        # Apply pagination
        return PaginationHelper.paginate_query(
            query=query,
            page_options=search_dto,
            response_model=AudioFileSchema
        )
```

## 5. Update Response Common

### Standardize Response Wrapper
**Location**: Update `app/common/response_common.py`

```python
from app.schemas.pagination import ResponseCommon
from typing import TypeVar, Optional

T = TypeVar('T')

def create_success_response(
    data: Optional[T] = None,
    message: str = "SUCCESSFULLY",
    code: int = 200
) -> ResponseCommon[T]:
    """Create a successful response"""
    return ResponseCommon(
        code=code,
        success=True,
        message=message,
        data=data
    )

def create_error_response(
    message: str,
    code: int = 400,
    data: Optional[T] = None
) -> ResponseCommon[T]:
    """Create an error response"""
    return ResponseCommon(
        code=code,
        success=False,
        message=message,
        data=data
    )
```

## 6. Client Request Examples

### JavaScript/TypeScript Example

```typescript
// Search notes
const searchNotes = async () => {
  const response = await fetch('/api/v1/notes/search', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify({
      page: 1,
      page_size: 10,
      order: 'DESC',
      search: 'meeting',
      category: 'work',
      priority: 'high',
      is_favorite: true,
      from_date: '2025-01-01T00:00:00',
      to_date: '2025-12-31T23:59:59'
    })
  });
  
  const result = await response.json();
  
  // Access data
  console.log(result.data.data); // Array of notes
  console.log(result.data.meta); // Pagination metadata
  
  // Use metadata
  const { page, page_size, item_count, page_count, has_next_page } = result.data.meta;
};

// Dropdown mode (get all items)
const getAllCategories = async () => {
  const response = await fetch('/api/v1/notes/search', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify({
      is_dropdown: true // Returns all items without pagination
    })
  });
  
  const result = await response.json();
  return result.data.data; // All items
};
```

### Python Client Example

```python
import requests

def search_notes(token: str):
    response = requests.post(
        'http://localhost:8000/api/v1/notes/search',
        headers={'Authorization': f'Bearer {token}'},
        json={
            'page': 1,
            'page_size': 10,
            'order': 'DESC',
            'search': 'meeting',
            'category': 'work',
            'is_favorite': True
        }
    )
    
    result = response.json()
    
    # Access data
    notes = result['data']['data']
    meta = result['data']['meta']
    
    print(f"Total items: {meta['item_count']}")
    print(f"Current page: {meta['page']} of {meta['page_count']}")
    
    return notes
```

## 7. Migration Strategy

### Step-by-Step Migration

1. **Create Base Schemas** (Week 1)
   - Create `app/schemas/pagination.py`
   - Create `app/common/pagination_utils.py`
   - Update `app/common/response_common.py`

2. **Update Notes Endpoints** (Week 1)
   - Create `NoteSearchDto` in `app/schemas/note.py`
   - Add `/notes/search` endpoint
   - Update `note_service.py` with `search_notes()` method
   - Test thoroughly
   - Keep old `/notes` endpoint for backwards compatibility (mark as deprecated)

3. **Update Audio Endpoints** (Week 2)
   - Create `AudioSearchDto` in `app/schemas/audio.py`
   - Add `/audio/search` endpoint
   - Update `audio_service.py` with `search_audio_files()` method
   - Test thoroughly
   - Keep old `/audio/files` endpoint (mark as deprecated)

4. **Update Other Endpoints** (Week 2-3)
   - Apply same pattern to:
     - Tasks
     - Transcripts
     - Chatbot conversations
     - Any other list endpoints

5. **Deprecation & Cleanup** (Week 4)
   - Notify clients about deprecated endpoints
   - Set deprecation timeline (e.g., 30 days)
   - Remove old endpoints after migration period

### Backwards Compatibility

Keep old endpoints during migration:

```python
# Old endpoint (deprecated)
@router.get("/", response_model=NotesListResponse, deprecated=True)
async def get_notes_legacy(
    skip: int = Query(0),
    limit: int = Query(10),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    ⚠️ DEPRECATED: Use POST /notes/search instead
    """
    # Map to new search method
    search_dto = NoteSearchDto(
        page=(skip // limit) + 1,
        page_size=limit
    )
    paginated = await note_service.search_notes(db, current_user.id, search_dto)
    
    # Convert to old response format
    return NotesListResponse(
        notes=paginated.data,
        total_count=paginated.meta.item_count,
        page=paginated.meta.page,
        page_size=paginated.meta.page_size
    )

# New endpoint
@router.post("/search", response_model=ResponseCommon[PageDto[Note]])
async def search_notes(...):
    ...
```

## 8. Testing

### Unit Test Example

```python
# tests/test_note_service.py
import pytest
from app.services.note_service import NoteService
from app.schemas.note import NoteSearchDto

@pytest.mark.asyncio
async def test_search_notes_with_filters(db_session, test_user, sample_notes):
    """Test note search with multiple filters"""
    service = NoteService()
    
    search_dto = NoteSearchDto(
        page=1,
        page_size=10,
        search="meeting",
        category="work",
        is_favorite=True
    )
    
    result = await service.search_notes(
        db=db_session,
        user_id=test_user.id,
        search_dto=search_dto
    )
    
    assert result.meta.page == 1
    assert result.meta.page_size == 10
    assert len(result.data) <= 10
    assert all(note.category == "work" for note in result.data)
    assert all(note.is_favorite for note in result.data)

@pytest.mark.asyncio
async def test_dropdown_mode(db_session, test_user, sample_notes):
    """Test dropdown mode returns all items"""
    service = NoteService()
    
    search_dto = NoteSearchDto(is_dropdown=True)
    
    result = await service.search_notes(
        db=db_session,
        user_id=test_user.id,
        search_dto=search_dto
    )
    
    assert result.meta.page == 1
    assert result.meta.page_count == 1
    assert len(result.data) == result.meta.item_count
```

### Integration Test Example

```python
# tests/test_note_endpoints.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_search_notes_endpoint(client: AsyncClient, auth_headers):
    """Test notes search endpoint"""
    response = await client.post(
        "/api/v1/notes/search",
        json={
            "page": 1,
            "page_size": 10,
            "order": "DESC",
            "category": "work"
        },
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["success"] is True
    assert data["code"] == 200
    assert "data" in data
    assert "data" in data["data"]
    assert "meta" in data["data"]
    
    meta = data["data"]["meta"]
    assert "page" in meta
    assert "page_size" in meta
    assert "item_count" in meta
    assert "page_count" in meta
    assert "has_previous_page" in meta
    assert "has_next_page" in meta
```

## 9. API Documentation

FastAPI will automatically generate OpenAPI documentation with the new structure. Access at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### Example OpenAPI Schema

```yaml
/api/v1/notes/search:
  post:
    summary: Search Notes
    requestBody:
      content:
        application/json:
          schema:
            type: object
            properties:
              page:
                type: integer
                default: 1
              page_size:
                type: integer
                default: 10
              order:
                type: string
                enum: [ASC, DESC]
              search:
                type: string
              category:
                type: string
              is_favorite:
                type: boolean
    responses:
      200:
        content:
          application/json:
            schema:
              type: object
              properties:
                code:
                  type: integer
                success:
                  type: boolean
                message:
                  type: string
                data:
                  type: object
                  properties:
                    data:
                      type: array
                      items:
                        $ref: '#/components/schemas/Note'
                    meta:
                      type: object
                      properties:
                        page: integer
                        page_size: integer
                        item_count: integer
                        page_count: integer
                        has_previous_page: boolean
                        has_next_page: boolean
```

## 10. Best Practices

### DO:
- ✅ Always use `page_size` (not `pageSize`) for consistency
- ✅ Validate page and page_size with Field constraints
- ✅ Use POST for search endpoints (supports complex payloads)
- ✅ Include comprehensive filters in DTOs
- ✅ Provide example payloads in schema Config
- ✅ Use Generic types for reusable response wrappers
- ✅ Apply proper ordering to queries
- ✅ Include search in multiple fields with OR conditions
- ✅ Handle dropdown mode for select inputs

### DON'T:
- ❌ Mix snake_case and camelCase in request/response
- ❌ Use GET requests for complex filtering
- ❌ Forget to apply user_id filter for security
- ❌ Return unfiltered queries without pagination
- ❌ Skip metadata in paginated responses
- ❌ Hard-code page_size limits without validation

## Summary

This standardization provides:
- ✅ Consistent pagination across all endpoints
- ✅ Rich filtering capabilities
- ✅ Standardized response structure
- ✅ Type-safe schemas with Pydantic
- ✅ Reusable helper utilities
- ✅ Better developer experience
- ✅ Automatic OpenAPI documentation
- ✅ Easy client-side implementation

Following this pattern ensures a professional, scalable API that's easy to use and maintain.
