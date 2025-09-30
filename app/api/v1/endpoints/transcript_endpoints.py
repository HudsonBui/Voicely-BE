import os
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from app.api.deps import get_db, get_current_active_user
from app.models import User, AudioFile
from app.schemas.transcript import (
    TranscriptRequest, 
    TranscriptResponse, 
    TranscriptStatus, 
    SupportedLanguage
)
from app.services.transcript_service import transcript_service
from app.services.audio_service import audio_service

router = APIRouter()

@router.post("/transcribe", response_model=TranscriptResponse)
async def transcribe_audio(
    request: TranscriptRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Transcribe an audio file by audio ID.
    
    This endpoint processes the audio file and returns transcription results.
    For long audio files, processing happens in the background.
    """
    
    # Get the audio file
    audio_file = audio_service.get_audio_file_by_id(
        db=db,
        audio_id=request.audio_id,
        user=current_user
    )
    
    if not audio_file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audio file not found"
        )
    
    # Check if transcription service is available
    if not transcript_service.is_transcription_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Transcription service is not available. Please configure Google Cloud Speech API credentials."
        )
    
    # Check if already transcribed
    if audio_file.transcription and audio_file.status == "completed":
        # Return existing transcription
        return TranscriptResponse(
            audio_id=audio_file.id,
            transcript=audio_file.transcription,
            confidence=audio_file.confidence_score or 0.0,
            language_code=request.language_code,
            segments=[],  # Segments not stored in basic version
            word_count=len(audio_file.transcription.split()) if audio_file.transcription else 0,
            duration_transcribed=audio_file.duration,
            status=audio_file.status,
            processed_at=audio_file.updated_at
        )
    
    try:
        # Update status to processing
        audio_file.status = "processing"
        db.commit()
        
        # Perform transcription
        transcription_result = transcript_service.transcribe_audio_file(
            audio_file=audio_file,
            language_code=request.language_code
        )
        
        # Update database with results
        updated_audio_file = transcript_service.update_audio_file_transcription(
            db=db,
            audio_file=audio_file,
            transcription_result=transcription_result
        )
        
        # Return response
        return TranscriptResponse(
            audio_id=updated_audio_file.id,
            transcript=transcription_result["transcript"],
            confidence=transcription_result["confidence"],
            language_code=request.language_code,
            segments=transcription_result.get("segments", []),
            word_count=transcription_result["word_count"],
            duration_transcribed=transcription_result.get("duration_transcribed"),
            status=transcription_result["status"],
            processed_at=datetime.utcnow()
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions
        audio_file.status = "failed"
        db.commit()
        raise
    except Exception as e:
        # Handle unexpected errors
        audio_file.status = "failed"
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Transcription failed: {str(e)}"
        )

# @router.get("/status/{audio_id}", response_model=TranscriptStatus)
# def get_transcription_status(
#     audio_id: int,
#     db: Session = Depends(get_db),
#     current_user: User = Depends(get_current_active_user)
# ):
#     """
#     Get the transcription status of an audio file.
#     """
    
#     audio_file = audio_service.get_audio_file_by_id(
#         db=db,
#         audio_id=audio_id,
#         user=current_user
#     )
    
#     if not audio_file:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="Audio file not found"
#         )
    
#     return TranscriptStatus(
#         audio_id=audio_file.id,
#         status=audio_file.status,
#         transcript=audio_file.transcription,
#         confidence=audio_file.confidence_score,
#         created_at=audio_file.created_at,
#         updated_at=audio_file.updated_at
#     )

# @router.get("/languages", response_model=List[SupportedLanguage])
# def get_supported_languages():
#     """
#     Get list of supported languages for transcription.
#     """
#     return transcript_service.get_supported_languages()

# @router.post("/retranscribe/{audio_id}", response_model=TranscriptResponse)
# async def retranscribe_audio(
#     audio_id: int,
#     language_code: str = "en-US",
#     db: Session = Depends(get_db),
#     current_user: User = Depends(get_current_active_user)
# ):
#     """
#     Force re-transcribe an audio file, even if it was already transcribed.
#     """
    
#     # Get the audio file
#     audio_file = audio_service.get_audio_file_by_id(
#         db=db,
#         audio_id=audio_id,
#         user=current_user
#     )
    
#     if not audio_file:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="Audio file not found"
#         )
    
#     # Check transcription service
#     if not transcript_service.is_transcription_available():
#         raise HTTPException(
#             status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
#             detail="Transcription service is not available"
#         )
    
#     try:
#         # Reset status and clear previous transcription
#         audio_file.status = "processing"
#         audio_file.transcription = None
#         audio_file.confidence_score = None
#         db.commit()
        
#         # Perform transcription
#         transcription_result = transcript_service.transcribe_audio_file(
#             audio_file=audio_file,
#             language_code=language_code
#         )
        
#         # Update database
#         updated_audio_file = transcript_service.update_audio_file_transcription(
#             db=db,
#             audio_file=audio_file,
#             transcription_result=transcription_result
#         )
        
#         return TranscriptResponse(
#             audio_id=updated_audio_file.id,
#             transcript=transcription_result["transcript"],
#             confidence=transcription_result["confidence"],
#             language_code=language_code,
#             segments=transcription_result.get("segments", []),
#             word_count=transcription_result["word_count"],
#             duration_transcribed=transcription_result.get("duration_transcribed"),
#             status=transcription_result["status"],
#             processed_at=datetime.utcnow()
#         )
        
#     except HTTPException:
#         audio_file.status = "failed"
#         db.commit()
#         raise
#     except Exception as e:
#         audio_file.status = "failed"
#         db.commit()
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Re-transcription failed: {str(e)}"
#         )

@router.delete("/transcript/{audio_id}")
def delete_transcription(
    audio_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Delete the transcription data for an audio file (keeps the audio file).
    """
    
    audio_file = audio_service.get_audio_file_by_id(
        db=db,
        audio_id=audio_id,
        user=current_user
    )
    
    if not audio_file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audio file not found"
        )
    
    try:
        # Clear transcription data
        audio_file.transcription = None
        audio_file.confidence_score = None
        audio_file.status = "uploaded"  # Reset to uploaded status
        
        db.commit()
        
        return {"message": "Transcription deleted successfully"}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete transcription: {str(e)}"
        )

@router.get("/check/{audio_id}")
def check_transcription_compatibility(
    audio_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Check if an audio file can be transcribed with current setup.
    """
    
    audio_file = audio_service.get_audio_file_by_id(
        db=db,
        audio_id=audio_id,
        user=current_user
    )
    
    if not audio_file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audio file not found"
        )
    
    # Check if transcription service is available
    if not transcript_service.is_transcription_available():
        return {
            "can_transcribe": False,
            "reason": "Google Cloud Speech API not configured",
            "recommendation": "Configure GOOGLE_APPLICATION_CREDENTIALS in environment"
        }
    
    # Check file constraints
    file_size = 0
    if os.path.exists(audio_file.file_path):
        file_size = os.path.getsize(audio_file.file_path)
    
    duration = audio_file.duration or 0
    
    # Current limitations
    max_size_simple = 10 * 1024 * 1024   # 10MB for synchronous
    max_size_direct_long = 1 * 1024 * 1024  # 1MB for long running without GCS
    max_duration_simple = 60              # 60 seconds for synchronous
    
    # Check if GCS is available for large files
    gcs_available = transcript_service.is_gcs_available()
    
    if duration <= max_duration_simple and file_size <= max_size_simple:
        return {
            "can_transcribe": True,
            "method": "synchronous",
            "file_size_mb": round(file_size / 1024 / 1024, 2),
            "duration_seconds": duration,
            "recommendation": "File is compatible with direct synchronous transcription"
        }
    elif duration > max_duration_simple and file_size <= max_size_direct_long:
        return {
            "can_transcribe": True,
            "method": "asynchronous_direct",
            "file_size_mb": round(file_size / 1024 / 1024, 2),
            "duration_seconds": duration,
            "recommendation": "File will use asynchronous transcription with direct upload"
        }
    elif gcs_available:
        return {
            "can_transcribe": True,
            "method": "asynchronous_gcs",
            "file_size_mb": round(file_size / 1024 / 1024, 2),
            "duration_seconds": duration,
            "recommendation": "File will be uploaded to Google Cloud Storage for transcription",
            "gcs_bucket": transcript_service.gcs_bucket_name
        }
    else:
        return {
            "can_transcribe": False,
            "reason": f"File too large ({file_size / 1024 / 1024:.1f}MB) or too long ({duration:.1f}s) and GCS not configured",
            "file_size_mb": round(file_size / 1024 / 1024, 2),
            "duration_seconds": duration,
            "recommendation": "Configure GCS_BUCKET_NAME environment variable for large files, or use smaller files (<1MB, <60s)",
            "limits": {
                "max_size_simple_mb": max_size_simple / 1024 / 1024,
                "max_size_direct_long_mb": max_size_direct_long / 1024 / 1024,
                "max_duration_simple_seconds": max_duration_simple
            },
            "gcs_available": gcs_available
        }

@router.get("/health")
def transcription_health_check():
    """
    Check the health of transcription services (Speech API and GCS).
    """
    health_status = {
        "speech_api_available": transcript_service.is_transcription_available(),
        "gcs_available": transcript_service.is_gcs_available(),
        "timestamp": datetime.utcnow().isoformat()
    }
    
    if transcript_service.is_transcription_available():
        health_status["speech_api_status"] = "configured"
    else:
        health_status["speech_api_status"] = "not_configured"
        health_status["speech_api_recommendation"] = "Set GOOGLE_APPLICATION_CREDENTIALS environment variable"
    
    if transcript_service.is_gcs_available():
        health_status["gcs_status"] = "configured"
        health_status["gcs_bucket"] = transcript_service.gcs_bucket_name
    else:
        health_status["gcs_status"] = "not_configured"
        health_status["gcs_recommendation"] = "Set GCS_BUCKET_NAME environment variable and ensure proper IAM permissions"
    
    # Overall status
    if health_status["speech_api_available"]:
        if health_status["gcs_available"]:
            health_status["overall_status"] = "fully_operational"
            health_status["capabilities"] = ["short_audio", "medium_audio", "large_audio_gcs"]
        else:
            health_status["overall_status"] = "limited_operation"
            health_status["capabilities"] = ["short_audio", "medium_audio"]
            health_status["limitations"] = ["large_audio_requires_gcs_setup"]
    else:
        health_status["overall_status"] = "not_operational"
        health_status["capabilities"] = []
        health_status["limitations"] = ["transcription_not_configured"]
    
    return health_status