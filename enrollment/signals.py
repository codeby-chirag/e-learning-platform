from django.conf import settings
from django.core.mail import send_mail
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Enrollment


@receiver(post_save, sender=Enrollment)
def send_enrollment_email(sender, instance, created, **kwargs):
  
    # Automatically execute when a new Enrollment obj is created.
    if created:
        subject = f"Successfully Enrolled in {instance.course.course_title}"
        message = (
            f"Hi {instance.student.first_name} {instance.student.last_name},\n\n"
            f"You have successfully enrolled in '{instance.course.course_title}' on EduParadise.\n"
            f"You can view your course materials anytime from your student dashboard.\n\n"
            f"Happy Learning!\n"
            f"The EduParadise Team"
        )
        recipient_list = [instance.student.email]

        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipient_list,
            fail_silently=False,
        )