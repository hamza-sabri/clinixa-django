from django.db import models
from django.conf import settings


class Clinic(models.Model):
    """Clinic model - owned by a doctor."""
    
    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='clinics',
        verbose_name='doctor/owner'
    )
    name = models.CharField('clinic name', max_length=255)
    location = models.CharField('location', max_length=500)
    phone = models.CharField('phone number', max_length=20)
    type = models.CharField('clinic type', max_length=100, default='عيادة اطفال')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'clinic'
        verbose_name_plural = 'clinics'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} - {self.doctor.name or self.doctor.email}"


class Employee(models.Model):
    """Employee model - links staff users to clinics with roles."""
    
    staff = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='employments',
        verbose_name='staff member'
    )
    clinic = models.ForeignKey(
        Clinic,
        on_delete=models.CASCADE,
        related_name='employees',
        verbose_name='clinic'
    )
    role = models.CharField('role', max_length=100, default='staff')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'employee'
        verbose_name_plural = 'employees'
        ordering = ['-created_at']
        unique_together = ['staff', 'clinic']  # Prevent duplicate assignments
    
    def __str__(self):
        return f"{self.staff.name or self.staff.email} - {self.role} at {self.clinic.name}"


