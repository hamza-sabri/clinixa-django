from django.db import models
from django.conf import settings


class Visit(models.Model):
    """
    Visit model - patient appointments at clinics.
    Now linked to Pregnancy instead of directly to patient.
    """
    
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
    # NEW: Link to pregnancy (will be required after data migration)
    pregnancy = models.ForeignKey(
        'users.Pregnancy',
        on_delete=models.CASCADE,
        related_name='visits',
        verbose_name='pregnancy',
        null=True,  # Temporary: nullable for migration
        blank=True
    )
    # DEPRECATED: Will be removed after data migration
    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='visits',
        verbose_name='patient (deprecated)',
        null=True,  # Make nullable for transition
        blank=True
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
    
    # Cancellation tracking fields
    cancelled_at = models.DateTimeField('cancelled at', null=True, blank=True)
    cancelled_by = models.CharField(
        'cancelled by',
        max_length=20,
        blank=True,
        help_text='Who cancelled: patient or clinic'
    )
    cancellation_reason = models.TextField('cancellation reason', blank=True)
    
    # Reschedule tracking fields
    rescheduled_at = models.DateTimeField('rescheduled at', null=True, blank=True)
    previous_time = models.DateTimeField('previous appointment time', null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'visit'
        verbose_name_plural = 'visits'
        ordering = ['-time']
    
    def __str__(self):
        if self.pregnancy:
            patient = self.pregnancy.patient
            return f"{patient.name or patient.email} - {self.clinic.name} ({self.time.strftime('%Y-%m-%d %H:%M')})"
        elif self.patient:
            return f"{self.patient.name or self.patient.email} - {self.clinic.name} ({self.time.strftime('%Y-%m-%d %H:%M')})"
        return f"Visit at {self.clinic.name} ({self.time.strftime('%Y-%m-%d %H:%M')})"
    
    @property
    def patient_user(self):
        """Get the patient user from pregnancy or legacy patient field."""
        if self.pregnancy:
            return self.pregnancy.patient
        return self.patient



