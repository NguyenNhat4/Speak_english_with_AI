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

# POST /audio2text - Convert audio to text
# This endpoint will handle audio file upload and speech-to-text conversion

# POST /audio/upload - Upload audio file (to be implemented)
# This endpoint will handle raw audio file uploads

# GET /audio/{audio_id} - Get audio file details (to be implemented)
# This endpoint will retrieve audio file metadata and transcription

# POST /audio/{audio_id}/transcribe - Transcribe specific audio (to be implemented)
# This endpoint will trigger transcription for a previously uploaded audio file

# DELETE /audio/{audio_id} - Delete audio file (to be implemented)
# This endpoint will handle audio file deletion and cleanup 