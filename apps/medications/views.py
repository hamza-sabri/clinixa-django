from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .models import Med, PatientMed
from .serializers import (
    MedSerializer,
    MedListSerializer,
    PatientMedSerializer,
    PatientMedCreateSerializer,
    PatientMedListSerializer,
)
from apps.clinics.models import Clinic, Employee
from apps.core.swagger import PAGINATION_PARAMETERS, PAGINATION_DESCRIPTION


# ============================================================================
# MEDICATION VIEWS
# ============================================================================

class MedListAPIView(generics.ListAPIView):
    """GET /api/meds/ - List medications"""
    permission_classes = [IsAuthenticated]
    serializer_class = MedListSerializer
    queryset = Med.objects.all().select_related('created_by')
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['created_by']
    
    @swagger_auto_schema(
        operation_id='getMeds',
        operation_summary='List medications',
        operation_description='Get a list of all medications in the system.' + PAGINATION_DESCRIPTION,
        tags=['Meds'],
        manual_parameters=[
            openapi.Parameter('created_by', openapi.IN_QUERY, description='Filter by creator ID', type=openapi.TYPE_INTEGER),
        ] + PAGINATION_PARAMETERS
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class MedDetailAPIView(generics.RetrieveAPIView):
    """GET /api/meds/{id}/ - Get medication details"""
    permission_classes = [IsAuthenticated]
    serializer_class = MedSerializer
    queryset = Med.objects.all().select_related('created_by')
    
    @swagger_auto_schema(
        operation_id='getMedsById',
        operation_summary='Get medication details',
        operation_description='Get detailed information about a specific medication.',
        tags=['Meds']
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class MedCreateAPIView(generics.CreateAPIView):
    """POST /api/meds/create/ - Create medication"""
    permission_classes = [IsAuthenticated]
    serializer_class = MedSerializer
    
    @swagger_auto_schema(
        operation_id='postMeds',
        operation_summary='Create a new medication',
        operation_description='Add a new medication to the system.',
        tags=['Meds'],
        request_body=MedSerializer
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class MedUpdateAPIView(generics.UpdateAPIView):
    """PUT/PATCH /api/meds/{id}/update/ - Update medication"""
    permission_classes = [IsAuthenticated]
    serializer_class = MedSerializer
    queryset = Med.objects.all()
    
    @swagger_auto_schema(
        operation_id='putMedsById',
        operation_summary='Update a medication',
        operation_description='Update medication information.',
        tags=['Meds']
    )
    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_id='patchMedsById',
        operation_summary='Partially update a medication',
        operation_description='Partially update medication information.',
        tags=['Meds']
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)


class MedDeleteAPIView(generics.DestroyAPIView):
    """DELETE /api/meds/{id}/delete/ - Delete medication"""
    permission_classes = [IsAuthenticated]
    queryset = Med.objects.all()
    
    @swagger_auto_schema(
        operation_id='deleteMedsById',
        operation_summary='Delete a medication',
        operation_description='Delete a medication from the system.',
        tags=['Meds']
    )
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)


# ============================================================================
# PATIENT MEDICATION VIEWS
# ============================================================================

class PatientMedQuerySetMixin:
    """Mixin to handle queryset logic for patient medications based on user type."""
    
    def get_queryset(self):
        user = self.request.user
        
        # Patients see only their own medication records
        if user.user_type == 'patient':
            return PatientMed.objects.filter(patient=user).select_related('patient', 'med', 'created_by')
        
        # Doctors see medication records of patients who visited their clinics
        elif user.user_type == 'doctor':
            from apps.visits.models import Visit
            clinic_ids = Clinic.objects.filter(doctor=user).values_list('id', flat=True)
            patient_ids = Visit.objects.filter(clinic_id__in=clinic_ids).values_list('patient_id', flat=True).distinct()
            return PatientMed.objects.filter(patient_id__in=patient_ids).select_related('patient', 'med', 'created_by')
        
        # Employees see medication records based on their clinic assignments
        elif user.user_type == 'employee':
            from apps.visits.models import Visit
            clinic_ids = Employee.objects.filter(staff=user).values_list('clinic_id', flat=True)
            patient_ids = Visit.objects.filter(clinic_id__in=clinic_ids).values_list('patient_id', flat=True).distinct()
            return PatientMed.objects.filter(patient_id__in=patient_ids).select_related('patient', 'med', 'created_by')
        
        return PatientMed.objects.none()


class PatientMedListAPIView(PatientMedQuerySetMixin, generics.ListAPIView):
    """GET /api/patient-meds/ - List patient medications"""
    permission_classes = [IsAuthenticated]
    serializer_class = PatientMedListSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['patient', 'med']
    
    @swagger_auto_schema(
        operation_id='getPatientMeds',
        operation_summary='List patient medications',
        operation_description='Get a list of patient medication records. Patients see their own records. Doctors/employees see records of their clinic patients.' + PAGINATION_DESCRIPTION,
        tags=['Patient Meds'],
        manual_parameters=[
            openapi.Parameter('patient', openapi.IN_QUERY, description='Filter by patient ID', type=openapi.TYPE_INTEGER),
            openapi.Parameter('med', openapi.IN_QUERY, description='Filter by medication ID', type=openapi.TYPE_INTEGER),
        ] + PAGINATION_PARAMETERS
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class PatientMedDetailAPIView(PatientMedQuerySetMixin, generics.RetrieveAPIView):
    """GET /api/patient-meds/{id}/ - Get patient medication details"""
    permission_classes = [IsAuthenticated]
    serializer_class = PatientMedSerializer
    
    @swagger_auto_schema(
        operation_id='getPatientMedsById',
        operation_summary='Get patient medication details',
        operation_description='Get detailed information about a specific patient medication record.',
        tags=['Patient Meds']
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class PatientMedCreateAPIView(generics.CreateAPIView):
    """POST /api/patient-meds/create/ - Create patient medication"""
    permission_classes = [IsAuthenticated]
    serializer_class = PatientMedCreateSerializer
    
    @swagger_auto_schema(
        operation_id='postPatientMeds',
        operation_summary='Create a patient medication record',
        operation_description='Add a medication to a patient record. If patient is not specified, the authenticated user is used.',
        tags=['Patient Meds'],
        request_body=PatientMedCreateSerializer
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        
        # Return full details
        output_serializer = PatientMedSerializer(instance, context={'request': request})
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)


class PatientMedUpdateAPIView(PatientMedQuerySetMixin, generics.UpdateAPIView):
    """PUT/PATCH /api/patient-meds/{id}/update/ - Update patient medication"""
    permission_classes = [IsAuthenticated]
    serializer_class = PatientMedSerializer
    
    @swagger_auto_schema(
        operation_id='putPatientMedsById',
        operation_summary='Update a patient medication record',
        operation_description='Update a patient medication record.',
        tags=['Patient Meds']
    )
    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_id='patchPatientMedsById',
        operation_summary='Partially update a patient medication record',
        operation_description='Partially update a patient medication record.',
        tags=['Patient Meds']
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)


class PatientMedDeleteAPIView(PatientMedQuerySetMixin, generics.DestroyAPIView):
    """DELETE /api/patient-meds/{id}/delete/ - Delete patient medication"""
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        operation_id='deletePatientMedsById',
        operation_summary='Delete a patient medication record',
        operation_description='Remove a medication from a patient record.',
        tags=['Patient Meds']
    )
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)
