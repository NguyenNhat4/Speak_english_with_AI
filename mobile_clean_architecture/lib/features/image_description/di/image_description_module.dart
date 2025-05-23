import 'package:get_it/get_it.dart';
import 'package:http/http.dart' as http;
import 'package:internet_connection_checker/internet_connection_checker.dart';

import '../../../core/network/network_info.dart';
import '../data/datasources/image_remote_data_source.dart';
import '../data/repositories/image_repository_impl.dart';
import '../data/services/audio_recording_service.dart';
import '../domain/repositories/image_repository.dart';
import '../domain/usecases/get_image_feedback.dart';
import '../domain/usecases/get_image_url.dart';
import '../domain/usecases/get_practice_images.dart';
import '../presentation/cubit/image_description_cubit.dart';

/// Initializes the image description feature dependency injection
///
/// Registers all necessary dependencies for the image description feature
void initImageDescriptionModule() {
  final GetIt sl = GetIt.instance;

  // Services
  if (!sl.isRegistered<AudioRecordingService>()) {
    sl.registerLazySingleton<AudioRecordingService>(
      () => AudioRecordingService(),
    );
  }

  // Cubit
  sl.registerFactory(
    () => ImageDescriptionCubit(
      getPracticeImages: sl(),
      getImageUrl: sl(),
      getImageFeedback: sl(),
      audioService: sl(),
    ),
  );

  // Use cases
  if (!sl.isRegistered<GetPracticeImages>()) {
    sl.registerLazySingleton(() => GetPracticeImages(sl()));
  }

  if (!sl.isRegistered<GetImageUrl>()) {
    sl.registerLazySingleton(() => GetImageUrl(sl()));
  }

  if (!sl.isRegistered<GetImageFeedback>()) {
    sl.registerLazySingleton(() => GetImageFeedback(sl()));
  }

  // Repository
  if (!sl.isRegistered<ImageRepository>()) {
    sl.registerLazySingleton<ImageRepository>(
      () => ImageRepositoryImpl(
        remoteDataSource: sl(),
        networkInfo: sl(),
      ),
    );
  }

  // Data sources
  if (!sl.isRegistered<ImageRemoteDataSource>()) {
    sl.registerLazySingleton<ImageRemoteDataSource>(
      () => ImageRemoteDataSourceImpl(client: sl()),
    );
  }

  // Core
  if (!sl.isRegistered<NetworkInfo>()) {
    sl.registerLazySingleton<NetworkInfo>(() => NetworkInfoImpl(sl()));
  }

  // External
  if (!sl.isRegistered<http.Client>()) {
    sl.registerLazySingleton(() => http.Client());
  }

  if (!sl.isRegistered<InternetConnectionChecker>()) {
    sl.registerLazySingleton(() => InternetConnectionChecker());
  }
}
