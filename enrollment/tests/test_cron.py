from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.utils import timezone

from courses.models import Course
from enrollment.cron import send_daily_admin_report
from enrollment.models import Enrollment

User = get_user_model()


class TestEnrollmentCronJob(TestCase):

    def test_send_daily_admin_report_sends_csv_attachment(self):
        """Daily cron job must generate a CSV of today's enrollments and email the admin."""
        instructor = User.objects.create_user(
            username='inst@example.com',
            email='inst@example.com',
            password='StrongPassword123!',
            is_staff=True
        )
        student = User.objects.create_user(
            username='stu@example.com',
            email='stu@example.com',
            password='StrongPassword123!'
        )
        now = timezone.now()
        dummy_image = SimpleUploadedFile(
            name='c.jpg',
            content=b'\x47\x49\x46\x38\x39\x61',
            content_type='image/jpeg'
        )
        course = Course.objects.create(
            instructor=instructor,
            course_title='Daily Report Course',
            category='Data',
            description='Desc',
            duration='2 Weeks',
            course_image=dummy_image,
            enrollment_start_date=now - timedelta(days=1),
            enrollment_end_date=now + timedelta(days=5),
            course_start_date=now + timedelta(days=6),
            course_end_date=now + timedelta(days=20),
        )
        Enrollment.objects.create(student=student, course=course)
        mail.outbox.clear()

        send_daily_admin_report()

        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertIn("Daily Platform Activity Report CSV", email.subject)
        self.assertEqual(len(email.attachments), 1)
        _filename, content, mimetype = email.attachments[0]
        self.assertIn("Daily Report Course", content)
        self.assertEqual(mimetype, "text/csv")