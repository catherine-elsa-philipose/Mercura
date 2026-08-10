import 'package:dio/dio.dart';
import 'package:jwt_decoder/jwt_decoder.dart';
import '../storage/local_storage.dart';
import 'package:go_router/go_router.dart';

class AuthInterceptor extends Interceptor {
  final TokenStorage _tokenStorage;
  final GoRouter _router;

  AuthInterceptor(this._tokenStorage, this._router);

  @override
  Future<void> onRequest(RequestOptions options, RequestInterceptorHandler handler) async {
    final token = await _tokenStorage.getToken();

    if (token != null) {
      if (JwtDecoder.isExpired(token)) {
        await _tokenStorage.deleteToken();
        _router.go('/login');
        return handler.reject(
          DioException(
            requestOptions: options,
            type: DioExceptionType.cancel,
            error: 'Token expired',
          ),
        );
      }
      options.headers['Authorization'] = 'Bearer $token';
    }

    return handler.next(options);
  }

  @override
  void onError(DioException err, ErrorInterceptorHandler handler) async {
    if (err.response?.statusCode == 401) {
      await _tokenStorage.deleteToken();
      _router.go('/login');
    }
    return handler.next(err);
  }
}
