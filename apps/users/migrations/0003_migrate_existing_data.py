"""
Data migration to convert existing patient data to the new pregnancy-centric architecture.

This migration:
1. Creates PatientProfile for each patient user
2. Creates a default Pregnancy for each patient profile
3. Creates a default Baby for each pregnancy (if they have baby vitals)
4. Links existing Visits to the pregnancy
5. Links existing Vitals to the pregnancy
6. Links existing BabyVitals to the baby
"""
from django.db import migrations


def migrate_existing_data(apps, schema_editor):
    """Forward migration: Create profiles and link existing data."""
    User = apps.get_model('users', 'User')
    PatientProfile = apps.get_model('users', 'PatientProfile')
    Pregnancy = apps.get_model('users', 'Pregnancy')
    Baby = apps.get_model('users', 'Baby')
    Visit = apps.get_model('visits', 'Visit')
    Vital = apps.get_model('vitals', 'Vital')
    BabyVital = apps.get_model('vitals', 'BabyVital')
    
    # Get all patient users
    patient_users = User.objects.filter(user_type='patient')
    
    for user in patient_users:
        # Create or get PatientProfile
        profile, created = PatientProfile.objects.get_or_create(
            user=user,
            defaults={
                'blood_type': '',
                'allergies': '',
                'medical_history': '',
                'notes': ''
            }
        )
        
        # Check if this user has any visits, vitals, or baby vitals
        has_visits = Visit.objects.filter(patient=user).exists()
        has_vitals = Vital.objects.filter(patient=user).exists()
        has_baby_vitals = BabyVital.objects.filter(parent=user).exists()
        
        # Only create pregnancy if user has data to migrate
        if has_visits or has_vitals or has_baby_vitals:
            # Create default pregnancy
            pregnancy = Pregnancy.objects.create(
                patient_profile=profile,
                status='ongoing',
                notes='Migrated from legacy data'
            )
            
            # Link existing visits to pregnancy
            Visit.objects.filter(patient=user).update(pregnancy=pregnancy)
            
            # Link existing vitals to pregnancy
            Vital.objects.filter(patient=user).update(pregnancy=pregnancy)
            
            # If has baby vitals, create a default baby and link them
            if has_baby_vitals:
                baby = Baby.objects.create(
                    pregnancy=pregnancy,
                    name='',
                    gender='unknown',
                    is_born=False,
                    notes='Migrated from legacy data'
                )
                
                # Link existing baby vitals to baby
                BabyVital.objects.filter(parent=user).update(baby=baby)


def reverse_migration(apps, schema_editor):
    """Reverse migration: Nothing to do as we keep old FKs intact."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0002_patientprofile_pregnancy_baby'),
        ('visits', '0002_visit_pregnancy_alter_visit_patient'),
        ('vitals', '0002_babyvital_baby_babyvital_visit_vital_pregnancy_and_more'),
    ]

    operations = [
        migrations.RunPython(migrate_existing_data, reverse_migration),
    ]

