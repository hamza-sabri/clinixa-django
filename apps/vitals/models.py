from django.db import models
from django.conf import settings


class Vital(models.Model):
    """Vital signs record for a patient."""
    
    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='vitals',
        verbose_name='patient'
    )
    systolic = models.IntegerField('systolic pressure', null=True, blank=True)
    diastolic = models.IntegerField('diastolic pressure', null=True, blank=True)
    o2 = models.IntegerField('oxygen saturation', null=True, blank=True)
    puls = models.IntegerField('pulse rate', null=True, blank=True)
    temp = models.FloatField('temperature', null=True, blank=True)
    weight = models.FloatField('weight (kg)', null=True, blank=True)
    reading_date = models.DateTimeField('reading date', null=True, blank=True)
    files = models.JSONField('attached files', default=list, blank=True)  # Array of Cloudinary URLs
    mood = models.CharField('mood', max_length=100, blank=True)
    note = models.TextField('patient note', blank=True)
    dr_note = models.TextField('doctor note', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'vital'
        verbose_name_plural = 'vitals'
        ordering = ['-reading_date', '-created_at']
    
    def __str__(self):
        return f"{self.patient.name or self.patient.email} - {self.reading_date or self.created_at}"


class BabyVital(models.Model):
    """Vital signs record for baby/pregnancy tracking."""
    
    parent = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='baby_vitals',
        verbose_name='parent'
    )
    puls = models.IntegerField('pulse rate', null=True, blank=True)
    systolic = models.IntegerField('systolic pressure', null=True, blank=True)
    diastolic = models.IntegerField('diastolic pressure', null=True, blank=True)
    o2 = models.FloatField('oxygen saturation', null=True, blank=True)
    weight = models.FloatField('weight (kg)', null=True, blank=True)
    age = models.CharField('age', max_length=50, blank=True)
    note = models.TextField('note', blank=True)
    reading_date = models.DateTimeField('reading date', null=True, blank=True)
    files = models.JSONField('attached files', default=list, blank=True)  # Array of Cloudinary URLs
    due_date = models.DateField('due date', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'baby vital'
        verbose_name_plural = 'baby vitals'
        ordering = ['-reading_date', '-created_at']
    
    def __str__(self):
        return f"{self.parent.name or self.parent.email} - Baby - {self.reading_date or self.created_at}"


