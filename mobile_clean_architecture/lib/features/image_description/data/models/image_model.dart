import 'package:mobile_clean_architecture/features/image_description/domain/entities/image_entity.dart';

/// ImageModel represents image data returned from the API
class ImageModel extends ImageEntity {
  /// Creates an ImageModel instance
  const ImageModel({
    required super.id,
    required super.name,
    required super.detailDescription,
  });

  /// Creates an ImageModel instance from JSON data
  factory ImageModel.fromJson(Map<String, dynamic> json) {
    try {
      print('DEBUG: Parsing image: ${json['id']} - ${json['name']}');

      // Ensure all required fields are present
      if (json['id'] == null ||
          json['name'] == null ||
          json['detail_description'] == null) {
        print('DEBUG: Image data missing required fields: $json');
        throw FormatException('Image data missing required fields');
      }

      return ImageModel(
        id: json['id'].toString(),
        name: json['name'].toString(),
        detailDescription: json['detail_description'].toString(),
      );
    } catch (e) {
      print('DEBUG: Error parsing image model: $e');
      // Return a placeholder model in case of error
      return const ImageModel(
        id: 'error',
        name: 'error',
        detailDescription: 'Error loading image description',
      );
    }
  }

  /// Converts the ImageModel instance to a JSON map
  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'name': name,
      'detail_description': detailDescription,
    };
  }
}
