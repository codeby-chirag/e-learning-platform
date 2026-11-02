from datetime import date

from django.contrib.auth.models import User
from django.db import models


# Create your models here.
class UserProfile(models.Model):
    GENDER_CHOICES = [  # noqa: RUF012
        ('Male', 'Male'),
        ('Female', 'Female'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    gender = models.CharField(max_length=15, choices=GENDER_CHOICES, blank=True, null=True)
    birthdate = models.DateField(blank=True, null=True)
    
    profile_pic = models.ImageField(upload_to='images/', blank=True, null=True)
    
    mobile_number = models.CharField(max_length=15, blank=True, null=True)
            
    def calculate_age(self):
        if not self.birthdate:
            return None
        
        today = date.today()  # noqa: DTZ011, RUF100
        age = today.year - self.birthdate.year
        
        if (today.month, today.day) < (self.birthdate.month, self.birthdate.day):
            age -= 1
            
        return age
    
    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name}'s Profile"
    
class UserActivityLog(models.Model):
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='activity_logs')
    path = models.CharField(max_length=255)
    method = models.CharField(max_length=10)
    status_code = models.PositiveSmallIntegerField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']  # noqa: RUF012