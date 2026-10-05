from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, PasswordResetForm
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction
from django.template import loader

from .models import UserProfile
from .tasks import send_password_reset_email_task

User = get_user_model() # featch current active active User model, whether it is the built-in default or a custom user model

class UserRegistrationForm(forms.ModelForm):
    email = forms.EmailField(
        required=True, 
        widget=forms.EmailInput(attrs={'placeholder': 'email@gmail.com', 'class': 'form-control form-control-lg'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Password', 'class': 'form-control form-control-lg'})
    )
    firstname = forms.CharField(
        max_length=150, 
        widget=forms.TextInput(attrs={'placeholder': 'First Name', 'class': 'form-control form-control-lg'})
    )
    lastname = forms.CharField(
        max_length=150, 
        widget=forms.TextInput(attrs={'placeholder': 'Last Name', 'class': 'form-control form-control-lg'})
    )
    mobile_number = forms.CharField(
        max_length=15, 
        widget=forms.TextInput(attrs={'placeholder': 'Mobile Number', 'class': 'form-control form-control-lg'})
    )
    birthdate = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control form-control-lg'})
    )
    
    GENDER_CHOICES = [  # noqa: RUF012
        ('male', 'Male'),
        ('female', 'Female'),
    ]
    gender = forms.ChoiceField(
        choices=GENDER_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'form-radio-input'})
    )

    class Meta:
        model = User
        fields = ['email', 'password']  # noqa: RUF012

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email__iexact=email).exists() or UserProfile.objects.filter(user__email__iexact=email).exists(): 
            raise ValidationError("An account with this email already exists.")
        return email

    def clean_password(self):
        password = self.cleaned_data.get('password')
        validate_password(password)
        return password

    def save(self, commit=True):
        with transaction.atomic():  #If any error happens while executing the lines inside this block all changes made within this line of block are rolled back.
            user = super().save(commit=False) # take the entered data but can't store in databse yet
            
            user.set_password(self.cleaned_data["password"])
            email = self.cleaned_data.get('email')
            user.username = email  
            user.first_name = self.cleaned_data.get('firstname')
            user.last_name = self.cleaned_data.get('lastname')
            user.is_active = False  
            
            if commit:
                user.save()
                
                UserProfile.objects.create(
                    user=user,
                    mobile_number=self.cleaned_data.get('mobile_number'),
                    gender=self.cleaned_data.get('gender'),
                    birthdate=self.cleaned_data.get('birthdate')
                )
        return user


class CustomAuthenticationForm(AuthenticationForm):
    username = forms.CharField(
        label="Email",
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg', 
            'placeholder': 'Enter email or username'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control form-control-lg', 
            'placeholder': 'Enter password'
        })
    )
    
class CustomPasswordResetForm(PasswordResetForm): # Inherits from Django's built-in password reset form
    email = forms.EmailField(
        max_length=254,
        widget=forms.EmailInput(attrs={
            'placeholder': 'Enter your email', 
            'class': 'form-control form-control-lg'
        })
    )
    
    def send_mail(self, subject_template_name, email_template_name, context, from_email, to_email, html_email_template_name=None):
            subject = loader.render_to_string(subject_template_name, context) # Render email templat
            subject = ''.join(subject.splitlines()) # Remove accidental newlines
            body = loader.render_to_string(email_template_name, context) # render main email body by loder michanism
            
            send_password_reset_email_task.delay(subject, body, from_email, [to_email]) # async use delay