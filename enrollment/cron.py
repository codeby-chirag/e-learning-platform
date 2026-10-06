import csv
import io
from datetime import date

from django.conf import settings
from django.core.mail import EmailMessage, send_mail

from .models import Enrollment


def send_daily_admin_report():
    today = date.today()  # noqa: DTZ011
    
    # Fetch data items created today
    new_enrollments = Enrollment.objects.filter(enrolled_at__date=today)
    total_new_enrollments = new_enrollments.count()
    
    completed_enrollments = Enrollment.objects.filter(
        is_active=True, 
        updated_at__date=today
    )
    total_completed_courses = completed_enrollments.count()
    
    # Setup a dynamic text buffer to build our CSV file data in memory
    csv_buffer = io.StringIO()
    writer = csv.writer(csv_buffer)
    
    # Write the CSV Header Row
    writer.writerow(['Report Type', 'Student Email', 'Course Name', 'Timestamp / Date'])
    
    # Populate row entries for New Enrollments
    for entry in new_enrollments:
        student_email = getattr(entry.student, 'email', getattr(entry.student, 'username', 'Unknown Student'))
        course_name = str(entry.course)
        writer.writerow(['New Enrollment', student_email, course_name, entry.enrolled_at.strftime('%Y-%m-%d %H:%M')])
        
    # Populate row entries for Completed/Active Updates
    for entry in completed_enrollments:
        student_email = getattr(entry.student, 'email', getattr(entry.student, 'username', 'Unknown Student'))
        course_name = str(entry.course)
        writer.writerow(['Course Completed/Active', student_email, course_name, entry.updated_at.strftime('%Y-%m-%d %H:%M')])
        
    subject = f"Daily Platform Activity Report CSV - {today.strftime('%Y-%m-%d')}"
    
    body = (
        f"Hello Admin,\n\n"
        f"Please find attached the daily platform activity spreadsheet summary report for {today}.\n\n"
        f"Summary Counters:\n"
        f"- New Enrollments: {total_new_enrollments}\n"
        f"- Active Completions: {total_completed_courses}\n\n"
        f"Best regards,\nYour E-Learning Platform Automation Engine"
    )
    
    # Use EmailMessage instead of send_mail to handle attachments smoothly
    email = EmailMessage(
        subject=subject,
        body=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=['chirag.ms46@gmail.com'],
    )
    
    filename = f"daily_report_{today.strftime('%Y-%m-%d')}.csv"
    email.attach(
        filename=filename,
        content=csv_buffer.getvalue(),
        mimetype='text/csv'
    )
    
    csv_buffer.close()
    
    email.send(fail_silently=False)
