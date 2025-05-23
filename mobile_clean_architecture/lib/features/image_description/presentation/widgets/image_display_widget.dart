import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import '../../../../core/theme/app_colors.dart';
import '../../../../core/theme/text_styles.dart';
import '../../../../core/utils/responsive_layout.dart';

/// Widget for displaying practice images with loading and error states
class ImageDisplayWidget extends StatelessWidget {
  final String? imageUrl;
  final bool isLoading;
  final String? errorMessage;
  final VoidCallback? onRetry;

  const ImageDisplayWidget({
    super.key,
    this.imageUrl,
    this.isLoading = false,
    this.errorMessage,
    this.onRetry,
  });

  @override
  Widget build(BuildContext context) {
    final isDarkMode = Theme.of(context).brightness == Brightness.dark;
    final imageHeight = ResponsiveLayout.isLargeScreen(context) ? 350.0 : 300.0;

    return Container(
      height: imageHeight,
      width: double.infinity,
      margin: EdgeInsets.symmetric(
        horizontal: ResponsiveLayout.getCardPadding(context),
        vertical: ResponsiveLayout.getElementSpacing(context),
      ),
      decoration: BoxDecoration(
        color: AppColors.getSurfaceColor(isDarkMode),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: AppColors.primary.withOpacity(0.1),
          width: 1,
        ),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.05),
            blurRadius: 8,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(16),
        child: _buildImageContent(context, isDarkMode),
      ),
    );
  }

  Widget _buildImageContent(BuildContext context, bool isDarkMode) {
    if (isLoading) {
      return _buildLoadingState(context, isDarkMode);
    }

    if (errorMessage != null) {
      return _buildErrorState(context, isDarkMode);
    }

    if (imageUrl != null && imageUrl!.isNotEmpty) {
      return _buildImageWidget(context, isDarkMode);
    }

    return _buildEmptyState(context, isDarkMode);
  }

  Widget _buildLoadingState(BuildContext context, bool isDarkMode) {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          CircularProgressIndicator(
            valueColor: AlwaysStoppedAnimation<Color>(AppColors.primary),
          ),
          SizedBox(height: ResponsiveLayout.getElementSpacing(context)),
          Text(
            'Loading image...',
            style: TextStyles.body(context, isDarkMode: isDarkMode),
          ),
        ],
      ),
    );
  }

  Widget _buildErrorState(BuildContext context, bool isDarkMode) {
    return Center(
      child: Padding(
        padding: EdgeInsets.all(ResponsiveLayout.getCardPadding(context)),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.error_outline,
              size: 64,
              color: AppColors.error,
            ),
            SizedBox(height: ResponsiveLayout.getElementSpacing(context)),
            Text(
              'Image Error',
              style: TextStyles.h3(context, isDarkMode: isDarkMode),
            ),
            SizedBox(height: ResponsiveLayout.getElementSpacing(context)),
            Text(
              errorMessage ?? 'Failed to load image from server',
              style: TextStyles.body(context, isDarkMode: isDarkMode),
              textAlign: TextAlign.center,
            ),
            SizedBox(height: ResponsiveLayout.getElementSpacing(context)),
            if (imageUrl != null) ...[
              Text(
                'URL: $imageUrl',
                style: TextStyles.caption(context, isDarkMode: isDarkMode),
                textAlign: TextAlign.center,
              ),
            ],
            if (onRetry != null) ...[
              SizedBox(height: ResponsiveLayout.getSectionSpacing(context)),
              ElevatedButton(
                onPressed: onRetry,
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppColors.primary,
                  foregroundColor: Colors.white,
                ),
                child: Text(
                  'Try Again',
                  style: TextStyles.button(context),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildEmptyState(BuildContext context, bool isDarkMode) {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            Icons.image_outlined,
            size: 64,
            color: AppColors.getTextSecondaryColor(isDarkMode),
          ),
          SizedBox(height: ResponsiveLayout.getElementSpacing(context)),
          Text(
            'No image available',
            style: TextStyles.body(context, isDarkMode: isDarkMode),
          ),
        ],
      ),
    );
  }

  Widget _buildImageWidget(BuildContext context, bool isDarkMode) {
    print('DEBUG: Building image widget for URL: $imageUrl');
    
    if (imageUrl == null || imageUrl!.isEmpty) {
      print('DEBUG: No image URL provided');
      return _buildDetailedErrorState(context, isDarkMode, 'No image URL provided');
    }

    // Direct approach - try to load image immediately with comprehensive error handling
    return _buildDirectNetworkImage(context, isDarkMode);
  }

  Widget _buildDirectNetworkImage(BuildContext context, bool isDarkMode) {
    print('DEBUG: Loading image from FileResponse endpoint: $imageUrl');
    
    return ClipRRect(
      borderRadius: BorderRadius.circular(16),
      child: Image.network(
        imageUrl!,
        fit: BoxFit.cover,
        width: double.infinity,
        height: double.infinity,
        loadingBuilder: (context, child, loadingProgress) {
          if (loadingProgress == null) {
            print('DEBUG: ✅ FileResponse image loaded successfully: $imageUrl');
            return child;
          }
          
          final bytesLoaded = loadingProgress.cumulativeBytesLoaded;
          final totalBytes = loadingProgress.expectedTotalBytes;
          final progress = totalBytes != null ? bytesLoaded / totalBytes : null;
          
          return Container(
            color: AppColors.getSurfaceColor(isDarkMode),
            child: Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  CircularProgressIndicator(
                    value: progress,
                    valueColor: AlwaysStoppedAnimation<Color>(AppColors.primary),
                    strokeWidth: 3,
                  ),
                  SizedBox(height: ResponsiveLayout.getElementSpacing(context)),
                  Text(
                    progress != null 
                      ? 'Loading ${(progress * 100).toStringAsFixed(0)}%'
                      : 'Loading image...',
                    style: TextStyles.body(context, isDarkMode: isDarkMode),
                  ),
                  SizedBox(height: ResponsiveLayout.getElementSpacing(context)),
                  Text(
                    'FileResponse: ${(bytesLoaded / 1024).toStringAsFixed(0)} KB',
                    style: TextStyles.caption(context, isDarkMode: isDarkMode),
                  ),
                ],
              ),
            ),
          );
        },
        errorBuilder: (context, error, stackTrace) {
          print('DEBUG: ❌ FileResponse image loading failed');
          print('DEBUG: Error: $error');
          print('DEBUG: Error type: ${error.runtimeType}');
          print('DEBUG: FileResponse URL: $imageUrl');
          print('DEBUG: Stack trace: ${stackTrace.toString().split('\n').take(3).join('\n')}');
          
          return _buildFallbackImage(context, isDarkMode, error);
        },
      ),
    );
  }

  Widget _buildFallbackImage(BuildContext context, bool isDarkMode, dynamic originalError) {
    print('DEBUG: All image loading attempts failed, showing error state');
    return _buildDetailedErrorState(context, isDarkMode, originalError);
  }

  Future<bool> _testImageUrl(String url) async {
    try {
      print('DEBUG: Testing image URL: $url');
      final uri = Uri.parse(url);
      final client = http.Client();
      
      final response = await client.head(uri).timeout(
        const Duration(seconds: 10),
      );
      
      client.close();
      
      print('DEBUG: Image URL test response: ${response.statusCode}');
      print('DEBUG: Content-Type: ${response.headers['content-type']}');
      
      if (response.statusCode == 200) {
        final contentType = response.headers['content-type'] ?? '';
        if (contentType.startsWith('image/')) {
          print('DEBUG: Image URL test PASSED');
          return true;
        } else {
          print('DEBUG: Invalid content type: $contentType');
          return false;
        }
      } else {
        print('DEBUG: HTTP error: ${response.statusCode}');
        return false;
      }
    } catch (e) {
      print('DEBUG: Image URL test error: $e');
      return false;
    }
  }

  Widget _buildNetworkImage(BuildContext context, bool isDarkMode) {
    print('DEBUG: Creating network image widget for: $imageUrl');
    
    return Image.network(
      imageUrl!,
      fit: BoxFit.cover,
      width: double.infinity,
      height: double.infinity,
      loadingBuilder: (context, child, loadingProgress) {
        if (loadingProgress == null) {
          print('DEBUG: ✅ Image loaded successfully: $imageUrl');
          return child;
        }
        
        final progress = loadingProgress.expectedTotalBytes != null
            ? loadingProgress.cumulativeBytesLoaded / loadingProgress.expectedTotalBytes!
            : null;
        
        print('DEBUG: Loading progress: ${progress?.toStringAsFixed(2) ?? 'unknown'}%');
        return _buildLoadingState(context, isDarkMode);
      },
      errorBuilder: (context, error, stackTrace) {
        print('DEBUG: ❌ Image widget error: $error');
        print('DEBUG: Error type: ${error.runtimeType}');
        return _buildDetailedErrorState(context, isDarkMode, error);
      },
    );
  }

  Widget _buildDetailedErrorState(BuildContext context, bool isDarkMode, dynamic error) {
    String errorDetails = 'Unknown error';
    String suggestion = '';
    
    if (error.toString().contains('SocketException')) {
      errorDetails = 'Network connection failed';
      suggestion = 'Check if backend is running and ADB port forwarding is set up';
    } else if (error.toString().contains('HttpException')) {
      errorDetails = 'HTTP error - Server returned an error response';
      suggestion = 'Server might be overloaded or image not found';
    } else if (error.toString().contains('FormatException')) {
      errorDetails = 'Image format error';
      suggestion = 'Server response was not a valid image';
    } else if (error.toString().contains('TimeoutException')) {
      errorDetails = 'Request timeout';
      suggestion = 'Server is taking too long to respond';
    } else {
      errorDetails = error.toString();
      suggestion = 'Check network connection and backend status';
    }
    
    return Center(
      child: Padding(
        padding: EdgeInsets.all(ResponsiveLayout.getCardPadding(context)),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.error_outline,
              size: 64,
              color: AppColors.error,
            ),
            SizedBox(height: ResponsiveLayout.getElementSpacing(context)),
            Text(
              'Image Loading Error',
              style: TextStyles.h3(context, isDarkMode: isDarkMode),
            ),
            SizedBox(height: ResponsiveLayout.getElementSpacing(context)),
            Text(
              errorDetails,
              style: TextStyles.body(context, isDarkMode: isDarkMode).copyWith(
                fontWeight: FontWeight.w600,
              ),
              textAlign: TextAlign.center,
            ),
            SizedBox(height: ResponsiveLayout.getElementSpacing(context)),
            Text(
              suggestion,
              style: TextStyles.caption(context, isDarkMode: isDarkMode),
              textAlign: TextAlign.center,
            ),
            SizedBox(height: ResponsiveLayout.getElementSpacing(context)),
            if (imageUrl != null) ...[
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: isDarkMode ? Colors.grey[800] : Colors.grey[200],
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Text(
                  'URL: $imageUrl',
                  style: TextStyles.caption(context, isDarkMode: isDarkMode).copyWith(
                    fontFamily: 'monospace',
                  ),
                  textAlign: TextAlign.center,
                ),
              ),
            ],
            if (onRetry != null) ...[
              SizedBox(height: ResponsiveLayout.getSectionSpacing(context)),
              ElevatedButton(
                onPressed: onRetry,
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppColors.primary,
                  foregroundColor: Colors.white,
                ),
                child: Text(
                  'Try Again',
                  style: TextStyles.button(context),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

/// Widget that displays the progress indicator for multiple images
class ImageProgressWidget extends StatelessWidget {
  final int currentIndex;
  final int totalImages;

  const ImageProgressWidget({
    super.key,
    required this.currentIndex,
    required this.totalImages,
  });

  @override
  Widget build(BuildContext context) {
    final isDarkMode = Theme.of(context).brightness == Brightness.dark;

    if (totalImages <= 0) return const SizedBox.shrink();

    return Padding(
      padding: EdgeInsets.symmetric(
        horizontal: ResponsiveLayout.getCardPadding(context),
        vertical: ResponsiveLayout.getElementSpacing(context),
      ),
      child: Column(
        children: [
          LinearProgressIndicator(
            value: (currentIndex + 1) / totalImages,
            backgroundColor: AppColors.primary.withOpacity(0.1),
            valueColor: AlwaysStoppedAnimation<Color>(AppColors.primary),
            minHeight: 4,
            borderRadius: BorderRadius.circular(2),
          ),
          SizedBox(height: ResponsiveLayout.getElementSpacing(context)),
          Text(
            '${currentIndex + 1} of $totalImages',
            style: TextStyles.secondary(context, isDarkMode: isDarkMode),
          ),
        ],
      ),
    );
  }
}
