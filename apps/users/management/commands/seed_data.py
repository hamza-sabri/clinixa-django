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
from apps.users.models import PatientProfile, Pregnancy, Baby

User = get_user_model()


class Command(BaseCommand):
    help = 'Seed the database with test data including pregnancy-centric architecture'

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
            Baby.objects.all().delete()
            Pregnancy.objects.all().delete()
            PatientProfile.objects.all().delete()
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
                all_employees.append(employee)
            
            self.stdout.write(f'Created {num_employees} employees for clinic {clinic.name}')

        # Create 100 patients with profiles
        patients = []
        profiles = []
        blood_types = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-']
        allergies_list = ['None', 'Penicillin', 'Peanuts', 'Lactose', 'Gluten', 'Shellfish', 'Eggs']
        
        for i in range(1, 101):
            patient = User.objects.create_user(
                email=f'patient{i}@clinixa.com',
                password='patient123',
                name=f'{self._get_arabic_name(random.randint(1, 50))} {self._get_arabic_name(random.randint(51, 100))}',
                phone=f'+97150{random.randint(1000000, 9999999)}',
                user_type='patient'
            )
            patients.append(patient)
            
            # Create patient profile
            profile = PatientProfile.objects.create(
                user=patient,
                blood_type=random.choice(blood_types),
                allergies=random.choice(allergies_list),
                medical_history='No significant medical history' if random.random() > 0.3 else 'Previous pregnancy complications',
                notes=f'Patient {i} profile notes' if random.random() > 0.5 else ''
            )
            profiles.append(profile)
        
        self.stdout.write(f'Created {len(patients)} patients with profiles')

        # Create pregnancies for patients (1-3 per patient, some have none)
        all_pregnancies = []
        pregnancy_statuses = ['ongoing', 'delivered', 'delivered', 'delivered', 'miscarriage']  # Higher chance of delivered
        
        for profile in profiles:
            # 80% of patients have at least one pregnancy
            if random.random() > 0.2:
                num_pregnancies = random.randint(1, 3)
                
                for p_idx in range(num_pregnancies):
                    # Calculate LMP and due date
                    if p_idx == 0 and random.random() > 0.5:
                        # Current/ongoing pregnancy
                        lmp_days_ago = random.randint(30, 250)
                        lmp = date.today() - timedelta(days=lmp_days_ago)
                        due_date = lmp + timedelta(days=280)
                        status = 'ongoing'
                    else:
                        # Historical pregnancy
                        lmp_days_ago = random.randint(300, 1000)
                        lmp = date.today() - timedelta(days=lmp_days_ago)
                        due_date = lmp + timedelta(days=280)
                        status = random.choice(pregnancy_statuses[1:])  # Not ongoing
                    
                    pregnancy = Pregnancy.objects.create(
                        patient_profile=profile,
                        created_by_clinic=random.choice(clinics),
                        lmp=lmp,
                        due_date=due_date,
                        status=status,
                        is_high_risk=random.random() > 0.8,
                        notes=f'Pregnancy {p_idx + 1} for patient'
                    )
                    all_pregnancies.append(pregnancy)
        
        self.stdout.write(f'Created {len(all_pregnancies)} pregnancies')

        # Create babies for pregnancies (1-2 per pregnancy, some twins)
        all_babies = []
        genders = ['male', 'female', 'unknown']
        
        for pregnancy in all_pregnancies:
            # Most pregnancies have 1 baby, 10% have twins
            num_babies = 2 if random.random() > 0.9 else 1
            
            for b_idx in range(num_babies):
                is_born = pregnancy.status == 'delivered'
                baby = Baby.objects.create(
                    pregnancy=pregnancy,
                    name=self._get_arabic_name(random.randint(1, 60)) if is_born and random.random() > 0.3 else '',
                    gender=random.choice(genders[:2]) if is_born else 'unknown',
                    birth_date=timezone.now() - timedelta(days=random.randint(0, 365)) if is_born else None,
                    birth_weight=round(random.uniform(2.5, 4.5), 2) if is_born else None,
                    birth_length=round(random.uniform(45, 55), 1) if is_born else None,
                    apgar_score=random.randint(7, 10) if is_born else None,
                    is_born=is_born,
                    notes=f'Baby {b_idx + 1}' if num_babies > 1 else ''
                )
                all_babies.append(baby)
        
        self.stdout.write(f'Created {len(all_babies)} babies')

        # Create visits for ongoing pregnancies
        visit_statuses = ['جاري التأكيد', 'مؤكد', 'مكتمل', 'ملغي']
        urgency_levels = ['عادي', 'عاجل', 'طوارئ', '']
        
        all_visits = []
        for pregnancy in all_pregnancies:
            # Each pregnancy has 2-8 visits
            num_visits = random.randint(2, 8)
            clinic = pregnancy.created_by_clinic or random.choice(clinics)
            
            for v_idx in range(num_visits):
                visit_time = timezone.now() - timedelta(
                    days=random.randint(0, 200),
                    hours=random.randint(0, 23),
                    minutes=random.randint(0, 59)
                )
                
                visit = Visit.objects.create(
                    clinic=clinic,
                    pregnancy=pregnancy,
                    time=visit_time,
                    status=random.choice(visit_statuses),
                    note=f'Visit {v_idx + 1} notes' if random.random() > 0.3 else '',
                    urgency=random.choice(urgency_levels) if random.random() > 0.5 else ''
                )
                all_visits.append(visit)
        
        self.stdout.write(f'Created {len(all_visits)} visits')

        # Create vitals for pregnancies (some linked to visits)
        moods = ['سعيد', 'عادي', 'قلق', 'مريض', '']
        
        for pregnancy in all_pregnancies:
            # Each pregnancy has 1-5 vital records
            num_vitals = random.randint(1, 5)
            pregnancy_visits = list(Visit.objects.filter(pregnancy=pregnancy))
            
            for v_idx in range(num_vitals):
                reading_date = timezone.now() - timedelta(
                    days=random.randint(0, 200),
                    hours=random.randint(0, 23)
                )
                
                # 50% chance to link to a visit if available
                visit = None
                if pregnancy_visits and random.random() > 0.5:
                    visit = random.choice(pregnancy_visits)
                    # Remove to avoid duplicate links
                    pregnancy_visits.remove(visit)
                
                Vital.objects.create(
                    pregnancy=pregnancy,
                    visit=visit,
                    systolic=random.randint(90, 140) if random.random() > 0.1 else None,
                    diastolic=random.randint(60, 90) if random.random() > 0.1 else None,
                    o2=random.randint(95, 100) if random.random() > 0.1 else None,
                    puls=random.randint(60, 100) if random.random() > 0.1 else None,
                    temp=round(random.uniform(36.0, 38.5), 1) if random.random() > 0.1 else None,
                    weight=round(random.uniform(50.0, 100.0), 1) if random.random() > 0.1 else None,
                    reading_date=reading_date,
                    files=[],
                    mood=random.choice(moods) if random.random() > 0.3 else '',
                    note=f'Vital note for pregnancy' if random.random() > 0.5 else '',
                    dr_note=f'Doctor observation' if random.random() > 0.3 else ''
                )
        
        self.stdout.write(f'Created vitals for pregnancies')

        # Create baby vitals
        for baby in all_babies:
            # Each baby has 1-3 vital records
            num_vitals = random.randint(1, 3)
            
            for v_idx in range(num_vitals):
                reading_date = timezone.now() - timedelta(
                    days=random.randint(0, 120),
                    hours=random.randint(0, 23)
                )
                
                due_date = baby.pregnancy.due_date
                
                BabyVital.objects.create(
                    baby=baby,
                    visit=None,  # Can be linked later
                    puls=random.randint(120, 160) if random.random() > 0.1 else None,
                    systolic=random.randint(70, 110) if random.random() > 0.1 else None,
                    diastolic=random.randint(40, 70) if random.random() > 0.1 else None,
                    o2=round(random.uniform(95.0, 100.0), 1) if random.random() > 0.1 else None,
                    weight=round(random.uniform(2.5, 4.5), 2) if random.random() > 0.1 else None,
                    age=f'{random.randint(0, 12)} months' if baby.is_born else '',
                    note=f'Baby vital note' if random.random() > 0.4 else '',
                    reading_date=reading_date,
                    files=[],
                    due_date=due_date if not baby.is_born else None
                )
        
        self.stdout.write(f'Created baby vitals')

        # Create medications
        medication_names = [
            'Paracetamol', 'Ibuprofen', 'Amoxicillin', 'Aspirin', 'Vitamin D',
            'Calcium', 'Iron Supplement', 'Folic Acid', 'Prenatal Vitamins', 'Antihistamine',
            'Progesterone', 'Magnesium', 'Omega-3', 'Vitamin B12', 'Zinc'
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

        # Create patient medications
        patients_with_meds = random.sample(patients, min(60, len(patients)))
        
        for patient in patients_with_meds:
            num_meds = random.randint(1, 4)
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
        self.stdout.write(f'Patient Profiles: {PatientProfile.objects.count()}')
        self.stdout.write(f'Pregnancies: {Pregnancy.objects.count()} (ongoing: {Pregnancy.objects.filter(status="ongoing").count()}, delivered: {Pregnancy.objects.filter(status="delivered").count()})')
        self.stdout.write(f'Babies: {Baby.objects.count()}')
        self.stdout.write(f'Clinics: {Clinic.objects.count()}')
        self.stdout.write(f'Visits: {Visit.objects.count()}')
        self.stdout.write(f'Vitals (mother): {Vital.objects.count()}')
        self.stdout.write(f'Baby Vitals: {BabyVital.objects.count()}')
        self.stdout.write(f'Medications: {Med.objects.count()}')
        self.stdout.write(f'Patient Medications: {PatientMed.objects.count()}')
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('Test Accounts:'))
        self.stdout.write('- Doctor: doctor1@clinixa.com / doctor123')
        self.stdout.write('- Employee: employee_1_1@clinixa.com / employee123')
        self.stdout.write('- Patient: patient1@clinixa.com / patient123')

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
