from django.urls import path

from .views import (
    # Auth views
    SignupView,
    SignupWithClinicView,
    SigninView,
    ForgetPasswordView,
    CustomTokenRefreshView,
    # Patient OTP Auth views
    RequestOTPView,
    VerifyOTPView,
    # Patient self-service views
    PatientMeView,
    # Patient views
    PatientListAPIView,
    PatientDetailAPIView,
    PatientCreateAPIView,
    PatientUpdateAPIView,
    # Pregnancy views
    PatientPregnancyListAPIView,
    PatientPregnancyCreateAPIView,
    PregnancyDetailAPIView,
    PregnancyUpdateAPIView,
    PregnancyDeleteAPIView,
    # Baby views
    PregnancyBabyListAPIView,
    PregnancyBabyCreateAPIView,
    BabyDetailAPIView,
    BabyUpdateAPIView,
    BabyDeleteAPIView,
)

app_name = 'users'

urlpatterns = [
    # Auth endpoints
    path('signup/', SignupView.as_view(), name='signup'),
    path('signup-with-clinic/', SignupWithClinicView.as_view(), name='signup-with-clinic'),
    path('signin/', SigninView.as_view(), name='signin'),
    path('forget-password/', ForgetPasswordView.as_view(), name='forget-password'),
    path('token/refresh/', CustomTokenRefreshView.as_view(), name='token-refresh'),
    
    # Patient OTP authentication endpoints
    path('request-otp/', RequestOTPView.as_view(), name='patient-request-otp'),
    path('verify-otp/', VerifyOTPView.as_view(), name='patient-verify-otp'),
]

# Patient URLs - to be mounted at /api/patients/
patient_urlpatterns = [
    path('', PatientListAPIView.as_view(), name='patient-list'),
    path('create/', PatientCreateAPIView.as_view(), name='patient-create'),
    path('<int:pk>/', PatientDetailAPIView.as_view(), name='patient-detail'),
    path('<int:pk>/update/', PatientUpdateAPIView.as_view(), name='patient-update'),
    # Nested pregnancies
    path('<int:patient_id>/pregnancies/', PatientPregnancyListAPIView.as_view(), name='patient-pregnancy-list'),
    path('<int:patient_id>/pregnancies/create/', PatientPregnancyCreateAPIView.as_view(), name='patient-pregnancy-create'),
]

# Pregnancy URLs - to be mounted at /api/pregnancies/
pregnancy_urlpatterns = [
    path('<int:pk>/', PregnancyDetailAPIView.as_view(), name='pregnancy-detail'),
    path('<int:pk>/update/', PregnancyUpdateAPIView.as_view(), name='pregnancy-update'),
    path('<int:pk>/delete/', PregnancyDeleteAPIView.as_view(), name='pregnancy-delete'),
    # Nested babies
    path('<int:pregnancy_id>/babies/', PregnancyBabyListAPIView.as_view(), name='pregnancy-baby-list'),
    path('<int:pregnancy_id>/babies/create/', PregnancyBabyCreateAPIView.as_view(), name='pregnancy-baby-create'),
]

# Baby URLs - to be mounted at /api/babies/
baby_urlpatterns = [
    path('<int:pk>/', BabyDetailAPIView.as_view(), name='baby-detail'),
    path('<int:pk>/update/', BabyUpdateAPIView.as_view(), name='baby-update'),
    path('<int:pk>/delete/', BabyDeleteAPIView.as_view(), name='baby-delete'),
]



