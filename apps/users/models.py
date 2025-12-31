from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class UserManager(BaseUserManager):
    """Custom user manager that uses email as the unique identifier."""
    
    def create_user(self, email, password=None, **extra_fields):
        """Create and save a regular user with the given email and password."""
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """Create and save a superuser with the given email and password."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('user_type', 'doctor')

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    """Custom user model that uses email for authentication instead of username."""
    
    class UserType(models.TextChoices):
        DOCTOR = 'doctor', 'Doctor'
        EMPLOYEE = 'employee', 'Employee'
        PATIENT = 'patient', 'Patient'
    
    # Remove username field, use email instead
    username = None
    email = models.EmailField('email address', unique=True)
    
    # Additional fields
    name = models.CharField('full name', max_length=255, blank=True)
    phone = models.CharField('phone number', max_length=20, blank=True)
    user_type = models.CharField(
        'user type',
        max_length=20,
        choices=UserType.choices,
        default=UserType.PATIENT
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    objects = UserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
    
    class Meta:
        verbose_name = 'user'
        verbose_name_plural = 'users'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name or self.email
    
    @property
    def is_doctor(self):
        return self.user_type == self.UserType.DOCTOR
    
    @property
    def is_employee(self):
        return self.user_type == self.UserType.EMPLOYEE
    
    @property
    def is_patient(self):
        return self.user_type == self.UserType.PATIENT


class PatientProfile(models.Model):
    """
    Extended profile for patient users.
    Contains medical information that doesn't change per pregnancy.
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='patient_profile',
        verbose_name='patient user'
    )
    blood_type = models.CharField('blood type', max_length=10, blank=True)  # A+, B-, AB+, O-, etc.
    allergies = models.TextField('allergies', blank=True)
    medical_history = models.TextField('medical history', blank=True)
    notes = models.TextField('notes', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'patient profile'
        verbose_name_plural = 'patient profiles'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Profile: {self.user.name or self.user.email}"


class Pregnancy(models.Model):
    """
    Pregnancy record for a patient.
    Central entity that links visits, vitals, and babies.
    """
    class Status(models.TextChoices):
        ONGOING = 'ongoing', 'Ongoing'
        DELIVERED = 'delivered', 'Delivered'
        MISCARRIAGE = 'miscarriage', 'Miscarriage'
        ECTOPIC = 'ectopic', 'Ectopic'
        STILLBIRTH = 'stillbirth', 'Stillbirth'
    
    patient_profile = models.ForeignKey(
        PatientProfile,
        on_delete=models.CASCADE,
        related_name='pregnancies',
        verbose_name='patient profile'
    )
    created_by_clinic = models.ForeignKey(
        'clinics.Clinic',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_pregnancies',
        verbose_name='created by clinic'
    )
    lmp = models.DateField('last menstrual period', null=True, blank=True)
    due_date = models.DateField('due date', null=True, blank=True)
    status = models.CharField(
        'status',
        max_length=20,
        choices=Status.choices,
        default=Status.ONGOING
    )
    is_high_risk = models.BooleanField('high risk pregnancy', default=False)
    notes = models.TextField('notes', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'pregnancy'
        verbose_name_plural = 'pregnancies'
        ordering = ['-created_at']
    
    def __str__(self):
        patient_name = self.patient_profile.user.name or self.patient_profile.user.email
        return f"{patient_name} - Pregnancy ({self.status})"
    
    @property
    def pregnancy_week(self):
        """Calculate current pregnancy week from LMP."""
        if self.lmp:
            from datetime import date
            days = (date.today() - self.lmp).days
            return max(0, days // 7)
        return None
    
    @property
    def trimester(self):
        """Calculate current trimester based on pregnancy week."""
        week = self.pregnancy_week
        if week is None:
            return None
        if week <= 12:
            return 1
        elif week <= 27:
            return 2
        return 3
    
    @property
    def patient(self):
        """Convenience property to access the patient user directly."""
        return self.patient_profile.user


class Baby(models.Model):
    """
    Baby record within a pregnancy.
    Supports multiple babies (twins, triplets, etc.).
    """
    pregnancy = models.ForeignKey(
        Pregnancy,
        on_delete=models.CASCADE,
        related_name='babies',
        verbose_name='pregnancy'
    )
    name = models.CharField('name', max_length=100, blank=True)
    gender = models.CharField('gender', max_length=20, blank=True)  # male/female/unknown
    birth_date = models.DateTimeField('birth date', null=True, blank=True)
    birth_weight = models.FloatField('birth weight (kg)', null=True, blank=True)
    birth_length = models.FloatField('birth length (cm)', null=True, blank=True)
    apgar_score = models.IntegerField('APGAR score', null=True, blank=True)
    is_born = models.BooleanField('is born', default=False)
    notes = models.TextField('notes', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'baby'
        verbose_name_plural = 'babies'
        ordering = ['-created_at']
    
    def __str__(self):
        if self.name:
            return f"{self.name} ({self.pregnancy})"
        return f"Baby - {self.pregnancy}"



