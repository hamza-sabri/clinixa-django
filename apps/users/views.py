from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .serializers import (
    SignupSerializer,
    SignupWithClinicSerializer,
    SigninSerializer,
    ForgetPasswordSerializer,
    UserSerializer,
    TokenResponseSerializer,
    CustomTokenObtainPairSerializer,
)


def get_tokens_for_user(user):
    """Generate access and refresh tokens for user with custom claims."""
    refresh = CustomTokenObtainPairSerializer.get_token(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }


class SignupView(APIView):
    """
    Register a new patient account.
    
    Creates a new user with user_type='patient'. Patients can book visits
    to any clinic and manage their own vitals records.
    """
    permission_classes = [AllowAny]
    
    @swagger_auto_schema(
        operation_id='postUsersSignup',
        operation_summary='Sign up a new patient',
        operation_description='Register a new patient account. Returns access and refresh tokens upon successful registration.',
        tags=['Auth'],
        request_body=SignupSerializer,
        responses={
            201: openapi.Response(
                description='User registered successfully',
                schema=TokenResponseSerializer
            ),
            400: openapi.Response(description='Validation error')
        }
    )
    def post(self, request):
        serializer = SignupSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            tokens = get_tokens_for_user(user)
            
            return Response({
                'access': tokens['access'],
                'refresh': tokens['refresh'],
                'user': UserSerializer(user).data
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SignupWithClinicView(APIView):
    """
    Register a new doctor with their clinic.
    
    Creates a doctor account and their clinic in a single request.
    The doctor becomes the owner of the created clinic.
    """
    permission_classes = [AllowAny]
    
    @swagger_auto_schema(
        operation_id='postUsersSignupWithClinic',
        operation_summary='Sign up a new doctor with their clinic',
        operation_description='Register a doctor account and create their clinic. Returns access and refresh tokens.',
        tags=['Auth'],
        request_body=SignupWithClinicSerializer,
        responses={
            201: openapi.Response(
                description='Doctor and clinic created successfully',
                schema=TokenResponseSerializer
            ),
            400: openapi.Response(description='Validation error')
        }
    )
    def post(self, request):
        serializer = SignupWithClinicSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            tokens = get_tokens_for_user(user)
            
            # Get clinic with statistics
            from apps.clinics.models import Clinic
            from apps.clinics.serializers import ClinicDetailSerializer
            
            clinic = Clinic.objects.filter(doctor=user).first()
            clinic_data = ClinicDetailSerializer(clinic).data if clinic else None
            
            return Response({
                'access': tokens['access'],
                'refresh': tokens['refresh'],
                'user': UserSerializer(user).data,
                'clinic': clinic_data
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SigninView(APIView):
    """
    Sign in an existing user.
    
    Authenticates user with email and password, returns JWT tokens.
    Works for all user types: doctors, employees, and patients.
    """
    permission_classes = [AllowAny]
    
    @swagger_auto_schema(
        operation_id='postUsersSignin',
        operation_summary='Sign in an existing user',
        operation_description='Authenticate with email and password. Returns access and refresh JWT tokens with user info.',
        tags=['Auth'],
        request_body=SigninSerializer,
        responses={
            200: openapi.Response(
                description='Login successful',
                schema=TokenResponseSerializer
            ),
            400: openapi.Response(description='Invalid credentials')
        }
    )
    def post(self, request):
        serializer = SigninSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            tokens = get_tokens_for_user(user)
            
            response_data = {
                'access': tokens['access'],
                'refresh': tokens['refresh'],
                'user': UserSerializer(user).data
            }
            
            # Add clinic with statistics for doctors
            if user.user_type == 'doctor':
                from apps.clinics.models import Clinic
                from apps.clinics.serializers import ClinicDetailSerializer
                
                clinic = Clinic.objects.filter(doctor=user).first()
                response_data['clinic'] = ClinicDetailSerializer(clinic).data if clinic else None
            
            return Response(response_data, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ForgetPasswordView(APIView):
    """
    Request password reset.
    
    Currently stubbed - returns success message but does not send email.
    Will be implemented with email service later.
    """
    permission_classes = [AllowAny]
    
    @swagger_auto_schema(
        operation_id='postUsersForgetPassword',
        operation_summary='Request password reset',
        operation_description='Request a password reset email. Currently stubbed - will be implemented later.',
        tags=['Auth'],
        request_body=ForgetPasswordSerializer,
        responses={
            200: openapi.Response(
                description='Password reset request processed',
                examples={
                    'application/json': {
                        'message': 'If an account with this email exists, a password reset link has been sent.'
                    }
                }
            ),
            400: openapi.Response(description='Validation error')
        }
    )
    def post(self, request):
        serializer = ForgetPasswordSerializer(data=request.data)
        if serializer.is_valid():
            # TODO: Implement email sending logic
            return Response({
                'message': 'If an account with this email exists, a password reset link has been sent.'
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CustomTokenRefreshView(TokenRefreshView):
    """
    Refresh access token using refresh token.
    
    Takes a valid refresh token and returns a new access token.
    The refresh token is rotated (old one invalidated, new one returned).
    """
    
    @swagger_auto_schema(
        operation_id='postUsersTokenRefresh',
        operation_summary='Refresh access token',
        operation_description='Use refresh token to get a new access token. Refresh token is rotated.',
        tags=['Auth'],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['refresh'],
            properties={
                'refresh': openapi.Schema(type=openapi.TYPE_STRING, description='Refresh token')
            }
        ),
        responses={
            200: openapi.Response(
                description='Token refreshed successfully',
                examples={
                    'application/json': {
                        'access': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...',
                        'refresh': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...'
                    }
                }
            ),
            401: openapi.Response(description='Invalid or expired refresh token')
        }
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


