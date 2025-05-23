import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:mobile_clean_architecture/core/constants/api_constants.dart';
import 'package:mobile_clean_architecture/core/error/exceptions.dart';
import 'package:mobile_clean_architecture/features/image_description/data/models/feedback_model.dart';
import 'package:mobile_clean_architecture/features/image_description/data/models/feedback_request.dart';
import 'package:mobile_clean_architecture/features/image_description/data/models/image_model.dart';

/// Data source interface for fetching image data from API
abstract class ImageRemoteDataSource {
  /// Get a list of practice images with descriptions
  Future<List<ImageModel>> getPracticeImages();

  /// Get image data by its ID
  Future<String> getImageUrl(String imageId);

  /// Submit user's description and get feedback
  Future<ImageFeedbackModel> getImageFeedback(ImageFeedbackRequest request);
}

/// Implementation of ImageRemoteDataSource that fetches data from a remote API
class ImageRemoteDataSourceImpl implements ImageRemoteDataSource {
  final http.Client client;

  /// Creates an ImageRemoteDataSourceImpl instance with an HTTP client
  ImageRemoteDataSourceImpl({required this.client});
  @override
  Future<List<ImageModel>> getPracticeImages() async {
    try {
      final endpoint = '/api/images/practice';
      print(
          'DEBUG: Fetching practice images from ${ApiConstants.baseUrl + endpoint}');

      // Use headers without authentication for this public endpoint
      final headers = {
        'Content-Type': 'application/json',
      };

      print('DEBUG: Headers: $headers');

      final response = await client
          .get(
            Uri.parse(ApiConstants.baseUrl + endpoint),
            headers: headers,
          )
          .timeout(const Duration(seconds: ApiConstants.timeoutDuration));

      print('DEBUG: Response status code: ${response.statusCode}');

      if (response.statusCode == 200) {
        print('DEBUG: Response received successfully');
        try {
          final List<dynamic> jsonData = json.decode(response.body);
          print('DEBUG: Parsed ${jsonData.length} images');
          return jsonData.map((json) => ImageModel.fromJson(json)).toList();
        } catch (parseError) {
          print('DEBUG: JSON parse error: $parseError');
          throw ServerException(
              message: 'Failed to parse practice images response: $parseError');
        }
      } else {
        print('DEBUG: Error response: ${response.body}');
        throw ServerException(
            message:
                'Failed to load practice images: Status ${response.statusCode}',
            statusCode: response.statusCode);
      }
    } catch (e) {
      print('DEBUG: Exception while loading practice images: $e');
      throw ServerException(
          message: 'Failed to load practice images: ${e.toString()}');
    }
  }

  @override
  Future<String> getImageUrl(String imageId) async {
    // Use the FileResponse endpoint which properly serves images
    final imageUrl = '${ApiConstants.baseUrl}/api/images/getimages/$imageId';
    print('DEBUG: Generated FileResponse URL for ID $imageId: $imageUrl');
    return imageUrl;
  }

  @override
  Future<ImageFeedbackModel> getImageFeedback(
      ImageFeedbackRequest request) async {
    try {
      final response = await client
          .post(
            Uri.parse(
                ApiConstants.baseUrl + ApiConstants.imageFeedbackEndpoint),
            headers: ApiConstants.authHeaders,
            body: json.encode(request.toJson()),
          )
          .timeout(const Duration(seconds: ApiConstants.timeoutDuration));

      if (response.statusCode != 200) {
        throw ServerException(
            message: 'Failed to get image feedback',
            statusCode: response.statusCode);
      }

      final Map<String, dynamic> jsonData = json.decode(response.body);
      return ImageFeedbackModel.fromJson(jsonData);
    } catch (e) {
      throw ServerException(
          message: 'Failed to get image feedback: ${e.toString()}');
    }
  }
}
