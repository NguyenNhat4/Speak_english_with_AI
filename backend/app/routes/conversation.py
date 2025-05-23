from fastapi import APIRouter, Depends, HTTPException
from app.config.database import db
from app.schemas.conversation import ConversationCreate, ConversationResponse
from app.schemas.message import MessageCreate, MessageResponse
from app.models.conversation import Conversation
from app.models.message import Message
from app.utils.auth import get_current_user
from app.utils.gemini import generate_response
from app.utils.transcription_error_message import TranscriptionErrorMessages
import json
import asyncio
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Body, Query, BackgroundTasks
from fastapi.responses import JSONResponse
from bson import ObjectId
from typing import List, Optional
from app.utils.feedback_service import FeedbackService
import os
import time
from app.utils.tts_client_service import get_speech_from_tts_service,pick_suitable_voice_name
import shutil
from pathlib import Path
from datetime import datetime
import base64
import logging
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
from app.utils.error_handler import get_not_found_exception, handle_general_exception
feedback_service = FeedbackService()

router = APIRouter()

# Create uploads directory if it doesn't exist
UPLOAD_DIR = Path("app/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Define valid audio file extensions
VALID_AUDIO_EXTENSIONS = ['.mp3', '.wav', '.m4a', '.aac', '.ogg', '.flac']

# Set up logger
logger = logging.getLogger(__name__)

logging.basicConfig(level=logging.INFO)


# Create a file handler for our logs
# Use existing logs directory under the backend folder
file_handler = logging.FileHandler("app/logs/conversation_logs.txt")
file_handler.setLevel(logging.INFO)


# Add the handler to the logger
logger.addHandler(file_handler)

router = APIRouter()

@router.post("/conversations", response_model=dict)
async def create_conversation(convo_data: ConversationCreate, current_user: dict = Depends(get_current_user)):
    """
    Create a new conversation and generate an initial AI response.
    
    Args:
        convo_data (ConversationCreate): Conversation creation data containing user_role, ai_role, and situation.
            Sample input:
            {
                "user_role": "a job seeker",
                "ai_role": "an experienced interviewer",
                "situation": "preparing for a software engineering job interview"
            }
        current_user (dict): The authenticated user's information.
            Sample input:
            {
                "_id": "507f1f77bcf86cd799439011",
                "name": "John Doe",
                "email": "john@example.com"
            }
        
    Returns:
        dict: A dictionary containing the conversation and initial message.
            Sample output:
            {
                "conversation": {
                    "id": "507f1f77bcf86cd799439012",
                    "user_id": "507f1f77bcf86cd799439011",
                    "user_role": "a job seeker",
                    "ai_role": "an experienced interviewer",
                    "situation": "preparing for a software engineering job interview",
                    "created_at": "2024-04-04T12:00:00"
                },
                "initial_message": {
                    "id": "507f1f77bcf86cd799439013",
                    "conversation_id": "507f1f77bcf86cd799439012",
                    "role": "ai",
                    "text": "Hello! I'll be your interviewer today...",
                    "created_at": "2024-04-04T12:00:00"
                }
            }
            
    Raises:
        HTTPException: If there are any errors during conversation creation.
    """

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
            Fields:
            - _id: User's ObjectId
            - email: User's email
            - role: User's role
    
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
    
    Args:
        conversation_id (str): ID of the conversation
            Path parameter identifying which conversation to add the message to
        audio_id (str): The ID of a previously uploaded and transcribed audio file
            This should be an ID returned from the /audio2text endpoint
        current_user (dict): The authenticated user's information
            Fields:
            - _id: User's ObjectId
            - email: User's email
            - role: User's role
        background_tasks (BackgroundTasks): FastAPI background tasks manager
            Used to process feedback generation asynchronously
        
    Returns:
        dict: Dictionary containing both the user's message and the AI's response
            Fields:
            - user_message: MessageResponse object with the transcribed user message
            - ai_message: MessageResponse object with the AI's generated response
            
            Each MessageResponse contains:
            - id: Message ID
            - conversation_id: ID of the conversation
            - sender: "user" or "ai"
            - content: The message text
            - timestamp: When the message was created
            - additional fields like audio_path, transcription (for user messages)
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
                
                # Process feedback in the background without blocking the response
              
                
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
    
    Args:
        message_id (str): ID of the message to get feedback for
            Path parameter that identifies which message's feedback to retrieve
        current_user (dict): Authenticated user information
            Fields:
            - _id: User's ObjectId
            - email: User's email
            - role: User's role
        
    Returns:
        dict: User-friendly feedback information
            Fields:
            - user_feedback: Either a string message (if feedback is not ready)
              or a dictionary containing the feedback details
            - is_ready: Boolean indicating if the feedback generation is complete
            
            When feedback is ready (is_ready=True), user_feedback contains:
            - id: Feedback document ID
            - user_feedback: Human-readable feedback text
            - created_at: Timestamp when feedback was generated
    """
    try:
        # Log the entry point with message ID for tracking
        
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


@router.get(
    "/messages/{message_id}/speech",
    summary="Get AI message audio stream",
    description="Retrieves an AI message's text, converts it to speech via an external TTS service, and streams the audio."
)
async def get_ai_message_as_speech_stream( 
    message_id: str,
    current_user: dict = Depends(get_current_user)
):
    try:
        start = time.time()
        
        logger.info(f"Getting AI message audio stream for message_id: {message_id}")
        message_object_id = ObjectId(message_id) # Convert string ID to ObjectId for MongoDB query
        message = db.messages.find_one({"_id": message_object_id})
        Conversation = db.conversations.find_one({"_id": message["conversation_id"]})
        conversation_voice_type = Conversation["voice_type"]
        end = time.time()
        logger.info(f"Time taken to fetch message and conversation: {end - start} seconds")
        if not message:
            raise HTTPException(status_code=404, detail="Message not found")

        # 2. Basic validation (optional but good)
        if message.get("sender") != "ai":
            raise HTTPException(status_code=400, detail="Speech can only be generated for AI messages")

        ai_text = message.get("content")
        if not ai_text:
            raise HTTPException(status_code=400, detail="AI Message has no text content to synthesize")

        default_lang_code = "en-US"     # Example: set to your primary language
        default_model_name = "kokoro"   # From your TTS API example
        default_response_format = "mp3"
        default_speed = 1.3

        return await get_speech_from_tts_service(
            text_to_speak=ai_text,
            voice_name=conversation_voice_type,
            model_name=default_model_name,
            response_format=default_response_format,
            speed=default_speed,
            lang_code=default_lang_code
        )

    except HTTPException as e:
        # If HTTPException was raised by us or  by get_speech_from_tts_service, re-raise it
        # print(f"ERROR: HTTPException in get_ai_message_as_speech_stream: {e.detail}")
        raise e
    except Exception as e:
        # Catch any other unexpected errors during DB access or other logic here
        # print(f"ERROR: Unexpected error in get_ai_message_as_speech_stream for message {message_id}: {str(e)}")
        # Consider logging 'e' with exc_info=True for full traceback
        raise HTTPException(status_code=500, detail=f"Failed to generate speech: An internal error occurred.")


@router.get(
    "/messages/demospeech",
    summary="Get AI message audio stream",
    description="Retrieves an AI message's text, converts it to speech via an external TTS service, and streams the audio."
)
async def get_ai_message_as_speech_stream_demo( 
    message: str = "Hello, how are you?"
):
    try:
        conversation_voice_type = "hm_omega"
        default_lang_code = "en-US"     # Example: set to your primary language
        default_model_name = "kokoro"   # From your TTS API example
        default_response_format = "mp3"
        default_speed = 1.3

        # 4. Call the TTS Service via your client function
        #    This function is expected to return a StreamingResponse
        start = time.time()
        stream_response = await get_speech_from_tts_service(
            text_to_speak=message,
            voice_name=conversation_voice_type,
            model_name=default_model_name,
            response_format=default_response_format,
            speed=default_speed,
            lang_code=default_lang_code
        )
        end = time.time()
        
        # Add timing information as a header instead of trying to return it with the stream
        stream_response.headers["X-Processing-Time"] = str(end - start)
        
        return stream_response
    except HTTPException as e:
        # If HTTPException was raised by us or by get_speech_from_tts_service, re-raise it
        # print(f"ERROR: HTTPException in get_ai_message_as_speech_stream: {e.detail}")
        raise e
    except Exception as e:
        # Catch any other unexpected errors during DB access or other logic here
        # print(f"ERROR: Unexpected error in get_ai_message_as_speech_stream for message {message_id}: {str(e)}")
        # Consider logging 'e' with exc_info=True for full traceback
        raise HTTPException(status_code=500, detail=f"Failed to generate speech: An internal error occurred.")

@router.get(
    "/messages/{message_id}/voice_context",
    summary="Get conversation voice type and latest AI message",
    description="Retrieves the conversation voice type and latest AI message based on the provided message ID."
)
async def get_voice_context(
    message_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get conversation voice type and latest AI message for the conversation containing the specified message.
    
    This endpoint is particularly useful for audio playback in the mobile app, as it provides
    both the voice type to use and the latest AI message that might need to be played.
    
    Args:
        message_id (str): ID of the message to use as a reference
            Path parameter used to identify which conversation to retrieve data from
        current_user (dict): Authenticated user information
            Fields:
            - _id: User's ObjectId
            - email: User's email
            - role: User's role
        
    Returns:
        dict: Voice context information
            Fields:
            - voice_type: The voice type to be used for TTS (e.g., "hm_omega", "jf_alpha")
            - latest_ai_message: Object containing the most recent AI message in the conversation
              - id: Message ID
              - content: Message text content
              - timestamp: When the message was created
            - is_latest: Boolean indicating if the referenced message is the latest AI message
            
    Raises:
        HTTPException 404: If the message or conversation is not found
        HTTPException 500: If any error occurs during processing
    """
    try:
        # Convert string ID to ObjectId for MongoDB query
        message_object_id = ObjectId(message_id)
        
        # Find the message
        message = db.messages.find_one({"_id": message_object_id})
        if not message:
            logger.warning(f"Message not found: {message_id}")
            raise HTTPException(status_code=404, detail="Message not found")
        
        # Get the conversation
        conversation_id = message["conversation_id"]
        conversation = db.conversations.find_one({"_id": conversation_id})
        if not conversation:
            logger.warning(f"Conversation not found for message: {message_id}")
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # Get the voice type from the conversation
        voice_type = conversation.get("voice_type", "hm_omega")  # Default to hm_omega if not found
        
        # Find the latest AI message in the conversation
        latest_ai_message = db.messages.find(
            {"conversation_id": conversation_id, "sender": "ai"}
        ).sort("timestamp", -1).limit(1)
        
        latest_ai_message_list = list(latest_ai_message)
        latest_ai_message_data = None
        is_latest = False
        
        if latest_ai_message_list:
            latest_msg = latest_ai_message_list[0]
            latest_ai_message_data = {
                "id": str(latest_msg["_id"]),
                "content": latest_msg.get("content", ""),
                "timestamp": latest_msg.get("timestamp", datetime.now().isoformat())
            }
            
        
       
        return {
            "voice_type": voice_type,
            "latest_ai_message": latest_ai_message_data,
        }
        
    except HTTPException as e:
        # Re-raise HTTP exceptions
        raise e
    except Exception as e:
        logger.error(f"Error getting voice context: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get voice context: {str(e)}"
        )

@router.get(
    "/messages/{message_id}/fallback_voice_context",
    summary="Get fallback voice context for any message ID",
    description="Provides voice context information without requiring the message to exist in the database."
)
async def get_fallback_voice_context(
    message_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get fallback voice context for any message ID without database validation.
    
    This endpoint is a reliable alternative to the /messages/{message_id}/voice_context endpoint
    when the message doesn't exist in the database. It always returns a valid response with
    the provided message ID as both the ID and content of the latest AI message.
    
    Args:
        message_id (str): Message ID to use in the response
        current_user (dict): Authenticated user information
        
    Returns:
        dict: Voice context information with the message ID as content
            Fields:
            - voice_type: Default voice type (jf_alpha)
            - latest_ai_message: Object containing the message ID as both ID and content
    """
    logger.info(f"Fallback voice context requested for message_id: {message_id}")
    
    # Create a timestamp in the expected format
    timestamp = datetime.utcnow().isoformat()
    
    return {
        "voice_type": "jf_alpha",
        "latest_ai_message": {
            "id": message_id,
            "content": "Hello, how can I help you today?",
            "timestamp": timestamp
        }
    }


