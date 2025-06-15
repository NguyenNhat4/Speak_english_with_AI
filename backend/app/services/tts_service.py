"""
TTS (Text-to-Speech) Service for handling TTS-related business logic.

This service manages text-to-speech conversion, voice selection,
and speech generation for the SpeakAI application.
"""

import logging
from typing import Dict, Any, Optional, Generator
from fastapi import HTTPException
from fastapi.responses import StreamingResponse

from app.utils.tts_client_service import (
    text_to_speech_streaming,
    text_to_speech_with_context,
    pick_suitable_voice_name
)

logger = logging.getLogger(__name__)


class TTSService:
    """
    Service class for handling TTS business logic.
    
    This service acts as a wrapper around existing TTS utilities
    and provides a clean interface for text-to-speech operations.
    """
    
    def __init__(self):
        """Initialize the TTS service."""
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def generate_speech_streaming(
        self,
        text: str,
        voice_name: Optional[str] = None,
        language_code: str = "en-US"
    ) -> Generator[bytes, None, None]:
        """
        Generate streaming speech from text.
        
        Args:
            text (str): The text to convert to speech
            voice_name (Optional[str]): The voice name to use
            language_code (str): The language code for speech generation
            
        Returns:
            Generator[bytes, None, None]: Streaming audio data
            
        Raises:
            HTTPException: If speech generation fails
        """
        try:
            if not text or not text.strip():
                raise HTTPException(
                    status_code=400,
                    detail="Text is required for speech generation"
                )
            
            # Generate streaming speech
            audio_stream = text_to_speech_streaming(
                text=text,
                voice_name=voice_name,
                language_code=language_code
            )
            
            self.logger.debug(f"Generated streaming speech for text length: {len(text)}")
            return audio_stream
            
        except Exception as e:
            self.logger.error(f"Failed to generate streaming speech: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Speech generation failed: {str(e)}"
            )
    
    def generate_speech_with_context(
        self,
        text: str,
        conversation_context: Dict[str, Any],
        voice_name: Optional[str] = None
    ) -> Generator[bytes, None, None]:
        """
        Generate speech with conversation context.
        
        Args:
            text (str): The text to convert to speech
            conversation_context (Dict[str, Any]): The conversation context
            voice_name (Optional[str]): The voice name to use
            
        Returns:
            Generator[bytes, None, None]: Streaming audio data
            
        Raises:
            HTTPException: If speech generation fails
        """
        try:
            if not text or not text.strip():
                raise HTTPException(
                    status_code=400,
                    detail="Text is required for speech generation"
                )
            
            # Generate speech with context
            audio_stream = text_to_speech_with_context(
                text=text,
                conversation_context=conversation_context,
                voice_name=voice_name
            )
            
            self.logger.debug(f"Generated contextual speech for text length: {len(text)}")
            return audio_stream
            
        except Exception as e:
            self.logger.error(f"Failed to generate contextual speech: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Contextual speech generation failed: {str(e)}"
            )
    
    def select_suitable_voice(
        self,
        gender: str,
        language_code: str = "en-US"
    ) -> str:
        """
        Select a suitable voice based on gender and language.
        
        Args:
            gender (str): The desired gender (male/female)
            language_code (str): The language code
            
        Returns:
            str: The selected voice name
            
        Raises:
            HTTPException: If voice selection fails
        """
        try:
            if not gender or gender.lower() not in ['male', 'female']:
                raise HTTPException(
                    status_code=400,
                    detail="Valid gender (male/female) is required"
                )
            
            voice_name = pick_suitable_voice_name(gender)
            
            self.logger.debug(f"Selected voice '{voice_name}' for gender: {gender}")
            return voice_name
            
        except Exception as e:
            self.logger.error(f"Failed to select suitable voice: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Voice selection failed: {str(e)}"
            )
    
    def create_streaming_response(
        self,
        audio_stream: Generator[bytes, None, None],
        filename: str = "speech.mp3"
    ) -> StreamingResponse:
        """
        Create a streaming response for audio data.
        
        Args:
            audio_stream (Generator[bytes, None, None]): The audio stream
            filename (str): The filename for the response
            
        Returns:
            StreamingResponse: The streaming response object
        """
        try:
            return StreamingResponse(
                audio_stream,
                media_type="audio/mpeg",
                headers={
                    "Content-Disposition": f"attachment; filename={filename}",
                    "Cache-Control": "no-cache"
                }
            )
            
        except Exception as e:
            self.logger.error(f"Failed to create streaming response: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to create audio response: {str(e)}"
            ) 