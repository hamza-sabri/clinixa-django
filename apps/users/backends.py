from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


class EmailBackend(ModelBackend):
    """Custom authentication backend that allows users to log in using their email."""
    
    def authenticate(self, request, email=None, password=None, **kwargs):
        UserModel = get_user_model()
        
        # Also check username parameter for compatibility
        if email is None:
            email = kwargs.get('username')
        
        if email is None:
            return None
            
        try:
            user = UserModel.objects.get(email=email)
        except UserModel.DoesNotExist:
            return None
        
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None



