from django.conf import settings
from django.db import models


# Create your models here.
class Enrollment(models.Model):
    
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='enrollments'
    )
    course = models.ForeignKey('courses.Course', on_delete=models.CASCADE, related_name='enrollments')
    
    # Timestamp and status fields
    enrolled_at = models.DateTimeField(auto_now_add=True)  
    updated_at = models.DateTimeField(auto_now=True)     
    is_active = models.BooleanField(default=True) 

    class Meta:
        unique_together = ('student', 'course') 

    def __str__(self):
        return f"{self.student} enrolled in {self.course}"