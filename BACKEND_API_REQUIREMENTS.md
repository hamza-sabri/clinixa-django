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

**Document Version:** 1.0  
**Last Updated:** January 2025  
**Frontend Contact:** Will use mock data until these endpoints are ready

