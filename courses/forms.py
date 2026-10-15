from django import forms

from .models import Course


class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = [  # noqa: RUF012
            'course_title',
            'category',
            'description',
            'duration',
            'course_image',
            'enrollment_start_date',
            'enrollment_end_date',
            'course_start_date',
            'course_end_date',
        ]
        
        widgets = {  # noqa: RUF012
            'course_title': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Enter course title'
            }),
            'category': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'e.g., Python, Web Development'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 4, 
                'placeholder': 'Enter detailed course description'
            }),
            'duration': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'e.g., 6 Weeks'
            }),
            'course_image': forms.ClearableFileInput(attrs={
                'class': 'form-control'
            }),
            'enrollment_start_date': forms.DateTimeInput(attrs={
                'class': 'form-control', 
                'type': 'datetime-local'
            }),
            'enrollment_end_date': forms.DateTimeInput(attrs={
                'class': 'form-control', 
                'type': 'datetime-local'
            }),
            'course_start_date': forms.DateTimeInput(attrs={
                'class': 'form-control', 
                'type': 'datetime-local'
            }),
            'course_end_date': forms.DateTimeInput(attrs={
                'class': 'form-control', 
                'type': 'datetime-local'
            }),
        }