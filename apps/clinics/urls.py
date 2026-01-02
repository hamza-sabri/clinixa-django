from django.urls import path

from .views import (
    ClinicListAPIView,
    ClinicDetailAPIView,
    ClinicCreateAPIView,
    ClinicUpdateAPIView,
    ClinicDeleteAPIView,
    ClinicAvailableSlotsView,
)

app_name = 'clinics'

urlpatterns = [
    path('', ClinicListAPIView.as_view(), name='clinic-list'),
    path('<int:pk>/', ClinicDetailAPIView.as_view(), name='clinic-detail'),
    path('<int:pk>/available-slots/', ClinicAvailableSlotsView.as_view(), name='clinic-available-slots'),
    path('create/', ClinicCreateAPIView.as_view(), name='clinic-create'),
    path('<int:pk>/update/', ClinicUpdateAPIView.as_view(), name='clinic-update'),
    path('<int:pk>/delete/', ClinicDeleteAPIView.as_view(), name='clinic-delete'),
]
