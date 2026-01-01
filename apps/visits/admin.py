from django.contrib import admin
from .models import Visit


@admin.register(Visit)
class VisitAdmin(admin.ModelAdmin):
    list_display = ('patient', 'clinic', 'time', 'status', 'urgency', 'created_at')
    list_filter = ('status', 'urgency', 'clinic', 'created_at')
    search_fields = ('patient__email', 'patient__name', 'clinic__name', 'note')
    raw_id_fields = ('patient', 'clinic')
    ordering = ('-time',)
    date_hierarchy = 'time'




