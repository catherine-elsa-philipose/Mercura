import 'package:flutter/foundation.dart';
import 'package:dio/dio.dart';
import '../../../core/storage/local_storage.dart';
import '../../../core/network/api_client.dart';

class AuthService {
  final ApiClient _apiClient;
  final TokenStorage _tokenStorage;

  AuthService(this._apiClient, this._tokenStorage);

  Future<bool> login(String email, String password) async {
    try {
      final response = await _apiClient.dio.post(
        '/auth/login',
        data: {'email': email.trim(), 'password': password},
      );

      final token = response.data['access_token'];

      if (token != null) {
        await _tokenStorage.saveToken(token);
        return true;
      }

      return false;
    } on DioException catch (e) {
      debugPrint("========== LOGIN ERROR ==========");
      debugPrint("Status Code: ${e.response?.statusCode}");
      debugPrint("Response: ${e.response?.data}");
      debugPrint("================================");
      return false;
    } catch (e) {
      debugPrint("Unexpected Login Error: $e");
      return false;
    }
  }

  Future<bool> register(String email, String fullName, String password, {String? businessName}) async {
    try {
      final response = await _apiClient.dio.post(
        '/auth/register',
        data: {
          'email': email.trim(),
          'full_name': fullName.trim(),
          'password': password,
          if (businessName != null && businessName.trim().isNotEmpty)
            'business_name': businessName.trim(),
        },
      );

      debugPrint("========== REGISTER SUCCESS ==========");
      debugPrint("Status Code: ${response.statusCode}");
      debugPrint("Response: ${response.data}");
      debugPrint("======================================");

      return response.statusCode == 200;
    } on DioException catch (e) {
      debugPrint("========== REGISTER ERROR ==========");
      debugPrint("Status Code: ${e.response?.statusCode}");
      debugPrint("Response: ${e.response?.data}");
      debugPrint("====================================");
      return false;
    } catch (e) {
      debugPrint("========== UNEXPECTED ERROR ==========");
      debugPrint(e.toString());
      debugPrint("======================================");
      return false;
    }
  }
}
