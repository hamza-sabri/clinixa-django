from django.urls import path

from .views import (
    VitalListAPIView,
    VitalDetailAPIView,
    VitalCreateAPIView,
    VitalUpdateAPIView,
    VitalDeleteAPIView,
    BabyVitalListAPIView,
    BabyVitalDetailAPIView,
    BabyVitalCreateAPIView,
    BabyVitalUpdateAPIView,
    BabyVitalDeleteAPIView,
)

app_name = 'vitals'

urlpatterns = [
    # Vitals
    path('vitals/', VitalListAPIView.as_view(), name='vital-list'),
    path('vitals/<int:pk>/', VitalDetailAPIView.as_view(), name='vital-detail'),
    path('vitals/create/', VitalCreateAPIView.as_view(), name='vital-create'),
    path('vitals/<int:pk>/update/', VitalUpdateAPIView.as_view(), name='vital-update'),
    path('vitals/<int:pk>/delete/', VitalDeleteAPIView.as_view(), name='vital-delete'),
    
    # Baby Vitals
    path('baby-vitals/', BabyVitalListAPIView.as_view(), name='baby-vital-list'),
    path('baby-vitals/<int:pk>/', BabyVitalDetailAPIView.as_view(), name='baby-vital-detail'),
    path('baby-vitals/create/', BabyVitalCreateAPIView.as_view(), name='baby-vital-create'),
    path('baby-vitals/<int:pk>/update/', BabyVitalUpdateAPIView.as_view(), name='baby-vital-update'),
    path('baby-vitals/<int:pk>/delete/', BabyVitalDeleteAPIView.as_view(), name='baby-vital-delete'),
]
