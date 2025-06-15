from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.responses import JSONResponse
from bson import ObjectId
from typing import List, Optional
import logging
import asyncio
from datetime import datetime

from app.config.database import db
from app.schemas.message import MessageCreate, MessageResponse
from app.models.message import Message
from app.utils.auth import get_current_user
from app.utils.gemini import generate_response
from app.utils.feedback_service import FeedbackService

# Set up logger
logger = logging.getLogger(__name__)

# Initialize feedback service
feedback_service = FeedbackService()

# Create router instance
router = APIRouter()

# ====================
# MESSAGE ENDPOINTS
# ====================

@router.post("/conversations/{conversation_id}/message", response_model=dict)
async def add_message_and_get_response (
    conversation_id: str,  
    audio_id: str ,  
    current_user: dict = Depends(get_current_user),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """
    Process speech audio and return an AI response.
    
    This endpoint:
    1. Retrieves the transcribed audio using the provided audio_id
    2. Adds the user's message to the conversation
    3. Generates an AI response based on conversation context
    4. Handles feedback generation in the background
    """   
    try:
                user_id = str(current_user["_id"])
                
                # MongoDB find_one is not a coroutine, we need to wrap these in async functions
                async def get_audio():
                    return db.audio.find_one({"_id": ObjectId(audio_id)})
                    
                async def get_conversation():
                    return db.conversations.find_one({
                        "_id": ObjectId(conversation_id),
                        "user_id": ObjectId(user_id)
                    })
         
                # Step 1: Fetch the audio and conversation data    
                # Now create tasks from the async functions
                audio_task = asyncio.create_task(get_audio())
                conversation_task = asyncio.create_task(get_conversation())
                
                # Gather the results
                audio_data, conversation = await asyncio.gather(audio_task, conversation_task)

                if not conversation:
                    raise HTTPException(status_code=404, detail="Conversation not found")
                
            
            
                user_message = Message(
                    conversation_id=ObjectId(conversation_id),
                    sender="user",
                    content=audio_data["transcription"],
                    audio_path=audio_data["file_path"],
                    transcription=audio_data["transcription"]
                )
                
                db.messages.insert_one(user_message.to_dict())
                background_tasks.add_task(
                    feedback_service.process_speech_feedback,
                    transcription=audio_data["transcription"],
                    user_id=user_id,
                    conversation_id=conversation_id,
                    audio_id=audio_data["_id"],
                    file_path=audio_data["file_path"],
                    user_message_id=str(user_message._id)
                )
                # Fetch conversation history
                messages = list(db.messages.find({"conversation_id": ObjectId(conversation_id)}).sort("timestamp", 1))
                
                # Include context in the prompt 
                prompt = (
                f"You are playing the role of {conversation['ai_role']} and the user is {conversation['user_role']}. "
                f"The situation is: {conversation['situation']}. "
                f"Stay fully in character as {conversation['ai_role']}. "
                f"Use natural, simple English that new and intermediate learners can easily understand. "
                f"Keep your response short and litterly alike the role you are in (1 to 4 sentences). "
                f"Avoid special characters like brackets or symbols. "
                f"Do not refer to the user with any placeholder like a name in brackets. Dont include asterisk in your response. "
                f"Ask an open-ended question that fits the situation and encourages the user to speak more."
                f"\nHere is the conversation so far:\n" +
                "\n".join([f"{msg['sender']}: {msg['content']}" for msg in messages]) +
                f"\nNow respond as {conversation['ai_role']}."
                )

                
                # Generate AI response
                ai_text = generate_response(prompt)
                
                # Store AI response
                ai_message =  Message(conversation_id=ObjectId(conversation_id), sender="ai", content=ai_text)
                db.messages.insert_one(ai_message.to_dict())
                
                # Return AI response in MessageResponse format
                ai_message_dict = ai_message.to_dict()
                ai_message_dict["id"] = str(ai_message_dict["_id"])
                ai_message_dict["conversation_id"] = str(ai_message_dict["conversation_id"])
                del ai_message_dict["_id"]
                
                user_message_dict = user_message.to_dict()
                user_message_dict["id"] = str(user_message_dict["_id"])
                user_message_dict["conversation_id"] = str(user_message_dict["conversation_id"])
                del user_message_dict["_id"]
                
                return {
                    "user_message": MessageResponse(**user_message_dict),
                    "ai_message": MessageResponse(**ai_message_dict)
                }
            
       
    except Exception as e:
        logger.error(f"Error /conversations/{conversation_id}/speechtomessage: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed at /conversations/{conversation_id}/speechtomessage: {str(e)}"
        )


@router.get("/messages/{message_id}/feedback",response_model=dict)
async def get_message_feedback(
    message_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get user-friendly feedback for a specific message.
    
    This endpoint retrieves the stored feedback for a message when the user
    clicks the feedback button in the UI.
    """
    try:
        user_id = str(current_user["_id"])
        # Find the message
        message = db.messages.find_one({"_id": ObjectId(message_id)})
        if not message:
            logger.warning(f"Message not found: {message_id}")
            raise HTTPException(status_code=404, detail="Message not found")
        
        
        # Check if message has associated feedback
        feedback_id = message.get("feedback_id")
        if not feedback_id:
            logger.info(f"No feedback_id found for message: {message_id}, feedback may still be processing")
            # Feedback might still be processing
            return {"user_feedback": "Feedback is still being generated. Please try again in a moment.", "is_ready": False}
        
        logger.info(f"Found feedback_id: {feedback_id}, retrieving feedback document")
        
        # Get the feedback document
        try:
            feedback = db.feedback.find_one({"_id": ObjectId(feedback_id)})
            # Log the structure of the feedback document to understand its contents
            logger.info(f"Feedback document structure: {type(feedback).__name__}, keys: {list(feedback.keys()) if feedback else 'None'}")
        except Exception as e:
            logger.error(f"Error retrieving feedback document: {str(e)}", exc_info=True)
            return {"user_feedback": "Error retrieving feedback. Please try again later.", "is_ready": False}
            
        if not feedback:
            logger.warning(f"No feedback found with ID: {feedback_id}")
            return {"user_feedback": "No feedback available for this message.", "is_ready": False}
            
        # Handle feedback document safely
        try:
            # Create a safe copy with only the fields we need
            
            feedback_dict = {
                "id": str(feedback.get("_id", "")),
                "user_feedback": feedback.get("user_feedback", "Feedback content unavailable"),
                "created_at": feedback.get("created_at", datetime.now().isoformat())
            }
            
            # Add detailed feedback if available
            logger.info(f"Feedback document: {feedback_dict}")
            return {"user_feedback": feedback_dict, "is_ready": True}
        except Exception as e:
            logger.error(f"Error processing feedback document: {str(e)}", exc_info=True)
            return {"user_feedback": "Error processing feedback data. Please try again later.", "is_ready": False}
        
    except Exception as e:
        logger.error(f"Error getting message feedback: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get message feedback: {str(e)}"
        )


# GET /messages/{message_id} - Get message details (to be implemented)
# This endpoint will retrieve a specific message with its content and metadata

# PUT /messages/{message_id} - Update message (to be implemented)
# This endpoint will allow updating message content or metadata

# DELETE /messages/{message_id} - Delete message (to be implemented)
# This endpoint will handle message deletion

# GET /conversations/{conversation_id}/messages - List conversation messages (to be implemented)
# This endpoint will retrieve all messages for a specific conversation 