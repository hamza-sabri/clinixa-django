from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import User, PatientProfile, Pregnancy, Baby, OTPVerification


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin configuration for custom User model."""
    
    list_display = ('email', 'name', 'phone', 'user_type', 'is_active', 'created_at')
    list_filter = ('user_type', 'is_active', 'is_staff', 'created_at')
    search_fields = ('email', 'name', 'phone')
    ordering = ('-created_at',)
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Personal info'), {'fields': ('name', 'phone', 'user_type')}),
        (_('Permissions'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'name', 'phone', 'user_type', 'password1', 'password2'),
        }),
    )


@admin.register(PatientProfile)
class PatientProfileAdmin(admin.ModelAdmin):
    """Admin configuration for PatientProfile model."""
    list_display = ('user', 'blood_type', 'created_at')
    search_fields = ('user__name', 'user__email', 'user__phone')
    list_filter = ('blood_type', 'created_at')


@admin.register(Pregnancy)
class PregnancyAdmin(admin.ModelAdmin):
    """Admin configuration for Pregnancy model."""
    list_display = ('patient_profile', 'status', 'due_date', 'is_high_risk', 'created_at')
    list_filter = ('status', 'is_high_risk', 'created_at')
    search_fields = ('patient_profile__user__name', 'patient_profile__user__email')


@admin.register(Baby)
class BabyAdmin(admin.ModelAdmin):
    """Admin configuration for Baby model."""
    list_display = ('name', 'pregnancy', 'gender', 'is_born', 'birth_date')
    list_filter = ('gender', 'is_born', 'created_at')
    search_fields = ('name', 'pregnancy__patient_profile__user__name')


@admin.register(OTPVerification)
class OTPVerificationAdmin(admin.ModelAdmin):
    """Admin configuration for OTPVerification model."""
    list_display = ('phone', 'otp_code', 'is_used', 'attempts', 'created_at', 'expires_at')
    list_filter = ('is_used', 'created_at')
    search_fields = ('phone',)
    readonly_fields = ('otp_code', 'created_at', 'expires_at')
    ordering = ('-created_at',)
