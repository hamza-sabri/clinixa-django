from django.db import models
from django.conf import settings


class Visit(models.Model):
    """Visit model - patient appointments at clinics."""
    
    class Status(models.TextChoices):
        PENDING = 'جاري التأكيد', 'جاري التأكيد'  # Pending confirmation
        CONFIRMED = 'مؤكد', 'مؤكد'  # Confirmed
        COMPLETED = 'مكتمل', 'مكتمل'  # Completed
        CANCELLED = 'ملغي', 'ملغي'  # Cancelled
    
    clinic = models.ForeignKey(
        'clinics.Clinic',
        on_delete=models.CASCADE,
        related_name='visits',
        verbose_name='clinic'
    )
    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='visits',
        verbose_name='patient'
    )
    time = models.DateTimeField('appointment time')
    status = models.CharField(
        'status',
        max_length=50,
        choices=Status.choices,
        default=Status.PENDING
    )
    note = models.TextField('patient note', blank=True)
    urgency = models.CharField('urgency level', max_length=50, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'visit'
        verbose_name_plural = 'visits'
        ordering = ['-time']
    
    def __str__(self):
        return f"{self.patient.name or self.patient.email} - {self.clinic.name} ({self.time.strftime('%Y-%m-%d %H:%M')})"


