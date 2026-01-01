from django.contrib import admin
from .models import Vital, BabyVital


@admin.register(Vital)
class VitalAdmin(admin.ModelAdmin):
    list_display = ('patient', 'systolic', 'diastolic', 'o2', 'puls', 'temp', 'weight', 'reading_date', 'mood')
    list_filter = ('mood', 'created_at', 'reading_date')
    search_fields = ('patient__email', 'patient__name', 'note', 'dr_note')
    raw_id_fields = ('patient',)
    ordering = ('-reading_date', '-created_at')
    date_hierarchy = 'reading_date'


@admin.register(BabyVital)
class BabyVitalAdmin(admin.ModelAdmin):
    list_display = ('parent', 'puls', 'systolic', 'diastolic', 'o2', 'weight', 'age', 'reading_date', 'due_date')
    list_filter = ('created_at', 'reading_date', 'due_date')
    search_fields = ('parent__email', 'parent__name', 'note')
    raw_id_fields = ('parent',)
    ordering = ('-reading_date', '-created_at')
    date_hierarchy = 'reading_date'




