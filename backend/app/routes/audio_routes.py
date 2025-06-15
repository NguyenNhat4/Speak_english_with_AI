from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import JSONResponse
from bson import ObjectId
from typing import List, Optional
import logging
import os
import shutil
from pathlib import Path
from datetime import datetime

from app.config.database import db
from app.models.audio import Audio
from app.schemas.audio import (
    AudioCreate, 
    AudioResponse, 
    AudioUpload,
    TranscriptionRequest, 
    TranscriptionResponse, 
    PronunciationFeedback,
    AnalysisRequest,
    AnalysisResponse,
    LanguageFeedback,
    FileProcessRequest,
    LocalFileRequest
)
from app.utils.auth import get_current_user
from app.utils.audio_processor import (
    transcribe_audio_local,
    generate_feedback
)
from app.utils.transcription_error_message import TranscriptionErrorMessages
from app.services.audio_service import AudioService

# Set up logger
logger = logging.getLogger(__name__)

# Create uploads directory if it doesn't exist
UPLOAD_DIR = Path("app/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Define valid audio file extensions
VALID_AUDIO_EXTENSIONS = ['.mp3', '.wav', '.m4a', '.aac', '.ogg', '.flac']

# Create router instance
router = APIRouter()

# ====================
# AUDIO ENDPOINTS
# ====================

@router.post("/audio2text", response_model=dict)
async def turn_to_text(
    audio_file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    """
    Converts an uploaded audio file to text using speech recognition.
    
    Args:
        audio_file (UploadFile): The audio file to transcribe.
            Supported formats include: mp3, wav, m4a, aac, ogg, flac
        current_user (dict): The authenticated user's information.
    
    Returns:
        dict: A dictionary containing:
            - audio_id: The ID of the saved audio record (if successful)
            - transcription: The transcribed text or an error message
            - success: Boolean indicating whether transcription was successful
    """
    # Initialize audio service
    audio_service = AudioService()
    user_id = str(current_user["_id"])
    
    try:
        # Step 1: Transcribe the audio file
        transcription, temp_file_path = audio_service.transcribe_audio(audio_file)
        
        # Step 2: Process audio for feedback and check success
        processing_result = audio_service.process_audio_for_feedback(
            transcription=transcription,
            user_id=user_id,
            conversation_id="",  # Not linked to conversation yet
            audio_id=None
        )
        
        # Step 3: If transcription was successful, save the file permanently
        if processing_result["success"]:
            try:
                # Reset file pointer to beginning of file for save operation
                audio_file.file.seek(0)
                
                # Save the audio file permanently
                audio_id = audio_service.save_audio_file(audio_file, user_id)
                
                # Update the processing result with audio_id
                processing_result["audio_id"] = audio_id
                
                # Clean up temporary file
                audio_service.cleanup_temp_file(temp_file_path)
                
                return {
                    "audio_id": audio_id,
                    "transcription": transcription,
                    "success": True
                }
                
            except Exception as e:
                logger.error(f"Error saving audio after successful transcription: {str(e)}")
                # Even if saving fails, return the transcription to the user
                audio_service.cleanup_temp_file(temp_file_path)
                return {
                    "audio_id": None,
                    "transcription": transcription,
                    "success": True,
                    "warning": "Transcription successful but audio storage failed"
                }
        else:
            # Transcription failed - clean up temp file and return error
            audio_service.cleanup_temp_file(temp_file_path)
            return {
                "audio_id": None,
                "transcription": transcription,
                "success": False
            }
            
    except Exception as e:
        logger.error(f"Error in audio transcription endpoint: {str(e)}")
        return {
            "audio_id": None,
            "transcription": "Error processing audio file",
            "success": False,
            "error": str(e)
        }


# POST /audio/upload - Upload audio file (to be implemented)
# This endpoint will handle raw audio file uploads

# GET /audio/{audio_id} - Get audio file details (to be implemented)
# This endpoint will retrieve audio file metadata and transcription

# POST /audio/{audio_id}/transcribe - Transcribe specific audio (to be implemented)
# This endpoint will trigger transcription for a previously uploaded audio file

# DELETE /audio/{audio_id} - Delete audio file (to be implemented)
# This endpoint will handle audio file deletion and cleanup 