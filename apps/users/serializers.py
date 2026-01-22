from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password

from apps.recordings.utils import generate_presigned_url

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model - used in responses."""
    
    city_name = serializers.CharField(source='city.name', read_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'email', 'name', 'phone', 'user_type', 'city', 'city_name', 'created_at']
        read_only_fields = ['id', 'city_name', 'created_at']


class ClinicInfoSerializer(serializers.Serializer):
    """Serializer for clinic info in JWT token."""
    id = serializers.IntegerField()
    name = serializers.CharField()
    location = serializers.CharField()
    phone = serializers.CharField()


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Custom token serializer that includes user info and clinic with statistics in the token."""
    
    username_field = 'email'
    
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        
        # Add custom claims to the token
        token['email'] = user.email
        token['name'] = user.name
        token['phone'] = user.phone
        token['user_type'] = user.user_type
        
        # Add clinic info for doctors
        if user.user_type == 'doctor':
            # Import here to avoid circular imports
            from apps.clinics.models import Clinic
            clinic = Clinic.objects.filter(doctor=user).first()
            if clinic:
                token['clinic'] = {
                    'id': clinic.id,
                    'name': clinic.name,
                    'location': clinic.location,
                    'phone': clinic.phone,
                }
            else:
                token['clinic'] = None
        
        # Add clinic info for employees
        elif user.user_type == 'employee':
            from apps.clinics.models import Employee
            employee = Employee.objects.filter(staff=user).select_related('clinic').first()
            if employee and employee.clinic:
                token['clinic'] = {
                    'id': employee.clinic.id,
                    'name': employee.clinic.name,
                    'location': employee.clinic.location,
                    'phone': employee.clinic.phone,
                }
                token['role'] = employee.role
            else:
                token['clinic'] = None
                token['role'] = None
        else:
            token['clinic'] = None
        
        return token
    
    def validate(self, attrs):
        data = super().validate(attrs)
        
        # Add user info to response
        data['user'] = UserSerializer(self.user).data
        
        # Add clinic info with statistics for doctors
        if self.user.user_type == 'doctor':
            from apps.clinics.models import Clinic
            from apps.clinics.serializers import ClinicDetailSerializer
            
            clinic = Clinic.objects.filter(doctor=self.user).first()
            if clinic:
                data['clinic'] = ClinicDetailSerializer(clinic).data
            else:
                data['clinic'] = None
        
        return data


class SignupSerializer(serializers.ModelSerializer):
    """Serializer for patient signup."""
    
    password = serializers.CharField(
        write_only=True,
        min_length=6,
        style={'input_type': 'password'}
    )
    city = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text='City ID for the patient'
    )
    
    class Meta:
        model = User
        fields = ['email', 'password', 'name', 'phone', 'city']
        extra_kwargs = {
            'name': {'required': False},
            'phone': {'required': False},
        }
    
    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError('A user with this email already exists.')
        return value.lower()
    
    def validate_city(self, value):
        if value is not None:
            from apps.locations.models import City
            if not City.objects.filter(id=value).exists():
                raise serializers.ValidationError('City not found.')
        return value
    
    def validate_password(self, value):
        validate_password(value)
        return value
    
    def create(self, validated_data):
        city_id = validated_data.pop('city', None)
        city = None
        if city_id:
            from apps.locations.models import City
            city = City.objects.filter(id=city_id).first()
        
        user = User.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            name=validated_data.get('name', ''),
            phone=validated_data.get('phone', ''),
            user_type='patient',
            city=city
        )
        return user


class SignupWithClinicSerializer(serializers.Serializer):
    """Serializer for doctor signup with clinic creation."""
    
    # User fields
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=6)
    name = serializers.CharField(required=False, allow_blank=True)
    phone = serializers.CharField(required=False, allow_blank=True)
    city = serializers.IntegerField(required=False, allow_null=True, help_text='City ID for the doctor')
    
    # Clinic fields
    clinic_name = serializers.CharField()
    clinic_location = serializers.CharField()
    clinic_phone = serializers.CharField()
    clinic_type = serializers.CharField(required=False, default='عيادة اطفال')
    clinic_city = serializers.IntegerField(required=False, allow_null=True, help_text='City ID for the clinic')
    
    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError('A user with this email already exists.')
        return value.lower()
    
    def validate_password(self, value):
        validate_password(value)
        return value
    
    def validate_city(self, value):
        if value is not None:
            from apps.locations.models import City
            if not City.objects.filter(id=value).exists():
                raise serializers.ValidationError('City not found.')
        return value
    
    def validate_clinic_city(self, value):
        if value is not None:
            from apps.locations.models import City
            if not City.objects.filter(id=value).exists():
                raise serializers.ValidationError('City not found.')
        return value
    
    def create(self, validated_data):
        # Import here to avoid circular imports
        from apps.clinics.models import Clinic
        from apps.locations.models import City
        
        # Get city objects
        user_city = None
        if validated_data.get('city'):
            user_city = City.objects.filter(id=validated_data['city']).first()
        
        clinic_city = None
        if validated_data.get('clinic_city'):
            clinic_city = City.objects.filter(id=validated_data['clinic_city']).first()
        
        # Create doctor user
        user = User.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            name=validated_data.get('name', ''),
            phone=validated_data.get('phone', ''),
            user_type='doctor',
            city=user_city
        )
        
        # Create clinic
        Clinic.objects.create(
            doctor=user,
            name=validated_data['clinic_name'],
            location=validated_data['clinic_location'],
            phone=validated_data['clinic_phone'],
            type=validated_data.get('clinic_type', 'عيادة اطفال'),
            city=clinic_city
        )
        
        return user


class SigninSerializer(serializers.Serializer):
    """Serializer for user signin - returns tokens."""
    
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    
    def validate(self, attrs):
        email = attrs.get('email', '').lower()
        password = attrs.get('password')
        
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise serializers.ValidationError({'email': 'No user found with this email.'})
        
        if not user.check_password(password):
            raise serializers.ValidationError({'password': 'Incorrect password.'})
        
        if not user.is_active:
            raise serializers.ValidationError({'email': 'This account has been deactivated.'})
        
        attrs['user'] = user
        return attrs


class ForgetPasswordSerializer(serializers.Serializer):
    """Serializer for forget password - stubbed for now."""
    
    email = serializers.EmailField()
    
    def validate_email(self, value):
        if not User.objects.filter(email=value.lower()).exists():
            raise serializers.ValidationError('No user found with this email.')
        return value.lower()


class TokenResponseSerializer(serializers.Serializer):
    """Serializer for token response - used in Swagger documentation."""
    
    access = serializers.CharField()
    refresh = serializers.CharField()
    user = UserSerializer()


# ============================================================================
# OTP AUTHENTICATION SERIALIZERS
# ============================================================================

class RequestOTPSerializer(serializers.Serializer):
    """Serializer for requesting OTP for patient login."""
    
    phone = serializers.CharField(
        max_length=20,
        help_text='Phone number in international format, e.g. +971501234567'
    )
    name = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
        help_text='Patient name (optional for returning users, required for new users)'
    )
    
    def validate_phone(self, value):
        """Validate and normalize phone number."""
        # Remove any spaces or dashes
        value = value.replace(' ', '').replace('-', '')

        # Convert local Palestinian numbers (05xxxxxxxx) to international format
        if value.startswith('05') and len(value) == 10:
            value = '+970' + value[1:]  # Replace leading 0 with +970
        # Also handle numbers starting with just 5 (without leading 0)
        elif value.startswith('5') and len(value) == 9:
            value = '+970' + value

        # Basic validation - should start with + and have at least 10 digits
        if not value.startswith('+'):
            raise serializers.ValidationError('Phone number must be in international format (starting with +) or local format (05xxxxxxxx)')
        if len(value) < 10:
            raise serializers.ValidationError('Phone number is too short')

        return value


class VerifyOTPSerializer(serializers.Serializer):
    """Serializer for verifying OTP and logging in patient."""
    
    phone = serializers.CharField(
        max_length=20,
        help_text='Phone number used to request OTP'
    )
    otp = serializers.CharField(
        max_length=6,
        min_length=6,
        help_text='6-digit OTP code received via SMS'
    )
    name = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
        help_text='Patient name (required only for new users)'
    )
    
    def validate_phone(self, value):
        """Validate and normalize phone number."""
        value = value.replace(' ', '').replace('-', '')

        # Convert local Palestinian numbers (05xxxxxxxx) to international format
        if value.startswith('05') and len(value) == 10:
            value = '+970' + value[1:]  # Replace leading 0 with +970
        # Also handle numbers starting with just 5 (without leading 0)
        elif value.startswith('5') and len(value) == 9:
            value = '+970' + value

        return value


class OTPResponseSerializer(serializers.Serializer):
    """Response serializer for OTP request - used in Swagger documentation."""
    
    message = serializers.CharField()
    phone = serializers.CharField()
    expires_in = serializers.IntegerField(help_text='Seconds until OTP expires')
    is_new_user = serializers.BooleanField(help_text='True if this is a new patient')


class PatientUserSerializer(serializers.ModelSerializer):
    """User serializer for patient responses - hides placeholder emails."""
    
    email = serializers.SerializerMethodField()
    city_name = serializers.CharField(source='city.name', read_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'email', 'name', 'phone', 'user_type', 'city', 'city_name', 'created_at']
        read_only_fields = ['id', 'city_name', 'created_at']
    
    def get_email(self, obj):
        """Return None for placeholder emails (phone-only users)."""
        if obj.email and obj.email.endswith('@clinixa-phone.local'):
            return None
        return obj.email


class OTPLoginResponseSerializer(serializers.Serializer):
    """Response serializer for OTP verification - used in Swagger documentation."""
    
    access = serializers.CharField()
    refresh = serializers.CharField()
    user = PatientUserSerializer()
    is_new_user = serializers.BooleanField()


# ============================================================================
# PATIENT SELF-SERVICE SERIALIZERS
# ============================================================================

class PatientMeSerializer(serializers.ModelSerializer):
    """Serializer for /patients/me/ endpoint - authenticated patient's own data."""
    
    profile = serializers.SerializerMethodField()
    pregnancies = serializers.SerializerMethodField()
    pregnancies_count = serializers.SerializerMethodField()
    ongoing_pregnancy = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()
    city_name = serializers.CharField(source='city.name', read_only=True)
    
    class Meta:
        model = User
        fields = [
            'id', 'email', 'phone', 'name', 'user_type', 'birth_date',
            'city', 'city_name',
            'profile', 'pregnancies', 'pregnancies_count', 'ongoing_pregnancy',
            'created_at'
        ]
        read_only_fields = ['id', 'user_type', 'city_name', 'created_at']
    
    def get_email(self, obj):
        """Return None for placeholder emails (phone-only users)."""
        if obj.email and obj.email.endswith('@clinixa-phone.local'):
            return None
        return obj.email
    
    def get_profile(self, obj):
        if hasattr(obj, 'patient_profile'):
            return PatientProfileSerializer(obj.patient_profile).data
        return None
    
    def get_pregnancies(self, obj):
        if hasattr(obj, 'patient_profile'):
            pregnancies = obj.patient_profile.pregnancies.order_by('-due_date')
            return PregnancyListSerializer(pregnancies, many=True).data
        return []
    
    def get_pregnancies_count(self, obj):
        if hasattr(obj, 'patient_profile'):
            return obj.patient_profile.pregnancies.count()
        return 0
    
    def get_ongoing_pregnancy(self, obj):
        if hasattr(obj, 'patient_profile'):
            ongoing = obj.patient_profile.pregnancies.filter(status='ongoing').order_by('-due_date').first()
            if ongoing:
                return PregnancyDetailSerializer(ongoing).data
        return None


class PatientMeUpdateSerializer(serializers.Serializer):
    """Serializer for updating patient's own profile via PATCH /patients/me/."""
    
    name = serializers.CharField(max_length=255, required=False, allow_blank=True)
    birth_date = serializers.DateField(required=False, allow_null=True, help_text='Patient birth date (YYYY-MM-DD)')
    city = serializers.IntegerField(required=False, allow_null=True, help_text='City ID')
    profile = serializers.DictField(required=False, help_text='Profile fields: blood_type, allergies, medical_history, notes')
    
    def validate_city(self, value):
        if value is not None:
            from apps.locations.models import City
            if not City.objects.filter(id=value).exists():
                raise serializers.ValidationError('City not found.')
        return value
    
    def update(self, instance, validated_data):
        # Collect fields to update on the user instance
        update_fields = []
        
        # Update name if provided
        if 'name' in validated_data:
            instance.name = validated_data['name']
            update_fields.append('name')
        
        # Update birth_date if provided
        if 'birth_date' in validated_data:
            instance.birth_date = validated_data['birth_date']
            update_fields.append('birth_date')
        
        # Update city if provided
        if 'city' in validated_data:
            from apps.locations.models import City
            city_id = validated_data['city']
            instance.city = City.objects.filter(id=city_id).first() if city_id else None
            update_fields.append('city')
        
        # Save user instance if any fields were updated
        if update_fields:
            instance.save(update_fields=update_fields)
        
        # Update profile if provided
        profile_data = validated_data.get('profile', {})
        if profile_data:
            from .models import PatientProfile
            profile, created = PatientProfile.objects.get_or_create(user=instance)
            
            if 'blood_type' in profile_data:
                profile.blood_type = profile_data['blood_type']
            if 'allergies' in profile_data:
                profile.allergies = profile_data['allergies']
            if 'medical_history' in profile_data:
                profile.medical_history = profile_data['medical_history']
            if 'notes' in profile_data:
                profile.notes = profile_data['notes']
            
            profile.save()
        
        return instance


# ============================================================================
# PATIENT PROFILE SERIALIZERS
# ============================================================================

from .models import PatientProfile, Pregnancy, Baby


class PatientProfileSerializer(serializers.ModelSerializer):
    """Serializer for PatientProfile model."""
    
    class Meta:
        model = PatientProfile
        fields = ['id', 'blood_type', 'allergies', 'medical_history', 'notes', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class PatientListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for patient lists - includes all pregnancies."""

    profile = PatientProfileSerializer(source='patient_profile', read_only=True)
    pregnancies = serializers.SerializerMethodField()
    pregnancies_count = serializers.SerializerMethodField()
    city_name = serializers.CharField(source='city.name', read_only=True)
    birth_date = serializers.DateField(read_only=True)
    age = serializers.SerializerMethodField()
    has_active_pregnancy = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'email', 'name', 'phone', 'birth_date', 'age', 'has_active_pregnancy', 'city', 'city_name', 'profile', 'pregnancies', 'pregnancies_count', 'created_at']

    def get_pregnancies(self, obj):
        """Get all pregnancies ordered by due_date descending."""
        if hasattr(obj, 'patient_profile'):
            pregnancies = obj.patient_profile.pregnancies.order_by('-due_date')
            return PregnancyListSerializer(pregnancies, many=True).data
        return []

    def get_pregnancies_count(self, obj):
        if hasattr(obj, 'patient_profile'):
            return obj.patient_profile.pregnancies.count()
        return 0

    def get_age(self, obj):
        """Calculate age from birth_date."""
        if obj.birth_date:
            from datetime import date
            today = date.today()
            age = today.year - obj.birth_date.year
            if (today.month, today.day) < (obj.birth_date.month, obj.birth_date.day):
                age -= 1
            return age
        return None

    def get_has_active_pregnancy(self, obj):
        """Check if patient has an ongoing pregnancy."""
        if hasattr(obj, 'patient_profile'):
            return obj.patient_profile.pregnancies.filter(status='ongoing').exists()
        return False


class PatientDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for single patient view - includes all pregnancies."""

    profile = PatientProfileSerializer(source='patient_profile', read_only=True)
    pregnancies = serializers.SerializerMethodField()
    pregnancies_count = serializers.SerializerMethodField()
    ongoing_pregnancy = serializers.SerializerMethodField()
    city_name = serializers.CharField(source='city.name', read_only=True)
    birth_date = serializers.DateField(read_only=True)
    age = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'email', 'name', 'phone', 'birth_date', 'age', 'city', 'city_name', 'profile', 'pregnancies', 'pregnancies_count', 'ongoing_pregnancy', 'created_at']
    
    def get_pregnancies(self, obj):
        """Get all pregnancies ordered by due_date descending."""
        if hasattr(obj, 'patient_profile'):
            pregnancies = obj.patient_profile.pregnancies.order_by('-due_date')
            return PregnancyListSerializer(pregnancies, many=True).data
        return []
    
    def get_pregnancies_count(self, obj):
        if hasattr(obj, 'patient_profile'):
            return obj.patient_profile.pregnancies.count()
        return 0
    
    def get_ongoing_pregnancy(self, obj):
        if hasattr(obj, 'patient_profile'):
            ongoing = obj.patient_profile.pregnancies.filter(status='ongoing').order_by('-due_date').first()
            if ongoing:
                return PregnancyListSerializer(ongoing).data
        return None

    def get_age(self, obj):
        """Calculate age from birth_date."""
        if obj.birth_date:
            from datetime import date
            today = date.today()
            age = today.year - obj.birth_date.year
            if (today.month, today.day) < (obj.birth_date.month, obj.birth_date.day):
                age -= 1
            return age
        return None


class PatientCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a new patient with profile."""
    
    # Profile fields (optional)
    blood_type = serializers.CharField(required=False, allow_blank=True)
    allergies = serializers.CharField(required=False, allow_blank=True)
    medical_history = serializers.CharField(required=False, allow_blank=True)
    profile_notes = serializers.CharField(required=False, allow_blank=True)
    city = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text='City ID for the patient'
    )
    
    class Meta:
        model = User
        fields = ['email', 'name', 'phone', 'city', 'blood_type', 'allergies', 'medical_history', 'profile_notes']
        extra_kwargs = {
            'name': {'required': False},
            'phone': {'required': False},
        }
    
    def validate_email(self, value):
        if User.objects.filter(email=value.lower()).exists():
            raise serializers.ValidationError('A user with this email already exists.')
        return value.lower()
    
    def validate_city(self, value):
        if value is not None:
            from apps.locations.models import City
            if not City.objects.filter(id=value).exists():
                raise serializers.ValidationError('City not found.')
        return value
    
    def create(self, validated_data):
        # Extract profile fields
        blood_type = validated_data.pop('blood_type', '')
        allergies = validated_data.pop('allergies', '')
        medical_history = validated_data.pop('medical_history', '')
        profile_notes = validated_data.pop('profile_notes', '')
        city_id = validated_data.pop('city', None)
        
        city = None
        if city_id:
            from apps.locations.models import City
            city = City.objects.filter(id=city_id).first()
        
        # Create user with a default password (can be reset later)
        import secrets
        temp_password = secrets.token_urlsafe(12)
        
        user = User.objects.create_user(
            email=validated_data['email'],
            password=temp_password,
            name=validated_data.get('name', ''),
            phone=validated_data.get('phone', ''),
            user_type='patient',
            city=city
        )
        
        # Create profile
        PatientProfile.objects.create(
            user=user,
            blood_type=blood_type,
            allergies=allergies,
            medical_history=medical_history,
            notes=profile_notes
        )
        
        return user


class PatientUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating patient and profile."""

    # Profile fields
    blood_type = serializers.CharField(required=False, allow_blank=True)
    allergies = serializers.CharField(required=False, allow_blank=True)
    medical_history = serializers.CharField(required=False, allow_blank=True)
    profile_notes = serializers.CharField(required=False, allow_blank=True)
    city_name = serializers.CharField(source='city.name', read_only=True)

    class Meta:
        model = User
        fields = ['name', 'phone', 'city', 'city_name', 'blood_type', 'allergies', 'medical_history', 'profile_notes']

    def update(self, instance, validated_data):
        # Extract profile fields
        blood_type = validated_data.pop('blood_type', None)
        allergies = validated_data.pop('allergies', None)
        medical_history = validated_data.pop('medical_history', None)
        profile_notes = validated_data.pop('profile_notes', None)

        # Update user fields
        instance.name = validated_data.get('name', instance.name)
        instance.phone = validated_data.get('phone', instance.phone)
        if 'city' in validated_data:
            instance.city = validated_data.get('city')
        instance.save()

        # Update or create profile
        profile, created = PatientProfile.objects.get_or_create(user=instance)
        if blood_type is not None:
            profile.blood_type = blood_type
        if allergies is not None:
            profile.allergies = allergies
        if medical_history is not None:
            profile.medical_history = medical_history
        if profile_notes is not None:
            profile.notes = profile_notes
        profile.save()

        return instance


# ============================================================================
# PREGNANCY SERIALIZERS
# ============================================================================

class BabyListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for baby lists."""
    
    class Meta:
        model = Baby
        fields = ['id', 'name', 'gender', 'is_born', 'birth_date', 'birth_weight', 'created_at']


class BabyWithVitalsSerializer(serializers.ModelSerializer):
    """Baby serializer with all vitals included."""
    
    vitals = serializers.SerializerMethodField()
    
    class Meta:
        model = Baby
        fields = [
            'id', 'name', 'gender', 'birth_date', 'birth_weight',
            'birth_length', 'apgar_score', 'is_born', 'notes',
            'vitals', 'created_at', 'updated_at'
        ]
    
    def get_vitals(self, obj):
        from apps.vitals.serializers import BabyVitalListSerializer
        return BabyVitalListSerializer(obj.vitals.all(), many=True).data


class PregnancyListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for pregnancy lists."""

    pregnancy_week = serializers.ReadOnlyField()
    trimester = serializers.ReadOnlyField()
    babies_count = serializers.SerializerMethodField()
    gestation = serializers.SerializerMethodField()
    is_ongoing = serializers.SerializerMethodField()

    class Meta:
        model = Pregnancy
        fields = ['id', 'lmp', 'due_date', 'status', 'is_ongoing', 'gestation', 'is_high_risk', 'pregnancy_week', 'trimester', 'babies_count', 'notes', 'created_at']

    def get_babies_count(self, obj):
        return obj.babies.count()

    def get_gestation(self, obj):
        """Return gestation as 'X weeks Y days' format."""
        if obj.lmp:
            from datetime import date
            days = (date.today() - obj.lmp).days
            if days < 0:
                return None
            weeks = days // 7
            remaining_days = days % 7
            return f"{weeks}w {remaining_days}d"
        return None

    def get_is_ongoing(self, obj):
        return obj.status == 'ongoing'


class PregnancyDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for single pregnancy view with ALL related data."""
    
    pregnancy_week = serializers.ReadOnlyField()
    trimester = serializers.ReadOnlyField()
    patient = serializers.SerializerMethodField()
    
    # Full related data
    babies = BabyWithVitalsSerializer(many=True, read_only=True)  # Babies WITH their vitals
    vitals = serializers.SerializerMethodField()  # Mother's vitals
    visits = serializers.SerializerMethodField()  # All visits
    
    # Counts for quick reference
    babies_count = serializers.SerializerMethodField()
    visits_count = serializers.SerializerMethodField()
    vitals_count = serializers.SerializerMethodField()
    last_visit = serializers.SerializerMethodField()
    created_by_clinic_name = serializers.CharField(source='created_by_clinic.name', read_only=True)
    
    class Meta:
        model = Pregnancy
        fields = [
            'id', 'patient', 'lmp', 'due_date', 'status', 'is_high_risk', 
            'pregnancy_week', 'trimester', 'notes',
            'babies_count', 'babies',
            'vitals_count', 'vitals',
            'visits_count', 'visits', 'last_visit',
            'created_by_clinic', 'created_by_clinic_name', 'created_at', 'updated_at'
        ]
    
    def get_patient(self, obj):
        user = obj.patient_profile.user
        return {
            'id': user.id,
            'name': user.name,
            'email': user.email,
            'phone': user.phone
        }
    
    def get_babies_count(self, obj):
        return obj.babies.count()
    
    def get_vitals(self, obj):
        from apps.vitals.serializers import VitalListSerializer
        return VitalListSerializer(obj.vitals.all(), many=True).data
    
    def get_visits(self, obj):
        from apps.visits.serializers import VisitListSerializer
        return VisitListSerializer(obj.visits.all(), many=True).data
    
    def get_visits_count(self, obj):
        return obj.visits.count()
    
    def get_vitals_count(self, obj):
        return obj.vitals.count()
    
    def get_last_visit(self, obj):
        last = obj.visits.order_by('-time').first()
        if last:
            return last.time.isoformat()
        return None


class PregnancyCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a new pregnancy."""
    
    babies_count = serializers.IntegerField(
        write_only=True,
        required=False,
        default=1,
        min_value=1,
        max_value=8,
        help_text='Number of babies to create for this pregnancy (twins, triplets, etc.)'
    )
    
    class Meta:
        model = Pregnancy
        fields = ['lmp', 'due_date', 'status', 'is_high_risk', 'notes', 'created_by_clinic', 'babies_count']
        extra_kwargs = {
            'lmp': {'required': False},
            'due_date': {'required': False},
            'status': {'required': False},
            'is_high_risk': {'required': False},
            'notes': {'required': False},
            'created_by_clinic': {'required': False},
        }
    
    def create(self, validated_data):
        # Remove babies_count from validated_data (not a model field)
        validated_data.pop('babies_count', None)
        return super().create(validated_data)


class PatientMePregnancyCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for patient self-service pregnancy creation.
    Excludes created_by_clinic as patients don't set this field.
    """
    
    babies_count = serializers.IntegerField(
        write_only=True,
        required=False,
        default=1,
        min_value=1,
        max_value=8,
        help_text='Number of babies to create for this pregnancy (twins, triplets, etc.)'
    )
    
    class Meta:
        model = Pregnancy
        fields = ['lmp', 'due_date', 'is_high_risk', 'notes', 'babies_count']
        extra_kwargs = {
            'lmp': {'required': False, 'help_text': 'Last menstrual period date (YYYY-MM-DD)'},
            'due_date': {'required': False, 'help_text': 'Expected due date (YYYY-MM-DD)'},
            'is_high_risk': {'required': False, 'default': False, 'help_text': 'Is this a high-risk pregnancy?'},
            'notes': {'required': False, 'help_text': 'Additional notes'},
        }
    
    def create(self, validated_data):
        # Remove babies_count from validated_data (not a model field)
        validated_data.pop('babies_count', None)
        return super().create(validated_data)


class PregnancyUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating a pregnancy."""
    
    class Meta:
        model = Pregnancy
        fields = ['lmp', 'due_date', 'status', 'is_high_risk', 'notes']


# ============================================================================
# BABY SERIALIZERS
# ============================================================================

class BabyDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for single baby view."""
    
    pregnancy_id = serializers.IntegerField(source='pregnancy.id', read_only=True)
    vitals_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Baby
        fields = [
            'id', 'pregnancy_id', 'name', 'gender', 'birth_date', 
            'birth_weight', 'birth_length', 'apgar_score', 'is_born', 
            'notes', 'vitals_count', 'created_at', 'updated_at'
        ]
    
    def get_vitals_count(self, obj):
        return obj.vitals.count()


class BabyCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a new baby."""
    
    class Meta:
        model = Baby
        fields = ['name', 'gender', 'birth_date', 'birth_weight', 'birth_length', 'apgar_score', 'is_born', 'notes']
        extra_kwargs = {
            'name': {'required': False},
            'gender': {'required': False},
            'birth_date': {'required': False},
            'birth_weight': {'required': False},
            'birth_length': {'required': False},
            'apgar_score': {'required': False},
            'is_born': {'required': False},
            'notes': {'required': False},
        }


class BabyUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating a baby."""
    
    class Meta:
        model = Baby
        fields = ['name', 'gender', 'birth_date', 'birth_weight', 'birth_length', 'apgar_score', 'is_born', 'notes']


# ============================================================================
# USER ATTACHMENT SERIALIZERS
# ============================================================================

from .models import UserAttachment


# ============================================================================
# QUICK PATIENT CREATE SERIALIZER
# ============================================================================

class QuickPatientCreateSerializer(serializers.Serializer):
    """
    Serializer for quickly creating a patient with optional pregnancy.

    Creates a patient user and optionally a pregnancy if lmp is provided.
    """

    # Required fields
    name = serializers.CharField(
        max_length=255,
        help_text='Patient full name (required)'
    )
    phone = serializers.CharField(
        max_length=20,
        help_text='Phone number in international format, e.g. +971501234567 (required)'
    )

    # Optional fields
    birthday = serializers.DateField(
        required=False,
        allow_null=True,
        help_text='Patient birth date (YYYY-MM-DD)'
    )
    city = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text='City ID for the patient'
    )
    lmp = serializers.DateField(
        required=False,
        allow_null=True,
        help_text='Last menstrual period date (YYYY-MM-DD). If provided, a pregnancy will be created. Due date will be calculated as LMP + 280 days if not provided.'
    )
    due_date = serializers.DateField(
        required=False,
        allow_null=True,
        help_text='Expected due date (YYYY-MM-DD). Optional - if not provided but lmp is, it will be calculated as LMP + 280 days.'
    )

    def validate_phone(self, value):
        """Validate and normalize phone number."""
        # Remove any spaces or dashes
        value = value.replace(' ', '').replace('-', '')

        # Check if a user with this phone already exists
        if User.objects.filter(phone=value).exists():
            raise serializers.ValidationError('A patient with this phone number already exists.')

        return value

    def validate_city(self, value):
        """Validate that the city exists."""
        if value is not None:
            from apps.locations.models import City
            if not City.objects.filter(id=value).exists():
                raise serializers.ValidationError('City not found.')
        return value

    def create(self, validated_data):
        """Create user, patient profile, and optionally pregnancy."""
        from apps.locations.models import City
        from datetime import timedelta

        # Extract fields
        name = validated_data['name']
        phone = validated_data['phone']
        birthday = validated_data.get('birthday')
        city_id = validated_data.get('city')
        lmp = validated_data.get('lmp')
        due_date = validated_data.get('due_date')

        # Get city object
        city = None
        if city_id:
            city = City.objects.filter(id=city_id).first()

        # Create user with phone (uses placeholder email)
        user = User.objects.create_user_with_phone(
            phone=phone,
            name=name
        )

        # Update birth_date and city
        if birthday:
            user.birth_date = birthday
        if city:
            user.city = city
        if birthday or city:
            user.save(update_fields=['birth_date', 'city'] if birthday and city else
                      ['birth_date'] if birthday else ['city'])

        # Ensure patient profile exists
        profile, _ = PatientProfile.objects.get_or_create(user=user)

        # Create pregnancy if lmp is provided
        pregnancy = None
        if lmp:
            # Calculate due_date from lmp if not provided (LMP + 280 days)
            if not due_date:
                due_date = lmp + timedelta(days=280)

            pregnancy = Pregnancy.objects.create(
                patient_profile=profile,
                lmp=lmp,
                due_date=due_date,
                status='ongoing'
            )
            # Create one baby by default
            Baby.objects.create(pregnancy=pregnancy)

        # Store pregnancy for response serialization
        user._created_pregnancy = pregnancy

        return user


class QuickPatientCreateResponseSerializer(serializers.Serializer):
    """Response serializer for quick patient creation - used in Swagger documentation."""

    id = serializers.IntegerField(help_text='Patient user ID')
    name = serializers.CharField(help_text='Patient name')
    phone = serializers.CharField(help_text='Patient phone number')
    birthday = serializers.DateField(help_text='Patient birth date', allow_null=True)
    city = serializers.IntegerField(help_text='City ID', allow_null=True)
    city_name = serializers.CharField(help_text='City name', allow_null=True)
    pregnancy = serializers.DictField(
        help_text='Created pregnancy details (null if no lmp provided)',
        allow_null=True
    )
    created_at = serializers.DateTimeField(help_text='Account creation timestamp')


class UserAttachmentSerializer(serializers.ModelSerializer):
    """Serializer for user attachments with presigned B2 URL."""
    
    url = serializers.SerializerMethodField()
    display_name = serializers.SerializerMethodField()
    
    class Meta:
        model = UserAttachment
        fields = ['id', 'name', 'display_name', 'file_type', 'description', 'created_at', 'url']
        read_only_fields = ['id', 'name', 'file_type', 'created_at', 'url', 'display_name']
    
    def get_url(self, obj):
        """Generate presigned URL for B2 file."""
        return generate_presigned_url(obj.name)
    
    def get_display_name(self, obj):
        """Extract the original filename from the B2 stored name.
        
        B2 name format: user_{id}_att_{timestamp}_{original_name}
        We want to return just the original_name part.
        """
        if not obj.name:
            return None
        
        parts = obj.name.split('_')
        if len(parts) >= 5:
            # Skip first 4 parts: user, {id}, att, {timestamp}
            original_name = '_'.join(parts[4:])
            return original_name
        return obj.name

