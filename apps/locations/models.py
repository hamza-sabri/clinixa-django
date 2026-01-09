from django.db import models


# Create your models here.
class City(models.Model):
    name = models.CharField('City name', max_length=255)

    class Meta:
        verbose_name = 'City'
        verbose_name_plural = 'cities'

    def __str__(self):
        return self.name
