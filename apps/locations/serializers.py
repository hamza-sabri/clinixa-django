from rest_framework import serializers
from .models import City


class CitySerializer(serializers.ModelSerializer):
    """Serializer for City model."""
    
    class Meta:
        model = City
        fields = ['id', 'name']
        read_only_fields = ['id']

