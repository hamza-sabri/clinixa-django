from rest_framework import serializers
from .models import Vital, BabyVital


class VitalSerializer(serializers.ModelSerializer):
    """Serializer for Vital model."""
    
    patient_name = serializers.CharField(source='patient.name', read_only=True)
    patient_email = serializers.CharField(source='patient.email', read_only=True)
    
    class Meta:
        model = Vital
        fields = [
            'id', 'patient', 'patient_name', 'patient_email',
            'systolic', 'diastolic', 'o2', 'puls', 'temp', 'weight',
            'reading_date', 'files', 'mood', 'note', 'dr_note', 'created_at'
        ]
        read_only_fields = ['id', 'patient', 'created_at']


class VitalCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a vital record."""
    
    # Accept file uploads
    uploaded_files = serializers.ListField(
        child=serializers.FileField(),
        write_only=True,
        required=False
    )
    
    class Meta:
        model = Vital
        fields = [
            'systolic', 'diastolic', 'o2', 'puls', 'temp', 'weight',
            'reading_date', 'files', 'mood', 'note', 'dr_note', 'uploaded_files'
        ]
        extra_kwargs = {
            'files': {'required': False},
        }
    
    def create(self, validated_data):
        # Handle file uploads if present
        uploaded_files = validated_data.pop('uploaded_files', [])
        validated_data['patient'] = self.context['request'].user
        
        # Upload files to Cloudinary
        if uploaded_files:
            from apps.vitals.utils import upload_files_to_cloudinary
            file_urls = upload_files_to_cloudinary(uploaded_files)
            validated_data['files'] = file_urls
        
        return super().create(validated_data)


class VitalUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating a vital record."""
    
    uploaded_files = serializers.ListField(
        child=serializers.FileField(),
        write_only=True,
        required=False
    )
    
    class Meta:
        model = Vital
        fields = [
            'systolic', 'diastolic', 'o2', 'puls', 'temp', 'weight',
            'reading_date', 'files', 'mood', 'note', 'dr_note', 'uploaded_files'
        ]
    
    def update(self, instance, validated_data):
        # Handle file uploads if present
        uploaded_files = validated_data.pop('uploaded_files', [])
        
        if uploaded_files:
            from apps.vitals.utils import upload_files_to_cloudinary
            file_urls = upload_files_to_cloudinary(uploaded_files)
            # Append new files to existing ones
            existing_files = instance.files or []
            validated_data['files'] = existing_files + file_urls
        
        return super().update(instance, validated_data)


class VitalListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for vital lists."""
    
    patient_name = serializers.CharField(source='patient.name', read_only=True)
    
    class Meta:
        model = Vital
        fields = [
            'id', 'patient', 'patient_name', 'systolic', 'diastolic',
            'o2', 'puls', 'temp', 'weight', 'reading_date', 'mood'
        ]


# Baby Vital Serializers

class BabyVitalSerializer(serializers.ModelSerializer):
    """Serializer for BabyVital model."""
    
    parent_name = serializers.CharField(source='parent.name', read_only=True)
    parent_email = serializers.CharField(source='parent.email', read_only=True)
    
    class Meta:
        model = BabyVital
        fields = [
            'id', 'parent', 'parent_name', 'parent_email',
            'puls', 'systolic', 'diastolic', 'o2', 'weight', 'age',
            'note', 'reading_date', 'files', 'due_date', 'created_at'
        ]
        read_only_fields = ['id', 'parent', 'created_at']


class BabyVitalCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a baby vital record."""
    
    uploaded_files = serializers.ListField(
        child=serializers.FileField(),
        write_only=True,
        required=False
    )
    
    class Meta:
        model = BabyVital
        fields = [
            'puls', 'systolic', 'diastolic', 'o2', 'weight', 'age',
            'note', 'reading_date', 'files', 'due_date', 'uploaded_files'
        ]
        extra_kwargs = {
            'files': {'required': False},
        }
    
    def create(self, validated_data):
        uploaded_files = validated_data.pop('uploaded_files', [])
        validated_data['parent'] = self.context['request'].user
        
        if uploaded_files:
            from apps.vitals.utils import upload_files_to_cloudinary
            file_urls = upload_files_to_cloudinary(uploaded_files)
            validated_data['files'] = file_urls
        
        return super().create(validated_data)


class BabyVitalUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating a baby vital record."""
    
    uploaded_files = serializers.ListField(
        child=serializers.FileField(),
        write_only=True,
        required=False
    )
    
    class Meta:
        model = BabyVital
        fields = [
            'puls', 'systolic', 'diastolic', 'o2', 'weight', 'age',
            'note', 'reading_date', 'files', 'due_date', 'uploaded_files'
        ]
    
    def update(self, instance, validated_data):
        uploaded_files = validated_data.pop('uploaded_files', [])
        
        if uploaded_files:
            from apps.vitals.utils import upload_files_to_cloudinary
            file_urls = upload_files_to_cloudinary(uploaded_files)
            existing_files = instance.files or []
            validated_data['files'] = existing_files + file_urls
        
        return super().update(instance, validated_data)


class BabyVitalListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for baby vital lists."""
    
    parent_name = serializers.CharField(source='parent.name', read_only=True)
    
    class Meta:
        model = BabyVital
        fields = [
            'id', 'parent', 'parent_name', 'puls', 'systolic', 'diastolic',
            'o2', 'weight', 'age', 'reading_date', 'due_date'
        ]


