from django.db import models

# Create your models here.
class Service(models.Model):
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ]
    name = models.CharField(max_length=200)
    description = models.TextField()
    base_price = models.DecimalField(max_digits=10, decimal_places=2)
    duration_hours = models.IntegerField()
    is_active = models.BooleanField(default=True)
    is_outdoor = models.BooleanField(default=True)
    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_CHOICES,
        default='medium',
    )
    def __str__(self):
        return self.name