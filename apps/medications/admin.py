from django.contrib import admin
from .models import Med, PatientMed


@admin.register(Med)
class MedAdmin(admin.ModelAdmin):
    list_display = ('name', 'avg_price', 'created_by', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('name', 'note', 'created_by__email', 'created_by__name')
    raw_id_fields = ('created_by',)
    ordering = ('name',)


@admin.register(PatientMed)
class PatientMedAdmin(admin.ModelAdmin):
    list_display = ('patient', 'med', 'med_name', 'created_by', 'created_at')
    list_filter = ('created_at', 'med')
    search_fields = ('patient__email', 'patient__name', 'med__name', 'med_name')
    raw_id_fields = ('patient', 'med', 'created_by')
    ordering = ('-created_at',)


