from django.urls import path

from .views import (
    PatientListAPIView,
    PatientDetailAPIView,
    PatientCreateAPIView,
    PatientUpdateAPIView,
    PatientPregnancyListAPIView,
    PatientPregnancyCreateAPIView,
    PatientPregnancyDetailAPIView,
    PatientPregnancyUpdateAPIView,
    PatientPregnancyDeleteAPIView,
    PatientMeView,
    PatientMePregnancyCreateView,
    PatientAttachmentListUploadAPIView,
    PatientAttachmentDeleteAPIView,
)

app_name = 'patients'

urlpatterns = [
    # Patient self-service endpoints
    path('me/', PatientMeView.as_view(), name='patient-me'),
    path('me/pregnancies/create/', PatientMePregnancyCreateView.as_view(), name='patient-me-pregnancy-create'),
    
    # Admin/staff patient management
    path('', PatientListAPIView.as_view(), name='patient-list'),
    path('create/', PatientCreateAPIView.as_view(), name='patient-create'),
    path('<int:pk>/', PatientDetailAPIView.as_view(), name='patient-detail'),
    path('<int:pk>/update/', PatientUpdateAPIView.as_view(), name='patient-update'),
    # Nested pregnancies under patient
    path('<int:patient_id>/pregnancies/', PatientPregnancyListAPIView.as_view(), name='patient-pregnancy-list'),
    path('<int:patient_id>/pregnancies/create/', PatientPregnancyCreateAPIView.as_view(), name='patient-pregnancy-create'),
    path('<int:patient_id>/pregnancies/<int:pregnancy_id>/', PatientPregnancyDetailAPIView.as_view(), name='patient-pregnancy-detail'),
    path('<int:patient_id>/pregnancies/<int:pregnancy_id>/update/', PatientPregnancyUpdateAPIView.as_view(), name='patient-pregnancy-update'),
    path('<int:patient_id>/pregnancies/<int:pregnancy_id>/delete/', PatientPregnancyDeleteAPIView.as_view(), name='patient-pregnancy-delete'),
    # Nested attachments under patient (for doctors/employees)
    path('<int:pk>/attachments/', PatientAttachmentListUploadAPIView.as_view(), name='patient-attachments'),
    path('<int:pk>/attachments/<int:attachment_id>/', PatientAttachmentDeleteAPIView.as_view(), name='patient-attachment-delete'),
]

