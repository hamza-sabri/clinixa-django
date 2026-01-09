"""
URL configuration for Clinixa project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

# Swagger/OpenAPI schema configuration
schema_view = get_schema_view(
    openapi.Info(
        title="Clinixa API",
        default_version='v1',
        description="""
## Clinixa API Documentation

A comprehensive API for clinic management system.

### Authentication
All endpoints (except auth) require JWT authentication. Include the token in the Authorization header:
```
Authorization: Bearer <your_access_token>
```

### User Types
- **Patient**: Can book visits, manage own vitals
- **Doctor**: Can manage clinics, employees, view patient data
- **Employee**: Can access assigned clinic data

### Token Lifetime
- Access Token: 24 hours
- Refresh Token: 7 days

### Pagination
All list endpoints support pagination with the following query parameters:
- `page` - Page number (default: 1)
- `page_size` - Number of items per page (default: 20, max: 100)

Paginated responses include:
```json
{
    "count": 100,
    "next": "http://api.clinixa.com/api/resource/?page=2",
    "previous": null,
    "page": 1,
    "page_size": 20,
    "total_pages": 5,
    "results": [...]
}
```
        """,
        terms_of_service="https://www.clinixa.com/terms/",
        contact=openapi.Contact(email="support@clinixa.com"),
        license=openapi.License(name="Proprietary"),
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
)

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),
    
    # API Documentation
    path('swagger<format>/', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    
    # API Endpoints - auth routes under /api/users/, resource routes at their own paths
    path('api/users/', include('apps.users.urls')),  # Authentication routes
    path('api/clinics/', include('apps.clinics.urls')),
    path('api/employees/', include('apps.clinics.employees_urls')),
    path('api/visits/', include('apps.visits.urls')),
    path('api/vitals/', include('apps.vitals.urls')),
    path('api/medications/', include('apps.medications.urls')),
    
    # New pregnancy-centric endpoints
    path('api/patients/', include('apps.users.patient_urls')),
    path('api/pregnancies/', include('apps.users.pregnancy_urls')),
    path('api/babies/', include('apps.users.baby_urls')),
    
    # Recordings (audio processing)
    path('api/recordings/', include('apps.recordings.urls')),
    
    # Locations (cities)
    path('api/locations/', include('apps.locations.urls')),
    
    # Health check endpoint
    path('health/', lambda request: __import__('django.http', fromlist=['JsonResponse']).JsonResponse({'status': 'healthy'}), name='health'),
    
    # Root endpoint
    path('', lambda request: __import__('django.http', fromlist=['JsonResponse']).JsonResponse({
        'message': 'Welcome to Clinixa API',
        'version': 'v1',
        'docs': '/swagger/',
    }), name='root'),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

