from rest_framework import permissions


class IsDoctor(permissions.BasePermission):
    """Permission class that only allows doctors to access the view."""
    
    message = 'Only doctors can perform this action.'
    
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.user_type == 'doctor'


class IsClinicOwner(permissions.BasePermission):
    """Permission class that only allows the clinic owner to modify it."""
    
    message = 'Only the clinic owner can perform this action.'
    
    def has_object_permission(self, request, view, obj):
        return obj.doctor == request.user


class IsEmployee(permissions.BasePermission):
    """Permission class that only allows employees to access the view."""
    
    message = 'Only employees can perform this action.'
    
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.user_type == 'employee'


class IsPatient(permissions.BasePermission):
    """Permission class that only allows patients to access the view."""
    
    message = 'Only patients can perform this action.'
    
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.user_type == 'patient'


class IsDoctorOrEmployee(permissions.BasePermission):
    """Permission class that allows doctors or employees."""
    
    message = 'Only doctors or employees can perform this action.'
    
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.user_type in ['doctor', 'employee']


