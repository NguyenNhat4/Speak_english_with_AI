import json
import logging
from typing import Dict, Any, Optional, List, Tuple, Union
from datetime import datetime
from bson import ObjectId
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import shutil
from fastapi import UploadFile, File
# Import Gemini client
from app.utils.gemini import generate_response
from app.config.database import db
from app.models.feedback import Feedback
from app.models.results.feedback_result import FeedbackResult

logger = logging.getLogger(__name__)


UPLOAD_DIR = Path("app/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
VALID_AUDIO_EXTENSIONS = ['.mp3', '.wav', '.m4a', '.aac', '.ogg', '.flac']

# Only configure if not already configured
if not logger.handlers:
    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Ensure logs directory exists
    os.makedirs("app/logs", exist_ok=True)
    
    # Create rotating file handler (limits log file size)
    file_handler = RotatingFileHandler(
        "app/logs/feedback_service.log", 
        maxBytes=10485760,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    
    # Optional: Add console handler for development
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)
    
    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    # Set logger level
    logger.setLevel(logging.DEBUG)


# Add the handler to the logger

class FeedbackService:
    """
    Service for generating language feedback using Gemini API.
    
    This service provides functionality to:
    1. Generate user-friendly feedback for a user's speech
    2. Build prompts for Gemini that ask for feedback
    3. Parse and validate the response from Gemini
    4. Store feedback in the database
    """
        
    async def process_speech_feedback(
        self,
        transcription: str,
        user_id: str,
        conversation_id: str,
        audio_id: str,
        file_path: str,
        user_message_id: str
    ):
        """
        Process speech feedback in the background.
        
        This function handles the feedback generation and storing part that
        was separated from the main speech analysis to allow quick responses.
        
        Args:
            transcription (str): The transcribed text from the audio
                The text content that will be analyzed for feedback
            user_id (str): ID of the user who submitted the audio
                Used to associate feedback with the user
            conversation_id (str): ID of the conversation
                Used to fetch conversation context for better feedback
            audio_id (str): ID of the stored audio record
                References the audio file in the database
            file_path (str): Path to the saved audio file
                Location of the audio file on disk
            user_message_id (str): ID of the user's message
                Used to link the generated feedback to the message
        
        Returns:
            None: This is a background task that doesn't return a value directly
            
        Side Effects:
            - Creates a feedback record in the database
            - Updates the user's message with the feedback_id
            - Triggers mistake extraction for learning purposes
        """
        try:
            # Initialize services
            from app.utils.feedback_service import FeedbackService
            from app.utils.event_handler import event_handler
            from app.models.results.feedback_result import FeedbackResult
            
            
            # Fetch conversation context
            context = {}
            conversation = db.conversations.find_one({"_id": ObjectId(conversation_id)})
            if conversation:
                # Fetch messages to build context
                messages = list(db.messages.find({"conversation_id": ObjectId(conversation_id)})
                            .sort("timestamp", 1)
                            .limit(10))
                
                # Format previous exchanges
                previous_exchanges = []
                for msg in messages:
                    sender = "User" if msg.get("sender") == "user" else "AI"
                    previous_exchanges.append(f"{sender}: {msg.get('content', '')}")
                
               
                context = {
                    "user_role": conversation.get("user_role", "Student"),
                    "ai_role": conversation.get("ai_role", "Teacher"),
                    "situation": conversation.get("situation", "General conversation"),
                    "previous_exchanges": "\n".join(previous_exchanges)
                }
            # Generate feedback
            try:
                feedback_result = self.generate_dual_feedback(transcription, context)
            except Exception as e:
                logger.error(f"Error generating feedback: {str(e)}", exc_info=True)
                # Create a fallback feedback result
                feedback_result = FeedbackResult(
                    user_feedback="Unable to generate detailed feedback at this time."
                )
            
            # Store feedback
            feedback_id = self.store_feedback(
                user_id, 
                feedback_result, 
                user_message_id,
                transcription=transcription
            )
            
            # Link feedback to message
            if feedback_id:
                db.messages.update_one(
                    {"_id": ObjectId(user_message_id)},
                    {"$set": {"feedback_id": feedback_id}}
                )
                
            
                
        except Exception as e:
            logger.error(f"Error processing speech feedback in background: {str(e)}", exc_info=True)

    async def save_audio_file(self,file: UploadFile, user_id: str) -> str:
        """
        Save an uploaded audio file to the server.
        
        Args:
            file (UploadFile): The audio file to save
                FastAPI UploadFile object containing the audio data
            user_id (str): ID of the user
                Used to create user-specific directories for organization
            
        Returns:
            str: Path to the saved file on disk
                Absolute file path that can be used to access the file later
        
        Side Effects:
            - Creates a user directory if it doesn't exist
            - Writes the audio file to disk with a timestamped filename
        """
        # Create user directory if it doesn't exist
        user_dir = UPLOAD_DIR / str(user_id)
        user_dir.mkdir(exist_ok=True)
        
        # Generate unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_filename = f"{timestamp}_{file.filename.replace(' ', '_')}"
        file_path = user_dir / safe_filename
        
        # Save the file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        return str(file_path)

    def generate_dual_feedback(
        self, 
        transcription: str, 
        context: Optional[Dict[str, Any]] = None
    ) -> FeedbackResult:
        """
        Generate user-friendly feedback for speech using Gemini.
        
        Args:
            transcription: Transcribed text from the user's speech
            context: Optional conversation context information
            
        Returns:
            FeedbackResult containing user_feedback
        """
        try:
            
            # Build prompt for dual feedback
            prompt = self._build_dual_feedback_prompt(transcription, context)


            # Call Gemini API   
            gemini_response = generate_response(prompt)
                        # Clean the response text by removing markdown formatting
            cleaned_text = gemini_response.strip()
            if cleaned_text.startswith("```json"):
                cleaned_text = cleaned_text[7:]  # Remove ```json prefix
            if cleaned_text.endswith("```"):
                cleaned_text = cleaned_text[:-3]  # Remove ``` suffix
            cleaned_text = cleaned_text.strip()
            # parse the json
            

            # Parse JSON response
            
            try:
               
                
            
                # Create and return FeedbackResult
                return FeedbackResult(
                    user_feedback=cleaned_text
                )
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse Gemini response as JSON: {e}")
                logger.debug(f"Raw response: {cleaned_text}")
                # Fall back to basic feedback
                return self._generate_fallback_feedback(transcription)
                
        except Exception as e:
            logger.error(f"Error generating feedback: {str(e)}")
            return self._generate_fallback_feedback(transcription)

    def store_feedback(
        self, 
        user_id: str, 
        feedback_data: Union[FeedbackResult, Dict[str, Any]], 
        user_message_id: Optional[str] = None, 
        transcription: Optional[str] = None
    ) -> str:
        """
        Store feedback in the database.
        
        Args:
            user_id: ID of the user who received the feedback
            feedback_data: Feedback data to store (FeedbackResult or dict)
            conversation_id: Optional ID of the associated conversation
            transcription: Optional transcription text
            
        Returns:
            ID of the stored feedback
        """
        try:
            # Validate required parameters
            if not user_id:
                logger.warning("Missing user_id for feedback storage")
                user_id = "unknown_user"  # Fallback value
            
            # Convert string IDs to ObjectIds
            try:
                user_object_id = ObjectId(user_id)
            except Exception as e:
                logger.warning(f"Invalid user_id format: {user_id}. Using generic ObjectId.")
                user_object_id = ObjectId()
            
            target_id = ObjectId(user_message_id) if user_message_id else ObjectId()
            
            # Process feedback data based on type
            if isinstance(feedback_data, FeedbackResult):
                user_feedback = feedback_data.user_feedback
            else:
                user_feedback = feedback_data.get("user_feedback", "")
                
            
            
            # Create feedback model with explicit user_id and transcription
            feedback = Feedback(
                user_id=user_object_id,
                target_id=target_id,
                target_type="message" if user_message_id else "conversation",
                transcription=transcription,
                user_feedback=user_feedback,
            )
            
            # Insert feedback into database
            result = db.feedback.insert_one(feedback.to_dict())
            
            # If associated with a conversation, update the conversation record
            if user_message_id:
                db.conversations.update_one(
                    {"_id": ObjectId(user_message_id)},
                    {"$push": {"feedback_ids": str(result.inserted_id)}}
                )
            
            # Return the feedback ID as a string
            return str(result.inserted_id)
                
        except Exception as e:
            logger.error(f"Error storing feedback: {str(e)}")
            raise Exception(f"Failed to store feedback: {str(e)}")

    def _build_dual_feedback_prompt(
        self, 
        transcription: str, 
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Build prompt for generating user feedback.
        
        Args:
            transcription: Transcribed text from the user's speech
            context: Optional conversation context information
            
        Returns:
            Formatted prompt string for Gemini
        """
        prompt = ""
        previous_exchanges =  f"""  \"\"\"{context.get('previous_exchanges', 'No previous exchanges')  }\"\"\"  """

        
        # Add context if available
        if context:
            prompt += f"""
            Context:
            - User role: {context.get('user_role', 'Student')}
            - AI role: {context.get('ai_role', 'Teacher')}
            - Situation: {context.get('situation', 'General conversation')}
            
            Previous exchanges:
             {previous_exchanges}
            """
        
        # Add user role and AI role        
        # Add transcription
        prompt += f"""
        Current student's speech: "{transcription}"
        you are an expert English teacher providing feedback on a student's speech. this feedback will be showned when user click feedback button, dont greet the user or say anything else.
        Note: because user speech is transcribed from audio, it may not contain punctuation. you do not need comment on this. 
        Generate  feedback in string format:
        Hãy đưa ra nhận xét và hướng dẫn như một người bản xứ nói tiếng Anh có thể sử dụng tiếng Việt để giải thích:
                -Phân tích câu trả lời của người học và chỉ ra các lỗi về ngữ pháp và từ vựng.
                -Cung cấp gợi ý hoặc ví dụ về cách dùng từ/cụm từ tốt hơn để diễn đạt tự nhiên hơn
                -Đưa ra 2-3 phiên bản câu hoàn chỉnh hơn, sát với câu gốc nhưng đúng hơn, phù hợp với trình độ người học.
                -Phân tích cấu trúc ngữ pháp (mental model) của câu ví dụ bạn đưa ra: chỉ ra chủ ngữ, động từ, bổ ngữ, cách dùng mệnh đề phụ (nếu có), và chức năng giao tiếp của từng phần trong câu. ( nhớ so sánh  với câu gốc của người học)
                -Nếu câu trả lời của người học ngắn, chưa rõ ý, hoặc sai lệch hoàn toàn, hãy đưa ra một câu trả lời mẫu đơn giản hơn để họ có thể hình dung cách diễn đạt đúng, nhưng không nâng cấp quá xa so với trình độ hiện tại của họ.
            
        Return only the feedback string 
        
        """
        # prompt += f"""
        # user's speech: "{transcription}"
        # You are an expert, patient, and encouraging English language coach. You are fluent in both English and Vietnamese. Your primary goal is to provide clear, constructive, and actionable vietnamese feedback on the student's latest spoken English respone to help them improve.
        # This feedback will be displayed to the student when they click a "feedback" button. Therefore, DO NOT include any greetings (e.g., "Hello"), introductions, or concluding remarks (e.g., "Keep practicing!"). Focus solely on delivering the core feedback in vietnamese .

        # Important Note: The student's speech is transcribed from audio and may lack punctuation (commas, periods, question marks, etc.). Do not comment on the absence of punctuation in the transcription.

        # Generate the feedback as a single string. Please structure your feedback clearly , using Vietnamese for explanations where it significantly aids clarity, especially for grammatical concepts or nuanced corrections. 
        
        #     lưu ý điều này: người dùng là người việt luyện nói tiếng anh , nên là họ sẽ diễn đạt ý không trôi chảy, không tự nhiên, sai ngữ pháp. bạn có thể đoán ý họ một chút dựa trên context để đưa ra feedback
        #     - Bắt đầu bằng một nhận xét ngắn gọn, mang tính xây dựng (nếu có thể, hãy tìm một điểm tích cực nhỏ trước khi chỉ ra lỗi).
        #         Chỉ ra nhận xét câu trả lời trong bối cảnh tình huống và ngữ cảnh.
        #         Chỉ ra cụ thể các lỗi về ngữ pháp (grammar) và từ vựng (vocabulary) trong câu của học viên. 
        #         Ví dụ: "In the phrase '...', the verb tense should be '...' instead of '...' because..."
        #         Giải thích ngắn gọn bằng tiếng Việt tại sao đó là lỗi và cách sửa đúng. giải thích tại sao lại như vậy. tập trung vào cái mental model (của người bản xứ ) mà người dung cần hiểu để tránh mắc lỗi tương tự trong tương lai.
        #         Ví dụ: "Ở đây, bạn nên dùng thì quá khứ đơn vì hành động đã xảy ra và kết thúc trong quá khứ."

        
        #     - Tiếp theo, Nếu có, cung cấp các gợi ý hoặc ví dụ về từ/cụm từ thay thế giúp diễn đạt ý của học viên một cách tự nhiên và chính xác hơn, gần với cách người bản xứ thường dùng.
        #         Ví dụ: "thay vì nói  '...', dùng cái này sẽ tự nhiên hơn '...'."
        #         Sau đó giải thích lựa chọn ,giải thích tại sao lựa chọn đó lại tự nhiên hơn . 

        #     - Câu Hoàn chỉnh/Câu Mẫu:
        #         Đưa ra một phiên bản câu đã được sửa lỗi, hoàn chỉnh hơn, và đúng ngữ pháp. Cố gắng giữ ý chính của câu gốc và điều chỉnh cho phù hợp với trình độ ước tính của người học (không làm câu quá phức tạp nếu câu gốc đơn giản).

        #         Ví dụ (Original): "I go to school yesterday."
        #         Ví dụ (Corrected): "I went to school yesterday."
        #         Trường hợp đặc biệt nếu có(Special Case):** Nếu câu trả lời gốc của người học rất ngắn, quá tối nghĩa, hoặc sai lệch nhiều về ý, hãy đưa ra một câu trả lời mẫu đơn giản, rõ ràng hơn để họ có thể hình dung cách diễn đạt đúng. Câu mẫu này nên dễ hiểu và không nâng cao độ khó quá xa so với trình độ hiện tại của họ.
        #         Ví dụ (Original, unclear): "School good."
        #         Ví dụ (Simpler Model): "Going to school is good for learning." or "I like my school." (tùy ngữ cảnh)

        #     - Phân tích Cấu trúc Ngữ pháp của Câu BẠN Đề xuất :**
        #         Phân tích cấu trúc ngữ pháp, sử dụng từ  (mental model) của câu ví dụ hoàn chỉnh/câu mẫu **bạn vừa đưa ra ở mục 3**.
        #         Chức năng giao tiếp (Communicative Function):** Giải thích ngắn gọn chức năng giao tiếp của từng thành phần chính trong câu đó (ví dụ: chủ ngữ thực hiện hành động, mệnh đề phụ chỉ lý do, tân ngữ là đối tượng bị tác động). Giải thích bằng tiếng Việt nếu cần cho rõ nghĩa.
        #         So sánh cấu trúc (Structural Comparison):** So sánh cấu trúc câu bạn đề xuất với câu gốc của người học (nếu có sự khác biệt đáng kể). Chỉ ra những điểm khác biệt chính (ví dụ: trật tự từ, lựa chọn thì, cách dùng từ nối, loại từ) và giải thích bằng tiếng Việt tại sao sự thay đổi đó làm cho câu trở nên đúng ngữ pháp hơn hoặc tự nhiên/chuẩn hơn.
        #         Ví dụ: "Trong câu gốc của bạn ('I go school'), thiếu động từ 'to be' hoặc giới từ. Câu đề xuất của tôi ('I go to school') sử dụng giới từ 'to' để chỉ hướng đến 'school', đây là cấu trúc chuẩn."

        # Return ONLY the feedback string.
        # """
        logger.info(f"Generated prompt for Gemini: {prompt}")
        return prompt

    def _generate_fallback_feedback(self, transcription: str) -> FeedbackResult:
        """
        Generate fallback feedback when the API call fails.
        
        Args:
            transcription: Transcribed text from user's speech
            
        Returns:
            Basic FeedbackResult with minimal content
        """
        return FeedbackResult(
            user_feedback="Thank you for your response. I had trouble analyzing it in detail, but please continue practicing.",
          
        ) 
        
        
