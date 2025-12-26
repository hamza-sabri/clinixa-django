from django.urls import path

from .views import (
    MedListAPIView,
    MedDetailAPIView,
    MedCreateAPIView,
    MedUpdateAPIView,
    MedDeleteAPIView,
    PatientMedListAPIView,
    PatientMedDetailAPIView,
    PatientMedCreateAPIView,
    PatientMedUpdateAPIView,
    PatientMedDeleteAPIView,
)

app_name = 'medications'

urlpatterns = [
    # Medications
    path('meds/', MedListAPIView.as_view(), name='med-list'),
    path('meds/<int:pk>/', MedDetailAPIView.as_view(), name='med-detail'),
    path('meds/create/', MedCreateAPIView.as_view(), name='med-create'),
    path('meds/<int:pk>/update/', MedUpdateAPIView.as_view(), name='med-update'),
    path('meds/<int:pk>/delete/', MedDeleteAPIView.as_view(), name='med-delete'),
    
    # Patient Medications
    path('patient-meds/', PatientMedListAPIView.as_view(), name='patient-med-list'),
    path('patient-meds/<int:pk>/', PatientMedDetailAPIView.as_view(), name='patient-med-detail'),
    path('patient-meds/create/', PatientMedCreateAPIView.as_view(), name='patient-med-create'),
    path('patient-meds/<int:pk>/update/', PatientMedUpdateAPIView.as_view(), name='patient-med-update'),
    path('patient-meds/<int:pk>/delete/', PatientMedDeleteAPIView.as_view(), name='patient-med-delete'),
]
