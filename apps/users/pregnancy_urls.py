from django.urls import path

from .views import (
    PregnancyDetailAPIView,
    PregnancyUpdateAPIView,
    PregnancyDeleteAPIView,
    PregnancyBabyListAPIView,
    PregnancyBabyCreateAPIView,
)

app_name = 'pregnancies'

urlpatterns = [
    path('<int:pk>/', PregnancyDetailAPIView.as_view(), name='pregnancy-detail'),
    path('<int:pk>/update/', PregnancyUpdateAPIView.as_view(), name='pregnancy-update'),
    path('<int:pk>/delete/', PregnancyDeleteAPIView.as_view(), name='pregnancy-delete'),
    # Nested babies under pregnancy
    path('<int:pregnancy_id>/babies/', PregnancyBabyListAPIView.as_view(), name='pregnancy-baby-list'),
    path('<int:pregnancy_id>/babies/create/', PregnancyBabyCreateAPIView.as_view(), name='pregnancy-baby-create'),
]

