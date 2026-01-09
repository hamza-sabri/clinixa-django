# Backend API Requirements for Clinixa Patient Portal

This document outlines all the backend API changes and new endpoints required to fully support the patient portal and public clinics features.

---

## 1. Patient Authentication (OTP-Based)

### 1.1 Request OTP
**Endpoint:** `POST /users/patient/request-otp/`

**Description:** Send OTP to patient's phone number for authentication.

**Request Body:**
```json
{
  "phone": "+971501234567",
  "name": "Patient Name"  // Optional for returning users
}
```

**Response (Success - 200):**
```json
{
  "message": "OTP sent successfully",
  "phone": "+971501234567",
  "expires_in": 300,  // seconds
  "is_new_user": true  // or false if existing patient
}
```

**Response (Error - 429):**
```json
{
  "error": "Too many requests. Please wait 60 seconds."
}
```

---

### 1.2 Verify OTP & Login
**Endpoint:** `POST /users/verify-otp/`

**Description:** Verify OTP and return JWT tokens for patient.

**Request Body:**
```json
{
  "phone": "+971501234567",
  "otp": "1234",
  "name": "Patient Name"  // Required only for new users
}
```

**Response (Success - 200):**
```json
{
  "access": "eyJ...",
  "refresh": "eyJ...",
  "user": {
    "id": 123,
    "phone": "+971501234567",
    "name": "Patient Name",
    "email": null,
    "user_type": "patient",
    "created_at": "2025-01-01T10:00:00Z"
  },
  "is_new_user": true
}
```

**Response (Error - 400):**
```json
{
  "error": "Invalid or expired OTP"
}
```

---

## 2. Clinic Endpoints Enhancements

### 2.1 List Clinics (Enhanced Filters)
**Endpoint:** `GET /clinics/` (existing, needs enhancement)

**New Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `search` | string | Search by clinic name, doctor name, or phone |
| `location` | string | Filter by location/area |
| `type` | string | Filter by clinic type (e.g., "عيادة نسائية") |
| `has_available_slots` | boolean | Only show clinics with available slots today |

**Example:** `GET /clinics/?search=نسائية&location=دبي&page=1&page_size=20`

---

### 2.2 Clinic Model Updates
**Add to Clinic model:**

```python
class Clinic(models.Model):
    # ... existing fields ...
    
    # NEW FIELDS
    working_hours = models.JSONField(
        default=dict,
        help_text="Working hours per day"
    )
    # Example: {
    #   "sunday": {"open": "09:00", "close": "17:00"},
    #   "monday": {"open": "09:00", "close": "17:00"},
    #   "tuesday": {"open": "09:00", "close": "17:00"},
    #   "wednesday": {"open": "09:00", "close": "17:00"},
    #   "thursday": {"open": "09:00", "close": "14:00"},
    #   "friday": null,  # closed
    #   "saturday": null  # closed
    # }
    
    slot_duration = models.IntegerField(
        default=30,
        help_text="Appointment slot duration in minutes"
    )
    
    latitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    longitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    
    description = models.TextField(blank=True, null=True)
    
    is_accepting_new_patients = models.BooleanField(default=True)
```

**Updated ClinicList Serializer Response:**
```json
{
  "id": 1,
  "name": "عيادة الأمل",
  "doctor_name": "د. أحمد محمد",
  "location": "دبي، الخليج التجاري",
  "phone": "+971501234567",
  "type": "عيادة نسائية",
  "working_hours": {
    "sunday": {"open": "09:00", "close": "17:00"},
    "monday": {"open": "09:00", "close": "17:00"},
    "friday": null
  },
  "slot_duration": 30,
  "is_accepting_new_patients": true,
  "visits_per_status": {...},
  "distinct_patients_count": 150
}
```

---

### 2.3 Get Available Slots
**Endpoint:** `GET /clinics/{id}/available-slots/`

**Description:** Get available appointment slots for a specific clinic on a given date.

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `date` | string (YYYY-MM-DD) | Yes | Date to check availability |

**Example:** `GET /clinics/1/available-slots/?date=2025-01-15`

**Response (Success - 200):**
```json
{
  "clinic_id": 1,
  "date": "2025-01-15",
  "working_hours": {
    "open": "09:00",
    "close": "17:00"
  },
  "slot_duration": 30,
  "available_slots": [
    {"time": "09:00", "available": true},
    {"time": "09:30", "available": true},
    {"time": "10:00", "available": false},  // already booked
    {"time": "10:30", "available": true},
    // ... more slots
  ],
  "booked_count": 5,
  "total_slots": 16
}
```

**Response (Closed Day - 200):**
```json
{
  "clinic_id": 1,
  "date": "2025-01-17",  // Friday
  "working_hours": null,
  "message": "Clinic is closed on this day",
  "available_slots": []
}
```

---

## 3. Patient Self-Service Endpoints

### 3.1 Get Current Patient Profile
**Endpoint:** `GET /patients/me/`

**Description:** Get the authenticated patient's own profile and data.

**Headers:** `Authorization: Bearer <patient_token>`

**Response (Success - 200):**
```json
{
  "id": 123,
  "email": "patient@email.com",  // may be null for phone-only users
  "phone": "+971501234567",
  "name": "فاطمة أحمد",
  "profile": {
    "blood_type": "A+",
    "allergies": "Penicillin",
    "medical_history": "None",
    "profile_notes": ""
  },
  "pregnancies": [...],
  "pregnancies_count": 2,
  "ongoing_pregnancy": {
    "id": 5,
    "due_date": "2025-06-15",
    "last_period": "2024-09-08",
    "status": "ongoing",
    "week": 18,
    "babies": [...]
  },
  "created_at": "2024-01-01T10:00:00Z"
}
```

---

### 3.2 Update Current Patient Profile
**Endpoint:** `PATCH /patients/me/`

**Description:** Update the authenticated patient's own profile.

**Request Body:**
```json
{
  "name": "فاطمة أحمد محمود",
  "profile": {
    "blood_type": "A+",
    "allergies": "Penicillin, Sulfa",
    "medical_history": "Gestational diabetes in 2023"
  }
}
```

**Response (Success - 200):** Updated patient object

---

### 3.3 Get Patient's Own Visits
**Endpoint:** `GET /visits/visits/` (existing, needs filter)

**New Query Parameter:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `patient` | string | Use `me` to get own visits |

**Example:** `GET /visits/visits/?patient=me&status=مؤكد`

**Response:** Paginated list of patient's visits

---

### 3.4 Get Patient's Own Vitals
**Endpoint:** `GET /vitals/vitals/` (existing, needs filter)

**New Query Parameter:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `patient` | string | Use `me` to get own vitals |

**Example:** `GET /vitals/vitals/?patient=me`

---

## 4. Visit Management for Patients

### 4.1 Cancel Visit (Patient)
**Endpoint:** `POST /visits/visits/{id}/cancel/`

**Description:** Allow patient to cancel their own upcoming visit.

**Business Rules:**
- Can only cancel visits with status "جاري التأكيد" or "مؤكد"
- Cannot cancel visits less than 2 hours before appointment
- Sets status to "ملغي" with cancellation reason

**Request Body:**
```json
{
  "reason": "Personal emergency"  // optional
}
```

**Response (Success - 200):**
```json
{
  "id": 456,
  "status": "ملغي",
  "cancelled_at": "2025-01-14T10:30:00Z",
  "cancelled_by": "patient",
  "cancellation_reason": "Personal emergency"
}
```

**Response (Error - 400):**
```json
{
  "error": "Cannot cancel visit less than 2 hours before appointment"
}
```

---

### 4.2 Reschedule Visit (Patient)
**Endpoint:** `POST /visits/visits/{id}/reschedule/`

**Description:** Allow patient to reschedule their own upcoming visit.

**Business Rules:**
- Can only reschedule visits with status "جاري التأكيد" or "مؤكد"
- Cannot reschedule visits less than 2 hours before appointment
- New time must be an available slot

**Request Body:**
```json
{
  "new_time": "2025-01-20T14:30:00Z",
  "reason": "Schedule conflict"  // optional
}
```

**Response (Success - 200):**
```json
{
  "id": 456,
  "time": "2025-01-20T14:30:00Z",
  "status": "جاري التأكيد",  // reset to pending for reconfirmation
  "rescheduled_at": "2025-01-14T10:30:00Z",
  "previous_time": "2025-01-15T10:00:00Z"
}
```

---

## 5. Pregnancy & Baby Endpoints for Patients

### 5.1 Get Patient's Pregnancies
**Endpoint:** `GET /pregnancies/pregnancies/?patient=me`

Already exists but needs the `patient=me` filter support.

---

### 5.2 Update Pregnancy Details (Patient)
**Endpoint:** `PATCH /pregnancies/pregnancies/{id}/`

Patients should be able to update their own pregnancy details:
- `due_date`
- `last_period`
- `notes`

**Permission:** Patient can only update their own pregnancies.

---

## 6. Summary of Required Changes

### New Endpoints
| Method | Endpoint                          | Description |
|--------|-----------------------------------|-------------|
| POST | `/users/request-otp/`             | Request OTP for patient login |
| POST | `/users/verify-otp/`              | Verify OTP and get tokens |
| GET | `/clinics/{id}/available-slots/`  | Get available booking slots |
| GET | `/patients/me/`                   | Get current patient profile |
| PATCH | `/patients/me/`                   | Update current patient profile |
| POST | `/visits/visits/{id}/cancel/`     | Patient cancels visit |
| POST | `/visits/visits/{id}/reschedule/` | Patient reschedules visit |

### Model Changes
| Model | Field | Type | Description |
|-------|-------|------|-------------|
| Clinic | `working_hours` | JSONField | Working hours per day |
| Clinic | `slot_duration` | IntegerField | Slot duration in minutes |
| Clinic | `latitude` | DecimalField | GPS latitude |
| Clinic | `longitude` | DecimalField | GPS longitude |
| Clinic | `description` | TextField | Clinic description |
| Clinic | `is_accepting_new_patients` | BooleanField | Accepting new patients |
| Visit | `cancelled_at` | DateTimeField | When visit was cancelled |
| Visit | `cancelled_by` | CharField | Who cancelled (patient/clinic) |
| Visit | `cancellation_reason` | TextField | Reason for cancellation |
| Visit | `rescheduled_at` | DateTimeField | When visit was rescheduled |
| Visit | `previous_time` | DateTimeField | Original time before reschedule |

### Filter Additions
| Endpoint | New Filter | Description |
|----------|------------|-------------|
| `GET /clinics/` | `search` | Search by name, doctor, phone |
| `GET /clinics/` | `location` | Filter by location |
| `GET /clinics/` | `type` | Filter by clinic type |
| `GET /visits/visits/` | `patient=me` | Get own visits |
| `GET /vitals/vitals/` | `patient=me` | Get own vitals |
| `GET /pregnancies/pregnancies/` | `patient=me` | Get own pregnancies |

---

## 7. Priority Order

1. **High Priority (Required for MVP):**
   - Patient OTP endpoints (`request-otp`, `verify-otp`)
   - `GET /patients/me/`
   - `GET /clinics/{id}/available-slots/`
   - `patient=me` filter on visits

2. **Medium Priority:**
   - Clinic model updates (working hours, slot duration)
   - `PATCH /patients/me/`
   - Visit cancel/reschedule endpoints

3. **Lower Priority:**
   - Enhanced clinic search filters
   - GPS coordinates for location-based filtering
   - `patient=me` filter on vitals and pregnancies

---

## 8. Notes for Implementation

### OTP Service
Consider using a service like:
- Twilio
- MessageBird
- Local SMS gateway

For development/testing, you can:
- Log OTP to console
- Use a fixed OTP like "1234" for test phone numbers

### Slot Calculation Logic
```python
def get_available_slots(clinic, date):
    working_hours = clinic.working_hours.get(date.strftime('%A').lower())
    if not working_hours:
        return []
    
    open_time = datetime.strptime(working_hours['open'], '%H:%M')
    close_time = datetime.strptime(working_hours['close'], '%H:%M')
    
    slots = []
    current = open_time
    while current < close_time:
        slot_datetime = datetime.combine(date, current.time())
        is_booked = Visit.objects.filter(
            clinic=clinic,
            time=slot_datetime,
            status__in=['جاري التأكيد', 'مؤكد']
        ).exists()
        
        slots.append({
            'time': current.strftime('%H:%M'),
            'available': not is_booked
        })
        current += timedelta(minutes=clinic.slot_duration)
    
    return slots
```

---

## 9. City/Location Management

### 9.1 List Cities
**Endpoint:** `GET /api/locations/cities/`

**Description:** Get all available cities. Public endpoint (no auth required).

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `search` | string | Search by city name |
| `ordering` | string | Order by field (`name`, `-name`, `id`, `-id`) |

**Response (Success - 200):**
```json
[
  {"id": 1, "name": "Dubai"},
  {"id": 2, "name": "Abu Dhabi"},
  {"id": 3, "name": "Sharjah"}
]
```

---

### 9.2 City Field in User APIs

**City is now available in all User-related serializers:**

| API | Field | Description |
|-----|-------|-------------|
| `POST /api/users/signup/` | `city` (int) | City ID for patient signup |
| `POST /api/users/signup-with-clinic/` | `city` (int), `clinic_city` (int) | City for doctor and clinic |
| `POST /api/patients/` | `city` (int) | City ID when creating patient |
| `PATCH /api/patients/{id}/` | `city` (int) | Update patient city |
| `PATCH /api/patients/me/` | `city` (int) | Update own city |
| `GET /api/patients/`, `GET /api/patients/{id}/` | `city`, `city_name` | Returns city ID and name |
| `POST /api/employees/` | `city` (int) | City for employee user |

---

### 9.3 City Field in Clinic APIs

**City is now available in all Clinic-related serializers:**

| API | Field | Description |
|-----|-------|-------------|
| `POST /api/clinics/` | `city` (int) | City ID when creating clinic |
| `PATCH /api/clinics/{id}/` | `city` (int) | Update clinic city |
| `GET /api/clinics/`, `GET /api/clinics/{id}/` | `city`, `city_name` | Returns city ID and name |

---

## 10. Pregnancy Enhancements

### 10.1 Auto-Create Babies on Pregnancy Creation

**When creating a pregnancy, you can specify `babies_count` to auto-create multiple babies:**

**Endpoint:** `POST /api/patients/{patient_id}/pregnancies/`  
**Endpoint:** `POST /api/patients/me/pregnancies/create/`

**Request Body:**
```json
{
  "lmp": "2024-01-15",
  "due_date": "2024-10-22",
  "is_high_risk": false,
  "notes": "Twins pregnancy",
  "babies_count": 2
}
```

**babies_count:**
- Type: Integer (1-8)
- Default: 1
- Description: Number of babies to auto-create for this pregnancy (for twins, triplets, etc.)

**Response (Success - 201):**
```json
{
  "id": 123,
  "patient": {...},
  "lmp": "2024-01-15",
  "due_date": "2024-10-22",
  "status": "ongoing",
  "is_high_risk": false,
  "pregnancy_week": 12,
  "trimester": 1,
  "notes": "Twins pregnancy",
  "babies_count": 2,
  "babies": [
    {"id": 1, "name": "", "gender": "", "is_born": false, "vitals": []},
    {"id": 2, "name": "", "gender": "", "is_born": false, "vitals": []}
  ],
  "vitals_count": 0,
  "vitals": [],
  "visits_count": 0,
  "visits": [],
  "auto_closed_pregnancies_count": 1,
  "created_at": "2024-01-20T10:30:00Z"
}
```

---

### 10.2 Single Active Pregnancy Constraint

**Business Rule:** A patient can only have one active (status='ongoing') pregnancy at a time.

**Behavior when creating a new pregnancy:**
- All existing pregnancies with status `ongoing` for the patient are automatically marked as `delivered`
- The response includes `auto_closed_pregnancies_count` if any were closed
- This applies to both clinic-created and patient self-created pregnancies

---

### 10.3 Enhanced Pregnancy Detail Response

**The pregnancy detail API now returns ALL related data:**

**Endpoint:** `GET /api/pregnancies/{id}/`

**Response includes:**
- `babies` - Array of babies with their vitals
- `vitals` - Array of mother's vitals
- `visits` - Array of all visits
- `babies_count`, `vitals_count`, `visits_count` - Quick reference counts

**Full Response Example:**
```json
{
  "id": 123,
  "patient": {
    "id": 456,
    "name": "Patient Name",
    "email": "patient@example.com",
    "phone": "+971501234567"
  },
  "lmp": "2024-01-15",
  "due_date": "2024-10-22",
  "status": "ongoing",
  "is_high_risk": false,
  "pregnancy_week": 12,
  "trimester": 1,
  "notes": "",
  "babies_count": 2,
  "babies": [
    {
      "id": 1,
      "name": "Baby 1",
      "gender": "male",
      "birth_date": null,
      "birth_weight": null,
      "birth_length": null,
      "apgar_score": null,
      "is_born": false,
      "notes": "",
      "vitals": [
        {"id": 1, "puls": 140, "weight": 0.5, "reading_date": "2024-02-01"},
        {"id": 2, "puls": 142, "weight": 0.6, "reading_date": "2024-03-01"}
      ],
      "created_at": "2024-01-20T10:30:00Z",
      "updated_at": "2024-01-20T10:30:00Z"
    },
    {
      "id": 2,
      "name": "Baby 2",
      "gender": "",
      "is_born": false,
      "vitals": []
    }
  ],
  "vitals_count": 2,
  "vitals": [
    {"id": 1, "systolic": 120, "diastolic": 80, "weight": 65.5, "reading_date": "2024-02-01"},
    {"id": 2, "systolic": 118, "diastolic": 78, "weight": 66.0, "reading_date": "2024-03-01"}
  ],
  "visits_count": 2,
  "visits": [
    {"id": 1, "clinic": 1, "clinic_name": "العيادة", "time": "2024-02-01T10:00:00Z", "status": "مكتمل"},
    {"id": 2, "clinic": 1, "clinic_name": "العيادة", "time": "2024-03-01T10:00:00Z", "status": "مؤكد"}
  ],
  "last_visit": "2024-03-01T10:00:00Z",
  "created_by_clinic": 1,
  "created_by_clinic_name": "العيادة",
  "created_at": "2024-01-20T10:30:00Z",
  "updated_at": "2024-03-15T14:00:00Z"
}
```

---

## 11. Summary of New Features (January 2026)

### New Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/locations/cities/` | List all cities (public) |

### Model Changes
| Model | Field | Type | Description |
|-------|-------|------|-------------|
| User | `city` | ForeignKey | User's city |
| Clinic | `city` | ForeignKey | Clinic's city |
| City | `name` | CharField | City name |

### Serializer Changes
| Serializer | New Fields | Description |
|------------|------------|-------------|
| All Clinic serializers | `city`, `city_name` | City ID and name |
| All Patient/User serializers | `city`, `city_name` | City ID and name |
| PregnancyCreateSerializer | `babies_count` | Write-only, auto-create babies |
| PregnancyDetailSerializer | `babies`, `vitals`, `visits`, `babies_count` | Full related data |
| BabyWithVitalsSerializer | `vitals` | Baby's vitals included |

### Business Logic Changes
| Feature | Description |
|---------|-------------|
| Single Active Pregnancy | Only one ongoing pregnancy per patient; new creation marks old ones as delivered |
| Auto Baby Creation | Specify `babies_count` to auto-create babies when creating pregnancy |

---

**Document Version:** 1.1  
**Last Updated:** January 2026  
**Frontend Contact:** Will use mock data until these endpoints are ready

