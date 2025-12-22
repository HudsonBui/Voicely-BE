# Async Task Processing Implementation Guide

## Overview

This guide provides step-by-step instructions for implementing asynchronous task processing in the Voicely-BE backend using **FastAPI**, **ARQ** (Async Redis Queue), **Redis**, and **PostgreSQL**. This architecture enables long-running tasks (audio processing, transcription, summarization) to be handled in background workers without blocking API responses.

## Architecture

The system consists of three main components:

1. **FastAPI Application**: Receives HTTP requests from clients and returns job IDs immediately
2. **ARQ Worker**: Processes heavy tasks asynchronously in the background
3. **Redis**: Serves as the message broker and task queue
4. **PostgreSQL**: Stores job status, results, and application data

### Why This Architecture?

- **No Connection Blocking**: API responds immediately with a job ID, allowing the client to close the connection
- **Isolated Processing**: Heavy tasks run in separate worker processes without impacting API performance
- **Data Safety**: Job status is persisted in PostgreSQL; clients can retrieve results even after app restarts
- **Scalability**: Workers can be scaled independently from the API servers

## Implementation Steps

### Step 1: Add Required Dependencies

Add the following packages to your `requirements.txt`:

```txt
arq==0.26.0
redis==5.0.0
```

Then install:

```bash
pip install arq redis
```

### Step 2: Update Docker Compose Files

#### Development Environment (`docker-compose.yml`)

Add Redis service and configure environment variables:

```yaml
services: 
  app:
    build: .
    container_name: voicely_app
    ports:
      - "8000:8000"
    volumes:
      - .:/code
      - dev-static-data:/vol/web
    env_file:
      - .env
    depends_on:
      - db
      - redis
    environment:
      DB_HOST: db
      DB_NAME: ${POSTGRES_DB}
      DB_USER: ${POSTGRES_USER}
      DB_PASSWORD: ${POSTGRES_PASSWORD}
      REDIS_HOST: redis
      REDIS_PORT: 6379
      GOOGLE_APPLICATION_CREDENTIALS: /code/voicely-be-fb9f1d6b9381.json
    command: >
      uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

  worker:
    build: .
    container_name: voicely_worker
    volumes:
      - .:/code
      - dev-static-data:/vol/web
    env_file:
      - .env
    depends_on:
      - db
      - redis
    environment:
      DB_HOST: db
      DB_NAME: ${POSTGRES_DB}
      DB_USER: ${POSTGRES_USER}
      DB_PASSWORD: ${POSTGRES_PASSWORD}
      REDIS_HOST: redis
      REDIS_PORT: 6379
      GOOGLE_APPLICATION_CREDENTIALS: /code/voicely-be-fb9f1d6b9381.json
    command: >
      arq app.worker.WorkerSettings

  db:
    image: pgvector/pgvector:pg15
    container_name: voicely_db
    restart: always
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    container_name: voicely_redis
    restart: always
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
    command: redis-server --appendonly yes

volumes:
  pgdata:
  dev-static-data:
  redis-data:
```

#### Production Environment (`docker-compose.prod.yml`)

```yaml
services: 
  app:
    build: .
    container_name: voicely_app
    ports:
      - "8802:8800"
    volumes:
      - ./voicely-be-fb9f1d6b9381.json:/code/voicely-be-fb9f1d6b9381.json:ro
      - uploads-data:/code/uploads
    env_file:
      - .env
    depends_on:
      - db
      - redis
    environment:
      DB_HOST: db
      DB_NAME: ${POSTGRES_DB}
      DB_USER: ${POSTGRES_USER}
      DB_PASSWORD: ${POSTGRES_PASSWORD}
      REDIS_HOST: redis
      REDIS_PORT: 6379
      GOOGLE_APPLICATION_CREDENTIALS: /code/voicely-be-fb9f1d6b9381.json
    restart: unless-stopped
    command: >
      uvicorn app.main:app --host 0.0.0.0 --port 8800

  worker:
    build: .
    container_name: voicely_worker
    volumes:
      - ./voicely-be-fb9f1d6b9381.json:/code/voicely-be-fb9f1d6b9381.json:ro
      - uploads-data:/code/uploads
    env_file:
      - .env
    depends_on:
      - db
      - redis
    environment:
      DB_HOST: db
      DB_NAME: ${POSTGRES_DB}
      DB_USER: ${POSTGRES_USER}
      DB_PASSWORD: ${POSTGRES_PASSWORD}
      REDIS_HOST: redis
      REDIS_PORT: 6379
      GOOGLE_APPLICATION_CREDENTIALS: /code/voicely-be-fb9f1d6b9381.json
    restart: unless-stopped
    command: >
      arq app.worker.WorkerSettings

  db:
    image: pgvector/pgvector:pg15
    container_name: voicely_db
    restart: unless-stopped
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    container_name: voicely_redis
    restart: unless-stopped
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
    command: redis-server --appendonly yes

volumes:
  pgdata:
  uploads-data:
  redis-data:
```

### Step 3: Create Database Models for Job Tracking

Create a new migration to add the job tracking table:

```bash
alembic revision -m "add_task_jobs_table"
```

Add the following to the generated migration file:

```python
"""add_task_jobs_table

Revision ID: xxxxx
Revises: previous_revision
Create Date: 2024-xx-xx
"""
from alembic import op
import sqlalchemy as sa

def upgrade() -> None:
    op.create_table(
        'task_jobs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('task_type', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False, server_default='pending'),
        sa.Column('result', sa.Text(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('audio_id', sa.Integer(), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['audio_id'], ['audio_files.id'], ondelete='CASCADE'),
    )
    op.create_index('idx_task_jobs_user_id', 'task_jobs', ['user_id'])
    op.create_index('idx_task_jobs_status', 'task_jobs', ['status'])
    op.create_index('idx_task_jobs_task_type', 'task_jobs', ['task_type'])

def downgrade() -> None:
    op.drop_index('idx_task_jobs_task_type')
    op.drop_index('idx_task_jobs_status')
    op.drop_index('idx_task_jobs_user_id')
    op.drop_table('task_jobs')
```

Create the model file `app/models/task_job_model.py`:

```python
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.session import Base

class TaskJob(Base):
    __tablename__ = "task_jobs"

    id = Column(String, primary_key=True, index=True)
    task_type = Column(String, nullable=False, index=True)  # 'upload', 'transcribe', 'summarize'
    status = Column(String, default="pending", index=True)  # pending, queued, processing, completed, failed
    result = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    audio_id = Column(Integer, ForeignKey("audio_files.id", ondelete="CASCADE"), nullable=True)
    metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="task_jobs")
    audio_file = relationship("AudioFile", back_populates="task_jobs")
```

Update `app/models/__init__.py` to include the new model:

```python
from app.models.task_job_model import TaskJob
```

### Step 4: Create Redis Configuration

Create `app/core/redis_config.py`:

```python
import os
from arq.connections import RedisSettings

def get_redis_settings() -> RedisSettings:
    """Get Redis settings from environment variables"""
    return RedisSettings(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", "6379")),
        database=int(os.getenv("REDIS_DB", "0"))
    )

REDIS_SETTINGS = get_redis_settings()
```

### Step 5: Create Worker Implementation

Create `app/worker.py` (main worker file):

```python
import asyncio
import logging
from arq.connections import RedisSettings
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.task_job_model import TaskJob
from app.core.redis_config import REDIS_SETTINGS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("arq.worker")


async def handle_audio_upload(ctx, job_id: str, file_info: dict, user_id: int):
    """
    Background task for processing uploaded audio files.
    This can include format conversion, quality checks, duration calculation, etc.
    """
    db: Session = SessionLocal()
    try:
        logger.info(f"Starting audio upload processing for job: {job_id}")
        
        # Update status to processing
        job_record = db.query(TaskJob).filter(TaskJob.id == job_id).first()
        if not job_record:
            logger.error(f"Job {job_id} not found in database")
            return
        
        job_record.status = "processing"
        db.commit()

        # Simulate heavy processing (replace with actual logic)
        # Example: format conversion, audio analysis, etc.
        await asyncio.sleep(5)  # Placeholder for actual processing
        
        result = {
            "file_name": file_info.get("file_name"),
            "duration": file_info.get("duration", 0),
            "format": file_info.get("format"),
            "processed": True
        }

        # Update to completed
        job_record.status = "completed"
        job_record.result = str(result)
        db.commit()
        
        logger.info(f"Completed audio upload processing for job: {job_id}")

    except Exception as e:
        logger.error(f"Error processing audio upload job {job_id}: {str(e)}")
        if job_record:
            job_record.status = "failed"
            job_record.error_message = str(e)
            db.commit()
    finally:
        db.close()


async def handle_transcription(ctx, job_id: str, audio_id: int, language_code: str, user_id: int):
    """
    Background task for transcribing audio files.
    This is a long-running task that calls Google Speech API or similar services.
    """
    db: Session = SessionLocal()
    try:
        logger.info(f"Starting transcription for job: {job_id}, audio_id: {audio_id}")
        
        # Update status to processing
        job_record = db.query(TaskJob).filter(TaskJob.id == job_id).first()
        if not job_record:
            logger.error(f"Job {job_id} not found in database")
            return
        
        job_record.status = "processing"
        db.commit()

        # Import transcription service
        from app.services.transcript_service import transcript_service
        from app.services.audio_service import audio_service
        
        # Get audio file
        audio_file_response = audio_service.get_audio_file_by_id(
            db=db,
            audio_id=audio_id,
            user_id=user_id
        )
        
        if not audio_file_response.success:
            raise Exception(f"Audio file not found: {audio_id}")
        
        audio_file = audio_file_response.data
        
        # Perform transcription (this is the heavy operation)
        transcription_response = transcript_service.transcribe_audio(
            audio_file=audio_file,
            language_code=language_code
        )
        
        if not transcription_response.success:
            raise Exception(transcription_response.message)
        
        # Update audio file with transcription
        audio_file.transcription = transcription_response.data.get("transcript")
        audio_file.confidence_score = transcription_response.data.get("confidence", 0.0)
        audio_file.status = "completed"
        db.commit()

        # Update job status
        job_record.status = "completed"
        job_record.result = transcription_response.data.get("transcript")
        db.commit()
        
        logger.info(f"Completed transcription for job: {job_id}")

    except Exception as e:
        logger.error(f"Error processing transcription job {job_id}: {str(e)}")
        if job_record:
            job_record.status = "failed"
            job_record.error_message = str(e)
            db.commit()
    finally:
        db.close()


async def handle_summarization(ctx, job_id: str, audio_id: int, user_id: int):
    """
    Background task for summarizing transcripts.
    Uses AI models to generate summaries from transcribed text.
    """
    db: Session = SessionLocal()
    try:
        logger.info(f"Starting summarization for job: {job_id}, audio_id: {audio_id}")
        
        # Update status to processing
        job_record = db.query(TaskJob).filter(TaskJob.id == job_id).first()
        if not job_record:
            logger.error(f"Job {job_id} not found in database")
            return
        
        job_record.status = "processing"
        db.commit()

        # Import note service
        from app.services.note_service import summarize_audio_transcript
        
        # Perform summarization (this is the heavy operation)
        summary_response = summarize_audio_transcript(
            db=db,
            user_id=user_id,
            audio_id=audio_id
        )
        
        if not summary_response.success:
            raise Exception(summary_response.message)
        
        # Update job status
        job_record.status = "completed"
        job_record.result = str(summary_response.data)
        db.commit()
        
        logger.info(f"Completed summarization for job: {job_id}")

    except Exception as e:
        logger.error(f"Error processing summarization job {job_id}: {str(e)}")
        if job_record:
            job_record.status = "failed"
            job_record.error_message = str(e)
            db.commit()
    finally:
        db.close()


class WorkerSettings:
    """ARQ Worker Configuration"""
    functions = [
        handle_audio_upload,
        handle_transcription,
        handle_summarization,
    ]
    redis_settings = REDIS_SETTINGS
    max_jobs = 10  # Maximum concurrent jobs
    job_timeout = 3600  # 1 hour timeout for long-running tasks
    keep_result = 3600  # Keep job results for 1 hour
```

### Step 6: Create Task Job Schemas

Create `app/schemas/task_job.py`:

```python
from pydantic import BaseModel
from typing import Optional, Any
from datetime import datetime

class TaskJobResponse(BaseModel):
    job_id: str
    task_type: str
    status: str
    message: str

    class Config:
        from_attributes = True


class TaskJobStatusResponse(BaseModel):
    job_id: str
    task_type: str
    status: str
    result: Optional[Any] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
```

### Step 7: Update FastAPI Main App

Update `app/main.py` to initialize Redis pool:

```python
from fastapi import FastAPI
from arq import create_pool
from app.core.redis_config import REDIS_SETTINGS
from app.api.v1.router import api_router

app = FastAPI(title="Voicely API")

# Initialize ARQ Redis pool on startup
@app.on_event("startup")
async def startup():
    app.state.arq_pool = await create_pool(REDIS_SETTINGS)

@app.on_event("shutdown")
async def shutdown():
    if hasattr(app.state, "arq_pool"):
        await app.state.arq_pool.close()

app.include_router(api_router, prefix="/api/v1")
```

### Step 8: Create Task Job Service

Create `app/services/task_job_service.py`:

```python
import uuid
from sqlalchemy.orm import Session
from typing import Optional
from fastapi import Request
from app.models.task_job_model import TaskJob
from app.common.response_common import ResponseCommon
from app.schemas.task_job import TaskJobResponse, TaskJobStatusResponse


class TaskJobService:
    """Service for managing async task jobs"""
    
    async def create_and_queue_job(
        self,
        request: Request,
        db: Session,
        task_type: str,
        task_function: str,
        user_id: int,
        audio_id: Optional[int] = None,
        metadata: Optional[dict] = None,
        **kwargs
    ) -> ResponseCommon:
        """
        Create a task job record and enqueue it to ARQ worker
        
        Args:
            request: FastAPI request object (to access arq_pool)
            db: Database session
            task_type: Type of task (upload, transcribe, summarize)
            task_function: ARQ function name to call
            user_id: User ID
            audio_id: Optional audio file ID
            metadata: Optional metadata dict
            **kwargs: Additional arguments to pass to the task function
        """
        try:
            job_id = str(uuid.uuid4())
            
            # Create job record in database
            new_job = TaskJob(
                id=job_id,
                task_type=task_type,
                status="pending",
                user_id=user_id,
                audio_id=audio_id,
                metadata=metadata
            )
            db.add(new_job)
            db.commit()
            db.refresh(new_job)

            # Enqueue job to ARQ
            await request.app.state.arq_pool.enqueue_job(
                task_function,
                job_id,
                user_id=user_id,
                **kwargs,
                _job_id=job_id
            )
            
            # Update status to queued
            new_job.status = "queued"
            db.commit()

            return ResponseCommon.success_response(
                data={
                    "job_id": job_id,
                    "task_type": task_type,
                    "status": "queued"
                },
                message=f"Task queued successfully. Use job_id to check status."
            )

        except Exception as e:
            return ResponseCommon.error_response(
                message=f"Failed to create task job: {str(e)}",
                code=500
            )

    def get_job_status(
        self,
        db: Session,
        job_id: str,
        user_id: int
    ) -> ResponseCommon:
        """Get job status by job_id"""
        try:
            job = db.query(TaskJob).filter(
                TaskJob.id == job_id,
                TaskJob.user_id == user_id
            ).first()
            
            if not job:
                return ResponseCommon.error_response(
                    message="Job not found",
                    code=404
                )
            
            return ResponseCommon.success_response(
                data={
                    "job_id": job.id,
                    "task_type": job.task_type,
                    "status": job.status,
                    "result": job.result,
                    "error_message": job.error_message,
                    "created_at": job.created_at,
                    "updated_at": job.updated_at
                },
                message="Job status retrieved successfully"
            )

        except Exception as e:
            return ResponseCommon.error_response(
                message=f"Failed to get job status: {str(e)}",
                code=500
            )


task_job_service = TaskJobService()
```

### Step 9: Update Endpoints to Use Async Processing

#### Audio Upload Endpoint (`app/api/v1/endpoints/audio_endpoints.py`)

Add async processing option:

```python
from app.services.task_job_service import task_job_service

@router.post("/upload-async")
async def upload_audio_file_async(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Upload audio file with async processing.
    Returns job_id immediately for status polling.
    """
    # Quick validation
    validation_result = audio_service.validate_audio_file(file)
    if not validation_result.success:
        return Response(
            content=json.dumps(validation_result.to_json()),
            status_code=validation_result.code,
            media_type="application/json"
        )
    
    # Save file first
    save_result = audio_service.save_uploaded_file(file, current_user)
    if not save_result.success:
        return Response(
            content=json.dumps(save_result.to_json()),
            status_code=save_result.code,
            media_type="application/json"
        )
    
    file_info = {
        "file_path": save_result.data["file_path"],
        "file_format": save_result.data["file_format"],
        "file_name": file.filename
    }
    
    # Queue async processing
    result = await task_job_service.create_and_queue_job(
        request=request,
        db=db,
        task_type="upload",
        task_function="handle_audio_upload",
        user_id=current_user.id,
        file_info=file_info
    )
    
    return result.to_json()
```

#### Transcription Endpoint (`app/api/v1/endpoints/transcript_endpoints.py`)

```python
from app.services.task_job_service import task_job_service

@router.post("/transcribe-async")
async def transcribe_audio_async(
    request: Request,
    transcript_request: TranscriptRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Transcribe audio asynchronously.
    Returns job_id for status polling.
    """
    # Verify audio exists
    audio_file_response = audio_service.get_audio_file_by_id(
        db=db,
        audio_id=transcript_request.audio_id,
        user=current_user
    )
    
    if not audio_file_response.success:
        return Response(
            content=json.dumps(audio_file_response.to_json()),
            status_code=audio_file_response.code,
            media_type="application/json"
        )
    
    # Queue async transcription
    result = await task_job_service.create_and_queue_job(
        request=request,
        db=db,
        task_type="transcribe",
        task_function="handle_transcription",
        user_id=current_user.id,
        audio_id=transcript_request.audio_id,
        language_code=transcript_request.language_code
    )
    
    return result.to_json()
```

#### Summarization Endpoint (`app/api/v1/endpoints/note_endpoints.py`)

```python
from app.services.task_job_service import task_job_service

@router.post("/summarize-transcript-async")
async def summarize_transcript_async(
    request: Request,
    summarize_request: SummarizeTranscriptRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Summarize audio transcript asynchronously.
    Returns job_id for status polling.
    """
    # Queue async summarization
    result = await task_job_service.create_and_queue_job(
        request=request,
        db=db,
        task_type="summarize",
        task_function="handle_summarization",
        user_id=current_user.id,
        audio_id=summarize_request.audio_id
    )
    
    return result.to_json()
```

#### Add Job Status Endpoint

Create `app/api/v1/endpoints/task_endpoints.py`:

```python
from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session
import json

from app.api.deps import get_db, get_current_active_user
from app.models import User
from app.services.task_job_service import task_job_service

router = APIRouter()

@router.get("/status/{job_id}")
async def get_task_status(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get the status of an async task job.
    
    Status values:
    - pending: Job created but not yet queued
    - queued: Job is in the queue
    - processing: Job is being processed
    - completed: Job completed successfully
    - failed: Job failed with error
    """
    result = task_job_service.get_job_status(
        db=db,
        job_id=job_id,
        user_id=current_user.id
    )
    
    return Response(
        content=json.dumps(result.to_json()),
        status_code=result.code,
        media_type="application/json"
    )
```

Register the new router in `app/api/v1/router.py`:

```python
from app.api.v1.endpoints import task_endpoints

api_router.include_router(task_endpoints.router, prefix="/tasks", tags=["tasks"])
```

### Step 10: Running the System

#### Development Environment

```bash
# Start all services (app, worker, db, redis)
docker-compose up --build

# Or start individually:
docker-compose up db redis  # Start dependencies first
docker-compose up app       # Start API server
docker-compose up worker    # Start ARQ worker
```

#### Production Environment

```bash
docker-compose -f docker-compose.prod.yml up -d --build
```

#### Check Service Status

```bash
# Check if all containers are running
docker-compose ps

# View worker logs
docker-compose logs -f worker

# View app logs
docker-compose logs -f app

# View Redis logs
docker-compose logs -f redis
```

## Client-Side Implementation (Flutter/Mobile)

### Workflow for Async Operations

1. **Submit Task**: Call async endpoint (e.g., `/api/v1/transcript/transcribe-async`)
   ```dart
   final response = await http.post(
     Uri.parse('$baseUrl/api/v1/transcript/transcribe-async'),
     headers: headers,
     body: jsonEncode({"audio_id": audioId, "language_code": "en-US"})
   );
   final jobId = jsonDecode(response.body)['data']['job_id'];
   ```

2. **Show Loading UI**: Display a loading/progress screen to the user

3. **Poll for Status**: Use `Timer.periodic` to check job status every 3-5 seconds
   ```dart
   Timer.periodic(Duration(seconds: 3), (timer) async {
     final statusResponse = await http.get(
       Uri.parse('$baseUrl/api/v1/tasks/status/$jobId'),
       headers: headers
     );
     
     final data = jsonDecode(statusResponse.body)['data'];
     final status = data['status'];
     
     if (status == 'completed') {
       timer.cancel();
       // Show result
       final result = data['result'];
       navigateToResultScreen(result);
     } else if (status == 'failed') {
       timer.cancel();
       // Show error
       showError(data['error_message']);
     }
     // If 'processing' or 'queued', continue polling
   });
   ```

4. **Handle Result**: When status is "completed", retrieve and display the result

### Example Flutter Implementation

```dart
class AsyncTaskService {
  final String baseUrl;
  final String token;

  AsyncTaskService(this.baseUrl, this.token);

  Future<String> submitTranscriptionTask(int audioId) async {
    final response = await http.post(
      Uri.parse('$baseUrl/api/v1/transcript/transcribe-async'),
      headers: {
        'Authorization': 'Bearer $token',
        'Content-Type': 'application/json',
      },
      body: jsonEncode({
        "audio_id": audioId,
        "language_code": "en-US"
      }),
    );

    if (response.statusCode == 200) {
      final data = jsonDecode(response.body)['data'];
      return data['job_id'];
    }
    throw Exception('Failed to submit task');
  }

  Future<Map<String, dynamic>> checkJobStatus(String jobId) async {
    final response = await http.get(
      Uri.parse('$baseUrl/api/v1/tasks/status/$jobId'),
      headers: {
        'Authorization': 'Bearer $token',
      },
    );

    if (response.statusCode == 200) {
      return jsonDecode(response.body)['data'];
    }
    throw Exception('Failed to check status');
  }

  Stream<Map<String, dynamic>> pollJobStatus(String jobId) async* {
    while (true) {
      await Future.delayed(Duration(seconds: 3));
      final status = await checkJobStatus(jobId);
      yield status;
      
      if (status['status'] == 'completed' || status['status'] == 'failed') {
        break;
      }
    }
  }
}
```

## Monitoring and Debugging

### Check Redis Queue

```bash
# Connect to Redis container
docker exec -it voicely_redis redis-cli

# Check queue length
LLEN arq:queue

# View queued jobs
LRANGE arq:queue 0 -1

# Check job details
GET arq:job:<job_id>
```

### Check Database Job Status

```sql
-- View all jobs
SELECT id, task_type, status, created_at, updated_at 
FROM task_jobs 
ORDER BY created_at DESC 
LIMIT 10;

-- Count jobs by status
SELECT status, COUNT(*) 
FROM task_jobs 
GROUP BY status;

-- View failed jobs
SELECT id, task_type, error_message, created_at 
FROM task_jobs 
WHERE status = 'failed'
ORDER BY created_at DESC;
```

### Worker Performance

```bash
# Monitor worker in real-time
docker-compose logs -f worker

# Check worker resource usage
docker stats voicely_worker
```

## Scaling Considerations

### Horizontal Scaling

To handle more concurrent jobs, scale the worker service:

```bash
docker-compose up -d --scale worker=3
```

### Production Optimizations

1. **Job Timeout Configuration**: Adjust based on your longest-running tasks
2. **Max Jobs**: Configure `max_jobs` in `WorkerSettings` based on available resources
3. **Redis Persistence**: Enable AOF (Append Only File) for data durability
4. **Job Retention**: Configure `keep_result` to balance storage vs. result availability
5. **Error Handling**: Implement retry logic for transient failures

## Troubleshooting

### Worker Not Processing Jobs

```bash
# Check if worker is running
docker-compose ps worker

# Check worker logs for errors
docker-compose logs worker

# Restart worker
docker-compose restart worker
```

### Redis Connection Issues

```bash
# Test Redis connectivity
docker exec -it voicely_redis redis-cli PING

# Check Redis logs
docker-compose logs redis
```

### Jobs Stuck in "processing"

This can happen if worker crashes during job execution. Implement a cleanup script:

```python
# scripts/cleanup_stuck_jobs.py
from app.db.session import SessionLocal
from app.models.task_job_model import TaskJob
from datetime import datetime, timedelta

db = SessionLocal()
timeout = datetime.utcnow() - timedelta(hours=2)

stuck_jobs = db.query(TaskJob).filter(
    TaskJob.status == "processing",
    TaskJob.updated_at < timeout
).all()

for job in stuck_jobs:
    job.status = "failed"
    job.error_message = "Job timeout - exceeded maximum processing time"
    
db.commit()
print(f"Cleaned up {len(stuck_jobs)} stuck jobs")
```

## Summary

This implementation provides:

- ✅ Non-blocking API responses
- ✅ Isolated heavy processing in background workers  
- ✅ Persistent job status in PostgreSQL
- ✅ Scalable worker architecture
- ✅ Simple polling mechanism for clients
- ✅ Error handling and retry capabilities
- ✅ Production-ready Docker deployment

The system allows mobile clients to submit long-running tasks and check their progress without maintaining open connections, providing a better user experience and more reliable backend architecture.
