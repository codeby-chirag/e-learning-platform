import csv
import os

from celery import shared_task
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail

from courses.models import Course
from enrollment.models import Enrollment  # Adjust imports based on your app structure


@shared_task   # Marks this function as an asynchronous background task for Celery
def send_activation_email_task(user_email, activation_link, first_name):
    subject = "Email for account Activation!"
    message = f"Hi {first_name},\n\nPlease click the link below to activate your account:\n{activation_link}"
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user_email], fail_silently=False)
    
@shared_task 
def send_password_reset_email_task(subject, message, from_email, recipient_list):
    send_mail(subject, message, from_email, recipient_list, fail_silently=False)  # Safely dispatches the email in the background worker process
    
User = get_user_model()

@shared_task
def generate_platform_report_task(admin_email):
    # 1. Gather statistics from the database
    total_users = User.objects.count()
    total_courses = Course.objects.count()
    total_enrollments = Enrollment.objects.count() if 'Enrollment' in globals() else 0

    # 2. Create a summary text or CSV report content
    report_content = (
        f"--- E-Learning Platform Report ---\n"
        f"Total Registered Users: {total_users}\n"
        f"Total Courses Available: {total_courses}\n"
        f"Total Enrollments: {total_enrollments}\n"
    )

    # 3. Option A: Email the report to the admin asynchronously
    send_mail(
        subject="Asynchronous Platform Report Ready",
        message=report_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[admin_email],
        fail_silently=False,
    )

    return f"Report successfully generated and emailed to {admin_email}"