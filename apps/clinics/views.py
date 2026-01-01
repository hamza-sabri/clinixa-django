from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .models import Clinic, Employee
from .serializers import (
    ClinicSerializer,
    ClinicListSerializer,
    ClinicDetailSerializer,
    EmployeeListSerializer,
    EmployeeCreateSerializer,
    EmployeeUpdateSerializer,
)
from .permissions import IsDoctor, IsClinicOwner
from apps.core.swagger import PAGINATION_PARAMETERS, PAGINATION_DESCRIPTION


# ============================================================================
# CLINIC VIEWS
# ============================================================================

class ClinicListAPIView(generics.ListAPIView):
    """GET /api/clinics/ - List all clinics with statistics"""
    permission_classes = [AllowAny]
    serializer_class = ClinicListSerializer
    queryset = Clinic.objects.all()
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['doctor']
    
    @swagger_auto_schema(
        operation_id='getClinics',
        operation_summary='List clinics',
        operation_description='Get a list of all clinics with statistics. This endpoint is public and does not require authentication.' + PAGINATION_DESCRIPTION,
        tags=['Clinics'],
        manual_parameters=[
            openapi.Parameter('doctor', openapi.IN_QUERY, description='Filter by doctor ID', type=openapi.TYPE_INTEGER),
        ] + PAGINATION_PARAMETERS
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class ClinicDetailAPIView(generics.RetrieveAPIView):
    """GET /api/clinics/{id}/ - Get single clinic with statistics"""
    permission_classes = [AllowAny]
    serializer_class = ClinicDetailSerializer
    queryset = Clinic.objects.all()
    
    @swagger_auto_schema(
        operation_id='getClinicsById',
        operation_summary='Get clinic details',
        operation_description='Get detailed information about a specific clinic, including statistics (visits per status, distinct patients count, employees count).',
        tags=['Clinics']
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class ClinicCreateAPIView(generics.CreateAPIView):
    """POST /api/clinics/create/ - Create clinic"""
    permission_classes = [IsAuthenticated, IsDoctor]
    serializer_class = ClinicSerializer
    
    def perform_create(self, serializer):
        serializer.save(doctor=self.request.user)
    
    @swagger_auto_schema(
        operation_id='postClinics',
        operation_summary='Create a new clinic',
        operation_description='Create a new clinic. Only doctors can create clinics. The authenticated doctor becomes the owner.',
        tags=['Clinics']
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class ClinicUpdateAPIView(generics.UpdateAPIView):
    """PUT/PATCH /api/clinics/{id}/update/ - Update clinic"""
    permission_classes = [IsAuthenticated, IsClinicOwner]
    serializer_class = ClinicSerializer
    queryset = Clinic.objects.all()
    
    @swagger_auto_schema(
        operation_id='putClinicsById',
        operation_summary='Update a clinic',
        operation_description='Update clinic information. Only the clinic owner can update.',
        tags=['Clinics']
    )
    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_id='patchClinicsById',
        operation_summary='Partially update a clinic',
        operation_description='Partially update clinic information. Only the clinic owner can update.',
        tags=['Clinics']
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)


class ClinicDeleteAPIView(generics.DestroyAPIView):
    """DELETE /api/clinics/{id}/delete/ - Delete clinic"""
    permission_classes = [IsAuthenticated, IsClinicOwner]
    queryset = Clinic.objects.all()
    
    @swagger_auto_schema(
        operation_id='deleteClinicsById',
        operation_summary='Delete a clinic',
        operation_description='Delete a clinic. Only the clinic owner can delete.',
        tags=['Clinics']
    )
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)


# ============================================================================
# EMPLOYEE VIEWS
# ============================================================================

class EmployeeListAPIView(generics.ListAPIView):
    """GET /api/employees/ - List employees"""
    permission_classes = [IsAuthenticated, IsDoctor]
    serializer_class = EmployeeListSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['clinic']
    
    def get_queryset(self):
        user = self.request.user
        # Doctors see employees from their clinics only
        clinic_ids = Clinic.objects.filter(doctor=user).values_list('id', flat=True)
        return Employee.objects.filter(clinic_id__in=clinic_ids).select_related('staff', 'clinic')
    
    @swagger_auto_schema(
        operation_id='getEmployees',
        operation_summary='List employees',
        operation_description='Get a list of employees in your clinics. Only doctors can access this endpoint.' + PAGINATION_DESCRIPTION,
        tags=['Employees'],
        manual_parameters=[
            openapi.Parameter('clinic', openapi.IN_QUERY, description='Filter by clinic ID', type=openapi.TYPE_INTEGER),
        ] + PAGINATION_PARAMETERS
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class EmployeeDetailAPIView(generics.RetrieveAPIView):
    """GET /api/employees/{id}/ - Get employee details"""
    permission_classes = [IsAuthenticated, IsDoctor]
    serializer_class = EmployeeListSerializer
    
    def get_queryset(self):
        user = self.request.user
        clinic_ids = Clinic.objects.filter(doctor=user).values_list('id', flat=True)
        return Employee.objects.filter(clinic_id__in=clinic_ids).select_related('staff', 'clinic')
    
    @swagger_auto_schema(
        operation_id='getEmployeesById',
        operation_summary='Get employee details',
        operation_description='Get detailed information about a specific employee.',
        tags=['Employees']
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class EmployeeCreateAPIView(generics.CreateAPIView):
    """POST /api/employees/create/ - Create employee"""
    permission_classes = [IsAuthenticated, IsDoctor]
    serializer_class = EmployeeCreateSerializer
    
    @swagger_auto_schema(
        operation_id='postEmployees',
        operation_summary='Create a new employee',
        operation_description='Add a new employee to your clinic. Creates a user account with the provided credentials and links them to the clinic with the specified role.',
        tags=['Employees'],
        request_body=EmployeeCreateSerializer,
        responses={
            201: EmployeeListSerializer
        }
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        employee = serializer.save()
        
        # Return the created employee with full details
        output_serializer = EmployeeListSerializer(employee)
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)


class EmployeeUpdateAPIView(generics.UpdateAPIView):
    """PUT/PATCH /api/employees/{id}/update/ - Update employee"""
    permission_classes = [IsAuthenticated, IsDoctor]
    serializer_class = EmployeeUpdateSerializer
    
    def get_queryset(self):
        user = self.request.user
        clinic_ids = Clinic.objects.filter(doctor=user).values_list('id', flat=True)
        return Employee.objects.filter(clinic_id__in=clinic_ids)
    
    @swagger_auto_schema(
        operation_id='putEmployeesById',
        operation_summary='Update an employee',
        operation_description='Update employee role or clinic assignment.',
        tags=['Employees']
    )
    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_id='patchEmployeesById',
        operation_summary='Partially update an employee',
        operation_description='Partially update employee role or clinic assignment.',
        tags=['Employees']
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)


class EmployeeDeleteAPIView(generics.DestroyAPIView):
    """DELETE /api/employees/{id}/delete/ - Delete employee"""
    permission_classes = [IsAuthenticated, IsDoctor]
    
    def get_queryset(self):
        user = self.request.user
        clinic_ids = Clinic.objects.filter(doctor=user).values_list('id', flat=True)
        return Employee.objects.filter(clinic_id__in=clinic_ids)
    
    @swagger_auto_schema(
        operation_id='deleteEmployeesById',
        operation_summary='Delete an employee',
        operation_description='Remove an employee from your clinic. This only removes the employment record, not the user account.',
        tags=['Employees']
    )
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)
