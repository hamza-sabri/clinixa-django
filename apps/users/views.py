from rest_framework import status, generics, filters
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.views import TokenRefreshView
from django_filters.rest_framework import DjangoFilterBackend
from django.contrib.auth import get_user_model
from django.db.models import Q
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .models import PatientProfile, Pregnancy, Baby, UserAttachment
from apps.clinics.permissions import IsDoctorOrEmployee
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from apps.recordings.utils import upload_file_to_b2, delete_file_from_b2
import os
import time
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
    # User attachment serializers
    UserAttachmentSerializer,
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
        # Preserve original phone for response
        original_phone = request.data.get('phone', '')

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
            'phone': original_phone,
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
        # Preserve original phone for storage
        original_phone = request.data.get('phone', '')

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

        # Get or create user - search by all phone variants
        is_new_user = False
        user = otp_service.get_user_by_phone(phone)
        if not user:
            # Create new patient user with original phone format
            user = User.objects.create_user_with_phone(phone=original_phone, name=name)
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


class PatientMePregnancyCreateView(generics.CreateAPIView):
    """
    Create a new pregnancy for the authenticated patient.
    
    POST /api/patients/me/pregnancies/create/
    
    Allows patients to create their own pregnancy records.
    Automatically creates PatientProfile if it doesn't exist.
    """
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        from .serializers import PatientMePregnancyCreateSerializer
        return PatientMePregnancyCreateSerializer
    
    @swagger_auto_schema(
        operation_id='postPatientMePregnancy',
        operation_summary='Create pregnancy for current patient',
        operation_description='''
Create a new pregnancy record for the authenticated patient.

**Note:** This endpoint is only for patients (user_type='patient').

**All fields are optional:**
- `lmp` - Last menstrual period date (YYYY-MM-DD)
- `due_date` - Expected due date (YYYY-MM-DD)
- `is_high_risk` - Whether this is a high-risk pregnancy (default: false)
- `notes` - Additional notes
- `babies_count` - Number of babies to auto-create (1-8, default: 1)

**Example request:**
```json
{
    "lmp": "2024-01-15",
    "due_date": "2024-10-22",
    "is_high_risk": false,
    "notes": "First pregnancy",
    "babies_count": 2
}
```

**Note:** If you have any existing ongoing pregnancies, they will be automatically marked as 'delivered'.

**Returns:** Full pregnancy details including calculated fields (pregnancy_week, trimester).
        ''',
        tags=['Patient Self-Service'],
        responses={
            201: openapi.Response(
                description='Pregnancy created successfully',
                examples={
                    'application/json': {
                        'id': 123,
                        'patient': {'id': 456, 'name': 'فاطمة أحمد', 'email': None, 'phone': '+971501234567'},
                        'lmp': '2024-01-15',
                        'due_date': '2024-10-22',
                        'status': 'ongoing',
                        'is_high_risk': False,
                        'pregnancy_week': 12,
                        'trimester': 1,
                        'notes': 'First pregnancy',
                        'babies_count': 2,
                        'babies': [{'id': 1, 'name': '', 'gender': ''}, {'id': 2, 'name': '', 'gender': ''}],
                        'visits_count': 0,
                        'vitals_count': 0,
                        'created_at': '2024-01-20T10:30:00Z',
                        'auto_closed_pregnancies_count': 1
                    }
                }
            ),
            403: openapi.Response(description='Not a patient user')
        }
    )
    def post(self, request, *args, **kwargs):
        # Ensure only patients can access
        if request.user.user_type != 'patient':
            return Response(
                {'error': 'This endpoint is only for patient users'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get or create patient profile
        profile, _ = PatientProfile.objects.get_or_create(user=request.user)
        
        # Mark existing ongoing pregnancies as delivered (single active pregnancy constraint)
        existing_ongoing = Pregnancy.objects.filter(
            patient_profile=profile,
            status='ongoing'
        )
        auto_closed_count = existing_ongoing.count()
        existing_ongoing.update(status='delivered')
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Save with the patient profile
        pregnancy = serializer.save(patient_profile=profile)
        
        # Auto-create babies based on babies_count
        babies_count = int(request.data.get('babies_count', 1))
        babies_count = max(1, min(babies_count, 8))  # Clamp between 1-8
        for i in range(babies_count):
            Baby.objects.create(pregnancy=pregnancy)
        
        # Return full pregnancy details
        from .serializers import PregnancyDetailSerializer
        output_serializer = PregnancyDetailSerializer(pregnancy)
        response_data = output_serializer.data
        
        # Add info about auto-closed pregnancies if any
        if auto_closed_count > 0:
            response_data['auto_closed_pregnancies_count'] = auto_closed_count
        
        return Response(response_data, status=status.HTTP_201_CREATED)


# ============================================================================
# QUICK PATIENT CREATE VIEW
# ============================================================================

from .serializers import QuickPatientCreateSerializer, QuickPatientCreateResponseSerializer


class QuickPatientCreateAPIView(APIView):
    """
    Create a patient with optional pregnancy in a single request.

    POST /api/patients/quick-create/

    This endpoint allows doctors/employees to quickly register a new patient
    and optionally create a pregnancy for them in one API call.
    """
    permission_classes = [IsAuthenticated, IsDoctorOrEmployee]

    @swagger_auto_schema(
        operation_id='postPatientQuickCreate',
        operation_summary='Quick create patient with optional pregnancy',
        operation_description='''
Create a new patient and optionally a pregnancy in a single API call.

**Required fields:**
- `name` - Patient full name
- `phone` - Phone number in international format (e.g., +971501234567)

**Optional fields:**
- `birthday` - Patient birth date (YYYY-MM-DD)
- `city` - City ID for the patient
- `lmp` - Last menstrual period date (YYYY-MM-DD). If provided, a pregnancy will be created automatically.
- `due_date` - Expected due date (YYYY-MM-DD). Optional - if not provided but lmp is, it will be calculated as LMP + 280 days.

**Behavior:**
- Creates a new patient user with phone-based authentication
- Creates a PatientProfile for the user
- If `lmp` is provided, creates an ongoing pregnancy with one baby
- If `due_date` is not provided, it is calculated from LMP (LMP + 280 days)

**Example request (with pregnancy using lmp only):**
```json
{
    "name": "فاطمة أحمد",
    "phone": "+971501234567",
    "birthday": "1990-05-15",
    "city": 1,
    "lmp": "2026-01-10"
}
```

**Example request (with pregnancy using both lmp and due_date):**
```json
{
    "name": "فاطمة أحمد",
    "phone": "+971501234567",
    "birthday": "1990-05-15",
    "city": 1,
    "lmp": "2026-01-10",
    "due_date": "2026-10-17"
}
```

**Example request (without pregnancy):**
```json
{
    "name": "سارة محمد",
    "phone": "+971509876543"
}
```

**Note:** Only accessible by doctors and employees.
        ''',
        tags=['Patients'],
        request_body=QuickPatientCreateSerializer,
        responses={
            201: openapi.Response(
                description='Patient created successfully',
                schema=QuickPatientCreateResponseSerializer,
                examples={
                    'application/json': {
                        'id': 123,
                        'name': 'فاطمة أحمد',
                        'phone': '+971501234567',
                        'birthday': '1990-05-15',
                        'city': 1,
                        'city_name': 'Dubai',
                        'pregnancy': {
                            'id': 456,
                            'lmp': '2026-01-10',
                            'due_date': '2026-10-17',
                            'status': 'ongoing',
                            'pregnancy_week': 1,
                            'trimester': 1,
                            'babies_count': 1
                        },
                        'created_at': '2026-01-14T10:30:00Z'
                    }
                }
            ),
            400: openapi.Response(
                description='Validation error',
                examples={
                    'application/json': {
                        'phone': ['A patient with this phone number already exists.']
                    }
                }
            )
        }
    )
    def post(self, request):
        serializer = QuickPatientCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user = serializer.save()
        pregnancy = getattr(user, '_created_pregnancy', None)

        # Build response
        response_data = {
            'id': user.id,
            'name': user.name,
            'phone': user.phone,
            'birthday': user.birth_date,
            'city': user.city_id,
            'city_name': user.city.name if user.city else None,
            'pregnancy': None,
            'created_at': user.created_at
        }

        if pregnancy:
            response_data['pregnancy'] = {
                'id': pregnancy.id,
                'lmp': pregnancy.lmp,
                'due_date': pregnancy.due_date,
                'status': pregnancy.status,
                'pregnancy_week': pregnancy.pregnancy_week,
                'trimester': pregnancy.trimester,
                'babies_count': pregnancy.babies.count()
            }

        return Response(response_data, status=status.HTTP_201_CREATED)


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
        elif user.user_type == 'patient' and hasattr(user, 'patient_profile'):
            return User.objects.filter(id=user.id, user_type='patient').select_related('patient_profile').distinct()
        
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
            return Pregnancy.objects.all().select_related('patient_profile__user', 'created_by_clinic').distinct()
        
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
        operation_description='''
Get all pregnancies for a specific patient.

**Response includes:**
- Basic pregnancy info: id, lmp, due_date, status, is_high_risk
- Calculated fields: pregnancy_week, trimester
- Counts: babies_count
- Notes: pregnancy notes
        ''' + PAGINATION_DESCRIPTION,
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

**Optional fields:** lmp, due_date, status, is_high_risk, notes, created_by_clinic, babies_count

**babies_count:** Number of babies to auto-create (1-8, default: 1). Use for twins, triplets, etc.

**Note:** If the patient has any existing ongoing pregnancies, they will be automatically marked as 'delivered'.
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
        
        # Mark existing ongoing pregnancies as delivered (single active pregnancy constraint)
        existing_ongoing = Pregnancy.objects.filter(
            patient_profile=profile,
            status='ongoing'
        )
        auto_closed_count = existing_ongoing.count()
        existing_ongoing.update(status='delivered')
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        pregnancy = serializer.save(patient_profile=profile)
        
        # Auto-create babies based on babies_count
        babies_count = int(request.data.get('babies_count', 1))
        babies_count = max(1, min(babies_count, 8))  # Clamp between 1-8
        for i in range(babies_count):
            Baby.objects.create(pregnancy=pregnancy)
        
        output_serializer = PregnancyDetailSerializer(pregnancy)
        response_data = output_serializer.data
        
        # Add info about auto-closed pregnancies if any
        if auto_closed_count > 0:
            response_data['auto_closed_pregnancies_count'] = auto_closed_count
        
        return Response(response_data, status=status.HTTP_201_CREATED)


class PatientPregnancyDetailAPIView(generics.RetrieveAPIView):
    """GET /api/patients/{patient_id}/pregnancies/{pregnancy_id}/ - Get specific pregnancy for patient"""
    permission_classes = [IsAuthenticated, IsDoctorOrEmployee]
    serializer_class = PregnancyDetailSerializer
    lookup_url_kwarg = 'pregnancy_id'
    
    def get_queryset(self):
        patient_id = self.kwargs.get('patient_id')
        return Pregnancy.objects.filter(
            patient_profile__user_id=patient_id
        ).select_related('patient_profile__user', 'created_by_clinic')
    
    @swagger_auto_schema(
        operation_id='getPatientPregnancyById',
        operation_summary='Get specific pregnancy for patient',
        operation_description='''
Get detailed information about a specific pregnancy for a patient.

**Response includes:**
- All pregnancy fields: id, lmp, due_date, status, is_high_risk, notes
- Calculated fields: pregnancy_week, trimester
- Related data: babies (nested list with vitals), visits, vitals
- Counts: babies_count, visits_count, vitals_count

**Note:** Only accessible by doctors and employees.
        ''',
        tags=['Pregnancies']
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class PatientPregnancyUpdateAPIView(generics.UpdateAPIView):
    """PATCH/PUT /api/patients/{patient_id}/pregnancies/{pregnancy_id}/update/ - Update specific pregnancy for patient"""
    permission_classes = [IsAuthenticated, IsDoctorOrEmployee]
    serializer_class = PregnancyUpdateSerializer
    lookup_url_kwarg = 'pregnancy_id'
    
    def get_queryset(self):
        patient_id = self.kwargs.get('patient_id')
        return Pregnancy.objects.filter(
            patient_profile__user_id=patient_id
        ).select_related('patient_profile__user', 'created_by_clinic')
    
    @swagger_auto_schema(
        operation_id='patchPatientPregnancyById',
        operation_summary='Update specific pregnancy for patient',
        operation_description='''
Update a specific pregnancy for a patient.

**Updatable fields:**
- lmp: Last menstrual period date (YYYY-MM-DD)
- due_date: Expected due date (YYYY-MM-DD)
- status: ongoing, delivered, miscarriage, ectopic, stillbirth
- is_high_risk: Boolean
- notes: Text

**Returns:** Full updated pregnancy object with all related data.

**Note:** Only accessible by doctors and employees.
        ''',
        tags=['Pregnancies'],
        request_body=PregnancyUpdateSerializer,
        responses={
            200: PregnancyDetailSerializer
        }
    )
    def patch(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_id='putPatientPregnancyById',
        operation_summary='Update specific pregnancy for patient (full)',
        operation_description='Full update of a specific pregnancy for a patient.',
        tags=['Pregnancies'],
        request_body=PregnancyUpdateSerializer,
        responses={
            200: PregnancyDetailSerializer
        }
    )
    def put(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)
    
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        
        # Return full pregnancy details
        output_serializer = PregnancyDetailSerializer(instance)
        return Response(output_serializer.data)


class PatientPregnancyDeleteAPIView(generics.DestroyAPIView):
    """DELETE /api/patients/{patient_id}/pregnancies/{pregnancy_id}/delete/ - Delete specific pregnancy for patient"""
    permission_classes = [IsAuthenticated, IsDoctorOrEmployee]
    lookup_url_kwarg = 'pregnancy_id'
    
    def get_queryset(self):
        patient_id = self.kwargs.get('patient_id')
        return Pregnancy.objects.filter(
            patient_profile__user_id=patient_id
        ).select_related('patient_profile__user')
    
    @swagger_auto_schema(
        operation_id='deletePatientPregnancyById',
        operation_summary='Delete specific pregnancy for patient',
        operation_description='''
Delete a specific pregnancy for a patient.

**Warning:** This will also delete all associated:
- Visits
- Vitals (mother's)
- Babies and their vitals

**Returns:** 204 No Content on success.

**Note:** Only accessible by doctors and employees.
        ''',
        tags=['Pregnancies'],
        responses={
            204: openapi.Response(description='Pregnancy deleted successfully')
        }
    )
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)


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
            return Baby.objects.all().select_related('pregnancy__patient_profile__user').distinct()
        
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


# ============================================================================
# USER ATTACHMENT VIEWS
# ============================================================================

class UserMeAttachmentListUploadAPIView(APIView):
    """
    GET /api/users/me/attachments/ - List current user's attachments
    POST /api/users/me/attachments/ - Upload attachments for current user
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    
    @swagger_auto_schema(
        operation_id='getUserMeAttachments',
        operation_summary='List my attachments',
        operation_description='''
List all attachments for the authenticated user.

**Response includes:**
- Presigned B2 URLs for secure file access
- Original filename extracted from stored name
- File type and upload date
        ''',
        tags=['User Attachments'],
        responses={
            200: UserAttachmentSerializer(many=True)
        }
    )
    def get(self, request):
        attachments = UserAttachment.objects.filter(user=request.user)
        serializer = UserAttachmentSerializer(attachments, many=True)
        return Response({
            'attachments': serializer.data,
            'count': attachments.count()
        }, status=status.HTTP_200_OK)
    
    @swagger_auto_schema(
        operation_id='postUserMeAttachments',
        operation_summary='Upload my attachments',
        operation_description='''
Upload one or more file attachments for the authenticated user.

**Request:**
- Use `multipart/form-data` encoding
- Field name: `attachments` (can send multiple files)
- Optional: `description` field for each file (single description applies to all)
- Supported: Any file type (images, PDFs, documents, etc.)

**Form Fields:**
- `attachments` (file, required): Files to upload (can be multiple)
- `description` (string, optional): Description for the attachments

**Example (curl):**
```bash
curl -X POST 'http://localhost:8000/api/users/me/attachments/' \\
  -H 'Authorization: Bearer {token}' \\
  -F "attachments=@insurance_card.pdf" \\
  -F "attachments=@id_card.jpg" \\
  -F "description=Medical documents"
```

**Response:**
Returns the list of uploaded attachments with presigned URLs.
        ''',
        tags=['User Attachments'],
        responses={
            200: UserAttachmentSerializer(many=True),
            400: 'No files provided'
        }
    )
    def post(self, request):
        # Get uploaded files
        files = request.FILES.getlist('attachments')
        if not files:
            files = request.FILES.getlist('files')
        
        if not files:
            return Response(
                {'error': 'No files provided. Use field name "attachments" or "files".'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        description = request.data.get('description', '')
        uploaded_attachments = []
        errors = []
        
        for file_obj in files:
            try:
                # Naming: user_{id}_att_{timestamp}_{original_name}
                timestamp = int(time.time())
                safe_name = os.path.basename(file_obj.name).replace(' ', '_')
                target_filename = f"user_{request.user.id}_att_{timestamp}_{safe_name}"
                
                # Upload to B2
                uploaded = upload_file_to_b2(file_obj, target_filename)
                
                # Create attachment record
                attachment = UserAttachment.objects.create(
                    user=request.user,
                    name=uploaded.file_name,
                    file_id=uploaded.id_,
                    file_type=file_obj.content_type or 'application/octet-stream',
                    description=description
                )
                uploaded_attachments.append(attachment)
                
            except Exception as e:
                errors.append({
                    'file': file_obj.name,
                    'error': str(e)
                })
        
        # Serialize and return
        serializer = UserAttachmentSerializer(uploaded_attachments, many=True)
        response_data = {
            'attachments': serializer.data,
            'uploaded_count': len(uploaded_attachments)
        }
        
        if errors:
            response_data['errors'] = errors
        
        return Response(response_data, status=status.HTTP_200_OK)


class UserMeAttachmentDeleteAPIView(APIView):
    """DELETE /api/users/me/attachments/{attachment_id}/ - Delete an attachment"""
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        operation_id='deleteUserMeAttachment',
        operation_summary='Delete my attachment',
        operation_description='''
Delete a specific attachment from the authenticated user's account.

**Warning:** This permanently deletes the file from storage (B2).
        ''',
        tags=['User Attachments'],
        responses={
            200: openapi.Response(
                description='Attachment deleted successfully',
                examples={
                    'application/json': {
                        'message': 'Attachment deleted successfully'
                    }
                }
            ),
            404: 'Attachment not found'
        }
    )
    def delete(self, request, attachment_id):
        try:
            attachment = UserAttachment.objects.get(
                pk=attachment_id,
                user=request.user
            )
            
            # Delete from B2
            delete_file_from_b2(attachment.file_id, attachment.name)
            
            # Delete from database
            attachment.delete()
            
            return Response(
                {'message': 'Attachment deleted successfully'},
                status=status.HTTP_200_OK
            )
        except UserAttachment.DoesNotExist:
            return Response(
                {'error': 'Attachment not found'},
                status=status.HTTP_404_NOT_FOUND
            )


class PatientAttachmentListUploadAPIView(APIView):
    """
    GET /api/patients/{pk}/attachments/ - List patient's attachments (for doctors/employees)
    POST /api/patients/{pk}/attachments/ - Upload attachments for patient (for doctors/employees)
    """
    permission_classes = [IsAuthenticated, IsDoctorOrEmployee]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    
    @swagger_auto_schema(
        operation_id='getPatientAttachments',
        operation_summary='List patient attachments',
        operation_description='''
List all attachments for a specific patient.

**Access:** Only doctors and employees can access this endpoint.

**Response includes:**
- Presigned B2 URLs for secure file access
- Original filename extracted from stored name
- File type and upload date
        ''',
        tags=['Patient Attachments'],
        responses={
            200: UserAttachmentSerializer(many=True),
            404: 'Patient not found'
        }
    )
    def get(self, request, pk):
        try:
            patient = User.objects.get(pk=pk, user_type='patient')
        except User.DoesNotExist:
            return Response(
                {'error': 'Patient not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        attachments = UserAttachment.objects.filter(user=patient)
        serializer = UserAttachmentSerializer(attachments, many=True)
        return Response({
            'patient_id': patient.id,
            'patient_name': patient.name,
            'attachments': serializer.data,
            'count': attachments.count()
        }, status=status.HTTP_200_OK)
    
    @swagger_auto_schema(
        operation_id='postPatientAttachments',
        operation_summary='Upload patient attachments',
        operation_description='''
Upload one or more file attachments for a specific patient.

**Access:** Only doctors and employees can access this endpoint.

**Request:**
- Use `multipart/form-data` encoding
- Field name: `attachments` (can send multiple files)
- Optional: `description` field for each file
- Supported: Any file type (images, PDFs, documents, etc.)

**Form Fields:**
- `attachments` (file, required): Files to upload (can be multiple)
- `description` (string, optional): Description for the attachments

**Example (curl):**
```bash
curl -X POST 'http://localhost:8000/api/patients/{id}/attachments/' \\
  -H 'Authorization: Bearer {token}' \\
  -F "attachments=@lab_results.pdf" \\
  -F "description=Lab results from Jan 2026"
```
        ''',
        tags=['Patient Attachments'],
        responses={
            200: UserAttachmentSerializer(many=True),
            400: 'No files provided',
            404: 'Patient not found'
        }
    )
    def post(self, request, pk):
        try:
            patient = User.objects.get(pk=pk, user_type='patient')
        except User.DoesNotExist:
            return Response(
                {'error': 'Patient not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get uploaded files
        files = request.FILES.getlist('attachments')
        if not files:
            files = request.FILES.getlist('files')
        
        if not files:
            return Response(
                {'error': 'No files provided. Use field name "attachments" or "files".'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        description = request.data.get('description', '')
        uploaded_attachments = []
        errors = []
        
        for file_obj in files:
            try:
                # Naming: user_{id}_att_{timestamp}_{original_name}
                timestamp = int(time.time())
                safe_name = os.path.basename(file_obj.name).replace(' ', '_')
                target_filename = f"user_{patient.id}_att_{timestamp}_{safe_name}"
                
                # Upload to B2
                uploaded = upload_file_to_b2(file_obj, target_filename)
                
                # Create attachment record
                attachment = UserAttachment.objects.create(
                    user=patient,
                    name=uploaded.file_name,
                    file_id=uploaded.id_,
                    file_type=file_obj.content_type or 'application/octet-stream',
                    description=description
                )
                uploaded_attachments.append(attachment)
                
            except Exception as e:
                errors.append({
                    'file': file_obj.name,
                    'error': str(e)
                })
        
        # Serialize and return
        serializer = UserAttachmentSerializer(uploaded_attachments, many=True)
        response_data = {
            'patient_id': patient.id,
            'attachments': serializer.data,
            'uploaded_count': len(uploaded_attachments)
        }
        
        if errors:
            response_data['errors'] = errors
        
        return Response(response_data, status=status.HTTP_200_OK)


class PatientAttachmentDeleteAPIView(APIView):
    """DELETE /api/patients/{pk}/attachments/{attachment_id}/ - Delete patient attachment"""
    permission_classes = [IsAuthenticated, IsDoctorOrEmployee]
    
    @swagger_auto_schema(
        operation_id='deletePatientAttachment',
        operation_summary='Delete patient attachment',
        operation_description='''
Delete a specific attachment from a patient's account.

**Access:** Only doctors and employees can access this endpoint.

**Warning:** This permanently deletes the file from storage (B2).
        ''',
        tags=['Patient Attachments'],
        responses={
            200: openapi.Response(
                description='Attachment deleted successfully',
                examples={
                    'application/json': {
                        'message': 'Attachment deleted successfully'
                    }
                }
            ),
            404: 'Patient or attachment not found'
        }
    )
    def delete(self, request, pk, attachment_id):
        try:
            patient = User.objects.get(pk=pk, user_type='patient')
        except User.DoesNotExist:
            return Response(
                {'error': 'Patient not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        try:
            attachment = UserAttachment.objects.get(
                pk=attachment_id,
                user=patient
            )
            
            # Delete from B2
            delete_file_from_b2(attachment.file_id, attachment.name)
            
            # Delete from database
            attachment.delete()
            
            return Response(
                {'message': 'Attachment deleted successfully'},
                status=status.HTTP_200_OK
            )
        except UserAttachment.DoesNotExist:
            return Response(
                {'error': 'Attachment not found'},
                status=status.HTTP_404_NOT_FOUND
            )

