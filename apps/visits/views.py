from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .models import Visit
from .serializers import (
    VisitSerializer,
    VisitCreateSerializer,
    VisitUpdateSerializer,
    VisitListSerializer,
)
from apps.clinics.models import Clinic, Employee


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
- `?pregnancy=` - Filter by pregnancy ID
- `?clinic=` - Filter by clinic ID
- `?status=` - Filter by status
        ''',
        tags=['Visits'],
        manual_parameters=[
            openapi.Parameter('clinic', openapi.IN_QUERY, description='Filter by clinic ID', type=openapi.TYPE_INTEGER),
            openapi.Parameter('pregnancy', openapi.IN_QUERY, description='Filter by pregnancy ID', type=openapi.TYPE_INTEGER),
            openapi.Parameter('status', openapi.IN_QUERY, description='Filter by status', type=openapi.TYPE_STRING),
        ]
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
