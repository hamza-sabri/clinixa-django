from rest_framework import status, generics, filters
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView
from django_filters.rest_framework import DjangoFilterBackend
from django.contrib.auth import get_user_model
from django.db.models import Q
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .models import PatientProfile, Pregnancy, Baby
from .serializers import (
    SignupSerializer,
    SignupWithClinicSerializer,
    SigninSerializer,
    ForgetPasswordSerializer,
    UserSerializer,
    TokenResponseSerializer,
    CustomTokenObtainPairSerializer,
    # Patient serializers
    PatientListSerializer,
    PatientDetailSerializer,
    PatientCreateSerializer,
    PatientUpdateSerializer,
    # Pregnancy serializers
    PregnancyListSerializer,
    PregnancyDetailSerializer,
    PregnancyCreateSerializer,
    PregnancyUpdateSerializer,
    # Baby serializers
    BabyListSerializer,
    BabyDetailSerializer,
    BabyCreateSerializer,
    BabyUpdateSerializer,
)
from apps.core.swagger import PAGINATION_PARAMETERS, PAGINATION_DESCRIPTION

User = get_user_model()


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


# ============================================================================
# PATIENT OTP AUTHENTICATION VIEWS
# ============================================================================

from .serializers import (
    RequestOTPSerializer,
    VerifyOTPSerializer,
    OTPResponseSerializer,
    OTPLoginResponseSerializer,
    PatientUserSerializer,
    PatientMeSerializer,
    PatientMeUpdateSerializer,
)
from . import otp_service


class RequestOTPView(APIView):
    """
    Request OTP for patient login.
    
    Sends an OTP to the patient's phone number for authentication.
    Creates OTP record and triggers SMS (mocked for now).
    """
    permission_classes = [AllowAny]
    
    @swagger_auto_schema(
        operation_id='postPatientRequestOtp',
        operation_summary='Request OTP for patient login',
        operation_description='''
Request an OTP code to be sent to the patient's phone number.

**Rate Limiting:** Maximum 3 requests per minute per phone number.
**OTP Expiry:** 5 minutes (300 seconds).

If the phone number is new, a new patient account will be created upon successful OTP verification.
        ''',
        tags=['Patient Auth'],
        request_body=RequestOTPSerializer,
        responses={
            200: OTPResponseSerializer,
            429: openapi.Response(description='Too many requests')
        }
    )
    def post(self, request):
        serializer = RequestOTPSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        phone = serializer.validated_data['phone']
        
        # Check rate limiting
        rate_limit = otp_service.is_rate_limited(phone)
        if rate_limit['limited']:
            return Response({
                'error': f"Too many requests. Please wait {rate_limit['wait_seconds']} seconds."
            }, status=status.HTTP_429_TOO_MANY_REQUESTS)
        
        # Generate and send OTP
        result = otp_service.create_otp_verification(phone)
        
        # Check if user exists
        is_new_user = not otp_service.check_user_exists(phone)
        
        return Response({
            'message': 'OTP sent successfully',
            'phone': phone,
            'expires_in': result['expires_in'],
            'is_new_user': is_new_user
        }, status=status.HTTP_200_OK)


class VerifyOTPView(APIView):
    """
    Verify OTP and login patient.
    
    Verifies the OTP code and returns JWT tokens.
    For new users, creates the patient account and profile.
    """
    permission_classes = [AllowAny]
    
    @swagger_auto_schema(
        operation_id='postPatientVerifyOtp',
        operation_summary='Verify OTP and login patient',
        operation_description='''
Verify the OTP code and authenticate the patient.

**For new users:** 
- A new patient account is created
- PatientProfile is auto-created
- The `name` field is recommended for new users

**Returns:** JWT access and refresh tokens with user info.
        ''',
        tags=['Patient Auth'],
        request_body=VerifyOTPSerializer,
        responses={
            200: OTPLoginResponseSerializer,
            400: openapi.Response(description='Invalid or expired OTP')
        }
    )
    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        phone = serializer.validated_data['phone']
        otp_code = serializer.validated_data['otp']
        name = serializer.validated_data.get('name', '')
        
        # Verify OTP
        result = otp_service.verify_otp(phone, otp_code)
        
        if not result['success']:
            return Response({'error': result['error']}, status=status.HTTP_400_BAD_REQUEST)
        
        # Get or create user
        is_new_user = False
        try:
            user = User.objects.get(phone=phone)
        except User.DoesNotExist:
            # Create new patient user
            user = User.objects.create_user_with_phone(phone=phone, name=name)
            is_new_user = True
        
        # Ensure patient profile exists
        if not hasattr(user, 'patient_profile'):
            PatientProfile.objects.create(user=user)
        
        # Update name if provided and user already exists
        if name and not is_new_user and not user.name:
            user.name = name
            user.save(update_fields=['name'])
        
        # Generate tokens
        tokens = get_tokens_for_user(user)
        
        return Response({
            'access': tokens['access'],
            'refresh': tokens['refresh'],
            'user': PatientUserSerializer(user).data,
            'is_new_user': is_new_user
        }, status=status.HTTP_200_OK)


# ============================================================================
# PATIENT SELF-SERVICE VIEWS
# ============================================================================

class PatientMeView(APIView):
    """
    Get or update current patient's own profile.
    
    GET: Returns the authenticated patient's complete profile data.
    PATCH: Updates the patient's name and/or profile fields.
    """
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        operation_id='getPatientMe',
        operation_summary='Get current patient profile',
        operation_description='''
Get the authenticated patient's own profile data.

**Returns:**
- User info (id, email, phone, name)
- PatientProfile (blood_type, allergies, medical_history)
- All pregnancies with details
- Ongoing pregnancy info (if any)

**Note:** Only accessible by patients (user_type='patient').
        ''',
        tags=['Patient Self-Service'],
        responses={
            200: PatientMeSerializer,
            403: openapi.Response(description='Not a patient user')
        }
    )
    def get(self, request):
        if request.user.user_type != 'patient':
            return Response(
                {'error': 'This endpoint is only for patient users'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = PatientMeSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @swagger_auto_schema(
        operation_id='patchPatientMe',
        operation_summary='Update current patient profile',
        operation_description='''
Update the authenticated patient's own profile.

**Updatable fields:**
- `name` - Patient's display name
- `profile` - Object containing:
  - `blood_type` - Blood type (A+, B-, AB+, O-, etc.)
  - `allergies` - Known allergies
  - `medical_history` - Medical history notes
  - `notes` - Additional notes

**Example request:**
```json
{
    "name": "فاطمة أحمد",
    "profile": {
        "blood_type": "A+",
        "allergies": "Penicillin"
    }
}
```
        ''',
        tags=['Patient Self-Service'],
        request_body=PatientMeUpdateSerializer,
        responses={
            200: PatientMeSerializer,
            403: openapi.Response(description='Not a patient user')
        }
    )
    def patch(self, request):
        if request.user.user_type != 'patient':
            return Response(
                {'error': 'This endpoint is only for patient users'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = PatientMeUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        serializer.update(request.user, serializer.validated_data)
        
        output_serializer = PatientMeSerializer(request.user)
        return Response(output_serializer.data, status=status.HTTP_200_OK)


# ============================================================================
# PATIENT VIEWS
# ============================================================================

class PatientQuerySetMixin:
    """Mixin to handle patient queryset based on user type."""
    
    def get_queryset(self):
        user = self.request.user
        
        # Doctors see patients who visited their clinics
        if user.user_type == 'doctor':
            from apps.clinics.models import Clinic
            from apps.visits.models import Visit
            clinic_ids = Clinic.objects.filter(doctor=user).values_list('id', flat=True)
            patient_ids = Visit.objects.filter(clinic_id__in=clinic_ids).values_list('pregnancy__patient_profile__user_id', flat=True).distinct()
            # Also include patients from old visits (legacy)
            legacy_patient_ids = Visit.objects.filter(clinic_id__in=clinic_ids, patient__isnull=False).values_list('patient_id', flat=True).distinct()
            all_patient_ids = set(patient_ids) | set(legacy_patient_ids)
            return User.objects.filter(
                Q(id__in=all_patient_ids) | Q(user_type='patient')
            ).filter(user_type='patient').select_related('patient_profile').distinct()
        
        # Employees see patients from their assigned clinics
        elif user.user_type == 'employee':
            from apps.clinics.models import Employee
            from apps.visits.models import Visit
            clinic_ids = Employee.objects.filter(staff=user).values_list('clinic_id', flat=True)
            patient_ids = Visit.objects.filter(clinic_id__in=clinic_ids).values_list('pregnancy__patient_profile__user_id', flat=True).distinct()
            legacy_patient_ids = Visit.objects.filter(clinic_id__in=clinic_ids, patient__isnull=False).values_list('patient_id', flat=True).distinct()
            all_patient_ids = set(patient_ids) | set(legacy_patient_ids)
            return User.objects.filter(id__in=all_patient_ids, user_type='patient').select_related('patient_profile').distinct()
        
        return User.objects.none()


class PatientListAPIView(PatientQuerySetMixin, generics.ListAPIView):
    """GET /api/patients/ - List patients with search"""
    permission_classes = [IsAuthenticated]
    serializer_class = PatientListSerializer
    filter_backends = [filters.SearchFilter, DjangoFilterBackend]
    search_fields = ['name', 'email', 'phone']
    filterset_fields = ['email', 'phone']
    
    @swagger_auto_schema(
        operation_id='getPatients',
        operation_summary='List patients',
        operation_description='''
List all patients accessible by the authenticated user.

**Access Control:**
- Doctors see all patients (can create new ones)
- Employees see patients from their assigned clinics

**Search:** Use `?search=` to search by name, email, or phone
**Filters:** Use `?phone=` or `?email=` for exact matches
        ''' + PAGINATION_DESCRIPTION,
        tags=['Patients'],
        manual_parameters=[
            openapi.Parameter('search', openapi.IN_QUERY, description='Search by name, email, or phone', type=openapi.TYPE_STRING),
            openapi.Parameter('phone', openapi.IN_QUERY, description='Filter by exact phone number', type=openapi.TYPE_STRING),
            openapi.Parameter('email', openapi.IN_QUERY, description='Filter by exact email', type=openapi.TYPE_STRING),
        ] + PAGINATION_PARAMETERS
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class PatientDetailAPIView(PatientQuerySetMixin, generics.RetrieveAPIView):
    """GET /api/patients/{id}/ - Get patient details"""
    permission_classes = [IsAuthenticated]
    serializer_class = PatientDetailSerializer
    
    @swagger_auto_schema(
        operation_id='getPatientById',
        operation_summary='Get patient details',
        operation_description='Get detailed information about a patient including their profile and ongoing pregnancy.',
        tags=['Patients']
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class PatientCreateAPIView(generics.CreateAPIView):
    """POST /api/patients/ - Create a new patient"""
    permission_classes = [IsAuthenticated]
    serializer_class = PatientCreateSerializer
    
    @swagger_auto_schema(
        operation_id='postPatients',
        operation_summary='Create a new patient',
        operation_description='''
Create a new patient with their profile. 

A temporary password is generated for the patient account. The patient can reset it later.

**Required fields:** email
**Optional fields:** name, phone, blood_type, allergies, medical_history, profile_notes
        ''',
        tags=['Patients'],
        request_body=PatientCreateSerializer,
        responses={
            201: PatientDetailSerializer
        }
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        output_serializer = PatientDetailSerializer(user)
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)


class PatientUpdateAPIView(PatientQuerySetMixin, generics.UpdateAPIView):
    """PATCH /api/patients/{id}/ - Update patient"""
    permission_classes = [IsAuthenticated]
    serializer_class = PatientUpdateSerializer
    
    @swagger_auto_schema(
        operation_id='patchPatientById',
        operation_summary='Update patient',
        operation_description='Update patient information and profile.',
        tags=['Patients']
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_id='putPatientById',
        operation_summary='Update patient (full)',
        operation_description='Full update of patient information and profile.',
        tags=['Patients']
    )
    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)


# ============================================================================
# PREGNANCY VIEWS
# ============================================================================

class PregnancyQuerySetMixin:
    """Mixin to handle pregnancy queryset based on user type."""
    
    def get_queryset(self):
        user = self.request.user
        
        if user.user_type == 'doctor':
            from apps.clinics.models import Clinic
            clinic_ids = Clinic.objects.filter(doctor=user).values_list('id', flat=True)
            # Pregnancies created by doctor's clinics OR with visits to doctor's clinics
            return Pregnancy.objects.filter(
                Q(created_by_clinic_id__in=clinic_ids) |
                Q(visits__clinic_id__in=clinic_ids)
            ).select_related('patient_profile__user', 'created_by_clinic').distinct()
        
        elif user.user_type == 'employee':
            from apps.clinics.models import Employee
            clinic_ids = Employee.objects.filter(staff=user).values_list('clinic_id', flat=True)
            return Pregnancy.objects.filter(
                Q(created_by_clinic_id__in=clinic_ids) |
                Q(visits__clinic_id__in=clinic_ids)
            ).select_related('patient_profile__user', 'created_by_clinic').distinct()
        
        elif user.user_type == 'patient':
            # Patients see their own pregnancies
            if hasattr(user, 'patient_profile'):
                return Pregnancy.objects.filter(patient_profile=user.patient_profile)
        
        return Pregnancy.objects.none()


class PatientPregnancyListAPIView(generics.ListAPIView):
    """GET /api/patients/{patient_id}/pregnancies/ - List pregnancies for a patient"""
    permission_classes = [IsAuthenticated]
    serializer_class = PregnancyListSerializer
    
    def get_queryset(self):
        patient_id = self.kwargs.get('patient_id')
        return Pregnancy.objects.filter(
            patient_profile__user_id=patient_id
        ).select_related('patient_profile__user')
    
    @swagger_auto_schema(
        operation_id='getPatientPregnancies',
        operation_summary='List patient pregnancies',
        operation_description='Get all pregnancies for a specific patient.' + PAGINATION_DESCRIPTION,
        tags=['Pregnancies'],
        manual_parameters=PAGINATION_PARAMETERS
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class PatientPregnancyCreateAPIView(generics.CreateAPIView):
    """POST /api/patients/{patient_id}/pregnancies/ - Create pregnancy for patient"""
    permission_classes = [IsAuthenticated]
    serializer_class = PregnancyCreateSerializer
    
    @swagger_auto_schema(
        operation_id='postPatientPregnancy',
        operation_summary='Create pregnancy for patient',
        operation_description='''
Create a new pregnancy record for a patient.

**Optional fields:** lmp, due_date, status, is_high_risk, notes, created_by_clinic
        ''',
        tags=['Pregnancies'],
        request_body=PregnancyCreateSerializer,
        responses={
            201: PregnancyDetailSerializer
        }
    )
    def post(self, request, *args, **kwargs):
        patient_id = self.kwargs.get('patient_id')
        
        # Get or create patient profile
        try:
            user = User.objects.get(id=patient_id, user_type='patient')
        except User.DoesNotExist:
            return Response({'error': 'Patient not found'}, status=status.HTTP_404_NOT_FOUND)
        
        profile, _ = PatientProfile.objects.get_or_create(user=user)
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        pregnancy = serializer.save(patient_profile=profile)
        
        output_serializer = PregnancyDetailSerializer(pregnancy)
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)


class PregnancyDetailAPIView(PregnancyQuerySetMixin, generics.RetrieveAPIView):
    """GET /api/pregnancies/{id}/ - Get pregnancy details"""
    permission_classes = [IsAuthenticated]
    serializer_class = PregnancyDetailSerializer
    
    @swagger_auto_schema(
        operation_id='getPregnancyById',
        operation_summary='Get pregnancy details',
        operation_description='Get detailed pregnancy information including babies, visits count, and vitals count.',
        tags=['Pregnancies']
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class PregnancyUpdateAPIView(PregnancyQuerySetMixin, generics.UpdateAPIView):
    """PATCH /api/pregnancies/{id}/ - Update pregnancy"""
    permission_classes = [IsAuthenticated]
    serializer_class = PregnancyUpdateSerializer
    
    @swagger_auto_schema(
        operation_id='patchPregnancyById',
        operation_summary='Update pregnancy',
        operation_description='Update pregnancy information (lmp, due_date, status, is_high_risk, notes).',
        tags=['Pregnancies']
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_id='putPregnancyById',
        operation_summary='Update pregnancy (full)',
        operation_description='Full update of pregnancy information.',
        tags=['Pregnancies']
    )
    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)


class PregnancyDeleteAPIView(PregnancyQuerySetMixin, generics.DestroyAPIView):
    """DELETE /api/pregnancies/{id}/ - Delete pregnancy"""
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        operation_id='deletePregnancyById',
        operation_summary='Delete pregnancy',
        operation_description='Delete a pregnancy record. This will also delete associated visits, vitals, and babies.',
        tags=['Pregnancies']
    )
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)


# ============================================================================
# BABY VIEWS
# ============================================================================

class BabyQuerySetMixin:
    """Mixin to handle baby queryset based on user type."""
    
    def get_queryset(self):
        user = self.request.user
        
        if user.user_type == 'doctor':
            from apps.clinics.models import Clinic
            clinic_ids = Clinic.objects.filter(doctor=user).values_list('id', flat=True)
            return Baby.objects.filter(
                Q(pregnancy__created_by_clinic_id__in=clinic_ids) |
                Q(pregnancy__visits__clinic_id__in=clinic_ids)
            ).select_related('pregnancy__patient_profile__user').distinct()
        
        elif user.user_type == 'employee':
            from apps.clinics.models import Employee
            clinic_ids = Employee.objects.filter(staff=user).values_list('clinic_id', flat=True)
            return Baby.objects.filter(
                Q(pregnancy__created_by_clinic_id__in=clinic_ids) |
                Q(pregnancy__visits__clinic_id__in=clinic_ids)
            ).select_related('pregnancy__patient_profile__user').distinct()
        
        elif user.user_type == 'patient':
            if hasattr(user, 'patient_profile'):
                return Baby.objects.filter(pregnancy__patient_profile=user.patient_profile)
        
        return Baby.objects.none()


class PregnancyBabyListAPIView(generics.ListAPIView):
    """GET /api/pregnancies/{pregnancy_id}/babies/ - List babies in pregnancy"""
    permission_classes = [IsAuthenticated]
    serializer_class = BabyListSerializer
    
    def get_queryset(self):
        pregnancy_id = self.kwargs.get('pregnancy_id')
        return Baby.objects.filter(pregnancy_id=pregnancy_id)
    
    @swagger_auto_schema(
        operation_id='getPregnancyBabies',
        operation_summary='List babies in pregnancy',
        operation_description='Get all babies for a specific pregnancy.' + PAGINATION_DESCRIPTION,
        tags=['Babies'],
        manual_parameters=PAGINATION_PARAMETERS
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class PregnancyBabyCreateAPIView(generics.CreateAPIView):
    """POST /api/pregnancies/{pregnancy_id}/babies/ - Add baby to pregnancy"""
    permission_classes = [IsAuthenticated]
    serializer_class = BabyCreateSerializer
    
    @swagger_auto_schema(
        operation_id='postPregnancyBaby',
        operation_summary='Add baby to pregnancy',
        operation_description='''
Add a new baby to a pregnancy (for twins, triplets, etc.).

**Optional fields:** name, gender, birth_date, birth_weight, birth_length, apgar_score, is_born, notes
        ''',
        tags=['Babies'],
        request_body=BabyCreateSerializer,
        responses={
            201: BabyDetailSerializer
        }
    )
    def post(self, request, *args, **kwargs):
        pregnancy_id = self.kwargs.get('pregnancy_id')
        
        try:
            pregnancy = Pregnancy.objects.get(id=pregnancy_id)
        except Pregnancy.DoesNotExist:
            return Response({'error': 'Pregnancy not found'}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        baby = serializer.save(pregnancy=pregnancy)
        
        output_serializer = BabyDetailSerializer(baby)
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)


class BabyDetailAPIView(BabyQuerySetMixin, generics.RetrieveAPIView):
    """GET /api/babies/{id}/ - Get baby details"""
    permission_classes = [IsAuthenticated]
    serializer_class = BabyDetailSerializer
    
    @swagger_auto_schema(
        operation_id='getBabyById',
        operation_summary='Get baby details',
        operation_description='Get detailed baby information including vitals count.',
        tags=['Babies']
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class BabyUpdateAPIView(BabyQuerySetMixin, generics.UpdateAPIView):
    """PATCH /api/babies/{id}/ - Update baby"""
    permission_classes = [IsAuthenticated]
    serializer_class = BabyUpdateSerializer
    
    @swagger_auto_schema(
        operation_id='patchBabyById',
        operation_summary='Update baby',
        operation_description='Update baby information (name, gender, birth info, etc.).',
        tags=['Babies']
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_id='putBabyById',
        operation_summary='Update baby (full)',
        operation_description='Full update of baby information.',
        tags=['Babies']
    )
    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)


class BabyDeleteAPIView(BabyQuerySetMixin, generics.DestroyAPIView):
    """DELETE /api/babies/{id}/ - Delete baby"""
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        operation_id='deleteBabyById',
        operation_summary='Delete baby',
        operation_description='Delete a baby record.',
        tags=['Babies']
    )
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)

