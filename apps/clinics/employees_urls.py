from django.urls import path

from .views import (
    EmployeeListAPIView,
    EmployeeDetailAPIView,
    EmployeeCreateAPIView,
    EmployeeUpdateAPIView,
    EmployeeDeleteAPIView,
)

app_name = 'employees'

urlpatterns = [
    path('employees/', EmployeeListAPIView.as_view(), name='employee-list'),
    path('employees/<int:pk>/', EmployeeDetailAPIView.as_view(), name='employee-detail'),
    path('employees/create/', EmployeeCreateAPIView.as_view(), name='employee-create'),
    path('employees/<int:pk>/update/', EmployeeUpdateAPIView.as_view(), name='employee-update'),
    path('employees/<int:pk>/delete/', EmployeeDeleteAPIView.as_view(), name='employee-delete'),
]
