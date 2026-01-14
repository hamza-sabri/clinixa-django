from django.db import models
from django.conf import settings


class Vital(models.Model):
    """
    Vital signs record for a patient (mother).
    Now linked to Pregnancy instead of directly to patient.
    Can optionally be linked to a specific visit.
    """
    
    # NEW: Link to pregnancy (will be required after data migration)
    pregnancy = models.ForeignKey(
        'users.Pregnancy',
        on_delete=models.CASCADE,
        related_name='vitals',
        verbose_name='pregnancy',
        null=True,  # Temporary: nullable for migration
        blank=True
    )
    # NEW: Optional link to a specific visit
    visit = models.OneToOneField(
        'visits.Visit',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='vital',
        verbose_name='visit'
    )
    # DEPRECATED: Will be removed after data migration
    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='vitals',
        verbose_name='patient (deprecated)',
        null=True,  # Make nullable for transition
        blank=True
    )
    systolic = models.IntegerField('systolic pressure', null=True, blank=True)
    diastolic = models.IntegerField('diastolic pressure', null=True, blank=True)
    o2 = models.IntegerField('oxygen saturation', null=True, blank=True)
    puls = models.IntegerField('pulse rate', null=True, blank=True)
    temp = models.FloatField('temperature', null=True, blank=True)
    weight = models.FloatField('weight (kg)', null=True, blank=True)
    sugar_level = models.IntegerField(
        'blood glucose level',
        null=True,
        blank=True,
        help_text='Blood glucose level in mg/dL'
    )
    reading_date = models.DateTimeField('reading date', null=True, blank=True)
    files = models.JSONField('attached files', default=list, blank=True)  # Array of Cloudinary URLs
    mood = models.CharField('mood', max_length=100, blank=True)
    note = models.TextField('patient note', blank=True)
    dr_note = models.TextField('doctor note', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'vital'
        verbose_name_plural = 'vitals'
        ordering = ['-reading_date', '-created_at']
    
    def __str__(self):
        if self.pregnancy:
            patient = self.pregnancy.patient
            return f"{patient.name or patient.email} - {self.reading_date or self.created_at}"
        elif self.patient:
            return f"{self.patient.name or self.patient.email} - {self.reading_date or self.created_at}"
        return f"Vital - {self.reading_date or self.created_at}"
    
    @property
    def patient_user(self):
        """Get the patient user from pregnancy or legacy patient field."""
        if self.pregnancy:
            return self.pregnancy.patient
        return self.patient


class BabyVital(models.Model):
    """
    Vital signs record for baby/pregnancy tracking.
    Now linked to Baby instead of directly to parent.
    Can optionally be linked to a specific visit.
    """
    
    # NEW: Link to specific baby (will be required after data migration)
    baby = models.ForeignKey(
        'users.Baby',
        on_delete=models.CASCADE,
        related_name='vitals',
        verbose_name='baby',
        null=True,  # Temporary: nullable for migration
        blank=True
    )
    # NEW: Optional link to a specific visit
    visit = models.ForeignKey(
        'visits.Visit',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='baby_vitals',
        verbose_name='visit'
    )
    # DEPRECATED: Will be removed after data migration
    parent = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='baby_vitals',
        verbose_name='parent (deprecated)',
        null=True,  # Make nullable for transition
        blank=True
    )
    puls = models.IntegerField('pulse rate', null=True, blank=True)
    systolic = models.IntegerField('systolic pressure', null=True, blank=True)
    diastolic = models.IntegerField('diastolic pressure', null=True, blank=True)
    o2 = models.FloatField('oxygen saturation', null=True, blank=True)
    weight = models.FloatField('weight (kg)', null=True, blank=True)
    age = models.CharField('age', max_length=50, blank=True)
    note = models.TextField('note', blank=True)
    reading_date = models.DateTimeField('reading date', null=True, blank=True)
    files = models.JSONField('attached files', default=list, blank=True)  # Array of Cloudinary URLs
    due_date = models.DateField('due date', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'baby vital'
        verbose_name_plural = 'baby vitals'
        ordering = ['-reading_date', '-created_at']
    
    def __str__(self):
        if self.baby:
            pregnancy = self.baby.pregnancy
            patient = pregnancy.patient
            return f"{patient.name or patient.email} - Baby {self.baby.name or 'unnamed'} - {self.reading_date or self.created_at}"
        elif self.parent:
            return f"{self.parent.name or self.parent.email} - Baby - {self.reading_date or self.created_at}"
        return f"Baby Vital - {self.reading_date or self.created_at}"
    
    @property
    def patient_user(self):
        """Get the parent/patient user from baby or legacy parent field."""
        if self.baby:
            return self.baby.pregnancy.patient
        return self.parent
    
    @property
    def pregnancy(self):
        """Get pregnancy from baby."""
        if self.baby:
            return self.baby.pregnancy
        return None




class VitalAttachment(models.Model):
    """
    Attachments for a vital record (e.g. lab results, x-rays, etc.)
    Files are stored in Backblaze B2.
    """
    vital = models.ForeignKey(
        Vital,
        on_delete=models.CASCADE,
        related_name='attachments',
        verbose_name='vital'
    )
    name = models.CharField('file name', max_length=255)
    file_id = models.CharField('b2 file id', max_length=200)  # Store B2 file ID for secure access
    file_type = models.CharField('file type', max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.vital})"


class PatientVital(models.Model):
    """
    Patient-level vital signs record, independent of pregnancy.
    Linked directly to User (patient) instead of Pregnancy.
    Used when doctors need to track vitals for patients who are not pregnant.
    """

    # Link to patient (User)
    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='patient_vitals',
        verbose_name='patient'
    )
    # Track who created this vital record
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_patient_vitals',
        verbose_name='created by'
    )
    # Optional link to a specific visit
    visit = models.ForeignKey(
        'visits.Visit',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='patient_vitals',
        verbose_name='visit'
    )
    # Vital measurements (same as Vital model)
    systolic = models.IntegerField('systolic pressure', null=True, blank=True)
    diastolic = models.IntegerField('diastolic pressure', null=True, blank=True)
    o2 = models.IntegerField('oxygen saturation', null=True, blank=True)
    puls = models.IntegerField('pulse rate', null=True, blank=True)
    temp = models.FloatField('temperature', null=True, blank=True)
    weight = models.FloatField('weight (kg)', null=True, blank=True)
    sugar_level = models.IntegerField(
        'blood glucose level',
        null=True,
        blank=True,
        help_text='Blood glucose level in mg/dL'
    )
    reading_date = models.DateTimeField('reading date', null=True, blank=True)
    files = models.JSONField('attached files', default=list, blank=True)  # Array of Cloudinary URLs
    mood = models.CharField('mood', max_length=100, blank=True)
    note = models.TextField('patient note', blank=True)
    dr_note = models.TextField('doctor note', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'patient vital'
        verbose_name_plural = 'patient vitals'
        ordering = ['-reading_date', '-created_at']

    def __str__(self):
        return f"{self.patient.name or self.patient.email} - {self.reading_date or self.created_at}"


class PatientVitalAttachment(models.Model):
    """
    Attachments for a patient vital record (e.g. lab results, x-rays, etc.)
    Files are stored in Backblaze B2.
    """
    patient_vital = models.ForeignKey(
        PatientVital,
        on_delete=models.CASCADE,
        related_name='attachments',
        verbose_name='patient vital'
    )
    name = models.CharField('file name', max_length=255)
    file_id = models.CharField('b2 file id', max_length=200)  # Store B2 file ID for secure access
    file_type = models.CharField('file type', max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.patient_vital})"
