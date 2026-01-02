from django.urls import path

from .views import (
    PatientListAPIView,
    PatientDetailAPIView,
    PatientCreateAPIView,
    PatientUpdateAPIView,
    PatientPregnancyListAPIView,
    PatientPregnancyCreateAPIView,
    PatientMeView,
)

app_name = 'patients'

urlpatterns = [
    # Patient self-service endpoint
    path('me/', PatientMeView.as_view(), name='patient-me'),
    
    # Admin/staff patient management
    path('', PatientListAPIView.as_view(), name='patient-list'),
    path('create/', PatientCreateAPIView.as_view(), name='patient-create'),
    path('<int:pk>/', PatientDetailAPIView.as_view(), name='patient-detail'),
    path('<int:pk>/update/', PatientUpdateAPIView.as_view(), name='patient-update'),
    # Nested pregnancies under patient
    path('<int:patient_id>/pregnancies/', PatientPregnancyListAPIView.as_view(), name='patient-pregnancy-list'),
    path('<int:patient_id>/pregnancies/create/', PatientPregnancyCreateAPIView.as_view(), name='patient-pregnancy-create'),
]

