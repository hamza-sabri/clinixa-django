from django.urls import path

from .views import (
    BabyDetailAPIView,
    BabyUpdateAPIView,
    BabyDeleteAPIView,
)

app_name = 'babies'

urlpatterns = [
    path('<int:pk>/', BabyDetailAPIView.as_view(), name='baby-detail'),
    path('<int:pk>/update/', BabyUpdateAPIView.as_view(), name='baby-update'),
    path('<int:pk>/delete/', BabyDeleteAPIView.as_view(), name='baby-delete'),
]

