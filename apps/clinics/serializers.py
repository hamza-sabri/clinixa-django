from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.db.models import Count

from .models import Clinic, Employee

User = get_user_model()


class ClinicSerializer(serializers.ModelSerializer):
    """Serializer for Clinic model."""
    
    doctor_name = serializers.CharField(source='doctor.name', read_only=True)
    doctor_email = serializers.CharField(source='doctor.email', read_only=True)
    city_name = serializers.CharField(source='city.name', read_only=True)
    
    class Meta:
        model = Clinic
        fields = [
            'id', 'doctor', 'doctor_name', 'doctor_email',
            'name', 'location', 'phone', 'type', 'city', 'city_name',
            'working_hours', 'slot_duration', 'description',
            'latitude', 'longitude', 'is_accepting_new_patients', 'is_open',
            'created_at'
        ]
        read_only_fields = ['id', 'doctor', 'doctor_name', 'doctor_email', 'city_name', 'created_at']
    
    def create(self, validated_data):
        # Set the doctor to the current user
        validated_data['doctor'] = self.context['request'].user
        return super().create(validated_data)


class ClinicListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for clinic lists with statistics."""
    
    doctor_name = serializers.CharField(source='doctor.name', read_only=True)
    city_name = serializers.CharField(source='city.name', read_only=True)
    visits_per_status = serializers.SerializerMethodField()
    distinct_patients_count = serializers.SerializerMethodField()
    employees_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Clinic
        fields = [
            'id', 'name', 'doctor_name', 'location', 'phone', 'type',
            'city', 'city_name',
            'working_hours', 'slot_duration', 'is_accepting_new_patients', 'is_open',
            'description', 'latitude', 'longitude',
            'visits_per_status', 'distinct_patients_count', 'employees_count'
        ]
    
    def get_visits_per_status(self, obj):
        """Get count of visits grouped by status."""
        from apps.visits.models import Visit
        visits = Visit.objects.filter(clinic=obj).values('status').annotate(count=Count('id'))
        return {item['status']: item['count'] for item in visits}
    
    def get_distinct_patients_count(self, obj):
        """Get count of distinct patients who have visited this clinic."""
        from apps.visits.models import Visit
        return Visit.objects.filter(clinic=obj).values('pregnancy').distinct().count()
    
    def get_employees_count(self, obj):
        """Get total number of employees at this clinic."""
        return obj.employees.count()


class ClinicDetailSerializer(serializers.ModelSerializer):
    """Serializer for clinic detail with statistics."""
    
    doctor_name = serializers.CharField(source='doctor.name', read_only=True)
    doctor_email = serializers.CharField(source='doctor.email', read_only=True)
    city_name = serializers.CharField(source='city.name', read_only=True)
    visits_per_status = serializers.SerializerMethodField()
    distinct_patients_count = serializers.SerializerMethodField()
    employees_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Clinic
        fields = [
            'id', 'doctor', 'doctor_name', 'doctor_email',
            'name', 'location', 'phone', 'type', 'city', 'city_name',
            'working_hours', 'slot_duration', 'description',
            'latitude', 'longitude', 'is_accepting_new_patients', 'is_open',
            'visits_per_status', 'distinct_patients_count', 'employees_count',
            'created_at'
        ]
        read_only_fields = ['id', 'doctor', 'doctor_name', 'doctor_email', 'city_name', 'created_at']
    
    def get_visits_per_status(self, obj):
        """Get count of visits grouped by status."""
        from apps.visits.models import Visit
        visits = Visit.objects.filter(clinic=obj).values('status').annotate(count=Count('id'))
        return {item['status']: item['count'] for item in visits}
    
    def get_distinct_patients_count(self, obj):
        """Get count of distinct patients who have visited this clinic."""
        from apps.visits.models import Visit
        return Visit.objects.filter(clinic=obj).values('pregnancy').distinct().count()
    
    def get_employees_count(self, obj):
        """Get total number of employees at this clinic."""
        return obj.employees.count()


class EmployeeListSerializer(serializers.ModelSerializer):
    """Serializer for listing employees."""
    
    staff_name = serializers.CharField(source='staff.name', read_only=True)
    staff_email = serializers.CharField(source='staff.email', read_only=True)
    staff_phone = serializers.CharField(source='staff.phone', read_only=True)
    staff_city = serializers.IntegerField(source='staff.city.id', read_only=True)
    staff_city_name = serializers.CharField(source='staff.city.name', read_only=True)
    clinic_name = serializers.CharField(source='clinic.name', read_only=True)
    
    class Meta:
        model = Employee
        fields = [
            'id', 'staff', 'staff_name', 'staff_email', 'staff_phone',
            'staff_city', 'staff_city_name',
            'clinic', 'clinic_name', 'role', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class EmployeeCreateSerializer(serializers.Serializer):
    """
    Serializer for creating an employee.
    Creates both the User (with user_type='employee') and the Employee record.
    """
    
    # User fields
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=6)
    name = serializers.CharField(required=False, allow_blank=True)
    phone = serializers.CharField(required=False, allow_blank=True)
    city = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text='City ID for the employee'
    )
    
    # Employee fields
    clinic = serializers.PrimaryKeyRelatedField(queryset=Clinic.objects.all())
    role = serializers.CharField(default='staff')
    
    def validate_email(self, value):
        if User.objects.filter(email=value.lower()).exists():
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
    
    def validate_clinic(self, value):
        # Ensure the clinic belongs to the requesting doctor
        request = self.context.get('request')
        if request and value.doctor != request.user:
            raise serializers.ValidationError('You can only add employees to your own clinics.')
        return value
    
    def create(self, validated_data):
        # Extract city
        city_id = validated_data.pop('city', None)
        city = None
        if city_id:
            from apps.locations.models import City
            city = City.objects.filter(id=city_id).first()
        
        # Create the user
        user = User.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            name=validated_data.get('name', ''),
            phone=validated_data.get('phone', ''),
            user_type='employee',
            city=city
        )
        
        # Create the employee record
        employee = Employee.objects.create(
            staff=user,
            clinic=validated_data['clinic'],
            role=validated_data.get('role', 'staff')
        )
        
        return employee


class EmployeeUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating an employee (role and clinic only)."""
    
    class Meta:
        model = Employee
        fields = ['clinic', 'role']
    
    def validate_clinic(self, value):
        # Ensure the new clinic also belongs to the requesting doctor
        request = self.context.get('request')
        if request and value.doctor != request.user:
            raise serializers.ValidationError('You can only assign employees to your own clinics.')
        return value

