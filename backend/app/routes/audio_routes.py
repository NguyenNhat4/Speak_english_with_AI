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
    # Initialize services
    from app.utils.speech_service import SpeechService
    speech_service = SpeechService()
    user_id = str(current_user["_id"])
    
    # Step 1: Try to transcribe the audio from a temporary file
    transcription, temp_file_path = speech_service.transcribe_from_upload(audio_file)
    
    # Step 2: Check if transcription was successful
    transcription_successful = transcription != TranscriptionErrorMessages.DEFAULT_FALLBACK_ERROR.value and transcription != TranscriptionErrorMessages.EMPTY_TRANSCRIPTION.value
    
    # Step 3: If transcription was successful, save the file permanently
    if transcription_successful:
        try:
            # Reset file pointer to beginning of file for save operation
            audio_file.file.seek(0)
            
            # Now save the audio file permanently since transcription was successful
            file_path, audio_model = speech_service.save_audio_file(audio_file, user_id)
            audio_id = str(audio_model._id)
            
            # Update audio record with transcription
            db.audio.update_one(
                {"_id": ObjectId(audio_id)},
                {"$set": {"transcription": transcription, "has_error": False}}
            )
            
            # Clean up the temporary file since we've saved it properly now
            import os
            if temp_file_path and os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
                
            # Return success response
            return {
                "audio_id": audio_id,
                "transcription": transcription,
                "success": True
            }
            
        except Exception as e:
            logger.error(f"Error saving audio after successful transcription: {str(e)}")
            # Even if saving fails, return the transcription to the user
            return {
                "audio_id": None,
                "transcription": transcription,
                "success": True,
                "warning": "Transcription successful but audio storage failed"
            }
    else:
        # Transcription failed - clean up temp file and return error
        if temp_file_path:
            import os
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
                
        # Return error response with consistent format
        return {
            "audio_id": None,
            "transcription": transcription,
            "success": False
        }


# POST /audio/upload - Upload audio file (to be implemented)
# This endpoint will handle raw audio file uploads

# GET /audio/{audio_id} - Get audio file details (to be implemented)
# This endpoint will retrieve audio file metadata and transcription

# POST /audio/{audio_id}/transcribe - Transcribe specific audio (to be implemented)
# This endpoint will trigger transcription for a previously uploaded audio file

# DELETE /audio/{audio_id} - Delete audio file (to be implemented)
# This endpoint will handle audio file deletion and cleanup 