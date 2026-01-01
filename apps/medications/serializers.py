from rest_framework import serializers
from .models import Med, PatientMed


class MedSerializer(serializers.ModelSerializer):
    """Serializer for Med model."""
    
    created_by_name = serializers.CharField(source='created_by.name', read_only=True)
    
    class Meta:
        model = Med
        fields = ['id', 'name', 'note', 'avg_price', 'created_by', 'created_by_name', 'created_at']
        read_only_fields = ['id', 'created_by', 'created_at']
    
    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class MedListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for medication lists."""
    
    class Meta:
        model = Med
        fields = ['id', 'name', 'avg_price']


class PatientMedSerializer(serializers.ModelSerializer):
    """Serializer for PatientMed model."""
    
    patient_name = serializers.CharField(source='patient.name', read_only=True)
    patient_email = serializers.CharField(source='patient.email', read_only=True)
    medication_name = serializers.CharField(source='med.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.name', read_only=True)
    
    class Meta:
        model = PatientMed
        fields = [
            'id', 'patient', 'patient_name', 'patient_email',
            'med', 'medication_name', 'med_name',
            'created_by', 'created_by_name', 'created_at'
        ]
        read_only_fields = ['id', 'created_by', 'created_at']
    
    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        # Auto-set patient to current user if not provided and user is a patient
        if 'patient' not in validated_data:
            validated_data['patient'] = self.context['request'].user
        return super().create(validated_data)


class PatientMedCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating patient medication records."""
    
    class Meta:
        model = PatientMed
        fields = ['patient', 'med', 'med_name']
        extra_kwargs = {
            'patient': {'required': False},
            'med': {'required': False},
            'med_name': {'required': False},
        }
    
    def validate(self, attrs):
        # Ensure at least med or med_name is provided
        if not attrs.get('med') and not attrs.get('med_name'):
            raise serializers.ValidationError({
                'med': 'Either med or med_name must be provided.'
            })
        return attrs
    
    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        if 'patient' not in validated_data:
            validated_data['patient'] = self.context['request'].user
        return super().create(validated_data)


class PatientMedListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for patient medication lists."""
    
    patient_name = serializers.CharField(source='patient.name', read_only=True)
    medication_name = serializers.SerializerMethodField()
    
    class Meta:
        model = PatientMed
        fields = ['id', 'patient', 'patient_name', 'med', 'medication_name', 'created_at']
    
    def get_medication_name(self, obj):
        return obj.med_name or (obj.med.name if obj.med else None)




