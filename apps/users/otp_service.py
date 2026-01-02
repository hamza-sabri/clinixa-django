"""
OTP Service for Patient Authentication.

This module provides OTP generation, sending, and verification services
for patient phone-based authentication.

Currently mocked with hardcoded OTP "123456" - will be replaced with
actual SMS provider integration later.
"""

from datetime import timedelta
from django.utils import timezone
from django.db.models import Count

from .models import OTPVerification


# OTP Configuration
OTP_EXPIRY_SECONDS = 300  # 5 minutes
OTP_MAX_ATTEMPTS = 5
RATE_LIMIT_WINDOW_SECONDS = 60
RATE_LIMIT_MAX_REQUESTS = 3


def generate_otp(phone: str) -> str:
    """
    Generate a new OTP for the given phone number.
    
    Currently mocked to always return "123456".
    Will be replaced with random 6-digit generation when SMS provider is integrated.
    
    Args:
        phone: The phone number to generate OTP for
        
    Returns:
        str: The generated OTP code (currently always "123456")
    """
    # TODO: Replace with actual random OTP generation when SMS provider is ready
    # import random
    # return str(random.randint(100000, 999999))
    return "123456"


def send_otp(phone: str, otp_code: str) -> bool:
    """
    Send OTP to the given phone number via SMS.
    
    Currently mocked - logs to console instead of sending SMS.
    Will be replaced with actual SMS provider integration later.
    
    Args:
        phone: The phone number to send OTP to
        otp_code: The OTP code to send
        
    Returns:
        bool: True if SMS was sent successfully (always True for mock)
    """
    # TODO: Replace with actual SMS sending when provider is integrated
    # Example providers: Twilio, MessageBird, local SMS gateway
    print(f"[MOCK SMS] Sending OTP {otp_code} to {phone}")
    return True


def create_otp_verification(phone: str) -> dict:
    """
    Create a new OTP verification record and send OTP.
    
    Invalidates any previous unused OTPs for the same phone.
    
    Args:
        phone: The phone number to create OTP for
        
    Returns:
        dict: Contains 'success', 'otp_code' (for testing), 'expires_in'
    """
    # Invalidate any existing unused OTPs for this phone
    OTPVerification.objects.filter(
        phone=phone,
        is_used=False
    ).update(is_used=True)
    
    # Generate new OTP
    otp_code = generate_otp(phone)
    expires_at = timezone.now() + timedelta(seconds=OTP_EXPIRY_SECONDS)
    
    # Create verification record
    otp_record = OTPVerification.objects.create(
        phone=phone,
        otp_code=otp_code,
        expires_at=expires_at
    )
    
    # Send OTP via SMS (mocked)
    send_otp(phone, otp_code)
    
    return {
        'success': True,
        'otp_code': otp_code,  # Only for testing/development
        'expires_in': OTP_EXPIRY_SECONDS
    }


def verify_otp(phone: str, otp_code: str) -> dict:
    """
    Verify an OTP code for the given phone number.
    
    Args:
        phone: The phone number to verify OTP for
        otp_code: The OTP code to verify
        
    Returns:
        dict: Contains 'success', 'error' (if any), 'otp_record' (if successful)
    """
    # Find the most recent valid OTP for this phone
    otp_record = OTPVerification.objects.filter(
        phone=phone,
        is_used=False
    ).order_by('-created_at').first()
    
    if not otp_record:
        return {
            'success': False,
            'error': 'No active OTP found. Please request a new OTP.'
        }
    
    # Check if expired
    if otp_record.is_expired:
        return {
            'success': False,
            'error': 'OTP has expired. Please request a new OTP.'
        }
    
    # Check max attempts
    if otp_record.attempts >= OTP_MAX_ATTEMPTS:
        otp_record.mark_as_used()
        return {
            'success': False,
            'error': 'Too many failed attempts. Please request a new OTP.'
        }
    
    # Verify OTP code
    if otp_record.otp_code != otp_code:
        otp_record.increment_attempts()
        remaining_attempts = OTP_MAX_ATTEMPTS - otp_record.attempts
        return {
            'success': False,
            'error': f'Invalid OTP. {remaining_attempts} attempts remaining.'
        }
    
    # OTP is valid - mark as used
    otp_record.mark_as_used()
    
    return {
        'success': True,
        'otp_record': otp_record
    }


def is_rate_limited(phone: str) -> dict:
    """
    Check if the phone number has exceeded the rate limit for OTP requests.
    
    Args:
        phone: The phone number to check
        
    Returns:
        dict: Contains 'limited' (bool), 'wait_seconds' (int, if limited)
    """
    window_start = timezone.now() - timedelta(seconds=RATE_LIMIT_WINDOW_SECONDS)
    
    recent_requests = OTPVerification.objects.filter(
        phone=phone,
        created_at__gte=window_start
    ).count()
    
    if recent_requests >= RATE_LIMIT_MAX_REQUESTS:
        # Find when the oldest request in window was made
        oldest_in_window = OTPVerification.objects.filter(
            phone=phone,
            created_at__gte=window_start
        ).order_by('created_at').first()
        
        if oldest_in_window:
            wait_until = oldest_in_window.created_at + timedelta(seconds=RATE_LIMIT_WINDOW_SECONDS)
            wait_seconds = max(0, int((wait_until - timezone.now()).total_seconds()))
            return {
                'limited': True,
                'wait_seconds': wait_seconds
            }
    
    return {
        'limited': False,
        'wait_seconds': 0
    }


def check_user_exists(phone: str) -> bool:
    """
    Check if a user with the given phone number exists.
    
    Args:
        phone: The phone number to check
        
    Returns:
        bool: True if user exists, False otherwise
    """
    from django.contrib.auth import get_user_model
    User = get_user_model()
    return User.objects.filter(phone=phone).exists()
