from django.conf import settings
from django.db import models


# Create your models here.
class Course(models.Model):
    
    instructor = models.ForeignKey(
    settings.AUTH_USER_MODEL, 
    on_delete=models.CASCADE, 
    related_name='courses'
    )
    course_title = models.CharField(max_length=150)
    category = models.CharField(max_length=100)
    description = models.TextField()
    duration = models.CharField(max_length=50) 
    course_image = models.ImageField(upload_to='courses/')
    
    enrollment_start_date = models.DateTimeField()
    enrollment_end_date = models.DateTimeField()
    course_start_date = models.DateTimeField()
    course_end_date = models.DateTimeField()
    
    class Meta:
        permissions = (
            ("can_create_courses", "Provide grant to create courses."),
            ("can_edit_courses", "Provide grant to Edit courses."),
            ("can_delete_courses", "Provide grant to delete courses."),
        )
    
    
    def __str__(self):
        return self.course_title