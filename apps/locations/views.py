from rest_framework import generics, filters
from rest_framework.permissions import AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .models import City
from .serializers import CitySerializer


class CityListAPIView(generics.ListAPIView):
    """
    List all cities.
    
    This endpoint is public and returns all available cities.
    Used for populating city dropdowns in clinic and user registration forms.
    """
    permission_classes = [AllowAny]
    queryset = City.objects.all()
    serializer_class = CitySerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['name']
    search_fields = ['name']
    ordering_fields = ['name', 'id']
    ordering = ['name']
    
    @swagger_auto_schema(
        operation_id='getCities',
        operation_summary='List all cities',
        operation_description='''
Get a list of all available cities.

This endpoint is public and does not require authentication.
Used for populating city selection dropdowns in clinic and user forms.

**Search:** Use `?search=` to search by city name
**Ordering:** Use `?ordering=name` or `?ordering=-name` to sort
        ''',
        tags=['Locations'],
        manual_parameters=[
            openapi.Parameter(
                'search',
                openapi.IN_QUERY,
                description='Search by city name',
                type=openapi.TYPE_STRING
            ),
            openapi.Parameter(
                'ordering',
                openapi.IN_QUERY,
                description='Order by field (name, id, -name, -id)',
                type=openapi.TYPE_STRING
            ),
        ],
        responses={
            200: openapi.Response(
                description='List of cities',
                schema=openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                            'name': openapi.Schema(type=openapi.TYPE_STRING),
                        }
                    )
                )
            )
        }
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
