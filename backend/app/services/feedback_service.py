"""
Feedback Service for handling feedback-related business logic.

This service manages feedback generation, processing, and analysis
for the SpeakAI application.
"""

import logging
from typing import Dict, Any, Optional
from fastapi import HTTPException

from app.utils.feedback_service import FeedbackService as UtilsFeedbackService
from app.utils.mistake_service import MistakeService as UtilsMistakeService

logger = logging.getLogger(__name__)


class FeedbackService:
    """
    Service class for handling feedback business logic.
    
    This service acts as a wrapper around existing feedback utilities
    and provides a clean interface for feedback operations.
    """
    
    def __init__(self):
        """Initialize the feedback service."""
        self.logger = logging.getLogger(self.__class__.__name__)
        self.feedback_utils = UtilsFeedbackService()
        self.mistake_utils = UtilsMistakeService()
    
    def generate_speech_feedback(
        self,
        transcription: str,
        user_id: str,
        conversation_id: str,
        audio_id: str,
        file_path: str,
        user_message_id: str
    ) -> Dict[str, Any]:
        """
        Generate feedback for speech transcription.
        
        Args:
            transcription (str): The transcribed text
            user_id (str): The ID of the user
            conversation_id (str): The ID of the conversation
            audio_id (str): The ID of the audio file
            file_path (str): Path to the audio file
            user_message_id (str): The ID of the user message
            
        Returns:
            Dict[str, Any]: Feedback generation results
            
        Raises:
            HTTPException: If feedback generation fails
        """
        try:
            # Use existing feedback service
            result = self.feedback_utils.process_speech_feedback(
                transcription=transcription,
                user_id=user_id,
                conversation_id=conversation_id,
                audio_id=audio_id,
                file_path=file_path,
                user_message_id=user_message_id
            )
            
            self.logger.info(f"Successfully generated feedback for user {user_id}")
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to generate speech feedback: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Feedback generation failed: {str(e)}"
            )
    
    def process_mistakes(
        self,
        feedback_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Process mistakes from feedback.
        
        Args:
            feedback_id (str): The ID of the feedback
            user_id (str): The ID of the user
            
        Returns:
            Dict[str, Any]: Mistake processing results
            
        Raises:
            HTTPException: If mistake processing fails
        """
        try:
            # Use existing mistake service
            result = self.mistake_utils.process_feedback_for_mistakes(
                feedback_id=feedback_id,
                user_id=user_id
            )
            
            self.logger.info(f"Successfully processed mistakes for feedback {feedback_id}")
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to process mistakes: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Mistake processing failed: {str(e)}"
            ) 