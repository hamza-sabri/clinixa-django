from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q
from django.utils import timezone
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from datetime import timedelta

from .models import Visit
from .serializers import (
    VisitSerializer,
    VisitCreateSerializer,
    VisitUpdateSerializer,
    VisitListSerializer,
)
from apps.clinics.models import Clinic, Employee
from apps.core.swagger import PAGINATION_PARAMETERS, PAGINATION_DESCRIPTION


# Minimum hours before appointment to allow cancellation/reschedule
CANCELLATION_WINDOW_HOURS = 2


class VisitQuerySetMixin:
    """Mixin to handle queryset logic for visits based on user type."""
    
    def get_queryset(self):
        user = self.request.user
        
        # Patients see only their own visits (via pregnancy)
        if user.user_type == 'patient':
            if hasattr(user, 'patient_profile'):
                return Visit.objects.filter(
                    Q(pregnancy__patient_profile=user.patient_profile) |
                    Q(patient=user)  # Legacy support
                ).select_related('clinic', 'pregnancy__patient_profile__user', 'patient')
            return Visit.objects.filter(patient=user).select_related('clinic', 'patient')
        
        # Doctors see visits to their clinics
        elif user.user_type == 'doctor':
            clinic_ids = Clinic.objects.filter(doctor=user).values_list('id', flat=True)
            return Visit.objects.filter(clinic_id__in=clinic_ids).select_related(
                'clinic', 'pregnancy__patient_profile__user', 'patient'
            )
        
        # Employees see visits to their assigned clinics
        elif user.user_type == 'employee':
            clinic_ids = Employee.objects.filter(staff=user).values_list('clinic_id', flat=True)
            return Visit.objects.filter(clinic_id__in=clinic_ids).select_related(
                'clinic', 'pregnancy__patient_profile__user', 'patient'
            )
        
        return Visit.objects.none()


class VisitListAPIView(VisitQuerySetMixin, generics.ListAPIView):
    """GET /api/visits/ - List visits"""
    permission_classes = [IsAuthenticated]
    serializer_class = VisitListSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['clinic', 'pregnancy', 'status']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
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
        operation_id='getVisits',
        operation_summary='List visits',
        operation_description='''
Get a list of visits.

**Access Control:**
- Patients see their own visits (via pregnancy)
- Doctors see visits to their clinics
- Employees see visits to their assigned clinics

**Filters:**
- `?patient=me` - (For patients) Get only your own visits
- `?pregnancy=` - Filter by pregnancy ID
- `?clinic=` - Filter by clinic ID
- `?status=` - Filter by status
        ''' + PAGINATION_DESCRIPTION,
        tags=['Visits'],
        manual_parameters=[
            openapi.Parameter('patient', openapi.IN_QUERY, description='Filter by patient (use "me" for own visits)', type=openapi.TYPE_STRING),
            openapi.Parameter('clinic', openapi.IN_QUERY, description='Filter by clinic ID', type=openapi.TYPE_INTEGER),
            openapi.Parameter('pregnancy', openapi.IN_QUERY, description='Filter by pregnancy ID', type=openapi.TYPE_INTEGER),
            openapi.Parameter('status', openapi.IN_QUERY, description='Filter by status', type=openapi.TYPE_STRING),
        ] + PAGINATION_PARAMETERS
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class VisitDetailAPIView(VisitQuerySetMixin, generics.RetrieveAPIView):
    """GET /api/visits/{id}/ - Get visit details"""
    permission_classes = [IsAuthenticated]
    serializer_class = VisitSerializer
    
    @swagger_auto_schema(
        operation_id='getVisitsById',
        operation_summary='Get visit details',
        operation_description='Get detailed information about a specific visit including pregnancy info and vitals status.',
        tags=['Visits']
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class VisitCreateAPIView(generics.CreateAPIView):
    """POST /api/visits/create/ - Create visit"""
    permission_classes = [IsAuthenticated]
    serializer_class = VisitCreateSerializer
    
    @swagger_auto_schema(
        operation_id='postVisits',
        operation_summary='Create a new visit',
        operation_description='''
Create a new visit for a pregnancy.

**Required fields:**
- `pregnancy` - Pregnancy ID
- `clinic` - Clinic ID
- `time` - Appointment time (ISO 8601 format)

**Optional fields:**
- `status` - Visit status (defaults to pending)
- `note` - Patient note
- `urgency` - Urgency level

**Nested vitals (optional):**
You can create vital records along with the visit:

```json
{
    "pregnancy": 1,
    "clinic": 1,
    "time": "2025-01-15T10:00:00Z",
    "vital": {
        "systolic": 120,
        "diastolic": 80,
        "weight": 68.5
    },
    "baby_vitals": [
        {"baby": 1, "puls": 145, "weight": 2.5}
    ]
}
```
        ''',
        tags=['Visits'],
        request_body=VisitCreateSerializer,
        responses={
            201: VisitSerializer
        }
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        visit = serializer.save()
        output_serializer = VisitSerializer(visit)
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)


class VisitUpdateAPIView(VisitQuerySetMixin, generics.UpdateAPIView):
    """PUT/PATCH /api/visits/{id}/update/ - Update visit"""
    permission_classes = [IsAuthenticated]
    serializer_class = VisitUpdateSerializer
    
    @swagger_auto_schema(
        operation_id='putVisitsById',
        operation_summary='Update a visit',
        operation_description='Update visit information including time, status, and notes.',
        tags=['Visits']
    )
    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_id='patchVisitsById',
        operation_summary='Partially update a visit',
        operation_description='Partially update visit information.',
        tags=['Visits']
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)


class VisitDeleteAPIView(VisitQuerySetMixin, generics.DestroyAPIView):
    """DELETE /api/visits/{id}/delete/ - Delete visit"""
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        operation_id='deleteVisitsById',
        operation_summary='Delete a visit',
        operation_description='Cancel/delete a visit.',
        tags=['Visits']
    )
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)


# ============================================================================
# PATIENT VISIT MANAGEMENT VIEWS
# ============================================================================

class VisitCancelView(APIView):
    """POST /api/visits/{id}/cancel/ - Cancel a visit (patient self-service)"""
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        operation_id='postVisitCancel',
        operation_summary='Cancel a visit',
        operation_description='''
Cancel an upcoming visit. Only the patient who owns the visit can cancel it.

**Business Rules:**
- Cannot cancel a visit less than 2 hours before the appointment time
- Cannot cancel already completed or cancelled visits
- Cancellation reason is optional but recommended

**Request Body:**
```json
{
    "reason": "لم أعد بحاجة للموعد"
}
```
        ''',
        tags=['Patient Visit Management'],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'reason': openapi.Schema(type=openapi.TYPE_STRING, description='Cancellation reason (optional)')
            }
        ),
        responses={
            200: openapi.Response(description='Visit cancelled successfully'),
            400: openapi.Response(description='Cannot cancel - too close to appointment or invalid status'),
            403: openapi.Response(description='Not the owner of this visit'),
            404: openapi.Response(description='Visit not found')
        }
    )
    def post(self, request, pk):
        user = request.user
        
        # Only patients can use this endpoint
        if user.user_type != 'patient':
            return Response(
                {'error': 'This endpoint is only for patients'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get the visit
        try:
            visit = Visit.objects.select_related('pregnancy__patient_profile__user', 'patient').get(pk=pk)
        except Visit.DoesNotExist:
            return Response({'error': 'Visit not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Check ownership
        is_owner = False
        if visit.pregnancy and hasattr(user, 'patient_profile'):
            is_owner = visit.pregnancy.patient_profile.user_id == user.id
        elif visit.patient_id == user.id:
            is_owner = True
        
        if not is_owner:
            return Response(
                {'error': 'You can only cancel your own visits'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check if already cancelled or completed
        if visit.status == 'ملغي':
            return Response(
                {'error': 'This visit is already cancelled'},
                status=status.HTTP_400_BAD_REQUEST
            )
        if visit.status == 'مكتمل':
            return Response(
                {'error': 'Cannot cancel a completed visit'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check cancellation window (2 hours before appointment)
        now = timezone.now()
        min_cancel_time = visit.time - timedelta(hours=CANCELLATION_WINDOW_HOURS)
        if now > min_cancel_time:
            return Response({
                'error': f'Cannot cancel less than {CANCELLATION_WINDOW_HOURS} hours before the appointment'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Cancel the visit
        reason = request.data.get('reason', '')
        visit.status = 'ملغي'
        visit.cancelled_at = now
        visit.cancelled_by = 'patient'
        visit.cancellation_reason = reason
        visit.save()
        
        return Response({
            'message': 'Visit cancelled successfully',
            'visit_id': visit.id,
            'cancelled_at': visit.cancelled_at.isoformat()
        }, status=status.HTTP_200_OK)


class VisitRescheduleView(APIView):
    """POST /api/visits/{id}/reschedule/ - Reschedule a visit (patient self-service)"""
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        operation_id='postVisitReschedule',
        operation_summary='Reschedule a visit',
        operation_description='''
Reschedule an upcoming visit to a new time. Only the patient who owns the visit can reschedule it.

**Business Rules:**
- Cannot reschedule less than 2 hours before the current appointment time
- Cannot reschedule completed or cancelled visits
- New time must be in the future
- New time should ideally be an available slot at the clinic

**Request Body:**
```json
{
    "new_time": "2025-01-20T14:00:00Z"
}
```
        ''',
        tags=['Patient Visit Management'],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['new_time'],
            properties={
                'new_time': openapi.Schema(type=openapi.TYPE_STRING, format='date-time', description='New appointment time')
            }
        ),
        responses={
            200: openapi.Response(description='Visit rescheduled successfully'),
            400: openapi.Response(description='Cannot reschedule - invalid time or status'),
            403: openapi.Response(description='Not the owner of this visit'),
            404: openapi.Response(description='Visit not found')
        }
    )
    def post(self, request, pk):
        user = request.user
        
        # Only patients can use this endpoint
        if user.user_type != 'patient':
            return Response(
                {'error': 'This endpoint is only for patients'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get the visit
        try:
            visit = Visit.objects.select_related('pregnancy__patient_profile__user', 'patient', 'clinic').get(pk=pk)
        except Visit.DoesNotExist:
            return Response({'error': 'Visit not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Check ownership
        is_owner = False
        if visit.pregnancy and hasattr(user, 'patient_profile'):
            is_owner = visit.pregnancy.patient_profile.user_id == user.id
        elif visit.patient_id == user.id:
            is_owner = True
        
        if not is_owner:
            return Response(
                {'error': 'You can only reschedule your own visits'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check if already cancelled or completed
        if visit.status == 'ملغي':
            return Response(
                {'error': 'Cannot reschedule a cancelled visit'},
                status=status.HTTP_400_BAD_REQUEST
            )
        if visit.status == 'مكتمل':
            return Response(
                {'error': 'Cannot reschedule a completed visit'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check reschedule window (2 hours before appointment)
        now = timezone.now()
        min_reschedule_time = visit.time - timedelta(hours=CANCELLATION_WINDOW_HOURS)
        if now > min_reschedule_time:
            return Response({
                'error': f'Cannot reschedule less than {CANCELLATION_WINDOW_HOURS} hours before the appointment'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate new time
        new_time_str = request.data.get('new_time')
        if not new_time_str:
            return Response({'error': 'new_time is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            from datetime import datetime
            # Parse the new time
            if isinstance(new_time_str, str):
                new_time = datetime.fromisoformat(new_time_str.replace('Z', '+00:00'))
                if timezone.is_naive(new_time):
                    new_time = timezone.make_aware(new_time)
            else:
                new_time = new_time_str
        except (ValueError, TypeError):
            return Response({'error': 'Invalid date format. Use ISO 8601 format.'}, status=status.HTTP_400_BAD_REQUEST)
        
        # New time must be in the future
        if new_time <= now:
            return Response({'error': 'New time must be in the future'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Store previous time and update
        visit.previous_time = visit.time
        visit.time = new_time
        visit.rescheduled_at = now
        visit.status = 'جاري التأكيد'  # Reset to pending confirmation
        visit.save()
        
        return Response({
            'message': 'Visit rescheduled successfully',
            'visit_id': visit.id,
            'previous_time': visit.previous_time.isoformat(),
            'new_time': visit.time.isoformat(),
            'rescheduled_at': visit.rescheduled_at.isoformat()
        }, status=status.HTTP_200_OK)

