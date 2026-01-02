from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.clinics.models import Clinic
from apps.visits.models import Visit
from apps.users.models import PatientProfile, Pregnancy
from django.utils import timezone
from datetime import timedelta, time, datetime
import random

User = get_user_model()

class Command(BaseCommand):
    help = 'Seed database with initial clinic and patient data'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting data seeding...'))

        # 1. Backfill ALL existing clinics with working hours
        self.stdout.write('Checking all existing clinics for missing data...')
        clinics = Clinic.objects.all()
        updated_count = 0
        
        default_working_hours = {
            "monday": {"open": "09:00", "close": "17:00"},
            "tuesday": {"open": "09:00", "close": "17:00"},
            "wednesday": {"open": "09:00", "close": "14:00"},
            "thursday": {"open": "09:00", "close": "17:00"},
            "friday": {"open": "10:00", "close": "14:00"},
            "saturday": {"open": "10:00", "close": "14:00"}, # Added Weekend
            "sunday": {"open": "09:00", "close": "17:00"},   # Added Weekend
        }

        for clinic in clinics:
            # Force update working hours to include weekends for testing
            clinic.working_hours = default_working_hours
            
            # Set slot duration if missing or 0
            if not clinic.slot_duration:
                clinic.slot_duration = 30
            
            # Set default location if missing
            if not clinic.latitude:
                clinic.latitude = 25.2048 + (random.random() * 0.1)  # Random spot in Dubai
                clinic.longitude = 55.2708 + (random.random() * 0.1)
                
            clinic.save()
            updated_count += 1

        self.stdout.write(f'Finished config update. Updated {updated_count} clinics with 7-day working hours.')

        # ... (User/Doctor creation logic stays same) ...

        # 4. Generate Random Visits (Bookings)
        self.stdout.write('Generating random bookings for the next 30 days...')
        
        # Get a patient to book appointments for (create a generic test patient if needed)
        test_patient, _ = User.objects.get_or_create(
            phone='+971509998888',
            defaults={'name': 'Test Patient Generics', 'user_type': 'patient'}
        )
        # Ensure profile exists
        if not hasattr(test_patient, 'patient_profile'):
             profile = PatientProfile.objects.create(user=test_patient, blood_type='O+')
             Pregnancy.objects.create(
                patient_profile=profile,
                lmp=timezone.now().date() - timedelta(weeks=20),
                due_date=timezone.now().date() + timedelta(weeks=20),
                status='ongoing'
            )
        
        test_pregnancy = test_patient.patient_profile.pregnancies.first()
        
        start_date = timezone.now().date()
        date_list = [start_date + timedelta(days=x) for x in range(30)]
        
        bookings_created = 0
        
        for clinic in clinics:
            # For each day in the next 30 days
            for date in date_list:
                day_name = date.strftime('%A').lower()
                hours = clinic.working_hours.get(day_name)
                
                if not hours:
                    continue
                    
                open_time = datetime.strptime(hours['open'], '%H:%M')
                close_time = datetime.strptime(hours['close'], '%H:%M')
                
                # Generate slots for this day
                current = open_time
                day_slots = []
                while current < close_time:
                    day_slots.append(current)
                    current += timedelta(minutes=clinic.slot_duration)
                
                # Randomly book 30-50% of slots per day
                slots_to_book = random.sample(day_slots, k=int(len(day_slots) * random.uniform(0.3, 0.5)))
                
                for slot_time in slots_to_book:
                    visit_datetime = timezone.make_aware(datetime.combine(date, slot_time.time()))
                    
                    # Create visit if not exists
                    if not Visit.objects.filter(clinic=clinic, time=visit_datetime).exists():
                        Visit.objects.create(
                            patient=test_patient,
                            clinic=clinic,
                            pregnancy=test_pregnancy,
                            time=visit_datetime,
                            status=random.choice(['مؤكد', 'جاري التأكيد', 'مكتمل']),
                            note='Randomly generated test visit'
                        )
                        bookings_created += 1
        
        self.stdout.write(self.style.SUCCESS(f'Data seeding completed! Created {bookings_created} new bookings across all clinics.'))
