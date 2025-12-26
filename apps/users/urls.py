from django.urls import path

from .views import (
    SignupView,
    SignupWithClinicView,
    SigninView,
    ForgetPasswordView,
    CustomTokenRefreshView,
)

app_name = 'users'

urlpatterns = [
    path('signup/', SignupView.as_view(), name='signup'),
    path('signup-with-clinic/', SignupWithClinicView.as_view(), name='signup-with-clinic'),
    path('signin/', SigninView.as_view(), name='signin'),
    path('forget-password/', ForgetPasswordView.as_view(), name='forget-password'),
    path('token/refresh/', CustomTokenRefreshView.as_view(), name='token-refresh'),
]


