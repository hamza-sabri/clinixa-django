from rest_framework import generics, status, filters
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from datetime import datetime, timedelta
from django.utils import timezone

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
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['doctor', 'type', 'is_accepting_new_patients']
    search_fields = ['name', 'doctor__name', 'phone', 'location']
    
    @swagger_auto_schema(
        operation_id='getClinics',
        operation_summary='List clinics',
        operation_description='''
Get a list of all clinics with statistics. This endpoint is public and does not require authentication.

**Search:** Use `?search=` to search by clinic name, doctor name, phone, or location.
**Filters:**
- `?type=` - Filter by clinic type (e.g., "عيادة نسائية")
- `?is_accepting_new_patients=true` - Only show clinics accepting new patients
- `?doctor=` - Filter by doctor ID
        ''' + PAGINATION_DESCRIPTION,
        tags=['Clinics'],
        manual_parameters=[
            openapi.Parameter('search', openapi.IN_QUERY, description='Search by name, doctor, phone, or location', type=openapi.TYPE_STRING),
            openapi.Parameter('type', openapi.IN_QUERY, description='Filter by clinic type', type=openapi.TYPE_STRING),
            openapi.Parameter('is_accepting_new_patients', openapi.IN_QUERY, description='Filter by accepting new patients', type=openapi.TYPE_BOOLEAN),
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
        operation_description='Get detailed information about a specific clinic, including working hours, statistics, and appointment slot duration.',
        tags=['Clinics']
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class ClinicAvailableSlotsView(APIView):
    """GET /api/clinics/{id}/available-slots/ - Get available appointment slots"""
    permission_classes = [AllowAny]
    
    @swagger_auto_schema(
        operation_id='getClinicAvailableSlots',
        operation_summary='Get available appointment slots',
        operation_description='''
Get available appointment slots for a clinic on a specific date.

**Query Parameters:**
- `date` (required) - Date to check availability (YYYY-MM-DD format)

**Response:**
Returns a list of time slots with availability status based on the clinic's working hours and existing bookings.
        ''',
        tags=['Clinics'],
        manual_parameters=[
            openapi.Parameter('date', openapi.IN_QUERY, description='Date to check (YYYY-MM-DD)', type=openapi.TYPE_STRING, required=True),
        ],
        responses={
            200: openapi.Response(
                description='Available slots',
                examples={
                    'application/json': {
                        'clinic_id': 1,
                        'date': '2025-01-15',
                        'working_hours': {'open': '09:00', 'close': '17:00'},
                        'slot_duration': 30,
                        'available_slots': [
                            {'time': '09:00', 'available': True},
                            {'time': '09:30', 'available': True},
                            {'time': '10:00', 'available': False},
                        ],
                        'booked_count': 5,
                        'total_slots': 16
                    }
                }
            )
        }
    )
    def get(self, request, pk):
        # Get clinic
        try:
            clinic = Clinic.objects.get(pk=pk)
        except Clinic.DoesNotExist:
            return Response({'error': 'Clinic not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Get date parameter
        date_str = request.query_params.get('date')
        if not date_str:
            return Response({'error': 'Date parameter is required (YYYY-MM-DD)'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return Response({'error': 'Invalid date format. Use YYYY-MM-DD'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Get working hours for this day of week
        day_name = date.strftime('%A').lower()
        working_hours = clinic.working_hours.get(day_name) if clinic.working_hours else None
        
        # Clinic closed on this day
        if not working_hours:
            return Response({
                'clinic_id': clinic.id,
                'date': date_str,
                'working_hours': None,
                'message': 'Clinic is closed on this day',
                'slot_duration': clinic.slot_duration,
                'available_slots': [],
                'booked_count': 0,
                'total_slots': 0
            }, status=status.HTTP_200_OK)
        
        # Calculate slots
        try:
            open_time = datetime.strptime(working_hours['open'], '%H:%M')
            close_time = datetime.strptime(working_hours['close'], '%H:%M')
        except (KeyError, ValueError):
            return Response({
                'clinic_id': clinic.id,
                'date': date_str,
                'working_hours': working_hours,
                'message': 'Invalid working hours configuration',
                'slot_duration': clinic.slot_duration,
                'available_slots': [],
                'booked_count': 0,
                'total_slots': 0
            }, status=status.HTTP_200_OK)
        
        # Get existing bookings for this date
        from apps.visits.models import Visit
        booked_times = set()
        day_start = timezone.make_aware(datetime.combine(date, datetime.min.time()))
        day_end = day_start + timedelta(days=1)
        
        booked_visits = Visit.objects.filter(
            clinic=clinic,
            time__gte=day_start,
            time__lt=day_end,
            status__in=['جاري التأكيد', 'مؤكد']
        ).values_list('time', flat=True)
        
        for visit_time in booked_visits:
            booked_times.add(visit_time.strftime('%H:%M'))
        
        # Generate available slots
        slots = []
        current = open_time
        while current < close_time:
            time_str = current.strftime('%H:%M')
            slots.append({
                'time': time_str,
                'available': time_str not in booked_times
            })
            current += timedelta(minutes=clinic.slot_duration)
        
        booked_count = len(booked_times)
        total_slots = len(slots)
        
        return Response({
            'clinic_id': clinic.id,
            'date': date_str,
            'working_hours': working_hours,
            'slot_duration': clinic.slot_duration,
            'available_slots': slots,
            'booked_count': booked_count,
            'total_slots': total_slots
        }, status=status.HTTP_200_OK)


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
