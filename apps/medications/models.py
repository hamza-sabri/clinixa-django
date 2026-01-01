from django.db import models
from django.conf import settings


class Med(models.Model):
    """Medication model - stores medication information."""
    
    name = models.CharField('medication name', max_length=255)
    note = models.TextField('notes', blank=True)
    avg_price = models.FloatField('average price', null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_meds',
        verbose_name='created by'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'medication'
        verbose_name_plural = 'medications'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class PatientMed(models.Model):
    """Patient medication record - links patients to medications they take."""
    
    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='medications',
        verbose_name='patient'
    )
    med = models.ForeignKey(
        Med,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='patient_records',
        verbose_name='medication'
    )
    med_name = models.CharField(
        'medication name',
        max_length=255,
        blank=True,
        help_text='Stored for reference even if med is deleted'
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='prescribed_meds',
        verbose_name='prescribed by'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'patient medication'
        verbose_name_plural = 'patient medications'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.patient.name or self.patient.email} - {self.med_name or (self.med.name if self.med else 'Unknown')}"
    
    def save(self, *args, **kwargs):
        # Auto-populate med_name from med if not provided
        if self.med and not self.med_name:
            self.med_name = self.med.name
        super().save(*args, **kwargs)




