from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from bson import ObjectId
from typing import List, Optional
import logging
from datetime import datetime

from app.config.database import db
from app.schemas.conversation import ConversationCreate, ConversationResponse
from app.models.conversation import Conversation
from app.utils.auth import get_current_user
from app.utils.gemini import generate_response
from app.utils.tts_client_service import pick_suitable_voice_name
import json

# Set up logger
logger = logging.getLogger(__name__)

# Create router instance
router = APIRouter()

# =======================
# CONVERSATION ENDPOINTS
# =======================

@router.post("/conversations", response_model=dict)
async def create_conversation(convo_data: ConversationCreate, current_user: dict = Depends(get_current_user)):
    """
    Create a new conversation and generate an initial AI response.
    
    Args:
        convo_data (ConversationCreate): Conversation creation data containing user_role, ai_role, and situation.
        current_user (dict): The authenticated user's information.
        
    Returns:
        dict: A dictionary containing the conversation and initial message.
            
    Raises:
        HTTPException: If there are any errors during conversation creation.
    """
    from app.models.message import Message
    from app.schemas.message import MessageResponse

    # refine the promt to make it more accurate and complete or make sense
    promt_to_refine_roles_and_situation = f"""
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
        User role: {convo_data.user_role}
        AI role:  {convo_data.ai_role}
        Situation: {convo_data.situation}
        """
    # generate the refined response
    refined_response = generate_response(promt_to_refine_roles_and_situation)
    cleaned_response = refined_response.strip("```json\n").strip("\n```")

    
    try:
        data_json = json.loads(cleaned_response)
        required_fields = ["refined_user_role", "refined_ai_role", "refined_situation", "response","ai_gender"]
        missing_fields = [field for field in required_fields if field not in data_json]
        if missing_fields:
            raise ValueError(f"Missing required fields in response: {', '.join(missing_fields)}")
       
        voice_type =   pick_suitable_voice_name(data_json["ai_gender"] )    
        refined_user_role = data_json["refined_user_role"]
        refined_ai_role = data_json["refined_ai_role"]
        refined_situation = data_json["refined_situation"]
        ai_first_response = data_json["response"]
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON response: {e}\nResponse text: {cleaned_response}")
        raise HTTPException(
            status_code=500,
            detail="Failed to process AI response format"
        )
    except ValueError as e:
        logger.error(f"Invalid response format: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error processing response: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while processing the response"
        )

    # Get user ID from the current_user dictionary
    user_id = current_user.get("_id")
    if not user_id:
        raise HTTPException(status_code=500, detail="User ID not found in token")

    new_convo = Conversation(
        user_id=ObjectId(user_id),
        user_role=refined_user_role,
        ai_role=refined_ai_role,
        situation=refined_situation,
        voice_type=voice_type
    )
    result = db.conversations.insert_one(new_convo.to_dict())
    conversation_id = result.inserted_id

    
    # create the initial ai message first
    initial_message = Message(
        conversation_id=conversation_id, 
        sender="ai", 
        content=ai_first_response
    )
    db.messages.insert_one(initial_message.to_dict())

    # Fetch the conversation and convert ObjectId fields to strings
    created_convo = db.conversations.find_one({"_id": conversation_id})
    created_convo["id"] = str(created_convo["_id"])
    created_convo["user_id"] = str(created_convo["user_id"])  # Convert user_id to string
    del created_convo["_id"]

    initial_message_dict = initial_message.to_dict()
    initial_message_dict["id"] = str(initial_message_dict["_id"])
    initial_message_dict["conversation_id"] = str(initial_message_dict["conversation_id"])
    del initial_message_dict["_id"]

    # Fetch conversation history
    messages = list(db.messages.find({"conversation_id": ObjectId(conversation_id)}).sort("timestamp", 1))
    history = [
        {"role": "user" if msg["sender"] == "user" else "model", "parts": [msg["content"]]}
        for msg in messages
    ]

    return {
        "conversation": ConversationResponse(**created_convo),
        "initial_message": MessageResponse(**initial_message_dict)
    }


# GET /conversations - List user conversations (to be implemented)
# This endpoint will retrieve all conversations for the authenticated user

# GET /conversations/{conversation_id} - Get conversation details (to be implemented)  
# This endpoint will retrieve a specific conversation with its metadata

# PUT /conversations/{conversation_id} - Update conversation (to be implemented)
# This endpoint will allow updating conversation settings or metadata

# DELETE /conversations/{conversation_id} - Delete conversation (to be implemented)
# This endpoint will handle conversation deletion and cleanup 