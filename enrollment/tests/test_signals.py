from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.utils import timezone

from courses.models import Course
from enrollment.models import Enrollment

User = get_user_model()


class TestEnrollmentSignals(TestCase):

    def setUp(self):
        self.instructor = User.objects.create_user(
            username='instructor@example.com',
            email='instructor@example.com',
            password='StrongPassword123!',
            is_staff=True
        )
        self.student = User.objects.create_user(
            username='student@example.com',
            email='student@example.com',
            first_name='John',
            last_name='Doe',
            password='StrongPassword123!',
            is_staff=False
        )
        now = timezone.now()
        dummy_image = SimpleUploadedFile(
            name='course.jpg',
            content=b'\x47\x49\x46\x38\x39\x61',
            content_type='image/jpeg'
        )
        self.course = Course.objects.create(
            instructor=self.instructor,
            course_title='Python Bootcamp',
            category='Programming',
            description='Learn Python.',
            duration='6 Weeks',
            course_image=dummy_image,
            enrollment_start_date=now - timedelta(days=1),
            enrollment_end_date=now + timedelta(days=10),
            course_start_date=now + timedelta(days=11),
            course_end_date=now + timedelta(days=50),
        )
        mail.outbox.clear()

    def test_enrollment_post_save_signal_sends_confirmation_email(self):
        """Creating a new Enrollment must trigger send_enrollment_email via post_save."""
        Enrollment.objects.create(student=self.student, course=self.course)

        self.assertEqual(len(mail.outbox), 1)
        sent_email = mail.outbox[0]
        self.assertEqual(sent_email.subject, "Successfully Enrolled in Python Bootcamp")
        self.assertEqual(sent_email.to, ['student@example.com'])
        self.assertIn("Hi John Doe,", sent_email.body)

    def test_updating_existing_enrollment_does_not_resend_email(self):
        """Updating an existing Enrollment (created=False) must not send another email."""
        enrollment = Enrollment.objects.create(student=self.student, course=self.course)
        mail.outbox.clear()

        enrollment.is_active = False
        enrollment.save()

        self.assertEqual(len(mail.outbox), 0)