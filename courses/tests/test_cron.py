from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.utils import timezone

from courses.cron import announce_new_course_launches, remind_upcoming_deadlines
from courses.models import Course

User = get_user_model()


class TestCourseCronJobs(TestCase):

    def setUp(self):
        self.instructor = User.objects.create_user(
            username='inst@example.com',
            email='inst@example.com',
            password='StrongPassword123!',
            is_staff=True
        )
        self.student = User.objects.create_user(
            username='learner@example.com',
            email='learner@example.com',
            first_name='Alex',
            password='StrongPassword123!',
            is_staff=False
        )
        self.now = timezone.now()
        self.dummy_image = SimpleUploadedFile(
            name='cron.jpg',
            content=b'\x47\x49\x46\x38\x39\x61',
            content_type='image/jpeg'
        )

    def test_announce_new_course_launches_sends_email(self):
        """Cron job must email active students when enrollment_start_date is today."""
        Course.objects.create(
            instructor=self.instructor,
            course_title='Launched Today Course',
            category='AI',
            description='New AI course',
            duration='4 Weeks',
            course_image=self.dummy_image,
            enrollment_start_date=self.now,
            enrollment_end_date=self.now + timedelta(days=10),
            course_start_date=self.now + timedelta(days=11),
            course_end_date=self.now + timedelta(days=40),
        )
        mail.outbox.clear()
        announce_new_course_launches()

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("New Course Alert: Launched Today Course is now LIVE!", mail.outbox[0].subject)

    def test_remind_upcoming_deadlines_sends_email_to_unenrolled_students(self):
        """Cron job must remind unenrolled students when enrollment closes in 3 days."""
        Course.objects.create(
            instructor=self.instructor,
            course_title='Closing Soon Course',
            category='Cloud',
            description='Cloud computing',
            duration='3 Weeks',
            course_image=self.dummy_image,
            enrollment_start_date=self.now - timedelta(days=5),
            enrollment_end_date=self.now + timedelta(days=3),
            course_start_date=self.now + timedelta(days=4),
            course_end_date=self.now + timedelta(days=25),
        )
        mail.outbox.clear()
        remind_upcoming_deadlines()

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Only 3 days left to enroll in Closing Soon Course!", mail.outbox[0].subject)