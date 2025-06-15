"""
AI Service for handling all AI-related business logic.

This service manages AI interactions, prompt building, and response processing
for the SpeakAI application.
"""

import json
import logging
from typing import Dict, Any, Optional
from fastapi import HTTPException

from app.utils.gemini import generate_response
from app.utils.tts_client_service import pick_suitable_voice_name

logger = logging.getLogger(__name__)


class AIService:
    """
    Service class for handling AI interactions and prompt processing.
    
    This service encapsulates all AI-related business logic including
    prompt building, response generation, and data validation.
    """
    
    def __init__(self):
        """Initialize the AI service."""
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def refine_conversation_context(
        self, 
        user_role: str, 
        ai_role: str, 
        situation: str
    ) -> Dict[str, Any]:
        """
        Refine conversation context using AI to create coherent scenarios.
        
        Args:
            user_role (str): The role of the user in the conversation
            ai_role (str): The role of the AI in the conversation  
            situation (str): The conversation situation/context
            
        Returns:
            Dict[str, Any]: Refined conversation context with all required fields
            
        Raises:
            HTTPException: If AI response processing fails
        """
        try:
            prompt = self._build_refinement_prompt(user_role, ai_role, situation)
            refined_response = self.generate_ai_response(prompt)
            
            # Clean the response format
            cleaned_response = refined_response.strip("```json\n").strip("\n```")
            
            # Parse and validate the response
            data_json = json.loads(cleaned_response)
            self._validate_refinement_response(data_json)
            
            # Pick suitable voice based on AI gender
            voice_type = pick_suitable_voice_name(data_json["ai_gender"])
            data_json["voice_type"] = voice_type
            
            self.logger.info(f"Successfully refined conversation context for roles: {user_role} -> {ai_role}")
            return data_json
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse JSON response: {e}\nResponse text: {cleaned_response}")
            raise HTTPException(
                status_code=500,
                detail="Failed to process AI response format"
            )
        except ValueError as e:
            self.logger.error(f"Invalid response format: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=str(e)
            )
        except Exception as e:
            self.logger.error(f"Unexpected error processing AI response: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail="An unexpected error occurred while processing the AI response"
            )
    
    def generate_ai_response(self, prompt: str) -> str:
        """
        Generate AI response for the given prompt.
        
        Args:
            prompt (str): The prompt to send to the AI
            
        Returns:
            str: The AI-generated response
            
        Raises:
            HTTPException: If AI generation fails
        """
        try:
            response = generate_response(prompt)
            if not response or not response.strip():
                raise ValueError("Empty response from AI service")
            
            self.logger.debug(f"Generated AI response with length: {len(response)}")
            return response
            
        except Exception as e:
            self.logger.error(f"Failed to generate AI response: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"AI response generation failed: {str(e)}"
            )
    
    def _build_refinement_prompt(
        self, 
        user_role: str, 
        ai_role: str, 
        situation: str
    ) -> str:
        """
        Build the prompt for refining roles and situation.
        
        Args:
            user_role (str): The user's role
            ai_role (str): The AI's role
            situation (str): The conversation situation
            
        Returns:
            str: The formatted prompt for AI refinement
        """
        return f"""
        You are an AI assistant designed to engage in role-playing scenarios to help new, intermediate English learners in a natural, real-life conversation. You will be provided with a user role, an AI role, and a situation. These inputs may be incomplete, vague, or inconsistent. Your task is to:

        Analyze the given user role, AI role, and situation.

        Refine them to create a coherent and logical scenario. This may involve:
    
        Adjusting roles or situations that don't make sense together (e.g., if the roles and situation are incompatible, modify them to align).

        Making assumptions where necessary to create a plausible context.

        Use word choice that matches new and intermediate levels, which means it's common and close to real-life.

        User role and AI role: 1-2 words. 

        Once you have a refined scenario, generate an appropriate initial response as the AI in that scenario.

        Return the refined roles, situation, and response as a JSON object.

        Return your output in the following JSON format:
        {{
        "refined_user_role": "[your refined user role]",
        "refined_ai_role": "[your refined AI role]",
        "refined_situation": "[your refined situation]",
        "response": "[your first  response as refined_ai_role to the user regardless of the situation  you can use a random name for the user and yourself]"
        "ai_gender": "[decide female or male base on the refined_ai_role,refined_situation ]" ]"
        }}

        Here are the inputs:
        User role: {user_role}
        AI role:  {ai_role}
        Situation: {situation}
        """
    
    def _validate_refinement_response(self, data_json: Dict[str, Any]) -> None:
        """
        Validate the AI refinement response contains all required fields.
        
        Args:
            data_json (Dict[str, Any]): The parsed JSON response to validate
            
        Raises:
            ValueError: If required fields are missing
        """
        required_fields = [
            "refined_user_role", 
            "refined_ai_role", 
            "refined_situation", 
            "response",
            "ai_gender"
        ]
        
        missing_fields = [field for field in required_fields if field not in data_json]
        if missing_fields:
            raise ValueError(f"Missing required fields in AI response: {', '.join(missing_fields)}")
        
        # Validate non-empty values
        empty_fields = [field for field in required_fields if not data_json[field].strip()]
        if empty_fields:
            raise ValueError(f"Empty values for required fields: {', '.join(empty_fields)}") 