import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:equatable/equatable.dart';
import 'package:mobile_clean_architecture/core/error/failures.dart';
import 'package:mobile_clean_architecture/core/usecases/usecase.dart';
import 'package:mobile_clean_architecture/core/constants/api_constants.dart';
import 'package:mobile_clean_architecture/features/image_description/domain/entities/feedback_entity.dart';
import 'package:mobile_clean_architecture/features/image_description/domain/entities/image_entity.dart';
import 'package:mobile_clean_architecture/features/image_description/domain/usecases/get_image_feedback.dart';
import 'package:mobile_clean_architecture/features/image_description/domain/usecases/get_image_url.dart';
import 'package:mobile_clean_architecture/features/image_description/domain/usecases/get_practice_images.dart';
import '../../data/services/audio_recording_service.dart';
import 'package:http/http.dart' as http;

part 'image_description_state.dart';

/// Cubit for managing image description feature state
class ImageDescriptionCubit extends Cubit<ImageDescriptionState> {
  final GetPracticeImages getPracticeImages;
  final GetImageUrl getImageUrl;
  final GetImageFeedback getImageFeedback;
  final AudioRecordingService _audioService;

  /// Creates an ImageDescriptionCubit instance
  ImageDescriptionCubit({
    required this.getPracticeImages,
    required this.getImageUrl,
    required this.getImageFeedback,
    AudioRecordingService? audioService,
  })  : _audioService = audioService ?? AudioRecordingService(),
        super(const ImageDescriptionInitial());

  /// Fetches all practice images from the server
  Future<void> loadPracticeImages() async {
    print('DEBUG: Starting to load practice images...');
    emit(const ImageDescriptionLoading());

    // Test network connectivity first
    print('DEBUG: Testing network connectivity...');
    final networkOk = await testNetworkConnectivity();
    if (!networkOk) {
      print('DEBUG: Network connectivity test failed');
      emit(const ImageDescriptionError('Network connection failed. Please check if backend is running and accessible.'));
      return;
    }
    print('DEBUG: Network connectivity test passed');

    final result = await getPracticeImages(NoParams());

    result.fold(
      (failure) {
        print('DEBUG: Failed to load practice images: ${_mapFailureToMessage(failure)}');
        emit(ImageDescriptionError(_mapFailureToMessage(failure)));
      },
      (images) {
        print('DEBUG: Successfully loaded ${images.length} practice images');
        for (int i = 0; i < images.length && i < 3; i++) {
          print('DEBUG: Image $i - ID: ${images[i].id}, Name: ${images[i].name}');
        }
        emit(ImageDescriptionLoaded(images));
      },
    );
  }

  /// Test network connectivity to the backend
  Future<bool> testNetworkConnectivity() async {
    try {
      final response = await http.get(
        Uri.parse('${ApiConstants.baseUrl}/'),
        headers: {'Content-Type': 'application/json'},
      ).timeout(const Duration(seconds: 5));
      
      print('DEBUG: Network test - Status: ${response.statusCode}');
      return response.statusCode == 200;
    } catch (e) {
      print('DEBUG: Network test failed: $e');
      return false;
    }
  }

  /// Gets image URL for a specific image ID
  Future<String?> getImageUrlById(String imageId) async {
    // First, get images from state
    List<ImageEntity> images = [];
    if (state is ImageDescriptionLoaded) {
      images = (state as ImageDescriptionLoaded).images;
    } else if (state is ImageRecordingStarted) {
      images = (state as ImageRecordingStarted).images;
    } else if (state is ImageTranscriptionProcessing) {
      images = (state as ImageTranscriptionProcessing).images;
    } else if (state is ImageTranscriptionCompleted) {
      images = (state as ImageTranscriptionCompleted).images;
    } else if (state is ImageFeedbackReceived) {
      images = (state as ImageFeedbackReceived).images;
    }

    // Try to find the image directly in loaded images first
    ImageEntity? foundImage;
    try {
      foundImage = images.firstWhere((img) => img.id == imageId);
    } catch (e) {
      print('DEBUG: Image not found in loaded images, using API endpoint');
      foundImage = null;
    }

    // Clean imageId to ensure we don't have path prefixes
    String cleanId = imageId;
    if (imageId.contains('/')) {
      cleanId = imageId.split('/').last;
    }

    // Always use the get_image_by_id endpoint which returns FileResponse
    final apiUrl = '${ApiConstants.baseUrl}/api/images/getimages/$imageId';
    print('DEBUG: Using get_image_by_id endpoint: $apiUrl');
    print('DEBUG: Image found in loaded data: ${foundImage != null}');
    if (foundImage != null) {
      print('DEBUG: Found image name: ${foundImage!.name}');
    }
    return apiUrl;
  }

  /// Starts audio recording for image description
  Future<void> startRecording() async {
    try {
      // Check permissions first
      if (!await _audioService.hasPermission()) {
        emit(const ImageDescriptionError('Microphone permission is required'));
        return;
      }

      // Update state to recording
      if (state is ImageDescriptionLoaded) {
        final currentState = state as ImageDescriptionLoaded;
        emit(ImageRecordingStarted(currentState.images));
      } else {
        emit(const ImageRecordingStarted([]));
      }

      // Start recording
      final success = await _audioService.startRecording();
      if (!success) {
        emit(const ImageDescriptionError('Failed to start recording'));
      }
    } catch (e) {
      emit(ImageDescriptionError('Recording error: ${e.toString()}'));
    }
  }

  /// Stops recording and processes transcription
  Future<void> stopRecording(String imageId) async {
    try {
      // Update state to processing
      if (state is ImageRecordingStarted) {
        final currentState = state as ImageRecordingStarted;
        emit(ImageTranscriptionProcessing(currentState.images));
      }

      // Stop recording and get file path
      final audioFilePath = await _audioService.stopRecording();
      if (audioFilePath == null) {
        emit(const ImageDescriptionError('Failed to stop recording'));
        return;
      }

      // Transcribe audio
      final transcriptionResult =
          await _audioService.transcribeAudio(audioFilePath);

      if (transcriptionResult.success &&
          transcriptionResult.transcription.isNotEmpty) {
        // Get images from current state
        List<ImageEntity> images = [];
        if (state is ImageTranscriptionProcessing) {
          images = (state as ImageTranscriptionProcessing).images;
        }

        // Emit transcription completed state
        emit(ImageTranscriptionCompleted(
          images: images,
          transcription: transcriptionResult.transcription,
          imageId: imageId,
        ));

        // Automatically request feedback
        await _requestFeedbackForTranscription(
          imageId: imageId,
          transcription: transcriptionResult.transcription,
          images: images,
        );
      } else {
        emit(ImageDescriptionError(transcriptionResult.transcription.isNotEmpty
            ? transcriptionResult.transcription
            : 'Failed to transcribe audio'));
      }
    } catch (e) {
      emit(ImageDescriptionError('Transcription error: ${e.toString()}'));
    }
  }

  /// Cancels current recording
  Future<void> cancelRecording() async {
    try {
      await _audioService.cancelRecording();

      // Return to loaded state if we have images
      if (state is ImageRecordingStarted) {
        final currentState = state as ImageRecordingStarted;
        emit(ImageDescriptionLoaded(currentState.images));
      } else {
        emit(const ImageDescriptionInitial());
      }
    } catch (e) {
      emit(
          ImageDescriptionError('Error cancelling recording: ${e.toString()}'));
    }
  }

  /// Private method to request feedback after transcription
  Future<void> _requestFeedbackForTranscription({
    required String imageId,
    required String transcription,
    required List<ImageEntity> images,
  }) async {
    try {
      final result = await getImageFeedback(
        FeedbackParams(
          userId: 'current-user-id', // This should come from auth state
          imageId: imageId,
          userTranscription: transcription,
        ),
      );

      result.fold(
        (failure) => emit(ImageDescriptionError(_mapFailureToMessage(failure))),
        (feedback) => emit(ImageFeedbackReceived(
          images: images,
          transcription: transcription,
          feedback: feedback,
          imageId: imageId,
        )),
      );
    } catch (e) {
      emit(ImageDescriptionError('Error getting feedback: ${e.toString()}'));
    }
  }

  /// Manually request feedback (for retry scenarios)
  Future<void> requestFeedback({
    required String imageId,
    required String transcription,
  }) async {
    // Get current images
    List<ImageEntity> images = [];
    if (state is ImageTranscriptionCompleted) {
      images = (state as ImageTranscriptionCompleted).images;
    } else if (state is ImageDescriptionLoaded) {
      images = (state as ImageDescriptionLoaded).images;
    }

    emit(const ImageFeedbackLoading());

    await _requestFeedbackForTranscription(
      imageId: imageId,
      transcription: transcription,
      images: images,
    );
  }

  /// Reset to initial state
  void reset() {
    emit(const ImageDescriptionInitial());
  }

  /// Get recording status
  bool get isRecording => _audioService.isRecording;

  // Helper method to map failure to user-friendly message
  String _mapFailureToMessage(Failure failure) {
    switch (failure.runtimeType) {
      case ServerFailure:
        return failure.message ?? 'Server error occurred';
      case NetworkFailure:
        return failure.message ?? 'Network error occurred';
      default:
        return 'Unexpected error occurred';
    }
  }

  @override
  Future<void> close() {
    _audioService.dispose();
    return super.close();
  }
}
