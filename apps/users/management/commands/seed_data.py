"""
Django management command to seed the database with test data.

Usage: python manage.py seed_data
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta, date
import random

from apps.clinics.models import Clinic, Employee
from apps.visits.models import Visit
from apps.vitals.models import Vital, BabyVital
from apps.medications.models import Med, PatientMed

User = get_user_model()


class Command(BaseCommand):
    help = 'Seed the database with test data (10 doctors, clinics, employees, 100 patients, visits, etc.)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing data before seeding',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write(self.style.WARNING('Clearing existing data...'))
            PatientMed.objects.all().delete()
            Med.objects.all().delete()
            BabyVital.objects.all().delete()
            Vital.objects.all().delete()
            Visit.objects.all().delete()
            Employee.objects.all().delete()
            Clinic.objects.all().delete()
            User.objects.filter(user_type__in=['doctor', 'employee', 'patient']).delete()
            self.stdout.write(self.style.SUCCESS('Existing data cleared.'))

        self.stdout.write(self.style.SUCCESS('Starting data seeding...'))

        # Create 10 doctors with clinics
        doctors = []
        clinics = []
        for i in range(1, 11):
            doctor = User.objects.create_user(
                email=f'doctor{i}@clinixa.com',
                password='doctor123',
                name=f'Dr. {self._get_arabic_name(i)}',
                phone=f'+97150{random.randint(1000000, 9999999)}',
                user_type='doctor'
            )
            doctors.append(doctor)

            # Create clinic for each doctor
            clinic_types = ['عيادة اطفال', 'عيادة نساء', 'عيادة عامة', 'عيادة قلب', 'عيادة عيون']
            clinic = Clinic.objects.create(
                doctor=doctor,
                name=f'عيادة {self._get_arabic_name(i)}',
                location=f'Dubai, Area {chr(64+i)}',
                phone=f'+9714{random.randint(2000000, 9999999)}',
                type=random.choice(clinic_types)
            )
            clinics.append(clinic)
            self.stdout.write(f'Created doctor {i} and clinic: {clinic.name}')

        # Create employees for each clinic (1-10 random)
        all_employees = []
        employee_roles = ['nurse', 'receptionist', 'assistant', 'pharmacist', 'lab_technician', 'admin']
        
        for clinic in clinics:
            num_employees = random.randint(1, 10)
            clinic_employees = []
            
            for j in range(num_employees):
                employee_user = User.objects.create_user(
                    email=f'employee_{clinic.id}_{j+1}@clinixa.com',
                    password='employee123',
                    name=f'{self._get_arabic_name(random.randint(1, 50))} {self._get_arabic_name(random.randint(51, 100))}',
                    phone=f'+97150{random.randint(1000000, 9999999)}',
                    user_type='employee'
                )
                
                employee = Employee.objects.create(
                    staff=employee_user,
                    clinic=clinic,
                    role=random.choice(employee_roles)
                )
                clinic_employees.append(employee)
                all_employees.append(employee)
            
            self.stdout.write(f'Created {num_employees} employees for clinic {clinic.name}')

        # Create 100 patients
        patients = []
        for i in range(1, 101):
            patient = User.objects.create_user(
                email=f'patient{i}@clinixa.com',
                password='patient123',
                name=f'{self._get_arabic_name(random.randint(1, 50))} {self._get_arabic_name(random.randint(51, 100))}',
                phone=f'+97150{random.randint(1000000, 9999999)}',
                user_type='patient'
            )
            patients.append(patient)
        
        self.stdout.write(f'Created {len(patients)} patients')

        # Create visits for each clinic (15-100 random)
        visit_statuses = ['جاري التأكيد', 'مؤكد', 'مكتمل', 'ملغي']
        urgency_levels = ['عادي', 'عاجل', 'طوارئ', '']
        
        all_visits = []
        for clinic in clinics:
            num_visits = random.randint(15, 100)
            clinic_patients = random.sample(patients, min(num_visits, len(patients)))  # Different patients
            
            # Some patients visit multiple times
            if num_visits > len(clinic_patients):
                extra_visits = num_visits - len(clinic_patients)
                clinic_patients.extend(random.choices(patients, k=extra_visits))
            
            for j in range(num_visits):
                visit_time = timezone.now() - timedelta(
                    days=random.randint(0, 180),
                    hours=random.randint(0, 23),
                    minutes=random.randint(0, 59)
                )
                
                visit = Visit.objects.create(
                    clinic=clinic,
                    patient=clinic_patients[j],
                    time=visit_time,
                    status=random.choice(visit_statuses),
                    note=f'Visit note {j+1} for clinic {clinic.name}' if random.random() > 0.3 else '',
                    urgency=random.choice(urgency_levels) if random.random() > 0.5 else ''
                )
                all_visits.append(visit)
            
            self.stdout.write(f'Created {num_visits} visits for clinic {clinic.name}')

        # Create vitals for patients (some patients have multiple vitals)
        moods = ['سعيد', 'عادي', 'قلق', 'مريض', '']
        patients_with_vitals = random.sample(patients, min(80, len(patients)))  # 80% of patients have vitals
        
        for patient in patients_with_vitals:
            num_vitals = random.randint(1, 5)  # 1-5 vitals per patient
            
            for _ in range(num_vitals):
                reading_date = timezone.now() - timedelta(
                    days=random.randint(0, 90),
                    hours=random.randint(0, 23)
                )
                
                Vital.objects.create(
                    patient=patient,
                    systolic=random.randint(90, 140) if random.random() > 0.1 else None,
                    diastolic=random.randint(60, 90) if random.random() > 0.1 else None,
                    o2=random.randint(95, 100) if random.random() > 0.1 else None,
                    puls=random.randint(60, 100) if random.random() > 0.1 else None,
                    temp=round(random.uniform(36.0, 38.5), 1) if random.random() > 0.1 else None,
                    weight=round(random.uniform(50.0, 100.0), 1) if random.random() > 0.1 else None,
                    reading_date=reading_date,
                    files=[],
                    mood=random.choice(moods) if random.random() > 0.3 else '',
                    note=f'Patient note for {patient.name}' if random.random() > 0.5 else '',
                    dr_note=f'Doctor note for {patient.name}' if random.random() > 0.3 else ''
                )
        
        self.stdout.write(f'Created vitals for {len(patients_with_vitals)} patients')

        # Create baby vitals (for some patients who are parents)
        parents = random.sample(patients, min(30, len(patients)))  # 30% are parents
        
        for parent in parents:
            num_baby_vitals = random.randint(1, 3)
            
            for _ in range(num_baby_vitals):
                reading_date = timezone.now() - timedelta(
                    days=random.randint(0, 120),
                    hours=random.randint(0, 23)
                )
                
                due_date = date.today() + timedelta(days=random.randint(-60, 120))
                
                BabyVital.objects.create(
                    parent=parent,
                    puls=random.randint(120, 160) if random.random() > 0.1 else None,
                    systolic=random.randint(70, 110) if random.random() > 0.1 else None,
                    diastolic=random.randint(40, 70) if random.random() > 0.1 else None,
                    o2=round(random.uniform(95.0, 100.0), 1) if random.random() > 0.1 else None,
                    weight=round(random.uniform(2.5, 4.5), 2) if random.random() > 0.1 else None,
                    age=f'{random.randint(0, 12)} months' if random.random() > 0.2 else '',
                    note=f'Baby vital note for {parent.name}\'s baby' if random.random() > 0.4 else '',
                    reading_date=reading_date,
                    files=[],
                    due_date=due_date if random.random() > 0.3 else None
                )
        
        self.stdout.write(f'Created baby vitals for {len(parents)} parents')

        # Create medications
        medication_names = [
            'Paracetamol', 'Ibuprofen', 'Amoxicillin', 'Aspirin', 'Vitamin D',
            'Calcium', 'Iron Supplement', 'Antibiotic', 'Cough Syrup', 'Antihistamine',
            'Pain Relief', 'Fever Reducer', 'Nasal Spray', 'Eye Drops', 'Cream'
        ]
        
        meds = []
        for name in medication_names:
            med = Med.objects.create(
                name=name,
                note=f'Common medication: {name}',
                avg_price=round(random.uniform(10.0, 150.0), 2),
                created_by=random.choice(doctors)
            )
            meds.append(med)
        
        self.stdout.write(f'Created {len(meds)} medications')

        # Create patient medications (some patients are on medications)
        patients_with_meds = random.sample(patients, min(60, len(patients)))  # 60% of patients have meds
        
        for patient in patients_with_meds:
            num_meds = random.randint(1, 4)  # 1-4 medications per patient
            patient_meds = random.sample(meds, min(num_meds, len(meds)))
            
            for med in patient_meds:
                PatientMed.objects.create(
                    patient=patient,
                    med=med,
                    med_name=med.name,
                    created_by=random.choice(doctors)
                )
        
        self.stdout.write(f'Created patient medications for {len(patients_with_meds)} patients')

        # Summary
        self.stdout.write(self.style.SUCCESS('\n=== Seeding Complete ==='))
        self.stdout.write(f'Doctors: {User.objects.filter(user_type="doctor").count()}')
        self.stdout.write(f'Employees: {User.objects.filter(user_type="employee").count()}')
        self.stdout.write(f'Patients: {User.objects.filter(user_type="patient").count()}')
        self.stdout.write(f'Clinics: {Clinic.objects.count()}')
        self.stdout.write(f'Visits: {Visit.objects.count()}')
        self.stdout.write(f'Vitals: {Vital.objects.count()}')
        self.stdout.write(f'Baby Vitals: {BabyVital.objects.count()}')
        self.stdout.write(f'Medications: {Med.objects.count()}')
        self.stdout.write(f'Patient Medications: {PatientMed.objects.count()}')

    def _get_arabic_name(self, index):
        """Generate Arabic-sounding names for seeding."""
        first_names = [
            'أحمد', 'محمد', 'علي', 'حسن', 'حسين', 'عبدالله', 'خالد', 'سعيد', 'محمود', 'يوسف',
            'فاطمة', 'مريم', 'عائشة', 'خديجة', 'زينب', 'سارة', 'نور', 'ليلى', 'ريم', 'هند',
            'عمر', 'عثمان', 'طلال', 'بدر', 'سعد', 'ناصر', 'راشد', 'مشعل', 'سلطان', 'فيصل',
            'نورة', 'لينا', 'دانة', 'جنى', 'تالا', 'ميار', 'لارا', 'ميرا', 'ياسمين', 'روان',
            'إبراهيم', 'إسماعيل', 'يعقوب', 'يوسف', 'داود', 'سليمان', 'هارون', 'زكريا', 'يحيى', 'عيسى',
            'أسماء', 'صفية', 'رقية', 'أم كلثوم', 'سكينة', 'رقية', 'زينب', 'خديجة', 'فاطمة', 'مريم'
        ]
        return first_names[index % len(first_names)]


