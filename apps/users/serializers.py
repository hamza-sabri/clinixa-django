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


