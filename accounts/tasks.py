import csv
import io
import os  # noqa: F401

from celery import shared_task
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.mail import EmailMessage, send_mail

from courses.models import Course
from enrollment.models import Enrollment


@shared_task
def send_activation_email_task(user_email, activation_link, first_name):
    subject = "Email for account Activation!"
    message = f"Hi {first_name},\n\nPlease click the link below to activate your account:\n{activation_link}"
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user_email], fail_silently=False)
    
@shared_task 
def send_password_reset_email_task(subject, message, from_email, recipient_list):
    send_mail(subject, message, from_email, recipient_list, fail_silently=False)

User = get_user_model()

@shared_task
def generate_enrollment_report_task(admin_email):
    cache_key = "enrollment_report_csv"
    csv_data = cache.get(cache_key)
    
    if not csv_data:
        enrollments = Enrollment.objects.select_related('student', 'course').all()
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["Student Username", "Student Email", "Course Title", "Enrolled At", "Status"])
        for e in enrollments:
            writer.writerow([e.student.username, e.student.email, e.course.course_title, e.enrolled_at, "Active" if e.is_active else "Inactive"])
        csv_data = buf.getvalue()
        cache.set(cache_key, csv_data, timeout=3600)

    email = EmailMessage("Enrollment Report", "Attached is the enrollment report.", settings.DEFAULT_FROM_EMAIL, [admin_email])
    email.attach("enrollment_report.csv", csv_data, "text/csv")
    email.send(fail_silently=False)
    return f"Enrollment report sent to {admin_email}"

@shared_task
def generate_course_report_task(admin_email):
    cache_key = "course_report_csv"
    csv_data = cache.get(cache_key)
    
    if not csv_data:
        courses = Course.objects.all()
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["Course Title", "Description", "Created At"])
        for c in courses:
            # Safely check for description or course_description field names
            desc = getattr(c, 'description', getattr(c, 'course_description', 'N/A'))
            created = getattr(c, 'created_at', getattr(c, 'date_created', 'N/A'))
            title = getattr(c, 'course_title', getattr(c, 'title', str(c)))
            writer.writerow([title, desc, created])
            
        csv_data = buf.getvalue()
        cache.set(cache_key, csv_data, timeout=3600)

    email = EmailMessage("Course Details Report (CSV)", "Attached is the course details report.", settings.DEFAULT_FROM_EMAIL, [admin_email])
    email.attach("course_report.csv", csv_data, "text/csv")
    email.send(fail_silently=False)
    return f"Course report sent to {admin_email}"

@shared_task
def generate_student_report_task(admin_email):
    cache_key = "student_report_csv"
    csv_data = cache.get(cache_key)
    
    if not cache.get(cache_key):
        students = User.objects.filter(is_staff=False)
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["Username", "First Name", "Last Name", "Email", "Date Joined"])
        for s in students:
            writer.writerow([s.username, s.first_name, s.last_name, s.email, s.date_joined])
        csv_data = buf.getvalue()
        cache.set(cache_key, csv_data, timeout=3600)

    email = EmailMessage("Student Details Report", "Attached is the student details report.", settings.DEFAULT_FROM_EMAIL, [admin_email])
    email.attach("student_report.csv", csv_data, "text/csv")
    email.send(fail_silently=False)
    return f"Student report sent to {admin_email}"