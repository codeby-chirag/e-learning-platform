from datetime import date, timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail

from enrollment.models import Enrollment

from .models import Course

User = get_user_model()

# REMIND ABOUT UPCOMING ENROLLMENT DEADLINES
def remind_upcoming_deadlines():
    # Target exactly 3 days into the future
    target_date = date.today() + timedelta(days=3)  # noqa: DTZ011
    
    # Find courses whose enrollment closes on that target date
    closing_courses = Course.objects.filter(enrollment_end_date__date=target_date)
    
    for course in closing_courses:
        students = User.objects.filter(is_active=True, is_staff=False)
        
        for student in students:
            # Check if student is already enrolled to avoid spamming them
            already_enrolled = Enrollment.objects.filter(student=student, course=course).exists()
            
            if not already_enrolled and student.email:
                subject = f"Only 3 days left to enroll in {course.course_title}!"
                message = (
                    f"Hi {student.first_name or 'Student'},\n\n"
                    f"Don't miss out! Enrollment for our course '{course.course_title}' "
                    f"closes on {course.enrollment_end_date.strftime('%B %d, %Y')}.\n\n"
                    f"Category: {course.category}\n"
                    f"Duration: {course.duration}\n\n"
                    f"Click here to secure your spot before time runs out!"
                )
                
                send_mail(
                    subject=subject,
                    message=message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[student.email],
                    fail_silently=True  
                )


# ANNOUNCE NEW COURSE LAUNCHES
def announce_new_course_launches():
    today = date.today()  # noqa: DTZ011
    
    # Find courses whose enrollment opens exactly today
    launched_today = Course.objects.filter(enrollment_start_date__date=today)
    
    for course in launched_today:
        # Grab all standard active students on your platform
        all_students = User.objects.filter(is_active=True, is_staff=False)
        
        for student in all_students:
            if student.email:
                subject = f"New Course Alert: {course.course_title} is now LIVE!"
                message = (
                    f"Hi {student.first_name or 'Learner'},\n\n"
                    f"We are excited to announce a brand new course on our platform:\n\n"
                    f"{course.course_title}\n"
                    f"Category: {course.category}\n"
                    f"Duration: {course.duration}\n\n"
                    f"Description:\n{course.description}\n\n"
                    f"Enrollment opens today! Log into your dashboard to start learning."
                )
                
                # Send out single blast to this specific student
                send_mail(
                    subject=subject,
                    message=message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[student.email],
                    fail_silently=True
                )