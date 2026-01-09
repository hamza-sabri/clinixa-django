from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class UserManager(BaseUserManager):
    """Custom user manager that supports email or phone as unique identifier."""
    
    def create_user(self, email=None, password=None, **extra_fields):
        """Create and save a regular user with the given email and password."""
        if email:
            email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user
    
    def create_user_with_phone(self, phone, name='', **extra_fields):
        """Create and save a patient user with phone number only.
        
        Generates a placeholder email based on phone number.
        """
        if not phone:
            raise ValueError('The Phone field must be set')
        
        # Generate placeholder email from phone number
        placeholder_email = f"{phone.replace('+', '')}@clinixa-phone.local"
        
        extra_fields.setdefault('user_type', 'patient')
        extra_fields.setdefault('phone', phone)
        extra_fields.setdefault('name', name)
        
        user = self.model(email=placeholder_email, **extra_fields)
        user.set_unusable_password()
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
        
        if not email:
            raise ValueError('Superuser must have an email.')

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
    phone = models.CharField(
        'phone number',
        max_length=20,
        unique=True,
        null=True,
        blank=True,
        help_text='Unique phone number for OTP authentication'
    )
    user_type = models.CharField(
        'user type',
        max_length=20,
        choices=UserType.choices,
        default=UserType.PATIENT
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    birth_date = models.DateField('birth date', null=True, blank=True)
    city = models.ForeignKey('locations.City', on_delete=models.SET_NULL, null=True, blank=True, verbose_name='city')
    
    objects = UserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
    
    class Meta:
        verbose_name = 'user'
        verbose_name_plural = 'users'
        ordering = ['-created_at']
    
    def __str__(self):
        if self.name:
            return self.name
        if self.email and not self.email.endswith('@clinixa-phone.local'):
            return self.email
        return self.phone or 'Unknown User'
    
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


class OTPVerification(models.Model):
    """
    Stores OTP codes for phone verification.
    Used for patient authentication via phone number.
    """
    phone = models.CharField('phone number', max_length=20, db_index=True)
    otp_code = models.CharField('OTP code', max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField('expires at')
    is_used = models.BooleanField('is used', default=False)
    attempts = models.IntegerField('verification attempts', default=0)
    
    class Meta:
        verbose_name = 'OTP verification'
        verbose_name_plural = 'OTP verifications'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"OTP for {self.phone} - {'Used' if self.is_used else 'Active'}"
    
    @property
    def is_expired(self):
        """Check if the OTP has expired."""
        from django.utils import timezone
        return timezone.now() > self.expires_at
    
    @property
    def is_valid(self):
        """Check if OTP is still valid (not expired and not used)."""
        return not self.is_expired and not self.is_used
    
    def mark_as_used(self):
        """Mark the OTP as used."""
        self.is_used = True
        self.save(update_fields=['is_used'])
    
    def increment_attempts(self):
        """Increment the verification attempts counter."""
        self.attempts += 1
        self.save(update_fields=['attempts'])
