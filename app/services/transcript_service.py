import os
import io
from typing import Optional, Dict, Any
from pathlib import Path
import logging
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

try:
    from google.cloud import speech_v1 as speech
    from google.cloud import storage
    from google.api_core import exceptions as gcp_exceptions
    from google.api_core import retry as gcp_retry
    GOOGLE_CLOUD_AVAILABLE = True
except ImportError:
    GOOGLE_CLOUD_AVAILABLE = False
    speech = None
    storage = None
    gcp_exceptions = None
    gcp_retry = None

try:
    from pydub import AudioSegment
    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False
    AudioSegment = None

from app.models import AudioFile
from app.common.common_message import CommonMessage
from app.common.response_common import ResponseCommon

logger = logging.getLogger(__name__)

class TranscriptService:
    def __init__(self):
        self.client = None
        self.storage_client = None
        self.gcs_bucket_name = os.getenv('GCS_BUCKET_NAME')
        self._setup_clients()
    
    def _setup_clients(self):
        """Initialize the Speech and Storage clients with proper error handling."""
        try:
            # Check if credentials are available
            credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
            if not credentials_path:
                print("Warning: GOOGLE_APPLICATION_CREDENTIALS not set")
                return
            
            if not os.path.exists(credentials_path):
                print(f"Warning: Credentials file not found at {credentials_path}")
                return
            
            if not GOOGLE_CLOUD_AVAILABLE:
                print("Warning: Google Cloud libraries not available")
                return
            
            # Initialize Speech client
            self.client = speech.SpeechClient()
            print("Google Cloud Speech client initialized successfully")
            
            # Initialize Storage client if bucket is configured
            if self.gcs_bucket_name:
                self.storage_client = storage.Client()
                print(f"Google Cloud Storage client initialized successfully for bucket: {self.gcs_bucket_name}")
            else:
                print("Warning: GCS_BUCKET_NAME not set. Long audio transcription will be limited.")
            
        except ImportError:
            print("Warning: google-cloud-speech or google-cloud-storage not installed")
        except Exception as e:
            print(f"Warning: Failed to initialize Google Cloud clients: {e}")
    
    def is_transcription_available(self) -> bool:
        """Check if transcription service is available."""
        return self.client is not None and GOOGLE_CLOUD_AVAILABLE
    
    def is_gcs_available(self) -> bool:
        """Check if Google Cloud Storage is available for long audio files."""
        return self.storage_client is not None and self.gcs_bucket_name is not None

    def upload_to_gcs(self, local_file_path: str, gcs_file_name: str) -> str:
        """Upload a file to Google Cloud Storage and return the GCS URI."""
        if not self.is_gcs_available():
            raise Exception("Google Cloud Storage not available. Configure GCS_BUCKET_NAME and credentials.")
        
        try:
            bucket = self.storage_client.bucket(self.gcs_bucket_name)
            blob = bucket.blob(gcs_file_name)
            blob.chunk_size = 8 * 1024 * 1024

            upload_timeout = 600
            retry = None
            if gcp_retry is not None:
                retry = gcp_retry.Retry(
                    predicate=gcp_retry.if_transient_error,
                    deadline=upload_timeout,
                )

            # Upload the file
            blob.upload_from_filename(
                local_file_path,
                timeout=upload_timeout,
                retry=retry,
            )
            
            gcs_uri = f"gs://{self.gcs_bucket_name}/{gcs_file_name}"
            logger.info(f"File uploaded to GCS: {gcs_uri}")
            return gcs_uri
            
        except Exception as e:
            logger.error(f"Failed to upload file to GCS: {e}")
            raise Exception(f"GCS upload failed: {e}")

    def transcribe_long_audio_from_gcs(self, gcs_uri: str, language_code: str = "en-US") -> Dict[str, Any]:
        """Transcribe long audio file from Google Cloud Storage using asynchronous recognition."""
        if not self.is_transcription_available():
            raise Exception("Google Cloud Speech API not available")
        
        try:
            # Configure the audio source from GCS
            audio = speech.RecognitionAudio(uri=gcs_uri)
            
            # Configure recognition settings
            config = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
                sample_rate_hertz=16000,
                language_code=language_code,
                enable_automatic_punctuation=True,
                enable_word_time_offsets=True,
                model="latest_long",  # Use the latest long-form model
            )
            
            logger.info(f"Starting long-running transcription for: {gcs_uri}")
            
            # Start the long-running operation
            operation = self.client.long_running_recognize(config=config, audio=audio)
            
            logger.info("Waiting for transcription to complete...")
            # Wait for the operation to complete (timeout: 2 hours)
            response = operation.result(timeout=7200)
            
            # Process results
            full_transcript = ""
            confidence_scores = []
            transcriptions = []
            
            for result in response.results:
                if result.alternatives:
                    alternative = result.alternatives[0]
                    transcript_part = alternative.transcript
                    confidence = alternative.confidence
                    
                    full_transcript += transcript_part + " "
                    confidence_scores.append(confidence)
                    
                    # Add to segments for compatibility
                    transcriptions.append({
                        "transcript": transcript_part,
                        "confidence": confidence,
                        "words": []  # Word-level timing not available in this implementation
                    })
            
            # Calculate average confidence
            avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0
            
            full_transcript = full_transcript.strip()
            
            return {
                "transcript": full_transcript,
                "confidence": avg_confidence,
                "language_code": language_code,
                "segments": transcriptions,
                "word_count": len(full_transcript.split()) if full_transcript else 0,
                "duration_transcribed": None,  # Duration not directly available from GCS transcription
                "status": "completed",
                "method": "long_running_recognize_gcs"
            }
            
        except Exception as e:
            logger.error(f"Long-running transcription failed: {e}")
            raise Exception(f"Long-running transcription failed: {e}")

    def convert_audio_for_transcription(self, input_file: str, output_file: str) -> bool:
        """Convert audio to format suitable for Google Cloud Speech"""
        if not PYDUB_AVAILABLE:
            logger.warning("pydub not available. Audio conversion skipped.")
            return False
            
        try:
            # Load audio file
            audio = AudioSegment.from_file(input_file)
            
            # Convert to mono, 16kHz, WAV format (optimal for Google Cloud Speech)
            audio = audio.set_channels(1)  # Mono
            audio = audio.set_frame_rate(16000)  # 16kHz sample rate
            
            # Export as WAV
            audio.export(output_file, format="wav")
            logger.info(f"Audio converted successfully: {output_file}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to convert audio: {e}")
            return False

    def get_audio_config(self, file_path: str) -> speech.RecognitionConfig:
        """Get appropriate recognition config based on audio file"""
        
        # Default config for WAV files
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=16000,  # We convert to 16kHz
            language_code="en-US",  # Default to English
            enable_automatic_punctuation=True,
            enable_word_confidence=True,
            max_alternatives=1,
        )
        
        # You can add more sophisticated format detection here
        file_extension = Path(file_path).suffix.lower()
        
        if file_extension in ['.mp3']:
            config.encoding = speech.RecognitionConfig.AudioEncoding.MP3
        elif file_extension in ['.flac']:
            config.encoding = speech.RecognitionConfig.AudioEncoding.FLAC
        elif file_extension in ['.ogg']:
            config.encoding = speech.RecognitionConfig.AudioEncoding.OGG_OPUS
            
        return config

    def estimate_duration_from_file_size(self, file_path: str, format: str) -> Optional[float]:
        """Estimate duration based on file size (rough approximation)"""
        try:
            file_size = os.path.getsize(file_path)
            
            # Rough estimates based on typical bitrates (very approximate)
            bitrate_estimates = {
                'mp3': 128000,  # 128 kbps
                'wav': 1411000,  # 16-bit 44.1kHz stereo
                'flac': 700000,  # ~700 kbps average
                'm4a': 128000,  # 128 kbps
                'aac': 128000,  # 128 kbps
                'ogg': 128000,  # 128 kbps
            }
            
            bitrate = bitrate_estimates.get(format.lower(), 128000)  # Default to 128 kbps
            estimated_duration = (file_size * 8) / bitrate  # Convert to seconds
            
            logger.info(f"Estimated duration from file size: {estimated_duration}s (very rough estimate)")
            return estimated_duration
        except Exception as e:
            logger.warning(f"Could not estimate duration from file size: {e}")
            return None

    def transcribe_audio_file(self, audio_file: AudioFile, language_code: str = "en-US") -> Dict[str, Any]:
        """
        Transcribe an audio file using Google Cloud Speech-to-Text
        
        Args:
            audio_file: AudioFile model instance
            language_code: Language code (e.g., "en-US", "vi-VN")
            
        Returns:
            Dict containing transcription results
        """
        
        if not self.is_transcription_available():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=CommonMessage.TRANSCRIPTION_SERVICE_UNAVAILABLE
            )
        
        if not os.path.exists(audio_file.file_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=CommonMessage.AUDIO_FILE_NOT_FOUND_ON_DISK
            )
        
        try:
            # Prepare file for transcription
            original_file = audio_file.file_path
            converted_file = None
            
            # Convert audio if needed (for better recognition)
            if PYDUB_AVAILABLE and audio_file.format.lower() in ['mp3', 'm4a', 'aac']:
                converted_file = f"{original_file}_converted.wav"
                if self.convert_audio_for_transcription(original_file, converted_file):
                    transcribe_file = converted_file
                else:
                    transcribe_file = original_file
            else:
                transcribe_file = original_file
            
            # Check file size (Google Cloud has 10MB limit for direct content)
            file_size = os.path.getsize(transcribe_file)
            max_content_size = 10 * 1024 * 1024  # 10MB
            
            # Determine which method to use based on duration and file size
            use_long_running = False
            duration = audio_file.duration or 0
            
            # If duration is missing or seems inaccurate, try to get it
            if not duration or duration <= 0:
                logger.info("Duration missing or invalid, attempting to detect duration")
                if PYDUB_AVAILABLE:
                    try:
                        audio_segment = AudioSegment.from_file(transcribe_file)
                        duration = len(audio_segment) / 1000.0  # Convert to seconds
                        logger.info(f"Detected duration using pydub: {duration}s")
                    except Exception as e:
                        logger.warning(f"Could not detect duration with pydub: {e}")
                        # Estimate based on file size (very rough)
                        duration = self.estimate_duration_from_file_size(transcribe_file, audio_file.format)
                        
            if duration > 60:  # Longer than 1 minute
                use_long_running = True
                logger.info(f"Using long running recognize for audio duration: {duration}s")
            elif file_size > max_content_size:  # Larger than 10MB
                use_long_running = True
                logger.info(f"Using long running recognize for large file: {file_size / 1024 / 1024:.1f}MB")
            
            # Handle very large files with GCS
            if use_long_running and file_size > 1 * 1024 * 1024:  # 1MB limit for long running with content
                if not self.is_gcs_available():
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=CommonMessage.TRANSCRIPTION_GCS_REQUIRED
                    )
                
                # Use GCS-based transcription for large files
                logger.info(f"Using GCS-based transcription for large file: {file_size / 1024 / 1024:.1f}MB")
                
                # Generate unique filename for GCS
                import uuid
                gcs_filename = f"transcription/{uuid.uuid4()}_{Path(transcribe_file).name}"
                
                try:
                    # Upload to GCS
                    gcs_uri = self.upload_to_gcs(transcribe_file, gcs_filename)
                    
                    # Transcribe from GCS
                    result = self.transcribe_long_audio_from_gcs(gcs_uri, language_code)
                    
                    # Clean up the GCS file after transcription
                    try:
                        bucket = self.storage_client.bucket(self.gcs_bucket_name)
                        blob = bucket.blob(gcs_filename)
                        blob.delete()
                        logger.info(f"Cleaned up GCS file: {gcs_uri}")
                    except Exception as cleanup_error:
                        logger.warning(f"Failed to cleanup GCS file {gcs_uri}: {cleanup_error}")
                    
                    return result
                    
                except Exception as gcs_error:
                    logger.error(f"GCS-based transcription failed: {gcs_error}")
                    
                    # Check if we can fall back to direct transcription
                    # Allow fallback for files slightly over 1MB if duration is reasonable
                    can_fallback = (
                        file_size <= 2 * 1024 * 1024 and  # Up to 2MB
                        duration <= 300  # Up to 5 minutes
                    )
                    
                    if can_fallback:
                        logger.warning(f"Attempting fallback to direct transcription for {file_size / 1024 / 1024:.1f}MB file")
                        # Continue to direct transcription below
                    else:
                        raise HTTPException(
                            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=CommonMessage.TRANSCRIPTION_GCS_FAILED
                        )
            
            # For files that can be processed directly
            if file_size > max_content_size:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=CommonMessage.AUDIO_FILE_TOO_LARGE
                )
            
            # Read audio file
            with open(transcribe_file, "rb") as audio_content:
                content = audio_content.read()
            
            # Configure recognition
            audio = speech.RecognitionAudio(content=content)
            config = self.get_audio_config(transcribe_file)
            config.language_code = language_code
            
            # Perform transcription
            logger.info(f"Starting transcription for audio file ID: {audio_file.id}, method: {'long_running' if use_long_running else 'synchronous'}")
            
            if use_long_running:
                # Use asynchronous long running recognize
                operation = self.client.long_running_recognize(config=config, audio=audio)
                logger.info(f"Long running operation started, waiting for completion...")
                response = operation.result(timeout=600)  # 10 minutes timeout
                logger.info(f"Long running operation completed")
            else:
                # Use synchronous recognize for short files
                response = self.client.recognize(config=config, audio=audio)
            
            # Process results
            transcriptions = []
            overall_confidence = 0.0
            
            for i, result in enumerate(response.results):
                alternative = result.alternatives[0]
                transcriptions.append({
                    "transcript": alternative.transcript,
                    "confidence": alternative.confidence,
                    "words": [
                        {
                            "word": word_info.word,
                            "start_time": word_info.start_time.total_seconds(),
                            "end_time": word_info.end_time.total_seconds(),
                            "confidence": word_info.confidence
                        }
                        for word_info in alternative.words
                    ] if hasattr(alternative, 'words') else []
                })
                overall_confidence += alternative.confidence
            
            # Calculate average confidence
            if transcriptions:
                overall_confidence /= len(transcriptions)
            
            # Combine all transcripts
            full_transcript = " ".join([t["transcript"] for t in transcriptions])
            
            # Clean up converted file
            if converted_file and os.path.exists(converted_file):
                try:
                    os.remove(converted_file)
                except:
                    pass
            
            result_data = {
                "transcript": full_transcript,
                "confidence": overall_confidence,
                "language_code": language_code,
                "segments": transcriptions,
                "word_count": len(full_transcript.split()) if full_transcript else 0,
                "duration_transcribed": audio_file.duration,
                "status": "completed"
            }
            
            logger.info(f"Transcription completed for audio file ID: {audio_file.id}")
            return result_data
            
        except gcp_exceptions.GoogleAPIError as e:
            logger.error(f"Google Cloud API error: {e}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=CommonMessage.GOOGLE_CLOUD_API_ERROR
            )
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=CommonMessage.TRANSCRIPTION_FAILED
            )

    def transcribe_audio(
        self,
        audio_file: AudioFile,
        language_code: str = "en-US"
    ) -> ResponseCommon:
        """
        Wrapper that returns a standardized response for transcription requests.
        """
        try:
            result = self.transcribe_audio_file(audio_file=audio_file, language_code=language_code)
            return ResponseCommon.success_response(
                data=result,
                message="Transcription completed successfully"
            )
        except HTTPException as exc:
            return ResponseCommon.error_response(
                message=str(exc.detail),
                code=exc.status_code
            )
        except Exception as exc:
            logger.error("Unexpected transcription error: %s", exc, exc_info=True)
            return ResponseCommon.error_response(
                message=CommonMessage.TRANSCRIPTION_FAILED,
                code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def update_audio_file_transcription(
        self, 
        db: Session, 
        audio_file: AudioFile, 
        transcription_result: Dict[str, Any]
    ) -> ResponseCommon:
        """Update audio file with transcription results"""
        
        try:
            # Update database record
            audio_file.transcription = transcription_result["transcript"]
            audio_file.confidence_score = transcription_result["confidence"]
            audio_file.status = transcription_result["status"]
            
            db.commit()
            db.refresh(audio_file)
            
            logger.info("Updated audio file %s with transcription", audio_file.id)
            return ResponseCommon.success_response(
                data=audio_file,
                message="Transcription updated successfully"
            )
            
        except Exception as e:
            db.rollback()
            logger.error("Failed to update audio file transcription: %s", e, exc_info=True)
            return ResponseCommon.error_response(
                message=CommonMessage.TRANSCRIPTION_SAVE_FAILED,
                code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def get_supported_languages(self) -> list:
        """Get list of supported languages"""
        return [
            {"code": "en-US", "name": "English (US)"},
            {"code": "en-GB", "name": "English (UK)"},
            {"code": "vi-VN", "name": "Vietnamese"},
            {"code": "es-ES", "name": "Spanish"},
            {"code": "fr-FR", "name": "French"},
            {"code": "de-DE", "name": "German"},
            {"code": "ja-JP", "name": "Japanese"},
            {"code": "ko-KR", "name": "Korean"},
            {"code": "zh-CN", "name": "Chinese (Simplified)"},
            {"code": "pt-BR", "name": "Portuguese (Brazil)"},
        ]

# Global instance
transcript_service = TranscriptService()
