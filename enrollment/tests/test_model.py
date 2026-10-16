from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone

from courses.models import Course
from enrollment.models import Enrollment

User = get_user_model()


class TestEnrollmentModel(TestCase):

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

    def test_enrollment_creation_and_str(self):
        """Test creating an Enrollment record and its string representation."""
        enrollment = Enrollment.objects.create(student=self.student, course=self.course)
        self.assertTrue(enrollment.is_active)
        self.assertIsNotNone(enrollment.enrolled_at)
        self.assertEqual(str(enrollment), f"{self.student} enrolled in {self.course}")

    def test_unique_together_constraint_prevents_duplicate_enrollment(self):
        """A student cannot have two Enrollment rows for the same course."""
        Enrollment.objects.create(student=self.student, course=self.course)
        with self.assertRaises(IntegrityError):
            Enrollment.objects.create(student=self.student, course=self.course)