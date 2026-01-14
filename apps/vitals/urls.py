from django.urls import path

from .views import (
    VitalListAPIView,
    VitalDetailAPIView,
    VitalCreateAPIView,
    VitalUpdateAPIView,
    VitalDeleteAPIView,
    VitalAttachmentUploadAPIView,
    VitalAttachmentDeleteAPIView,
    BabyVitalListAPIView,
    BabyVitalDetailAPIView,
    BabyVitalCreateAPIView,
    BabyVitalUpdateAPIView,
    BabyVitalDeleteAPIView,
    PatientVitalListAPIView,
    PatientVitalDetailAPIView,
    PatientVitalCreateAPIView,
    PatientVitalUpdateAPIView,
    PatientVitalDeleteAPIView,
    PatientVitalAttachmentUploadAPIView,
    PatientVitalAttachmentDeleteAPIView,
)

app_name = 'vitals'

urlpatterns = [
    # Vitals
    path('', VitalListAPIView.as_view(), name='vital-list'),
    path('<int:pk>/', VitalDetailAPIView.as_view(), name='vital-detail'),
    path('create/', VitalCreateAPIView.as_view(), name='vital-create'),
    path('<int:pk>/update/', VitalUpdateAPIView.as_view(), name='vital-update'),
    path('<int:pk>/delete/', VitalDeleteAPIView.as_view(), name='vital-delete'),
    
    # Vital Attachments
    path('<int:pk>/attachments/', VitalAttachmentUploadAPIView.as_view(), name='vital-attachment-upload'),
    path('<int:vital_id>/attachments/<int:attachment_id>/', VitalAttachmentDeleteAPIView.as_view(), name='vital-attachment-delete'),
    
    # Baby Vitals
    path('baby-vitals/', BabyVitalListAPIView.as_view(), name='baby-vital-list'),
    path('baby-vitals/<int:pk>/', BabyVitalDetailAPIView.as_view(), name='baby-vital-detail'),
    path('baby-vitals/create/', BabyVitalCreateAPIView.as_view(), name='baby-vital-create'),
    path('baby-vitals/<int:pk>/update/', BabyVitalUpdateAPIView.as_view(), name='baby-vital-update'),
    path('baby-vitals/<int:pk>/delete/', BabyVitalDeleteAPIView.as_view(), name='baby-vital-delete'),

    # Patient Vitals (patient-level vitals, independent of pregnancy)
    path('patient-vitals/', PatientVitalListAPIView.as_view(), name='patient-vital-list'),
    path('patient-vitals/<int:pk>/', PatientVitalDetailAPIView.as_view(), name='patient-vital-detail'),
    path('patient-vitals/create/', PatientVitalCreateAPIView.as_view(), name='patient-vital-create'),
    path('patient-vitals/<int:pk>/update/', PatientVitalUpdateAPIView.as_view(), name='patient-vital-update'),
    path('patient-vitals/<int:pk>/delete/', PatientVitalDeleteAPIView.as_view(), name='patient-vital-delete'),

    # Patient Vital Attachments
    path('patient-vitals/<int:pk>/attachments/', PatientVitalAttachmentUploadAPIView.as_view(), name='patient-vital-attachment-upload'),
    path('patient-vitals/<int:patient_vital_id>/attachments/<int:attachment_id>/', PatientVitalAttachmentDeleteAPIView.as_view(), name='patient-vital-attachment-delete'),
]
