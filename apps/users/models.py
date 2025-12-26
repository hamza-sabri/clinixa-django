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


