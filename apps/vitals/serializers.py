from rest_framework import serializers
from .models import Vital, BabyVital, VitalAttachment, PatientVital, PatientVitalAttachment
from apps.recordings.utils import generate_presigned_url


# ============================================================================
# VITAL ATTACHMENT SERIALIZER
# ============================================================================

class VitalAttachmentSerializer(serializers.ModelSerializer):
    """Serializer for vital attachments."""
    url = serializers.SerializerMethodField()
    display_name = serializers.SerializerMethodField()
    
    class Meta:
        model = VitalAttachment
        fields = ['id', 'name', 'display_name', 'file_type', 'created_at', 'url']
        
    def get_url(self, obj):
        # Generate presigned URL for B2 file
        return generate_presigned_url(obj.name)
    
    def get_display_name(self, obj):
        """Extract the original filename from the B2 stored name.
        
        B2 name format: vital_{id}_att_{timestamp}_{original_name}
        We want to return just the original_name part.
        """
        if not obj.name:
            return None
        
        # Split by underscore and find where the original name starts
        # Format: vital_123_att_1768003006_sample-local-pdf.pdf
        parts = obj.name.split('_')
        if len(parts) >= 5:
            # Skip first 4 parts: vital, {id}, att, {timestamp}
            original_name = '_'.join(parts[4:])
            return original_name
        return obj.name


# ============================================================================
# VITAL SERIALIZERS (Mother's vitals)
# ============================================================================

class VitalSerializer(serializers.ModelSerializer):
    """Serializer for Vital model - detailed view."""
    
    # Patient info from pregnancy
    patient_id = serializers.SerializerMethodField()
    patient_name = serializers.SerializerMethodField()
    patient_email = serializers.SerializerMethodField()
    
    # Pregnancy info
    pregnancy_week = serializers.SerializerMethodField()
    
    # Visit info
    visit_id = serializers.IntegerField(source='visit.id', read_only=True)
    visit_time = serializers.DateTimeField(source='visit.time', read_only=True)
    
    class Meta:
        model = Vital
        fields = [
            'id', 'pregnancy', 'pregnancy_week', 'visit', 'visit_id', 'visit_time',
            'patient_id', 'patient_name', 'patient_email',
            'systolic', 'diastolic', 'o2', 'puls', 'temp', 'weight', 'sugar_level',
            'reading_date', 'files', 'mood', 'note', 'dr_note', 
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
    
    def get_pregnancy_week(self, obj):
        if obj.pregnancy:
            return obj.pregnancy.pregnancy_week
        return None


class VitalListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for vital lists."""
    
    patient_name = serializers.SerializerMethodField()
    patient_id = serializers.SerializerMethodField()
    pregnancy_week = serializers.SerializerMethodField()
    attachments = VitalAttachmentSerializer(many=True, read_only=True)
    visit_attachments = serializers.SerializerMethodField()
    
    class Meta:
        model = Vital
        fields = [
            'id', 'pregnancy', 'pregnancy_week', 'visit',
            'patient_id', 'patient_name',
            'systolic', 'diastolic', 'o2', 'puls', 'temp', 'weight', 'sugar_level',
            'reading_date', 'mood', 'note', 'dr_note', 'files', 'attachments', 'visit_attachments'
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
    
    def get_visit_attachments(self, obj):
        """Get attachments from the related visit with presigned URLs."""
        if obj.visit:
            from apps.visits.serializers import VisitAttachmentSerializer
            attachments = obj.visit.attachments.all()
            return VisitAttachmentSerializer(attachments, many=True).data
        return []



class VitalCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a vital record."""
    
    uploaded_files = serializers.ListField(
        child=serializers.FileField(),
        write_only=True,
        required=False
    )
    
    class Meta:
        model = Vital
        fields = [
            'pregnancy', 'visit',
            'systolic', 'diastolic', 'o2', 'puls', 'temp', 'weight', 'sugar_level',
            'reading_date', 'files', 'mood', 'note', 'dr_note', 'uploaded_files'
        ]
        extra_kwargs = {
            'pregnancy': {'required': True},
            'visit': {'required': False},
            'files': {'required': False},
            'reading_date': {'required': False},
        }
    
    def create(self, validated_data):
        uploaded_files = validated_data.pop('uploaded_files', [])
        
        # Upload files to Cloudinary if present
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
            'systolic', 'diastolic', 'o2', 'puls', 'temp', 'weight', 'sugar_level',
            'reading_date', 'files', 'mood', 'note', 'dr_note', 'uploaded_files'
        ]
    
    def update(self, instance, validated_data):
        uploaded_files = validated_data.pop('uploaded_files', [])
        
        if uploaded_files:
            from apps.vitals.utils import upload_files_to_cloudinary
            file_urls = upload_files_to_cloudinary(uploaded_files)
            existing_files = instance.files or []
            validated_data['files'] = existing_files + file_urls
        
        return super().update(instance, validated_data)


# ============================================================================
# BABY VITAL SERIALIZERS
# ============================================================================

class BabyVitalSerializer(serializers.ModelSerializer):
    """Serializer for BabyVital model - detailed view."""
    
    # Baby info
    baby_name = serializers.CharField(source='baby.name', read_only=True)
    baby_gender = serializers.CharField(source='baby.gender', read_only=True)
    
    # Parent/Patient info
    patient_id = serializers.SerializerMethodField()
    patient_name = serializers.SerializerMethodField()
    
    # Pregnancy info
    pregnancy_id = serializers.SerializerMethodField()
    pregnancy_week = serializers.SerializerMethodField()
    
    # Visit info
    visit_id = serializers.IntegerField(source='visit.id', read_only=True)
    visit_time = serializers.DateTimeField(source='visit.time', read_only=True)
    
    class Meta:
        model = BabyVital
        fields = [
            'id', 'baby', 'baby_name', 'baby_gender', 'visit', 'visit_id', 'visit_time',
            'pregnancy_id', 'pregnancy_week',
            'patient_id', 'patient_name',
            'puls', 'systolic', 'diastolic', 'o2', 'weight', 'age',
            'note', 'reading_date', 'files', 'due_date',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_patient_id(self, obj):
        if obj.baby and obj.baby.pregnancy:
            return obj.baby.pregnancy.patient.id
        elif obj.parent:
            return obj.parent.id
        return None
    
    def get_patient_name(self, obj):
        if obj.baby and obj.baby.pregnancy:
            return obj.baby.pregnancy.patient.name
        elif obj.parent:
            return obj.parent.name
        return None
    
    def get_pregnancy_id(self, obj):
        if obj.baby:
            return obj.baby.pregnancy.id
        return None
    
    def get_pregnancy_week(self, obj):
        if obj.baby and obj.baby.pregnancy:
            return obj.baby.pregnancy.pregnancy_week
        return None


class BabyVitalListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for baby vital lists."""
    
    baby_name = serializers.CharField(source='baby.name', read_only=True)
    patient_name = serializers.SerializerMethodField()
    pregnancy_id = serializers.SerializerMethodField()
    visit_attachments = serializers.SerializerMethodField()
    
    class Meta:
        model = BabyVital
        fields = [
            'id', 'baby', 'baby_name', 'visit',
            'pregnancy_id', 'patient_name',
            'puls', 'systolic', 'diastolic', 'o2', 'weight', 'age',
            'reading_date', 'due_date', 'note', 'files', 'visit_attachments'
        ]
    
    def get_patient_name(self, obj):
        if obj.baby and obj.baby.pregnancy:
            return obj.baby.pregnancy.patient.name
        elif obj.parent:
            return obj.parent.name
        return None
    
    def get_pregnancy_id(self, obj):
        if obj.baby:
            return obj.baby.pregnancy.id
        return None

    def get_visit_attachments(self, obj):
        """Get attachments from the related visit with presigned URLs."""
        if obj.visit:
            from apps.visits.serializers import VisitAttachmentSerializer
            attachments = obj.visit.attachments.all()
            return VisitAttachmentSerializer(attachments, many=True).data
        return []


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
            'baby', 'visit',
            'puls', 'systolic', 'diastolic', 'o2', 'weight', 'age',
            'note', 'reading_date', 'files', 'due_date', 'uploaded_files'
        ]
        extra_kwargs = {
            'baby': {'required': True},
            'visit': {'required': False},
            'files': {'required': False},
            'reading_date': {'required': False},
        }
    
    def create(self, validated_data):
        uploaded_files = validated_data.pop('uploaded_files', [])
        
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


# ============================================================================
# PATIENT VITAL SERIALIZERS (Patient-level vitals, independent of pregnancy)
# ============================================================================

class PatientVitalAttachmentSerializer(serializers.ModelSerializer):
    """Serializer for patient vital attachments."""
    url = serializers.SerializerMethodField()
    display_name = serializers.SerializerMethodField()

    class Meta:
        model = PatientVitalAttachment
        fields = ['id', 'name', 'display_name', 'file_type', 'created_at', 'url']

    def get_url(self, obj):
        return generate_presigned_url(obj.name)

    def get_display_name(self, obj):
        """Extract the original filename from the B2 stored name.

        B2 name format: patient_vital_{id}_att_{timestamp}_{original_name}
        """
        if not obj.name:
            return None

        parts = obj.name.split('_')
        if len(parts) >= 6:
            # Skip first 5 parts: patient, vital, {id}, att, {timestamp}
            original_name = '_'.join(parts[5:])
            return original_name
        return obj.name


class PatientVitalSerializer(serializers.ModelSerializer):
    """Serializer for PatientVital model - detailed view."""

    # Patient info
    patient_name = serializers.CharField(source='patient.name', read_only=True)
    patient_email = serializers.EmailField(source='patient.email', read_only=True)
    patient_phone = serializers.CharField(source='patient.phone', read_only=True)

    # Visit info
    visit_id = serializers.IntegerField(source='visit.id', read_only=True)
    visit_time = serializers.DateTimeField(source='visit.time', read_only=True)

    # Attachments
    attachments = PatientVitalAttachmentSerializer(many=True, read_only=True)

    class Meta:
        model = PatientVital
        fields = [
            'id', 'patient', 'patient_name', 'patient_email', 'patient_phone',
            'visit', 'visit_id', 'visit_time',
            'systolic', 'diastolic', 'o2', 'puls', 'temp', 'weight', 'sugar_level',
            'reading_date', 'files', 'mood', 'note', 'dr_note',
            'attachments', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class PatientVitalListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for patient vital lists."""

    patient_name = serializers.CharField(source='patient.name', read_only=True)
    patient_id = serializers.IntegerField(source='patient.id', read_only=True)
    attachments = PatientVitalAttachmentSerializer(many=True, read_only=True)
    visit_attachments = serializers.SerializerMethodField()

    class Meta:
        model = PatientVital
        fields = [
            'id', 'patient', 'patient_id', 'patient_name', 'visit',
            'systolic', 'diastolic', 'o2', 'puls', 'temp', 'weight', 'sugar_level',
            'reading_date', 'mood', 'note', 'dr_note', 'files',
            'attachments', 'visit_attachments'
        ]

    def get_visit_attachments(self, obj):
        """Get attachments from the related visit with presigned URLs."""
        if obj.visit:
            from apps.visits.serializers import VisitAttachmentSerializer
            attachments = obj.visit.attachments.all()
            return VisitAttachmentSerializer(attachments, many=True).data
        return []


class PatientVitalCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a patient vital record."""

    uploaded_files = serializers.ListField(
        child=serializers.FileField(),
        write_only=True,
        required=False
    )

    class Meta:
        model = PatientVital
        fields = [
            'patient', 'visit',
            'systolic', 'diastolic', 'o2', 'puls', 'temp', 'weight', 'sugar_level',
            'reading_date', 'files', 'mood', 'note', 'dr_note', 'uploaded_files'
        ]
        extra_kwargs = {
            'patient': {'required': True},
            'visit': {'required': False},
            'files': {'required': False},
            'reading_date': {'required': False},
        }

    def validate_patient(self, value):
        """Ensure patient is actually a patient user."""
        if value.user_type != 'patient':
            raise serializers.ValidationError('The specified user is not a patient.')
        return value

    def create(self, validated_data):
        uploaded_files = validated_data.pop('uploaded_files', [])

        if uploaded_files:
            from apps.vitals.utils import upload_files_to_cloudinary
            file_urls = upload_files_to_cloudinary(uploaded_files)
            validated_data['files'] = file_urls

        return super().create(validated_data)


class PatientVitalUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating a patient vital record."""

    uploaded_files = serializers.ListField(
        child=serializers.FileField(),
        write_only=True,
        required=False
    )

    class Meta:
        model = PatientVital
        fields = [
            'systolic', 'diastolic', 'o2', 'puls', 'temp', 'weight', 'sugar_level',
            'reading_date', 'files', 'mood', 'note', 'dr_note', 'uploaded_files'
        ]

    def update(self, instance, validated_data):
        uploaded_files = validated_data.pop('uploaded_files', [])

        if uploaded_files:
            from apps.vitals.utils import upload_files_to_cloudinary
            file_urls = upload_files_to_cloudinary(uploaded_files)
            existing_files = instance.files or []
            validated_data['files'] = existing_files + file_urls

        return super().update(instance, validated_data)
