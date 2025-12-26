from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .models import Vital, BabyVital
from .serializers import (
    VitalSerializer,
    VitalCreateSerializer,
    VitalUpdateSerializer,
    VitalListSerializer,
    BabyVitalSerializer,
    BabyVitalCreateSerializer,
    BabyVitalUpdateSerializer,
    BabyVitalListSerializer,
)
from apps.clinics.models import Clinic, Employee


# ============================================================================
# VITAL VIEWS
# ============================================================================

class VitalQuerySetMixin:
    """Mixin to handle queryset logic for vitals based on user type."""
    
    def get_queryset(self):
        user = self.request.user
        
        # Patients see only their own vitals
        if user.user_type == 'patient':
            return Vital.objects.filter(patient=user).select_related('patient')
        
        # Doctors see vitals of patients who visited their clinics
        elif user.user_type == 'doctor':
            from apps.visits.models import Visit
            clinic_ids = Clinic.objects.filter(doctor=user).values_list('id', flat=True)
            patient_ids = Visit.objects.filter(clinic_id__in=clinic_ids).values_list('patient_id', flat=True).distinct()
            return Vital.objects.filter(patient_id__in=patient_ids).select_related('patient')
        
        # Employees see vitals based on their clinic assignments
        elif user.user_type == 'employee':
            from apps.visits.models import Visit
            clinic_ids = Employee.objects.filter(staff=user).values_list('clinic_id', flat=True)
            patient_ids = Visit.objects.filter(clinic_id__in=clinic_ids).values_list('patient_id', flat=True).distinct()
            return Vital.objects.filter(patient_id__in=patient_ids).select_related('patient')
        
        return Vital.objects.none()


class VitalListAPIView(VitalQuerySetMixin, generics.ListAPIView):
    """GET /api/vitals/ - List vital records"""
    permission_classes = [IsAuthenticated]
    serializer_class = VitalListSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['patient']
    
    @swagger_auto_schema(
        operation_id='getVitals',
        operation_summary='List vital records',
        operation_description='Get a list of vital records. Patients see their own vitals. Doctors/employees see vitals of patients who visited their clinics.',
        tags=['Vitals'],
        manual_parameters=[
            openapi.Parameter('patient', openapi.IN_QUERY, description='Filter by patient ID', type=openapi.TYPE_INTEGER),
        ]
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
        operation_description='Create a new vital record. Supports file uploads via multipart/form-data. The authenticated user becomes the patient.',
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
        
        # Parents see only their own baby vitals
        if user.user_type == 'patient':
            return BabyVital.objects.filter(parent=user).select_related('parent')
        
        # Doctors see baby vitals of patients who visited their clinics
        elif user.user_type == 'doctor':
            from apps.visits.models import Visit
            clinic_ids = Clinic.objects.filter(doctor=user).values_list('id', flat=True)
            patient_ids = Visit.objects.filter(clinic_id__in=clinic_ids).values_list('patient_id', flat=True).distinct()
            return BabyVital.objects.filter(parent_id__in=patient_ids).select_related('parent')
        
        # Employees see baby vitals based on their clinic assignments
        elif user.user_type == 'employee':
            from apps.visits.models import Visit
            clinic_ids = Employee.objects.filter(staff=user).values_list('clinic_id', flat=True)
            patient_ids = Visit.objects.filter(clinic_id__in=clinic_ids).values_list('patient_id', flat=True).distinct()
            return BabyVital.objects.filter(parent_id__in=patient_ids).select_related('parent')
        
        return BabyVital.objects.none()


class BabyVitalListAPIView(BabyVitalQuerySetMixin, generics.ListAPIView):
    """GET /api/baby-vitals/ - List baby vital records"""
    permission_classes = [IsAuthenticated]
    serializer_class = BabyVitalListSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['parent']
    
    @swagger_auto_schema(
        operation_id='getBabyVitals',
        operation_summary='List baby vital records',
        operation_description='Get a list of baby vital records. Parents see their own records. Doctors/employees see records of patients who visited their clinics.',
        tags=['Baby Vitals'],
        manual_parameters=[
            openapi.Parameter('parent', openapi.IN_QUERY, description='Filter by parent ID', type=openapi.TYPE_INTEGER),
        ]
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


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
        operation_description='Create a new baby vital record. Supports file uploads via multipart/form-data.',
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
