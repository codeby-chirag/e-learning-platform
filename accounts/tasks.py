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

# @shared_task
# def generate_enrollment_report_task(admin_email):
#     cache_key = "enrollment_report_csv"
#     csv_data = cache.get(cache_key)
    
#     if not csv_data:
#         enrollments = Enrollment.objects.select_related('student', 'course').all()
#         buf = io.StringIO()
#         writer = csv.writer(buf)
#         writer.writerow(["Student Username", "Student Email", "Course Title", "Enrolled At", "Status"])
#         for e in enrollments:
#             writer.writerow([e.student.username, e.student.email, e.course.course_title, e.enrolled_at, "Active" if e.is_active else "Inactive"])
#         csv_data = buf.getvalue()
#         cache.set(cache_key, csv_data, timeout=3600)

#     email = EmailMessage("Enrollment Report", "Attached is the enrollment report.", settings.DEFAULT_FROM_EMAIL, [admin_email])
#     email.attach("enrollment_report.csv", csv_data, "text/csv")
#     email.send(fail_silently=False)
#     return f"Enrollment report sent to {admin_email}"

@shared_task
def generate_enrollment_report_task(admin_email):
    print(f"🚀 [TASK STARTED] Processing enrollment report for {admin_email}...")
    
    cache_key = "enrollment_report_csv"
    csv_data = cache.get(cache_key)

    if csv_data:
        print("🟢 [CACHE HIT] Found pre-built CSV in Redis cache! Skipping database query.")
    else:
        print("🔴 [CACHE MISS] Querying MySQL database using iterator stream...")
        
        enrollments = (
            Enrollment.objects.values_list(
                'student__username', 
                'student__email', 
                'course__course_title', 
                'enrolled_at', 
                'is_active'
            )
            .iterator(chunk_size=5000)
        )

        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["Student Username", "Student Email", "Course Title", "Enrolled At", "Status"])

        print("📦 [PROCESSING] Streaming rows into CSV buffer...")
        writer.writerows(
            (username, email, course_title, enrolled_at, "Active" if is_active else "Inactive")
            for username, email, course_title, enrolled_at, is_active in enrollments
        )

        csv_data = buf.getvalue()
        cache.set(cache_key, csv_data, timeout=3600)  # Save to Redis cache for 1 hour
        print("💾 [CACHED] CSV data successfully stored in Redis RAM.")

    print("📧 [SENDING EMAIL] Connecting to SMTP and attaching CSV report...")
    email = EmailMessage(
        "Enrollment Report", 
        "Attached is the enrollment report.", 
        settings.DEFAULT_FROM_EMAIL, 
        [admin_email]
    )
    email.attach("enrollment_report.csv", csv_data, "text/csv")
    email.send(fail_silently=False)
    
    print(f"✅ [COMPLETED] Enrollment report sent perfectly to {admin_email}!")
    return f"Enrollment report sent to {admin_email}"

def _send_part(part, header, chunk, admin_email):
    t = time.perf_counter()
    text = build_csv(header, chunk)
    send_csv(f"Enrollment Report (part {part})", "Attached is the enrollment report.",
             f"enrollment_part_{part}.csv", text, admin_email)
    log.warning("part %d: %.1f MB sent in %.1fs", part, len(text) / 1e6, time.perf_counter() - t)

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

# @shared_task
# def generate_student_report_task(admin_email):
#     cache_key = "student_report_csv"
#     csv_data = cache.get(cache_key)
    
#     if not cache.get(cache_key):
#         students = User.objects.filter(is_staff=False)
#         buf = io.StringIO()
#         writer = csv.writer(buf)
#         writer.writerow(["Username", "First Name", "Last Name", "Email", "Date Joined"])
#         for s in students:
#             writer.writerow([s.username, s.first_name, s.last_name, s.email, s.date_joined])
#         csv_data = buf.getvalue()
#         cache.set(cache_key, csv_data, timeout=3600)

#     email = EmailMessage("Student Details Report", "Attached is the student details report.", settings.DEFAULT_FROM_EMAIL, [admin_email])
#     email.attach("student_report.csv", csv_data, "text/csv")
#     email.send(fail_silently=False)
#     return f"Student report sent to {admin_email}"



import csv, io, time, logging
from celery import shared_task
from django.conf import settings
from django.core.cache import cache
from django.core.mail import EmailMessage

log = logging.getLogger(__name__)

def build_csv(header, rows):
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(header)
    w.writerows(rows)
    return buf.getvalue()

def send_csv(subject, body, filename, csv_text, to_email):
    email = EmailMessage(subject, body, settings.DEFAULT_FROM_EMAIL, [to_email])
    email.attach(filename, csv_text, "text/csv")      # direct CSV, no zip
    email.send(fail_silently=False)

@shared_task(time_limit=900)
def generate_student_report_task(admin_email):
    t0 = time.perf_counter()
    csv_text = cache.get("student_report_csv")
    if not csv_text:
        rows = (User.objects.filter(is_staff=False)
                .values_list("username", "first_name", "last_name", "email", "date_joined")
                .iterator(chunk_size=5000))
        csv_text = build_csv(["Username", "First Name", "Last Name", "Email", "Date Joined"], rows)
        cache.set("student_report_csv", csv_text, timeout=3600)
    t1 = time.perf_counter()
    send_csv("Student Details Report", "Attached is the student details report.",
             "student_report.csv", csv_text, admin_email)
    log.warning("student report: build %.1fs, send %.1fs, %.1f MB",
                t1 - t0, time.perf_counter() - t1, len(csv_text) / 1e6)
    return f"Student report sent to {admin_email}"


