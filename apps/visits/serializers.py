from rest_framework import serializers
from django.utils import timezone

from .models import Visit
from .models import Visit, VisitAttachment
from apps.clinics.serializers import ClinicListSerializer
from apps.recordings.utils import generate_presigned_url



class VisitAttachmentSerializer(serializers.ModelSerializer):
    """Serializer for visit attachments."""
    url = serializers.SerializerMethodField()
    display_name = serializers.SerializerMethodField()
    
    class Meta:
        model = VisitAttachment
        fields = ['id', 'name', 'display_name', 'file_type', 'created_at', 'url']
        
    def get_url(self, obj):
        # We assume 'name' stores the B2 file name (key)
        return generate_presigned_url(obj.name)
    
    def get_display_name(self, obj):
        """Extract the original filename from the B2 stored name.
        
        B2 name format: visit_{id}_att_{timestamp}_{original_name}
        We want to return just the original_name part.
        """
        if not obj.name:
            return None
        
        # Split by underscore and find where the original name starts
        # Format: visit_1825_att_1768003006_sample-local-pdf.pdf
        parts = obj.name.split('_')
        if len(parts) >= 5:
            # Skip first 4 parts: visit, {id}, att, {timestamp}
            original_name = '_'.join(parts[4:])
            return original_name
        return obj.name


class VisitSerializer(serializers.ModelSerializer):
    """Serializer for Visit model - detailed view."""
    
    # Patient info from pregnancy
    patient_id = serializers.SerializerMethodField()
    patient_name = serializers.SerializerMethodField()
    patient_email = serializers.SerializerMethodField()
    patient_phone = serializers.SerializerMethodField()
    
    # Pregnancy info
    pregnancy_week = serializers.SerializerMethodField()
    pregnancy_status = serializers.CharField(source='pregnancy.status', read_only=True)
    
    # Clinic info
    clinic_name = serializers.CharField(source='clinic.name', read_only=True)
    clinic_location = serializers.CharField(source='clinic.location', read_only=True)
    
    # Vitals attached to this visit
    has_vital = serializers.SerializerMethodField()
    # Vitals attached to this visit
    has_vital = serializers.SerializerMethodField()
    baby_vitals_count = serializers.SerializerMethodField()
    recording_url = serializers.SerializerMethodField()
    
    # Attachments
    attachments = VisitAttachmentSerializer(many=True, read_only=True)
    
    class Meta:
        model = Visit
        fields = [
            'id', 'clinic', 'clinic_name', 'clinic_location',
            'pregnancy', 'pregnancy_week', 'pregnancy_status',
            'patient_id', 'patient_name', 'patient_email', 'patient_phone',
            'time', 'status', 'note', 'urgency',
            'has_vital', 'baby_vitals_count',
            'recording_url', 'attachments',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_patient_id(self, obj):
        if obj.pregnancy:
            return obj.pregnancy.patient.id
        elif obj.patient:
            return obj.patient.id
        return None
    
    def get_patient_name(self, obj):
        if obj.pregnancy:
            return obj.pregnancy.patient.name
        elif obj.patient:
            return obj.patient.name
        return None
    
    def get_patient_email(self, obj):
        if obj.pregnancy:
            return obj.pregnancy.patient.email
        elif obj.patient:
            return obj.patient.email
        return None
    
    def get_patient_phone(self, obj):
        if obj.pregnancy:
            return obj.pregnancy.patient.phone
        elif obj.patient:
            return obj.patient.phone
        return None
    
    def get_pregnancy_week(self, obj):
        if obj.pregnancy:
            return obj.pregnancy.pregnancy_week
        return None
    
    def get_has_vital(self, obj):
        return hasattr(obj, 'vital') and obj.vital is not None
    
    def get_baby_vitals_count(self, obj):
        return obj.baby_vitals.count()

    def get_recording_url(self, obj):
        if obj.recording_url:
            return generate_presigned_url(obj.recording_url)
        return None


class VisitListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for visit lists."""
    
    patient_name = serializers.SerializerMethodField()
    patient_id = serializers.SerializerMethodField()
    clinic_name = serializers.CharField(source='clinic.name', read_only=True)
    pregnancy_week = serializers.SerializerMethodField()
    
    class Meta:
        model = Visit
        fields = [
            'id', 'clinic', 'clinic_name', 
            'pregnancy', 'pregnancy_week',
            'patient_id', 'patient_name', 
            'time', 'status', 'urgency'
        ]
    
    def get_patient_name(self, obj):
        if obj.pregnancy:
            return obj.pregnancy.patient.name
        elif obj.patient:
            return obj.patient.name
        return None
    
    def get_patient_id(self, obj):
        if obj.pregnancy:
            return obj.pregnancy.patient.id
        elif obj.patient:
            return obj.patient.id
        return None
    
    def get_pregnancy_week(self, obj):
        if obj.pregnancy:
            return obj.pregnancy.pregnancy_week
        return None


# Nested vital serializers for creating vitals with visit
class NestedVitalCreateSerializer(serializers.Serializer):
    """Serializer for creating a vital record nested in visit."""
    systolic = serializers.IntegerField(required=False, allow_null=True)
    diastolic = serializers.IntegerField(required=False, allow_null=True)
    o2 = serializers.IntegerField(required=False, allow_null=True)
    puls = serializers.IntegerField(required=False, allow_null=True)
    temp = serializers.FloatField(required=False, allow_null=True)
    weight = serializers.FloatField(required=False, allow_null=True)
    mood = serializers.CharField(required=False, allow_blank=True)
    note = serializers.CharField(required=False, allow_blank=True)
    dr_note = serializers.CharField(required=False, allow_blank=True)


class NestedBabyVitalCreateSerializer(serializers.Serializer):
    """Serializer for creating a baby vital record nested in visit."""
    baby = serializers.IntegerField()  # Baby ID
    puls = serializers.IntegerField(required=False, allow_null=True)
    systolic = serializers.IntegerField(required=False, allow_null=True)
    diastolic = serializers.IntegerField(required=False, allow_null=True)
    o2 = serializers.FloatField(required=False, allow_null=True)
    weight = serializers.FloatField(required=False, allow_null=True)
    note = serializers.CharField(required=False, allow_blank=True)


class VisitCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a visit with optional vitals."""
    
    # Optional nested vitals
    vital = NestedVitalCreateSerializer(required=False, write_only=True)
    baby_vitals = NestedBabyVitalCreateSerializer(many=True, required=False, write_only=True)
    
    class Meta:
        model = Visit
        fields = ['pregnancy', 'clinic', 'time', 'status', 'note', 'urgency', 'vital', 'baby_vitals']
        extra_kwargs = {
            'pregnancy': {'required': True},
            'clinic': {'required': True},
            'time': {'required': True},
            'status': {'required': False},
            'note': {'required': False},
            'urgency': {'required': False},
        }
    
    def validate_time(self, value):
        # Allow past times for recording completed visits
        return value
    
    def validate_pregnancy(self, value):
        # Ensure pregnancy exists and is accessible
        if not value:
            raise serializers.ValidationError('Pregnancy is required.')
        return value
    
    def create(self, validated_data):
        vital_data = validated_data.pop('vital', None)
        baby_vitals_data = validated_data.pop('baby_vitals', [])
        
        # Create the visit
        visit = super().create(validated_data)
        
        # Create vital record if provided
        if vital_data:
            from apps.vitals.models import Vital
            Vital.objects.create(
                pregnancy=visit.pregnancy,
                visit=visit,
                reading_date=visit.time,
                **vital_data
            )
        
        # Create baby vital records if provided
        if baby_vitals_data:
            from apps.vitals.models import BabyVital
            from apps.users.models import Baby
            
            for bv_data in baby_vitals_data:
                baby_id = bv_data.pop('baby')
                try:
                    baby = Baby.objects.get(id=baby_id, pregnancy=visit.pregnancy)
                    BabyVital.objects.create(
                        baby=baby,
                        visit=visit,
                        reading_date=visit.time,
                        **bv_data
                    )
                except Baby.DoesNotExist:
                    pass  # Skip invalid baby IDs
        
        return visit


class VisitUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating a visit."""
    
    class Meta:
        model = Visit
        fields = ['clinic', 'time', 'status', 'note', 'urgency']
