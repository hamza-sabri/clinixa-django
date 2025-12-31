from django.urls import path

from .views import AudioProcessingAPIView

app_name = 'recordings'

urlpatterns = [
    path('process/', AudioProcessingAPIView.as_view(), name='audio-process'),
]

