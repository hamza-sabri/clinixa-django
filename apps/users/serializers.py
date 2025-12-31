from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model - used in responses."""
    
    class Meta:
        model = User
        fields = ['id', 'email', 'name', 'phone', 'user_type', 'created_at']
        read_only_fields = ['id', 'created_at']


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
    
    class Meta:
        model = User
        fields = ['email', 'password', 'name', 'phone']
        extra_kwargs = {
            'name': {'required': False},
            'phone': {'required': False},
        }
    
    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError('A user with this email already exists.')
        return value.lower()
    
    def validate_password(self, value):
        validate_password(value)
        return value
    
    def create(self, validated_data):
        user = User.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            name=validated_data.get('name', ''),
            phone=validated_data.get('phone', ''),
            user_type='patient'
        )
        return user


class SignupWithClinicSerializer(serializers.Serializer):
    """Serializer for doctor signup with clinic creation."""
    
    # User fields
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=6)
    name = serializers.CharField(required=False, allow_blank=True)
    phone = serializers.CharField(required=False, allow_blank=True)
    
    # Clinic fields
    clinic_name = serializers.CharField()
    clinic_location = serializers.CharField()
    clinic_phone = serializers.CharField()
    clinic_type = serializers.CharField(required=False, default='عيادة اطفال')
    
    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError('A user with this email already exists.')
        return value.lower()
    
    def validate_password(self, value):
        validate_password(value)
        return value
    
    def create(self, validated_data):
        # Import here to avoid circular imports
        from apps.clinics.models import Clinic
        
        # Create doctor user
        user = User.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            name=validated_data.get('name', ''),
            phone=validated_data.get('phone', ''),
            user_type='doctor'
        )
        
        # Create clinic
        Clinic.objects.create(
            doctor=user,
            name=validated_data['clinic_name'],
            location=validated_data['clinic_location'],
            phone=validated_data['clinic_phone'],
            type=validated_data.get('clinic_type', 'عيادة اطفال')
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
    
    class Meta:
        model = User
        fields = ['id', 'email', 'name', 'phone', 'profile', 'pregnancies', 'pregnancies_count', 'created_at']
    
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


class PatientDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for single patient view - includes all pregnancies."""
    
    profile = PatientProfileSerializer(source='patient_profile', read_only=True)
    pregnancies = serializers.SerializerMethodField()
    pregnancies_count = serializers.SerializerMethodField()
    ongoing_pregnancy = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'email', 'name', 'phone', 'profile', 'pregnancies', 'pregnancies_count', 'ongoing_pregnancy', 'created_at']
    
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


class PatientCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a new patient with profile."""
    
    # Profile fields (optional)
    blood_type = serializers.CharField(required=False, allow_blank=True)
    allergies = serializers.CharField(required=False, allow_blank=True)
    medical_history = serializers.CharField(required=False, allow_blank=True)
    profile_notes = serializers.CharField(required=False, allow_blank=True)
    
    class Meta:
        model = User
        fields = ['email', 'name', 'phone', 'blood_type', 'allergies', 'medical_history', 'profile_notes']
        extra_kwargs = {
            'name': {'required': False},
            'phone': {'required': False},
        }
    
    def validate_email(self, value):
        if User.objects.filter(email=value.lower()).exists():
            raise serializers.ValidationError('A user with this email already exists.')
        return value.lower()
    
    def create(self, validated_data):
        # Extract profile fields
        blood_type = validated_data.pop('blood_type', '')
        allergies = validated_data.pop('allergies', '')
        medical_history = validated_data.pop('medical_history', '')
        profile_notes = validated_data.pop('profile_notes', '')
        
        # Create user with a default password (can be reset later)
        import secrets
        temp_password = secrets.token_urlsafe(12)
        
        user = User.objects.create_user(
            email=validated_data['email'],
            password=temp_password,
            name=validated_data.get('name', ''),
            phone=validated_data.get('phone', ''),
            user_type='patient'
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
    
    class Meta:
        model = User
        fields = ['name', 'phone', 'blood_type', 'allergies', 'medical_history', 'profile_notes']
    
    def update(self, instance, validated_data):
        # Extract profile fields
        blood_type = validated_data.pop('blood_type', None)
        allergies = validated_data.pop('allergies', None)
        medical_history = validated_data.pop('medical_history', None)
        profile_notes = validated_data.pop('profile_notes', None)
        
        # Update user fields
        instance.name = validated_data.get('name', instance.name)
        instance.phone = validated_data.get('phone', instance.phone)
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


class PregnancyListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for pregnancy lists."""
    
    pregnancy_week = serializers.ReadOnlyField()
    trimester = serializers.ReadOnlyField()
    babies_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Pregnancy
        fields = ['id', 'lmp', 'due_date', 'status', 'is_high_risk', 'pregnancy_week', 'trimester', 'babies_count', 'created_at']
    
    def get_babies_count(self, obj):
        return obj.babies.count()


class PregnancyDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for single pregnancy view."""
    
    pregnancy_week = serializers.ReadOnlyField()
    trimester = serializers.ReadOnlyField()
    patient = serializers.SerializerMethodField()
    babies = BabyListSerializer(many=True, read_only=True)
    visits_count = serializers.SerializerMethodField()
    vitals_count = serializers.SerializerMethodField()
    last_visit = serializers.SerializerMethodField()
    created_by_clinic_name = serializers.CharField(source='created_by_clinic.name', read_only=True)
    
    class Meta:
        model = Pregnancy
        fields = [
            'id', 'patient', 'lmp', 'due_date', 'status', 'is_high_risk', 
            'pregnancy_week', 'trimester', 'notes', 'babies', 
            'visits_count', 'vitals_count', 'last_visit',
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
    
    class Meta:
        model = Pregnancy
        fields = ['lmp', 'due_date', 'status', 'is_high_risk', 'notes', 'created_by_clinic']
        extra_kwargs = {
            'lmp': {'required': False},
            'due_date': {'required': False},
            'status': {'required': False},
            'is_high_risk': {'required': False},
            'notes': {'required': False},
            'created_by_clinic': {'required': False},
        }


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

