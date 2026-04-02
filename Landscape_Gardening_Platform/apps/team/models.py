from django.db import models
from django.contrib.auth.models import User
from apps.services.models import Service

# Create your models here.
class TeamMember(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    specialties = models.ManyToManyField(Service)
    is_available = models.BooleanField(default=True)
    def __str__(self):
        full_name = self.user.get_full_name().strip()
        return full_name or self.user.username