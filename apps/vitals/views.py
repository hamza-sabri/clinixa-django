from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
import os
import time

from rest_framework.pagination import PageNumberPagination

from .models import Vital, BabyVital, VitalAttachment, PatientVital, PatientVitalAttachment
from .serializers import (
    VitalSerializer,
    VitalCreateSerializer,
    VitalUpdateSerializer,
    VitalListSerializer,
    VitalAttachmentSerializer,
    BabyVitalSerializer,
    BabyVitalCreateSerializer,
    BabyVitalUpdateSerializer,
    BabyVitalListSerializer,
    PatientVitalSerializer,
    PatientVitalCreateSerializer,
    PatientVitalUpdateSerializer,
    PatientVitalListSerializer,
    PatientVitalAttachmentSerializer,
)
from apps.clinics.models import Clinic, Employee
from apps.core.swagger import PAGINATION_PARAMETERS, PAGINATION_DESCRIPTION
from apps.recordings.utils import upload_file_to_b2


# ============================================================================
# VITAL VIEWS (Mother's vitals)
# ============================================================================

class VitalQuerySetMixin:
    """Mixin to handle queryset logic for vitals based on user type."""
    
    def get_queryset(self):
        user = self.request.user
        
        # Patients see only their own vitals (via pregnancy)
        if user.user_type == 'patient':
            if hasattr(user, 'patient_profile'):
                return Vital.objects.filter(
                    Q(pregnancy__patient_profile=user.patient_profile) |
                    Q(patient=user)  # Legacy support
                ).select_related('pregnancy__patient_profile__user', 'patient', 'visit')
            return Vital.objects.filter(patient=user).select_related('patient', 'visit')
        
        # Doctors see vitals of patients who visited their clinics
        elif user.user_type == 'doctor':

            return Vital.objects.all().select_related('pregnancy__patient_profile__user', 'patient', 'visit').distinct()
        
        # Employees see vitals based on their clinic assignments
        elif user.user_type == 'employee':
            clinic_ids = Employee.objects.filter(staff=user).values_list('clinic_id', flat=True)
            return Vital.objects.filter(
                Q(pregnancy__visits__clinic_id__in=clinic_ids) |
                Q(pregnancy__created_by_clinic_id__in=clinic_ids) |
                Q(visit__clinic_id__in=clinic_ids)
            ).select_related('pregnancy__patient_profile__user', 'patient', 'visit').distinct()
        
        return Vital.objects.none()


class VitalListAPIView(VitalQuerySetMixin, generics.ListAPIView):
    """GET /api/vitals/ - List vital records"""
    permission_classes = [IsAuthenticated]
    serializer_class = VitalListSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['pregnancy', 'visit']
    
    def get_queryset(self):
        queryset = super().get_queryset().prefetch_related('visit__attachments', 'attachments')
        
        # Handle patient=me filter
        patient_filter = self.request.query_params.get('patient')
        if patient_filter == 'me' and self.request.user.user_type == 'patient':
            if hasattr(self.request.user, 'patient_profile'):
                queryset = queryset.filter(
                    Q(pregnancy__patient_profile=self.request.user.patient_profile) |
                    Q(patient=self.request.user)
                )
            else:
                queryset = queryset.filter(patient=self.request.user)
        
        return queryset
    
    @swagger_auto_schema(
        operation_id='getVitals',
        operation_summary='List vital records',
        operation_description='''
Get a list of vital records (mother's vitals).

**Access Control:**
- Patients see their own vitals
- Doctors/employees see vitals of patients who visited their clinics

**Filters:**
- `?patient=me` - (For patients) Get only your own vitals
- `?pregnancy=` - Filter by pregnancy ID
- `?visit=` - Filter by visit ID

**Response Fields:**
- `note` - Patient's notes for the vital record
- `dr_note` - Doctor's notes for the vital record
- `files` - Array of file URLs attached to the vital (e.g., Cloudinary URLs)
- `attachments` - Array of direct vital attachments (with presigned B2 URLs)
- `visit_attachments` - Array of attachments from the related visit (with presigned B2 URLs)
        ''' + PAGINATION_DESCRIPTION,
        tags=['Vitals'],
        manual_parameters=[
            openapi.Parameter('patient', openapi.IN_QUERY, description='Filter by patient (use "me" for own vitals)', type=openapi.TYPE_STRING),
            openapi.Parameter('pregnancy', openapi.IN_QUERY, description='Filter by pregnancy ID', type=openapi.TYPE_INTEGER),
            openapi.Parameter('visit', openapi.IN_QUERY, description='Filter by visit ID', type=openapi.TYPE_INTEGER),
        ] + PAGINATION_PARAMETERS
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class VitalDetailAPIView(VitalQuerySetMixin, generics.RetrieveAPIView):
    """GET /api/vitals/{id}/ - Get vital record details"""
    permission_classes = [IsAuthenticated]
    serializer_class = VitalSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    
    @swagger_auto_schema(
        operation_id='getVitalsById',
        operation_summary='Get vital record details',
        operation_description='Get detailed information about a specific vital record including attached files.',
        tags=['Vitals']
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class VitalCreateAPIView(generics.CreateAPIView):
    """POST /api/vitals/create/ - Create vital record"""
    permission_classes = [IsAuthenticated]
    serializer_class = VitalCreateSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    
    @swagger_auto_schema(
        operation_id='postVitals',
        operation_summary='Create a vital record',
        operation_description='''
Create a new vital record for a pregnancy.

**Required fields:**
- `pregnancy` - Pregnancy ID

**Optional fields:**
- `visit` - Link to a specific visit
- `systolic`, `diastolic` - Blood pressure readings
- `o2` - Oxygen saturation
- `puls` - Pulse rate
- `temp` - Temperature
- `weight` - Weight in kg
- `reading_date` - Date/time of reading
- `mood` - Patient mood
- `note` - Patient note
- `dr_note` - Doctor note
- `uploaded_files` - File attachments (multipart/form-data)
        ''',
        tags=['Vitals'],
        request_body=VitalCreateSerializer
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class VitalUpdateAPIView(VitalQuerySetMixin, generics.UpdateAPIView):
    """PUT/PATCH /api/vitals/{id}/update/ - Update vital record"""
    permission_classes = [IsAuthenticated]
    serializer_class = VitalUpdateSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    
    @swagger_auto_schema(
        operation_id='putVitalsById',
        operation_summary='Update a vital record',
        operation_description='Update a vital record. New file uploads are appended to existing files.',
        tags=['Vitals']
    )
    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_id='patchVitalsById',
        operation_summary='Partially update a vital record',
        operation_description='Partially update a vital record.',
        tags=['Vitals']
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)


class VitalDeleteAPIView(VitalQuerySetMixin, generics.DestroyAPIView):
    """DELETE /api/vitals/{id}/delete/ - Delete vital record"""
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        operation_id='deleteVitalsById',
        operation_summary='Delete a vital record',
        operation_description='Delete a vital record.',
        tags=['Vitals']
    )
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)


# ============================================================================
# BABY VITAL VIEWS
# ============================================================================

class BabyVitalQuerySetMixin:
    """Mixin to handle queryset logic for baby vitals based on user type."""
    
    def get_queryset(self):
        user = self.request.user
        
        # Patients see only their own baby vitals (via pregnancy)
        if user.user_type == 'patient':
            if hasattr(user, 'patient_profile'):
                return BabyVital.objects.filter(
                    Q(baby__pregnancy__patient_profile=user.patient_profile) |
                    Q(parent=user)  # Legacy support
                ).select_related('baby__pregnancy__patient_profile__user', 'parent', 'visit')
            return BabyVital.objects.filter(parent=user).select_related('parent', 'visit')
        
        # Doctors see baby vitals of patients who visited their clinics
        elif user.user_type == 'doctor':
            clinic_ids = Clinic.objects.filter(doctor=user).values_list('id', flat=True)
            return BabyVital.objects.filter(
                Q(baby__pregnancy__visits__clinic_id__in=clinic_ids) |
                Q(baby__pregnancy__created_by_clinic_id__in=clinic_ids) |
                Q(visit__clinic_id__in=clinic_ids)
            ).select_related('baby__pregnancy__patient_profile__user', 'parent', 'visit').distinct()
        
        # Employees see baby vitals based on their clinic assignments
        elif user.user_type == 'employee':
            clinic_ids = Employee.objects.filter(staff=user).values_list('clinic_id', flat=True)
            return BabyVital.objects.filter(
                Q(baby__pregnancy__visits__clinic_id__in=clinic_ids) |
                Q(baby__pregnancy__created_by_clinic_id__in=clinic_ids) |
                Q(visit__clinic_id__in=clinic_ids)
            ).select_related('baby__pregnancy__patient_profile__user', 'parent', 'visit').distinct()
        
        return BabyVital.objects.none()


class BabyVitalListAPIView(BabyVitalQuerySetMixin, generics.ListAPIView):
    """GET /api/baby-vitals/ - List baby vital records"""
    permission_classes = [IsAuthenticated]
    serializer_class = BabyVitalListSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['baby', 'visit']
    
    @swagger_auto_schema(
        operation_id='getBabyVitals',
        operation_summary='List baby vital records',
        operation_description='''
Get a list of baby vital records.

**Access Control:**
- Patients see their own baby vitals
- Doctors/employees see vitals from their clinics

**Filters:**
- `?baby=` - Filter by baby ID
- `?visit=` - Filter by visit ID

**Response Fields:**
- `note` - Notes
- `files` - Array of file URLs attached to the vital (e.g., Cloudinary URLs)
- `visit_attachments` - Array of attachments from the related visit (with presigned B2 URLs)
        ''' + PAGINATION_DESCRIPTION,
        tags=['Baby Vitals'],
        manual_parameters=[
            openapi.Parameter('baby', openapi.IN_QUERY, description='Filter by baby ID', type=openapi.TYPE_INTEGER),
            openapi.Parameter('visit', openapi.IN_QUERY, description='Filter by visit ID', type=openapi.TYPE_INTEGER),
        ] + PAGINATION_PARAMETERS
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        return super().get_queryset().prefetch_related('visit__attachments')


class BabyVitalDetailAPIView(BabyVitalQuerySetMixin, generics.RetrieveAPIView):
    """GET /api/baby-vitals/{id}/ - Get baby vital record details"""
    permission_classes = [IsAuthenticated]
    serializer_class = BabyVitalSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    
    @swagger_auto_schema(
        operation_id='getBabyVitalsById',
        operation_summary='Get baby vital record details',
        operation_description='Get detailed information about a specific baby vital record.',
        tags=['Baby Vitals']
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class BabyVitalCreateAPIView(generics.CreateAPIView):
    """POST /api/baby-vitals/create/ - Create baby vital record"""
    permission_classes = [IsAuthenticated]
    serializer_class = BabyVitalCreateSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    
    @swagger_auto_schema(
        operation_id='postBabyVitals',
        operation_summary='Create a baby vital record',
        operation_description='''
Create a new baby vital record.

**Required fields:**
- `baby` - Baby ID

**Optional fields:**
- `visit` - Link to a specific visit
- `puls` - Pulse rate
- `systolic`, `diastolic` - Blood pressure
- `o2` - Oxygen saturation
- `weight` - Weight in kg
- `age` - Age string
- `note` - Notes
- `reading_date` - Date/time of reading
- `due_date` - Due date
- `uploaded_files` - File attachments
        ''',
        tags=['Baby Vitals'],
        request_body=BabyVitalCreateSerializer
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class BabyVitalUpdateAPIView(BabyVitalQuerySetMixin, generics.UpdateAPIView):
    """PUT/PATCH /api/baby-vitals/{id}/update/ - Update baby vital record"""
    permission_classes = [IsAuthenticated]
    serializer_class = BabyVitalUpdateSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    
    @swagger_auto_schema(
        operation_id='putBabyVitalsById',
        operation_summary='Update a baby vital record',
        operation_description='Update a baby vital record. New file uploads are appended to existing files.',
        tags=['Baby Vitals']
    )
    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_id='patchBabyVitalsById',
        operation_summary='Partially update a baby vital record',
        operation_description='Partially update a baby vital record.',
        tags=['Baby Vitals']
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)


class BabyVitalDeleteAPIView(BabyVitalQuerySetMixin, generics.DestroyAPIView):
    """DELETE /api/baby-vitals/{id}/delete/ - Delete baby vital record"""
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        operation_id='deleteBabyVitalsById',
        operation_summary='Delete a baby vital record',
        operation_description='Delete a baby vital record.',
        tags=['Baby Vitals']
    )
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)


# ============================================================================
# VITAL ATTACHMENT VIEWS
# ============================================================================

class VitalAttachmentUploadAPIView(VitalQuerySetMixin, APIView):
    """POST /api/vitals/{id}/attachments/ - Upload attachments to a vital record"""
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    
    @swagger_auto_schema(
        operation_id='postVitalAttachments',
        operation_summary='Upload attachments to a vital record',
        operation_description='''
Upload one or more file attachments to a vital record.

**Request:**
- Use `multipart/form-data` encoding
- Field name: `attachments` (can send multiple files)
- Supported: Any file type (images, PDFs, documents, etc.)

**Example (curl):**
```bash
curl -X POST 'http://localhost:8000/api/vitals/{id}/attachments/' \\
  -H 'Authorization: Bearer {token}' \\
  -F "attachments=@file1.pdf" \\
  -F "attachments=@file2.jpg"
```

**Response:**
Returns the list of uploaded attachments with presigned URLs.
        ''',
        tags=['Vitals'],
        manual_parameters=[
            openapi.Parameter(
                'attachments',
                openapi.IN_FORM,
                description='Files to upload (can be multiple)',
                type=openapi.TYPE_FILE,
                required=True
            ),
        ],
        responses={
            200: VitalAttachmentSerializer(many=True),
            404: 'Vital record not found'
        }
    )
    def post(self, request, pk):
        # Get the vital record
        try:
            queryset = self.get_queryset()
            vital = queryset.get(pk=pk)
        except Vital.DoesNotExist:
            return Response(
                {'error': 'Vital record not found'},
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
        
        uploaded_attachments = []
        errors = []
        
        for file_obj in files:
            try:
                # Naming: vital_{id}_att_{timestamp}_{original_name}
                timestamp = int(time.time())
                safe_name = os.path.basename(file_obj.name).replace(' ', '_')
                target_filename = f"vital_{vital.id}_att_{timestamp}_{safe_name}"
                
                # Upload to B2
                uploaded = upload_file_to_b2(file_obj, target_filename)
                
                # Create attachment record
                attachment = VitalAttachment.objects.create(
                    vital=vital,
                    name=uploaded.file_name,
                    file_id=uploaded.id_,
                    file_type=file_obj.content_type or 'application/octet-stream'
                )
                uploaded_attachments.append(attachment)
                
            except Exception as e:
                errors.append({
                    'file': file_obj.name,
                    'error': str(e)
                })
        
        # Serialize and return
        serializer = VitalAttachmentSerializer(uploaded_attachments, many=True)
        response_data = {
            'attachments': serializer.data,
            'uploaded_count': len(uploaded_attachments)
        }
        
        if errors:
            response_data['errors'] = errors
        
        return Response(response_data, status=status.HTTP_200_OK)


class VitalAttachmentDeleteAPIView(VitalQuerySetMixin, APIView):
    """DELETE /api/vitals/{vital_id}/attachments/{attachment_id}/ - Delete an attachment"""
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        operation_id='deleteVitalAttachment',
        operation_summary='Delete a vital attachment',
        operation_description='Delete a specific attachment from a vital record.',
        tags=['Vitals'],
        responses={
            200: 'Attachment deleted successfully',
            404: 'Attachment not found'
        }
    )
    def delete(self, request, vital_id, attachment_id):
        try:
            queryset = self.get_queryset()
            vital = queryset.get(pk=vital_id)
            attachment = VitalAttachment.objects.get(pk=attachment_id, vital=vital)
            attachment.delete()
            return Response(
                {'message': 'Attachment deleted successfully'},
                status=status.HTTP_200_OK
            )
        except Vital.DoesNotExist:
            return Response(
                {'error': 'Vital record not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except VitalAttachment.DoesNotExist:
            return Response(
                {'error': 'Attachment not found'},
                status=status.HTTP_404_NOT_FOUND
            )


# ============================================================================
# PATIENT VITAL VIEWS (Patient-level vitals, independent of pregnancy)
# ============================================================================

class PatientVitalsPagination(PageNumberPagination):
    """Custom pagination for patient vitals - 100 records per page."""
    page_size = 100
    page_size_query_param = 'page_size'
    max_page_size = 500


class PatientVitalQuerySetMixin:
    """Mixin to handle queryset logic for patient vitals based on user type."""

    def get_queryset(self):
        user = self.request.user

        # Patients see only their own patient vitals
        if user.user_type == 'patient':
            return PatientVital.objects.filter(
                patient=user
            ).select_related('patient', 'visit')

        # Doctors see all patient vitals (same pattern as VitalQuerySetMixin for pregnancy vitals)
        elif user.user_type == 'doctor':
            return PatientVital.objects.all().select_related('patient', 'visit')

        # Employees see patient vitals based on their clinic assignments
        elif user.user_type == 'employee':
            clinic_ids = Employee.objects.filter(staff=user).values_list('clinic_id', flat=True)
            return PatientVital.objects.filter(
                Q(visit__clinic_id__in=clinic_ids) |
                Q(patient__visits__clinic_id__in=clinic_ids)
            ).select_related('patient', 'visit').distinct()

        return PatientVital.objects.none()


class PatientVitalListAPIView(PatientVitalQuerySetMixin, generics.ListAPIView):
    """GET /api/vitals/patient-vitals/ - List patient vital records"""
    permission_classes = [IsAuthenticated]
    serializer_class = PatientVitalListSerializer
    pagination_class = PatientVitalsPagination
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['patient', 'visit']

    def get_queryset(self):
        queryset = super().get_queryset().prefetch_related('visit__attachments', 'attachments')

        # Handle patient=me filter
        patient_filter = self.request.query_params.get('patient')
        if patient_filter == 'me' and self.request.user.user_type == 'patient':
            queryset = queryset.filter(patient=self.request.user)

        return queryset

    @swagger_auto_schema(
        operation_id='getPatientVitals',
        operation_summary='List patient vital records',
        operation_description='''
Get a list of patient-level vital records (independent of pregnancy).

**Access Control:**
- Patients see only their own vitals
- Doctors/employees see vitals of patients who visited their clinics

**Filters:**
- `?patient=me` - (For patients) Get only your own vitals
- `?patient=<id>` - Filter by patient ID
- `?visit=<id>` - Filter by visit ID

**Pagination:**
- Default page size: 100 records
- Max page size: 500 records

**Response Fields:**
- `created_by` - User ID of who created this vital record
- `created_by_id` - Same as created_by
- `created_by_name` - Name of the user who created this vital record
- `note` - Patient's notes for the vital record
- `dr_note` - Doctor's notes for the vital record
- `files` - Array of file URLs attached to the vital
- `attachments` - Array of direct vital attachments (with presigned B2 URLs)
- `visit_attachments` - Array of attachments from the related visit
        ''',
        tags=['Patient Vitals'],
        manual_parameters=[
            openapi.Parameter('patient', openapi.IN_QUERY, description='Filter by patient ID (use "me" for own vitals)', type=openapi.TYPE_STRING),
            openapi.Parameter('visit', openapi.IN_QUERY, description='Filter by visit ID', type=openapi.TYPE_INTEGER),
            openapi.Parameter('page', openapi.IN_QUERY, description='Page number', type=openapi.TYPE_INTEGER),
            openapi.Parameter('page_size', openapi.IN_QUERY, description='Items per page (default: 100, max: 500)', type=openapi.TYPE_INTEGER),
        ]
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class PatientVitalDetailAPIView(PatientVitalQuerySetMixin, generics.RetrieveAPIView):
    """GET /api/vitals/patient-vitals/{id}/ - Get patient vital record details"""
    permission_classes = [IsAuthenticated]
    serializer_class = PatientVitalSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    @swagger_auto_schema(
        operation_id='getPatientVitalsById',
        operation_summary='Get patient vital record details',
        operation_description='''
Get detailed information about a specific patient vital record including attached files.

**Response includes:**
- `created_by` - User ID of who created this vital record
- `created_by_id` - Same as created_by
- `created_by_name` - Name of the user who created this vital record
        ''',
        tags=['Patient Vitals']
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class PatientVitalCreateAPIView(generics.CreateAPIView):
    """POST /api/vitals/patient-vitals/create/ - Create patient vital record"""
    permission_classes = [IsAuthenticated]
    serializer_class = PatientVitalCreateSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    @swagger_auto_schema(
        operation_id='postPatientVitals',
        operation_summary='Create a patient vital record',
        operation_description='''
Create a new patient-level vital record (independent of pregnancy).

**Required fields:**
- `patient` - Patient ID (User with user_type='patient')

**Optional fields:**
- `visit` - Link to a specific visit
- `systolic`, `diastolic` - Blood pressure readings
- `o2` - Oxygen saturation
- `puls` - Pulse rate
- `temp` - Temperature
- `weight` - Weight in kg
- `sugar_level` - Blood glucose level in mg/dL
- `reading_date` - Date/time of reading
- `mood` - Patient mood
- `note` - Patient note
- `dr_note` - Doctor note
- `uploaded_files` - File attachments (multipart/form-data)

**Auto-set fields:**
- `created_by` - Automatically set to the authenticated user who creates the record

**Response includes:**
- `created_by` - User ID of who created this vital record
- `created_by_id` - Same as created_by
- `created_by_name` - Name of the user who created this vital record
        ''',
        tags=['Patient Vitals'],
        request_body=PatientVitalCreateSerializer
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class PatientVitalUpdateAPIView(PatientVitalQuerySetMixin, generics.UpdateAPIView):
    """PUT/PATCH /api/vitals/patient-vitals/{id}/update/ - Update patient vital record"""
    permission_classes = [IsAuthenticated]
    serializer_class = PatientVitalUpdateSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    @swagger_auto_schema(
        operation_id='putPatientVitalsById',
        operation_summary='Update a patient vital record',
        operation_description='Update a patient vital record. New file uploads are appended to existing files.',
        tags=['Patient Vitals']
    )
    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_id='patchPatientVitalsById',
        operation_summary='Partially update a patient vital record',
        operation_description='Partially update a patient vital record.',
        tags=['Patient Vitals']
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)


class PatientVitalDeleteAPIView(PatientVitalQuerySetMixin, generics.DestroyAPIView):
    """DELETE /api/vitals/patient-vitals/{id}/delete/ - Delete patient vital record"""
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_id='deletePatientVitalsById',
        operation_summary='Delete a patient vital record',
        operation_description='Delete a patient vital record.',
        tags=['Patient Vitals']
    )
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)


# ============================================================================
# PATIENT VITAL ATTACHMENT VIEWS
# ============================================================================

class PatientVitalAttachmentUploadAPIView(PatientVitalQuerySetMixin, APIView):
    """POST /api/vitals/patient-vitals/{id}/attachments/ - Upload attachments to a patient vital record"""
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    @swagger_auto_schema(
        operation_id='postPatientVitalAttachments',
        operation_summary='Upload attachments to a patient vital record',
        operation_description='''
Upload one or more file attachments to a patient vital record.

**Request:**
- Use `multipart/form-data` encoding
- Field name: `attachments` (can send multiple files)
- Supported: Any file type (images, PDFs, documents, etc.)

**Example (curl):**
```bash
curl -X POST 'http://localhost:8000/api/vitals/patient-vitals/{id}/attachments/' \\
  -H 'Authorization: Bearer {token}' \\
  -F "attachments=@file1.pdf" \\
  -F "attachments=@file2.jpg"
```

**Response:**
Returns the list of uploaded attachments with presigned URLs.
        ''',
        tags=['Patient Vitals'],
        manual_parameters=[
            openapi.Parameter(
                'attachments',
                openapi.IN_FORM,
                description='Files to upload (can be multiple)',
                type=openapi.TYPE_FILE,
                required=True
            ),
        ],
        responses={
            200: PatientVitalAttachmentSerializer(many=True),
            404: 'Patient vital record not found'
        }
    )
    def post(self, request, pk):
        try:
            queryset = self.get_queryset()
            patient_vital = queryset.get(pk=pk)
        except PatientVital.DoesNotExist:
            return Response(
                {'error': 'Patient vital record not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        files = request.FILES.getlist('attachments')
        if not files:
            files = request.FILES.getlist('files')

        if not files:
            return Response(
                {'error': 'No files provided. Use field name "attachments" or "files".'},
                status=status.HTTP_400_BAD_REQUEST
            )

        uploaded_attachments = []
        errors = []

        for file_obj in files:
            try:
                timestamp = int(time.time())
                safe_name = os.path.basename(file_obj.name).replace(' ', '_')
                target_filename = f"patient_vital_{patient_vital.id}_att_{timestamp}_{safe_name}"

                uploaded = upload_file_to_b2(file_obj, target_filename)

                attachment = PatientVitalAttachment.objects.create(
                    patient_vital=patient_vital,
                    name=uploaded.file_name,
                    file_id=uploaded.id_,
                    file_type=file_obj.content_type or 'application/octet-stream'
                )
                uploaded_attachments.append(attachment)

            except Exception as e:
                errors.append({
                    'file': file_obj.name,
                    'error': str(e)
                })

        serializer = PatientVitalAttachmentSerializer(uploaded_attachments, many=True)
        response_data = {
            'attachments': serializer.data,
            'uploaded_count': len(uploaded_attachments)
        }

        if errors:
            response_data['errors'] = errors

        return Response(response_data, status=status.HTTP_200_OK)


class PatientVitalAttachmentDeleteAPIView(PatientVitalQuerySetMixin, APIView):
    """DELETE /api/vitals/patient-vitals/{patient_vital_id}/attachments/{attachment_id}/ - Delete an attachment"""
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_id='deletePatientVitalAttachment',
        operation_summary='Delete a patient vital attachment',
        operation_description='Delete a specific attachment from a patient vital record.',
        tags=['Patient Vitals'],
        responses={
            200: 'Attachment deleted successfully',
            404: 'Attachment not found'
        }
    )
    def delete(self, request, patient_vital_id, attachment_id):
        try:
            queryset = self.get_queryset()
            patient_vital = queryset.get(pk=patient_vital_id)
            attachment = PatientVitalAttachment.objects.get(pk=attachment_id, patient_vital=patient_vital)
            attachment.delete()
            return Response(
                {'message': 'Attachment deleted successfully'},
                status=status.HTTP_200_OK
            )
        except PatientVital.DoesNotExist:
            return Response(
                {'error': 'Patient vital record not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except PatientVitalAttachment.DoesNotExist:
            return Response(
                {'error': 'Attachment not found'},
                status=status.HTTP_404_NOT_FOUND
            )
