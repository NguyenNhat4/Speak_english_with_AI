# Speaking English With AI - Full-Stack Application

A comprehensive AI-powered English learning platform consisting of a Flutter mobile application with clean architecture and a FastAPI backend. The platform helps users improve their English speaking skills through real-time AI feedback, speech analysis, and interactive learning exercises.

## 🎯 Project Overview

This full-stack application provides an advanced platform for English language learning through:

### 🎤 Core AI Features
- **Speech-to-Text Conversion**: Record user voice and convert it to text using advanced speech recognition
- **AI Response with Realistic Voice**: Convert AI text responses to natural, realistic voice using text-to-speech technology
- **Image Description Practice**: Users speak descriptions of shown images to practice vocabulary and expression
- **Speech Correction & Analysis**: Get corrected versions of spoken text with detailed explanations
- **Grammar & Vocabulary Feedback**: Real-time analysis and feedback on grammar usage and vocabulary choices
- **Conversation Context**: AI maintains conversation context for more natural interactions

### 📚 Learning Features
- User authentication and profile management
- Interactive conversation practice with AI tutoring
- Multi-platform support (Android, iOS, Web, Desktop)


## 🎤 AI-Powered Features Deep Dive

### 1. Speech-to-Text Processing
- **Real-time transcription** of user speech using advanced speech recognition
- **Multi-language support** with focus on English learning
- **Noise cancellation** and audio optimization for better accuracy
- **Context-aware processing** for improved transcription quality

### 2. AI Response with Realistic Voice
- **Natural TTS integration** converts AI responses to human-like speech
- **Multiple voice options** with different accents and speaking styles
- **Emotion and intonation control** for more engaging conversations
- **Real-time audio streaming** for immediate feedback

### 3. Image Description Practice
```
User Flow:
1. App displays an image
2. User speaks their description
3. Speech is converted to text
4. AI analyzes the description quality
5. Provides corrections and suggestions
6. Offers alternative expressions and vocabulary
```

### 4. Speech Correction & Explanation
- **Grammar analysis** with detailed explanations
- **Vocabulary enhancement** suggestions
- **Sentence structure** improvements
- **Cultural context** explanations for idiomatic expressions



## 🚀 Getting Started

### Prerequisites

#### Backend Requirements
- Python 3.9+
- MongoDB 4.4+
- Google Gemini AI API key
- Docker & Docker Compose (optional)

#### Frontend Requirements
- Flutter SDK (>=3.4.3 <4.0.0)
- Dart SDK
- Android Studio / VS Code with Flutter extensions
- Git

### Installation & Setup

#### 1. Clone the Repository
```bash
git clone <repository-url>
cd speak_ai_flutter_app
```

#### 2. Backend Setup

**Option A: Docker (Recommended)**
```bash
cd backend

# For CPU-based deployment
docker-compose -f docker-compose.cpu.yml up -d

# For GPU-accelerated deployment
docker-compose -f docker-compose.gpu.yml up -d
```

**Option B: Local Development**
```bash
cd backend

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp env.txt .env
# Edit .env with your actual API keys and configuration

# Run the server
uvicorn app.main:app --reload
```

#### 3. Frontend Setup
```bash
cd mobile_clean_architecture

# Install Flutter dependencies
flutter pub get

# Generate code for JSON serialization and Hive adapters
flutter packages pub run build_runner build --delete-conflicting-outputs

# Run the application
flutter run
```

#### 4. Database Setup
```bash
# MongoDB connection string for local development
mongodb://admin:password@localhost:27017/speak_ai_db?authSource=admin

# Use MongoDB Compass or any MongoDB client to connect
```

## 📡 API Documentation

The backend provides comprehensive RESTful APIs:

### Audio Processing Endpoints
- `POST /api/audio/transcribe`: Convert speech to text
- `POST /api/audio/pronunciation`: Analyze pronunciation quality
- `POST /api/audio/analyze`: Complete speech analysis (transcription + feedback)
- `POST /api/audio/text-to-speech`: Convert text to realistic voice

### AI Learning Endpoints
- `POST /api/learning/image-description`: Process image description exercises
- `POST /api/learning/conversation`: Handle AI conversation interactions
- `POST /api/learning/correction`: Provide speech corrections and explanations
- `GET /api/learning/suggestions`: Get personalized learning suggestions

### User Management
- `POST /api/users/register`: User registration
- `POST /api/users/login`: Authentication
- `GET /api/users/me`: User profile
- `PUT /api/users/progress`: Update learning progress

**API Documentation**: Visit `http://localhost:8000/docs` for interactive Swagger documentation

## 🏛️ Clean Architecture Implementation

### Frontend Architecture (Flutter)
The mobile app follows **Clean Architecture** principles:

#### Domain Layer
- **Entities**: Core business objects (User, Conversation, Mistake)
- **Use Cases**: Business logic (TranscribeSpeech, AnalyzePronunciation)
- **Repository Interfaces**: Data access contracts

#### Data Layer
- **Models**: JSON serializable data structures
- **Repository Implementations**: API and local storage integration
- **Data Sources**: Remote (HTTP) and Local (Hive) data handling

#### Presentation Layer
- **BLoC/Cubit**: State management for complex business logic
- **Pages/Screens**: UI screens and navigation
- **Widgets**: Reusable UI components

#### Core Layer
- **Services**: Audio recording, AI integration, networking
- **Utils**: Shared utilities and helpers
- **Constants**: App-wide configuration

### Backend Architecture (FastAPI)
The backend follows **layered architecture**:

#### API Layer
- **Routes**: HTTP endpoint handlers
- **Schemas**: Request/response validation
- **Middleware**: Authentication, CORS, error handling

#### Service Layer
- **Audio Service**: Speech processing and TTS
- **AI Service**: Gemini AI integration
- **Learning Service**: Educational logic and algorithms
- **User Service**: Authentication and profile management

#### Data Layer
- **Models**: MongoDB document models
- **Repositories**: Data access layer
- **Database**: MongoDB with optimized indexes

## 🎨 Technology Stack

### Frontend (Flutter)
- **State Management**: BLoC pattern, Provider, Cubit
- **Local Storage**: Hive (NoSQL), SharedPreferences
- **Audio**: `record` package for recording, `just_audio` for playback
- **Networking**: HTTP client with connectivity checking
- **UI/UX**: Material Design 3, custom animations, responsive design
- **Navigation**: GoRouter for declarative routing

### Backend (Python/FastAPI)
- **Framework**: FastAPI with automatic API documentation
- **AI Integration**: Google Gemini AI for language processing
- **Speech Processing**: Whispir Open AI using turbo Model 
- **Database**: MongoDB with Motor async driver
- **Authentication**: JWT tokens with OAuth2 patterns
- **Deployment**: Docker containers with GPU support

### Infrastructure
- **Containerization**: Docker with multi-stage builds
- **Database**: MongoDB with replica sets
- **API Gateway**: FastAPI with automatic OpenAPI generation
- **Monitoring**: Structured logging and health checks


## 📱 Platform Support

### Mobile App
- ✅ Android (5.0+)
- ✅ iOS (11.0+)
- ✅ Web browsers
- ✅ Windows desktop
- ✅ macOS desktop
- ✅ Linux desktop

### Backend API
- ✅ Docker containers
- ✅ GPU acceleration support



## 📝 Documentation

- **API Documentation**: Interactive Swagger UI at `/docs`
- **Architecture Guide**: Clean architecture implementation
- **Feature Documentation**: Individual module READMEs

## 🤝 Contributing

### Development Workflow
1. Fork the repository
2. Create feature branches (`feature/speech-improvement`)
3. Follow coding standards and architecture patterns
4. Write comprehensive tests
5. Update documentation
6. Submit pull requests

### Code Standards
- **Frontend**: Flutter/Dart style guide with clean architecture
- **Backend**: PEP 8 Python standards with FastAPI best practices
- **Documentation**: Inline documentation and README updates

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support & Resources

### Getting Help
- **Frontend Issues**: Check `mobile_clean_architecture/lib/features/`
- **Backend Issues**: Review `backend/app/` modules
- **API Documentation**: Visit `http://localhost:8000/docs`
- **Architecture Guide**: See individual feature READMEs


## 🔄 Version History

### Version 1.0.0 - Initial Release
- ✅ Complete speech-to-text functionality
- ✅ AI-powered realistic text-to-speech
- ✅ Image description practice exercises
- ✅ Speech correction with detailed explanations
- ✅ Personalized learning suggestions
- ✅ User authentication and profile management
- ✅ Clean architecture implementation
- ✅ Comprehensive API documentation
