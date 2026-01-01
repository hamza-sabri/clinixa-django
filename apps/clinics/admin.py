from django.contrib import admin
from .models import Clinic, Employee


@admin.register(Clinic)
class ClinicAdmin(admin.ModelAdmin):
    list_display = ('name', 'doctor', 'location', 'phone', 'type', 'created_at')
    list_filter = ('type', 'created_at')
    search_fields = ('name', 'location', 'doctor__email', 'doctor__name')
    raw_id_fields = ('doctor',)
    ordering = ('-created_at',)


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('staff', 'clinic', 'role', 'created_at')
    list_filter = ('role', 'clinic', 'created_at')
    search_fields = ('staff__email', 'staff__name', 'clinic__name')
    raw_id_fields = ('staff', 'clinic')
    ordering = ('-created_at',)




