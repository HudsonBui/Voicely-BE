# Active Tasks List Endpoint Implementation Guide

## Overview
This guide provides complete instructions for implementing a paginated endpoint to retrieve all currently running (active) tasks for a user. The implementation follows the project's pagination standardization pattern and best practices.

## Goal
Create `POST /api/v1/tasks/search` endpoint that:
- ✅ Returns paginated list of user's tasks
- ✅ Supports filtering by status, task_type, and date ranges
- ✅ Follows project's pagination standard (PageOptionsDto, PageDto, ResponseCommon)
- ✅ Provides rich metadata for client-side pagination
- ✅ Allows searching across multiple fields

## Task Status Values

Tasks in the system go through the following status lifecycle:
- `pending` - Task created, not yet queued
- `queued` - Task queued to ARQ worker
- `processing` - Worker is actively processing
- `completed` - Task finished successfully
- `failed` - Task encountered an error

**Active Tasks** are those with status: `pending`, `queued`, or `processing`

## Implementation Steps

### Step 1: Create Task Search DTO

**Location**: Update `app/schemas/task_job.py`

Add the following schemas:

```python
from pydantic import BaseModel, Field
from typing import Optional, Any
from datetime import datetime
from app.schemas.pagination import PageOptionsDto

class TaskJobResponse(BaseModel):
    """Individual task job response"""
    job_id: str
    task_type: str
    status: str
    result: Optional[Any] = None
    error_message: Optional[str] = None
    audio_id: Optional[int] = None
    metadata: Optional[dict] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class TaskJobStatusResponse(BaseModel):
    """Task job status response (backward compatibility)"""
    job_id: str
    task_type: str
    status: str
    result: Optional[Any] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class TaskSearchDto(PageOptionsDto):
    """
    Task search/filter request payload.
    Extends base pagination with task-specific filters.
    """
    # Inherited from PageOptionsDto:
    # - page: int
    # - page_size: int
    # - order: SortOrder
    # - search: str (searches in task_type, status)
    # - is_dropdown: bool
    
    # Task-specific filters
    status: Optional[str] = Field(
        default=None, 
        description="Filter by status (pending, queued, processing, completed, failed)"
    )
    task_type: Optional[str] = Field(
        default=None,
        description="Filter by task type (upload, transcribe, summarize)"
    )
    audio_id: Optional[int] = Field(
        default=None,
        description="Filter by linked audio file ID"
    )
    from_date: Optional[datetime] = Field(
        default=None,
        description="Filter tasks created after this date"
    )
    to_date: Optional[datetime] = Field(
        default=None,
        description="Filter tasks created before this date"
    )
    active_only: bool = Field(
        default=False,
        description="If true, only return active tasks (pending, queued, processing)"
    )
    
    class Config:
        use_enum_values = True
        json_schema_extra = {
            "example": {
                "page": 1,
                "page_size": 10,
                "order": "DESC",
                "status": "processing",
                "task_type": "transcribe",
                "active_only": True,
                "from_date": "2025-12-01T00:00:00Z",
                "to_date": "2025-12-31T23:59:59Z"
            }
        }
```

### Step 2: Update Task Job Service

**Location**: Update `app/services/task_job_service.py`

Add the search method to `TaskJobService` class:

```python
import json
import uuid
from typing import Optional
from sqlalchemy.orm import Session, Query
from sqlalchemy import or_, and_
from fastapi import Request

from app.common.response_common import ResponseCommon
from app.models.task_job_model import TaskJob
from app.schemas.task_job import TaskSearchDto, TaskJobResponse
from app.schemas.pagination import PageDto
from app.common.pagination_utils import PaginationHelper

class TaskJobService:
    """Service for managing async task jobs."""

    # ... existing methods ...

    def search_tasks(
        self,
        db: Session,
        user_id: int,
        search_dto: TaskSearchDto
    ) -> PageDto[TaskJobResponse]:
        """
        Search and filter user's tasks with pagination
        
        Args:
            db: Database session
            user_id: Current user ID
            search_dto: Search filters and pagination options
            
        Returns:
            PageDto with tasks and pagination metadata
        """
        # Base query - filter by user
        query: Query = db.query(TaskJob).filter(TaskJob.user_id == user_id)
        
        # Apply general search (if provided)
        if search_dto.search:
            search_term = f"%{search_dto.search}%"
            query = query.filter(
                or_(
                    TaskJob.task_type.ilike(search_term),
                    TaskJob.status.ilike(search_term),
                    TaskJob.id.ilike(search_term)
                )
            )
        
        # Apply specific filters
        if search_dto.status is not None:
            query = query.filter(TaskJob.status == search_dto.status)
        
        if search_dto.task_type is not None:
            query = query.filter(TaskJob.task_type == search_dto.task_type)
        
        if search_dto.audio_id is not None:
            query = query.filter(TaskJob.audio_id == search_dto.audio_id)
        
        # Active tasks filter (pending, queued, processing)
        if search_dto.active_only:
            query = query.filter(
                TaskJob.status.in_(['pending', 'queued', 'processing'])
            )
        
        # Date range filters
        if search_dto.from_date:
            query = query.filter(TaskJob.created_at >= search_dto.from_date)
        
        if search_dto.to_date:
            query = query.filter(TaskJob.created_at <= search_dto.to_date)
        
        # Apply ordering
        if search_dto.order.value == "ASC":
            query = query.order_by(TaskJob.created_at.asc())
        else:
            query = query.order_by(TaskJob.created_at.desc())
        
        # Apply pagination and return
        return PaginationHelper.paginate_query(
            query=query,
            page_options=search_dto,
            response_model=TaskJobResponse
        )

    def get_job_status(self, db: Session, job_id: str, user_id: int) -> ResponseCommon:
        """Get job status by job_id."""
        try:
            job = (
                db.query(TaskJob)
                .filter(TaskJob.id == job_id, TaskJob.user_id == user_id)
                .first()
            )

            if not job:
                return ResponseCommon.error_response(message="Job not found", code=404)

            # Parse result from JSON string to dict if present
            result_data = None
            if job.result:
                try:
                    result_data = json.loads(job.result)
                except (json.JSONDecodeError, TypeError):
                    # If parsing fails, return as-is
                    result_data = job.result

            return ResponseCommon.success_response(
                data={
                    "job_id": job.id,
                    "task_type": job.task_type,
                    "status": job.status,
                    "result": result_data,
                    "error_message": job.error_message,
                    "created_at": job.created_at,
                    "updated_at": job.updated_at,
                },
                message="Job status retrieved successfully",
            )

        except Exception as exc:
            return ResponseCommon.error_response(
                message=f"Failed to get job status: {str(exc)}",
                code=500,
            )

    async def create_and_queue_job(
        self,
        request: Request,
        db: Session,
        task_type: str,
        task_function: str,
        user_id: int,
        audio_id: Optional[int] = None,
        metadata: Optional[dict] = None,
        **kwargs,
    ) -> ResponseCommon:
        """Create a task job record and enqueue it to the ARQ worker."""
        # ... existing implementation ...
```

### Step 3: Create Search Endpoint

**Location**: Update `app/api/v1/endpoints/task_endpoints.py`

Add the search endpoint:

```python
from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session
import json

from app.api.deps import get_db, get_current_active_user
from app.models import User
from app.services.task_job_service import task_job_service
from app.schemas.task_job import TaskSearchDto, TaskJobResponse
from app.schemas.pagination import ResponseCommon, PageDto
from app.common.pagination_utils import PaginationHelper

router = APIRouter()


@router.post("/search", response_model=ResponseCommon[PageDto[TaskJobResponse]])
async def search_tasks(
    search_dto: TaskSearchDto,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Search and filter user's tasks with pagination.
    
    This endpoint allows you to retrieve and filter task jobs with the following options:
    
    **Pagination:**
    - `page`: Current page number (default: 1)
    - `page_size`: Items per page (default: 10, max: 100)
    - `order`: Sort order - ASC or DESC (default: DESC)
    
    **Search:**
    - `search`: Search across task_type, status, and job_id
    
    **Filters:**
    - `status`: Filter by task status (pending, queued, processing, completed, failed)
    - `task_type`: Filter by task type (upload, transcribe, summarize)
    - `audio_id`: Filter by linked audio file ID
    - `from_date`: Filter tasks created after this date
    - `to_date`: Filter tasks created before this date
    - `active_only`: If true, only return active tasks (pending, queued, processing)
    
    **Response:**
    Returns paginated list of tasks with metadata including total count, page count, etc.
    
    **Example Request:**
    ```json
    {
        "page": 1,
        "page_size": 20,
        "order": "DESC",
        "active_only": true,
        "task_type": "transcribe",
        "status": "processing"
    }
    ```
    """
    paginated_tasks = task_job_service.search_tasks(
        db=db,
        user_id=current_user.id,
        search_dto=search_dto
    )
    
    return PaginationHelper.create_response(
        paginated_data=paginated_tasks,
        message="Tasks retrieved successfully"
    )


@router.get("/status/{job_id}")
async def get_task_status(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get the status of a specific async task job.
    
    Returns detailed information about a single task including:
    - Current status
    - Result data (if completed)
    - Error message (if failed)
    - Timestamps
    """
    result = task_job_service.get_job_status(
        db=db,
        job_id=job_id,
        user_id=current_user.id,
    )

    return Response(
        content=json.dumps(result.to_json()),
        status_code=result.code,
        media_type="application/json",
    )
```

### Step 4: Update TaskJobResponse Model

**Location**: Update `app/schemas/task_job.py` (ensure TaskJobResponse includes all fields)

The `TaskJobResponse` schema needs to map all fields from the `TaskJob` model:

```python
class TaskJobResponse(BaseModel):
    """Individual task job response"""
    job_id: str = Field(..., alias="id")  # Map database 'id' to 'job_id'
    task_type: str
    status: str
    result: Optional[Any] = None
    error_message: Optional[str] = None
    audio_id: Optional[int] = None
    metadata: Optional[dict] = Field(None, alias="metadata_json")  # Map metadata_json
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        populate_by_name = True  # Allow using both 'id' and 'job_id'
```

**Important:** Update the `PaginationHelper.paginate_query()` to handle the result parsing:

**Location**: Update `app/common/pagination_utils.py`

Modify the paginate_query method to parse JSON results:

```python
import json
from typing import List, TypeVar, Type
from sqlalchemy.orm import Query
from app.schemas.pagination import PageDto, PageMetaDto, PageOptionsDto
from math import ceil

T = TypeVar('T')

class PaginationHelper:
    """Helper class for creating paginated responses"""
    
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
                data=[PaginationHelper._convert_to_model(item, response_model) for item in items],
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
        data = [PaginationHelper._convert_to_model(item, response_model) for item in items]
        
        return PageDto(data=data, meta=meta)
    
    @staticmethod
    def _convert_to_model(item, response_model: Type[T]) -> T:
        """
        Convert SQLAlchemy model to Pydantic model with special handling
        for JSON fields like 'result' in TaskJob
        """
        # Convert to dict first
        item_dict = {column.name: getattr(item, column.name) 
                     for column in item.__table__.columns}
        
        # Special handling for 'result' field (parse JSON string)
        if 'result' in item_dict and item_dict['result']:
            try:
                item_dict['result'] = json.loads(item_dict['result'])
            except (json.JSONDecodeError, TypeError):
                pass  # Keep as string if parsing fails
        
        # Map 'id' to 'job_id' for TaskJobResponse
        if 'id' in item_dict and hasattr(response_model, '__fields__'):
            if 'job_id' in response_model.__fields__:
                item_dict['job_id'] = item_dict['id']
        
        return response_model.from_orm(item)
    
    @staticmethod
    def create_meta(
        page: int,
        page_size: int,
        total_items: int
    ) -> PageMetaDto:
        """Create pagination metadata"""
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
    def create_response(
        paginated_data: PageDto[T],
        message: str = "SUCCESSFULLY",
        code: int = 200
    ):
        """Wrap paginated data in ResponseCommon"""
        from app.schemas.pagination import ResponseCommon
        return ResponseCommon(
            code=code,
            success=True,
            message=message,
            data=paginated_data
        )
```

## API Examples

### 1. Get All Active Tasks

**Request:**
```bash
curl -X POST http://localhost:8000/api/v1/tasks/search \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "page": 1,
    "page_size": 10,
    "active_only": true
  }'
```

**Response:**
```json
{
  "code": 200,
  "success": true,
  "message": "Tasks retrieved successfully",
  "data": {
    "data": [
      {
        "job_id": "550e8400-e29b-41d4-a716-446655440000",
        "task_type": "transcribe",
        "status": "processing",
        "result": null,
        "error_message": null,
        "audio_id": 123,
        "metadata": null,
        "created_at": "2025-12-25T10:00:00Z",
        "updated_at": "2025-12-25T10:01:30Z"
      },
      {
        "job_id": "660e9511-f30c-52e5-b827-557766551111",
        "task_type": "upload",
        "status": "queued",
        "result": null,
        "error_message": null,
        "audio_id": 124,
        "metadata": null,
        "created_at": "2025-12-25T09:58:00Z",
        "updated_at": "2025-12-25T09:58:00Z"
      }
    ],
    "meta": {
      "page": 1,
      "page_size": 10,
      "item_count": 2,
      "page_count": 1,
      "has_previous_page": false,
      "has_next_page": false
    }
  }
}
```

### 2. Filter by Task Type

**Request:**
```bash
curl -X POST http://localhost:8000/api/v1/tasks/search \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "page": 1,
    "page_size": 20,
    "task_type": "transcribe",
    "order": "DESC"
  }'
```

### 3. Filter by Status

**Request:**
```bash
curl -X POST http://localhost:8000/api/v1/tasks/search \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "page": 1,
    "page_size": 10,
    "status": "completed",
    "from_date": "2025-12-01T00:00:00Z",
    "to_date": "2025-12-31T23:59:59Z"
  }'
```

### 4. Search Across Fields

**Request:**
```bash
curl -X POST http://localhost:8000/api/v1/tasks/search \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "page": 1,
    "page_size": 10,
    "search": "transcribe"
  }'
```

## Flutter Integration Example

### Dart Model

```dart
class TaskJob {
  final String jobId;
  final String taskType;
  final String status;
  final dynamic result;
  final String? errorMessage;
  final int? audioId;
  final Map<String, dynamic>? metadata;
  final DateTime createdAt;
  final DateTime updatedAt;
  
  TaskJob({
    required this.jobId,
    required this.taskType,
    required this.status,
    this.result,
    this.errorMessage,
    this.audioId,
    this.metadata,
    required this.createdAt,
    required this.updatedAt,
  });
  
  factory TaskJob.fromJson(Map<String, dynamic> json) {
    return TaskJob(
      jobId: json['job_id'],
      taskType: json['task_type'],
      status: json['status'],
      result: json['result'],
      errorMessage: json['error_message'],
      audioId: json['audio_id'],
      metadata: json['metadata'],
      createdAt: DateTime.parse(json['created_at']),
      updatedAt: DateTime.parse(json['updated_at']),
    );
  }
  
  bool get isActive => ['pending', 'queued', 'processing'].contains(status);
  bool get isCompleted => status == 'completed';
  bool get isFailed => status == 'failed';
}

class TasksPage {
  final List<TaskJob> tasks;
  final PaginationMeta meta;
  
  TasksPage({required this.tasks, required this.meta});
  
  factory TasksPage.fromJson(Map<String, dynamic> json) {
    return TasksPage(
      tasks: (json['data'] as List)
          .map((task) => TaskJob.fromJson(task))
          .toList(),
      meta: PaginationMeta.fromJson(json['meta']),
    );
  }
}

class PaginationMeta {
  final int page;
  final int pageSize;
  final int itemCount;
  final int pageCount;
  final bool hasPreviousPage;
  final bool hasNextPage;
  
  PaginationMeta({
    required this.page,
    required this.pageSize,
    required this.itemCount,
    required this.pageCount,
    required this.hasPreviousPage,
    required this.hasNextPage,
  });
  
  factory PaginationMeta.fromJson(Map<String, dynamic> json) {
    return PaginationMeta(
      page: json['page'],
      pageSize: json['page_size'],
      itemCount: json['item_count'],
      pageCount: json['page_count'],
      hasPreviousPage: json['has_previous_page'],
      hasNextPage: json['has_next_page'],
    );
  }
}
```

### Service Implementation

```dart
import 'package:dio/dio.dart';

class TaskService {
  final Dio _dio;
  final String baseUrl;
  
  TaskService(this._dio, this.baseUrl);
  
  /// Get active tasks for current user
  Future<TasksPage> getActiveTasks({
    int page = 1,
    int pageSize = 10,
  }) async {
    try {
      final response = await _dio.post(
        '$baseUrl/api/v1/tasks/search',
        data: {
          'page': page,
          'page_size': pageSize,
          'active_only': true,
          'order': 'DESC',
        },
        options: Options(
          headers: {'Authorization': 'Bearer ${await getToken()}'},
        ),
      );
      
      if (response.data['success'] == true) {
        return TasksPage.fromJson(response.data['data']);
      } else {
        throw Exception(response.data['message']);
      }
      
    } catch (e) {
      print('❌ Get active tasks failed: $e');
      rethrow;
    }
  }
  
  /// Search tasks with filters
  Future<TasksPage> searchTasks({
    int page = 1,
    int pageSize = 10,
    String? status,
    String? taskType,
    int? audioId,
    DateTime? fromDate,
    DateTime? toDate,
    bool activeOnly = false,
    String? searchQuery,
  }) async {
    try {
      Map<String, dynamic> requestData = {
        'page': page,
        'page_size': pageSize,
        'order': 'DESC',
      };
      
      if (status != null) requestData['status'] = status;
      if (taskType != null) requestData['task_type'] = taskType;
      if (audioId != null) requestData['audio_id'] = audioId;
      if (fromDate != null) requestData['from_date'] = fromDate.toIso8601String();
      if (toDate != null) requestData['to_date'] = toDate.toIso8601String();
      if (activeOnly) requestData['active_only'] = true;
      if (searchQuery != null) requestData['search'] = searchQuery;
      
      final response = await _dio.post(
        '$baseUrl/api/v1/tasks/search',
        data: requestData,
        options: Options(
          headers: {'Authorization': 'Bearer ${await getToken()}'},
        ),
      );
      
      if (response.data['success'] == true) {
        return TasksPage.fromJson(response.data['data']);
      } else {
        throw Exception(response.data['message']);
      }
      
    } catch (e) {
      print('❌ Search tasks failed: $e');
      rethrow;
    }
  }
  
  Future<String> getToken() async {
    // Get JWT token from secure storage
    return 'your_jwt_token';
  }
}
```

### UI Implementation

```dart
class ActiveTasksScreen extends StatefulWidget {
  @override
  _ActiveTasksScreenState createState() => _ActiveTasksScreenState();
}

class _ActiveTasksScreenState extends State<ActiveTasksScreen> {
  final TaskService _taskService = TaskService(Dio(), 'http://api.voicely.com');
  
  List<TaskJob> _tasks = [];
  PaginationMeta? _meta;
  bool _isLoading = false;
  int _currentPage = 1;
  
  @override
  void initState() {
    super.initState();
    _loadActiveTasks();
  }
  
  Future<void> _loadActiveTasks() async {
    setState(() => _isLoading = true);
    
    try {
      final tasksPage = await _taskService.getActiveTasks(
        page: _currentPage,
        pageSize: 20,
      );
      
      setState(() {
        _tasks = tasksPage.tasks;
        _meta = tasksPage.meta;
        _isLoading = false;
      });
      
    } catch (e) {
      setState(() => _isLoading = false);
      _showError('Failed to load tasks: $e');
    }
  }
  
  Future<void> _loadNextPage() async {
    if (_meta?.hasNextPage == true) {
      setState(() => _currentPage++);
      await _loadActiveTasks();
    }
  }
  
  Future<void> _loadPreviousPage() async {
    if (_meta?.hasPreviousPage == true) {
      setState(() => _currentPage--);
      await _loadActiveTasks();
    }
  }
  
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('Active Tasks'),
        actions: [
          IconButton(
            icon: Icon(Icons.refresh),
            onPressed: _loadActiveTasks,
          ),
        ],
      ),
      body: _isLoading
          ? Center(child: CircularProgressIndicator())
          : Column(
              children: [
                // Task list
                Expanded(
                  child: ListView.builder(
                    itemCount: _tasks.length,
                    itemBuilder: (context, index) {
                      final task = _tasks[index];
                      return _buildTaskCard(task);
                    },
                  ),
                ),
                
                // Pagination controls
                if (_meta != null) _buildPaginationControls(),
              ],
            ),
    );
  }
  
  Widget _buildTaskCard(TaskJob task) {
    return Card(
      margin: EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      child: ListTile(
        leading: _getStatusIcon(task.status),
        title: Text('${task.taskType.toUpperCase()}'),
        subtitle: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Status: ${task.status}'),
            Text('Created: ${_formatDate(task.createdAt)}'),
            if (task.errorMessage != null)
              Text(
                'Error: ${task.errorMessage}',
                style: TextStyle(color: Colors.red),
              ),
          ],
        ),
        trailing: task.isActive
            ? CircularProgressIndicator()
            : Icon(
                task.isCompleted ? Icons.check_circle : Icons.error,
                color: task.isCompleted ? Colors.green : Colors.red,
              ),
        onTap: () {
          // Navigate to task details
        },
      ),
    );
  }
  
  Widget _buildPaginationControls() {
    return Container(
      padding: EdgeInsets.all(16),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          ElevatedButton(
            onPressed: _meta!.hasPreviousPage ? _loadPreviousPage : null,
            child: Text('Previous'),
          ),
          Text('Page ${_meta!.page} of ${_meta!.pageCount}'),
          ElevatedButton(
            onPressed: _meta!.hasNextPage ? _loadNextPage : null,
            child: Text('Next'),
          ),
        ],
      ),
    );
  }
  
  Widget _getStatusIcon(String status) {
    switch (status) {
      case 'pending':
        return Icon(Icons.schedule, color: Colors.grey);
      case 'queued':
        return Icon(Icons.hourglass_empty, color: Colors.orange);
      case 'processing':
        return Icon(Icons.autorenew, color: Colors.blue);
      case 'completed':
        return Icon(Icons.check_circle, color: Colors.green);
      case 'failed':
        return Icon(Icons.error, color: Colors.red);
      default:
        return Icon(Icons.help_outline);
    }
  }
  
  String _formatDate(DateTime date) {
    return '${date.year}-${date.month.toString().padLeft(2, '0')}-${date.day.toString().padLeft(2, '0')} '
           '${date.hour.toString().padLeft(2, '0')}:${date.minute.toString().padLeft(2, '0')}';
  }
  
  void _showError(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(message), backgroundColor: Colors.red),
    );
  }
}
```

## Testing

### Unit Test Example

```python
# tests/test_task_service.py
import pytest
from app.services.task_job_service import task_job_service
from app.schemas.task_job import TaskSearchDto

@pytest.mark.asyncio
async def test_search_active_tasks(db_session, test_user, sample_tasks):
    """Test searching for active tasks"""
    search_dto = TaskSearchDto(
        page=1,
        page_size=10,
        active_only=True
    )
    
    result = task_job_service.search_tasks(
        db=db_session,
        user_id=test_user.id,
        search_dto=search_dto
    )
    
    assert result.meta.page == 1
    assert result.meta.page_size == 10
    assert all(task.status in ['pending', 'queued', 'processing'] for task in result.data)

@pytest.mark.asyncio
async def test_filter_by_task_type(db_session, test_user, sample_tasks):
    """Test filtering tasks by type"""
    search_dto = TaskSearchDto(
        page=1,
        page_size=10,
        task_type="transcribe"
    )
    
    result = task_job_service.search_tasks(
        db=db_session,
        user_id=test_user.id,
        search_dto=search_dto
    )
    
    assert all(task.task_type == "transcribe" for task in result.data)
```

### Integration Test Example

```python
# tests/test_task_endpoints.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_search_tasks_endpoint(client: AsyncClient, auth_headers):
    """Test tasks search endpoint"""
    response = await client.post(
        "/api/v1/tasks/search",
        json={
            "page": 1,
            "page_size": 10,
            "active_only": true
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
```

## Summary

This implementation provides:

- ✅ **Paginated task listing** following project standards
- ✅ **Rich filtering options** (status, type, date, active_only)
- ✅ **Consistent API structure** with ResponseCommon wrapper
- ✅ **Automatic result parsing** (JSON string → object)
- ✅ **Complete Flutter integration** with models and UI
- ✅ **Backward compatibility** with existing `/status/{job_id}` endpoint
- ✅ **Testable implementation** with unit and integration tests

### Key Features

1. **Active Tasks Filter**: Quickly get only running tasks with `active_only: true`
2. **Flexible Filtering**: Filter by status, type, date range, audio_id
3. **General Search**: Search across task_type, status, and job_id
4. **Pagination Metadata**: Full metadata for building pagination UI
5. **Parsed Results**: Result field automatically parsed from JSON string to object

### Usage Recommendations

- Use `active_only: true` for dashboard/monitoring screens
- Filter by `task_type` when showing specific workflow steps
- Use date filters for historical analysis and reporting
- Implement auto-refresh for active tasks screens (every 2-3 seconds)
- Show notification when active tasks complete
