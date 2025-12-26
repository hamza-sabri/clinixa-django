from rest_framework import serializers
from django.utils import timezone

from .models import Visit
from apps.clinics.serializers import ClinicListSerializer


class VisitSerializer(serializers.ModelSerializer):
    """Serializer for Visit model."""
    
    patient_name = serializers.CharField(source='patient.name', read_only=True)
    patient_email = serializers.CharField(source='patient.email', read_only=True)
    patient_phone = serializers.CharField(source='patient.phone', read_only=True)
    clinic_name = serializers.CharField(source='clinic.name', read_only=True)
    clinic_location = serializers.CharField(source='clinic.location', read_only=True)
    
    class Meta:
        model = Visit
        fields = [
            'id', 'clinic', 'clinic_name', 'clinic_location',
            'patient', 'patient_name', 'patient_email', 'patient_phone',
            'time', 'status', 'note', 'urgency', 'created_at'
        ]
        read_only_fields = ['id', 'patient', 'created_at']
    
    def create(self, validated_data):
        # Set the patient to the current user
        validated_data['patient'] = self.context['request'].user
        return super().create(validated_data)


class VisitCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a visit."""
    
    class Meta:
        model = Visit
        fields = ['clinic', 'time', 'status', 'note', 'urgency']
        extra_kwargs = {
            'status': {'required': False},
            'note': {'required': False},
            'urgency': {'required': False},
        }
    
    def validate_time(self, value):
        if value < timezone.now():
            raise serializers.ValidationError('Visit time cannot be in the past.')
        return value
    
    def create(self, validated_data):
        validated_data['patient'] = self.context['request'].user
        return super().create(validated_data)


class VisitUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating a visit."""
    
    class Meta:
        model = Visit
        fields = ['clinic', 'time', 'status', 'note', 'urgency']


class VisitListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for visit lists."""
    
    patient_name = serializers.CharField(source='patient.name', read_only=True)
    clinic_name = serializers.CharField(source='clinic.name', read_only=True)
    
    class Meta:
        model = Visit
        fields = ['id', 'clinic', 'clinic_name', 'patient', 'patient_name', 'time', 'status', 'urgency']


