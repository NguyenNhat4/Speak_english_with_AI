import 'package:http/http.dart' as http;
import 'dart:convert';

// Test function to check API access
Future<void> main() async {
  const baseUrl = 'http://localhost:9000';
  const endpoint = '/api/images/practice';

  print('Attempting to access $baseUrl$endpoint');

  try {
    final response = await http.get(
      Uri.parse(baseUrl + endpoint),
      headers: {'Content-Type': 'application/json'},
    );

    print('Response status code: ${response.statusCode}');

    if (response.statusCode == 200) {
      print('Success! Found ${json.decode(response.body).length} images');
      // Print the first image to verify format
      final List<dynamic> images = json.decode(response.body);
      if (images.isNotEmpty) {
        print('First image: ${images[0]}');
      }
    } else {
      print('Error! Response body: ${response.body}');
    }
  } catch (e) {
    print('Exception: $e');
  }
}
