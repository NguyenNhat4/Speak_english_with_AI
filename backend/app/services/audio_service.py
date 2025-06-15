"""
Audio Service for handling audio processing business logic.

This service manages audio file operations, transcription, validation,
and feedback processing for the SpeakAI application.
"""

import logging
import os
import shutil
from typing import Dict, Any, Optional, Tuple
from pathlib import Path
from fastapi import HTTPException, UploadFile
from bson import ObjectId

from app.config.database import db
from app.models.audio import Audio
from app.utils.speech_service import SpeechService
from app.utils.transcription_error_message import TranscriptionErrorMessages

logger = logging.getLogger(__name__)

# Define valid audio file extensions
VALID_AUDIO_EXTENSIONS = ['.mp3', '.wav', '.m4a', '.aac', '.ogg', '.flac']
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB


class AudioService:
    """
    Service class for handling audio processing business logic.
    
    This service encapsulates all audio-related operations including
    file saving, transcription, validation, and feedback processing.
    """
    
    def __init__(self):
        """Initialize the audio service."""
        self.logger = logging.getLogger(self.__class__.__name__)
        self.speech_service = SpeechService()
        self.upload_dir = Path("app/uploads")
        self.upload_dir.mkdir(parents=True, exist_ok=True)
    
    def save_audio_file(self, file: UploadFile, user_id: str) -> str:
        """
        Save an audio file to storage and create database record.
        
        Args:
            file (UploadFile): The audio file to save
            user_id (str): The ID of the user uploading the file
            
        Returns:
            str: The ID of the saved audio record
            
        Raises:
            HTTPException: If file saving fails
        """
        try:
            # Validate the audio file
            self.validate_audio_file(file)
            
            # Save the file using speech service
            file_path, audio_model = self.speech_service.save_audio_file(file, user_id)
            audio_id = str(audio_model._id)
            
            self.logger.info(f"Successfully saved audio file for user {user_id}: {audio_id}")
            return audio_id
            
        except Exception as e:
            self.logger.error(f"Failed to save audio file for user {user_id}: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to save audio file: {str(e)}"
            )
    
    def transcribe_audio(self, file: UploadFile) -> Tuple[str, Optional[str]]:
        """
        Transcribe audio file to text.
        
        Args:
            file (UploadFile): The audio file to transcribe
            
        Returns:
            Tuple[str, Optional[str]]: Transcription text and temporary file path
            
        Raises:
            HTTPException: If transcription fails
        """
        try:
            # Use speech service to transcribe from upload
            transcription, temp_file_path = self.speech_service.transcribe_from_upload(file)
            
            self.logger.debug(f"Transcription completed with length: {len(transcription) if transcription else 0}")
            return transcription, temp_file_path
            
        except Exception as e:
            self.logger.error(f"Failed to transcribe audio: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Audio transcription failed: {str(e)}"
            )
    
    def validate_audio_file(self, file: UploadFile) -> bool:
        """
        Validate audio file format and size.
        
        Args:
            file (UploadFile): The audio file to validate
            
        Returns:
            bool: True if validation passes
            
        Raises:
            HTTPException: If validation fails
        """
        try:
            # Check if file is provided
            if not file:
                raise HTTPException(
                    status_code=400,
                    detail="No audio file provided"
                )
            
            # Check file extension
            file_extension = Path(file.filename).suffix.lower()
            if file_extension not in VALID_AUDIO_EXTENSIONS:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid audio format. Supported formats: {', '.join(VALID_AUDIO_EXTENSIONS)}"
                )
            
            # Check file size if possible
            if hasattr(file.file, 'seek') and hasattr(file.file, 'tell'):
                file.file.seek(0, 2)  # Seek to end
                file_size = file.file.tell()
                file.file.seek(0)  # Reset to beginning
                
                if file_size > MAX_FILE_SIZE:
                    raise HTTPException(
                        status_code=400,
                        detail=f"File size too large. Maximum size: {MAX_FILE_SIZE // 1024 // 1024}MB"
                    )
            
            # Check filename length
            if len(file.filename) > 255:
                raise HTTPException(
                    status_code=400,
                    detail="Filename too long"
                )
            
            self.logger.debug(f"Audio file validation passed for: {file.filename}")
            return True
            
        except HTTPException:
            raise
        except Exception as e:
            self.logger.error(f"Audio file validation error: {str(e)}")
            raise HTTPException(
                status_code=400,
                detail=f"File validation failed: {str(e)}"
            )
    
    def process_audio_for_feedback(
        self, 
        transcription: str, 
        user_id: str, 
        conversation_id: str,
        audio_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process audio transcription for feedback generation.
        
        Args:
            transcription (str): The transcribed text from audio
            user_id (str): The ID of the user
            conversation_id (str): The ID of the conversation
            audio_id (Optional[str]): The ID of the audio record
            
        Returns:
            Dict[str, Any]: Processing results and feedback data
            
        Raises:
            HTTPException: If processing fails
        """
        try:
            # Validate inputs
            if not transcription or not transcription.strip():
                raise HTTPException(
                    status_code=400,
                    detail="Empty transcription provided"
                )
            
            if not ObjectId.is_valid(user_id):
                raise HTTPException(
                    status_code=400,
                    detail="Invalid user ID format"
                )
            
            if not ObjectId.is_valid(conversation_id):
                raise HTTPException(
                    status_code=400,
                    detail="Invalid conversation ID format"
                )
            
            # Check if transcription was successful
            is_successful = (
                transcription != TranscriptionErrorMessages.DEFAULT_FALLBACK_ERROR.value and
                transcription != TranscriptionErrorMessages.EMPTY_TRANSCRIPTION.value
            )
            
            if not is_successful:
                return {
                    "success": False,
                    "transcription": transcription,
                    "audio_id": audio_id,
                    "error": "Transcription was not successful"
                }
            
            # Update audio record with transcription if audio_id is provided
            if audio_id and ObjectId.is_valid(audio_id):
                db.audio.update_one(
                    {"_id": ObjectId(audio_id)},
                    {"$set": {"transcription": transcription, "has_error": False}}
                )
            
            self.logger.info(f"Successfully processed audio for feedback - User: {user_id}, Conversation: {conversation_id}")
            
            return {
                "success": True,
                "transcription": transcription,
                "audio_id": audio_id,
                "user_id": user_id,
                "conversation_id": conversation_id
            }
            
        except HTTPException:
            raise
        except Exception as e:
            self.logger.error(f"Failed to process audio for feedback: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Audio processing failed: {str(e)}"
            )
    
    def cleanup_temp_file(self, file_path: Optional[str]) -> None:
        """
        Clean up temporary audio file.
        
        Args:
            file_path (Optional[str]): Path to the temporary file to clean up
        """
        if file_path and os.path.exists(file_path):
            try:
                os.unlink(file_path)
                self.logger.debug(f"Cleaned up temporary file: {file_path}")
            except Exception as e:
                self.logger.warning(f"Failed to clean up temporary file {file_path}: {str(e)}")
    
    def get_audio_metadata(self, audio_id: str) -> Dict[str, Any]:
        """
        Retrieve audio file metadata.
        
        Args:
            audio_id (str): The ID of the audio record
            
        Returns:
            Dict[str, Any]: Audio metadata
            
        Raises:
            HTTPException: If audio not found or retrieval fails
        """
        try:
            if not ObjectId.is_valid(audio_id):
                raise HTTPException(
                    status_code=400,
                    detail="Invalid audio ID format"
                )
            
            audio_record = db.audio.find_one({"_id": ObjectId(audio_id)})
            if not audio_record:
                raise HTTPException(
                    status_code=404,
                    detail="Audio record not found"
                )
            
            # Format response
            audio_record["id"] = str(audio_record["_id"])
            audio_record["user_id"] = str(audio_record["user_id"])
            if "conversation_id" in audio_record:
                audio_record["conversation_id"] = str(audio_record["conversation_id"])
            del audio_record["_id"]
            
            self.logger.debug(f"Retrieved audio metadata for: {audio_id}")
            return audio_record
            
        except HTTPException:
            raise
        except Exception as e:
            self.logger.error(f"Failed to retrieve audio metadata for {audio_id}: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to retrieve audio metadata: {str(e)}"
            ) 