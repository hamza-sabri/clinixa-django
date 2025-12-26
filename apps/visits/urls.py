from django.urls import path

from .views import (
    VisitListAPIView,
    VisitDetailAPIView,
    VisitCreateAPIView,
    VisitUpdateAPIView,
    VisitDeleteAPIView,
)

app_name = 'visits'

urlpatterns = [
    path('visits/', VisitListAPIView.as_view(), name='visit-list'),
    path('visits/<int:pk>/', VisitDetailAPIView.as_view(), name='visit-detail'),
    path('visits/create/', VisitCreateAPIView.as_view(), name='visit-create'),
    path('visits/<int:pk>/update/', VisitUpdateAPIView.as_view(), name='visit-update'),
    path('visits/<int:pk>/delete/', VisitDeleteAPIView.as_view(), name='visit-delete'),
]
