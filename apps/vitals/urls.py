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
]
