from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.utils import timezone

from courses.models import Course

User = get_user_model()


class TestCourseModel(TestCase):

    def setUp(self):
        self.instructor = User.objects.create_user(
            username='instructor@example.com',
            email='instructor@example.com',
            password='StrongPassword123!',
            is_staff=True
        )
        self.now = timezone.now()
        self.dummy_image = SimpleUploadedFile(
            name='course_banner.jpg',
            content=b'\x47\x49\x46\x38\x39\x61',
            content_type='image/jpeg' 
        )
        self.course = Course.objects.create(
            instructor=self.instructor,
            course_title='Django Masterclass',
            category='Web Development',
            description='Learn Django from scratch.',
            duration='6 Weeks',
            course_image=self.dummy_image,
            enrollment_start_date=self.now,
            enrollment_end_date=self.now + timedelta(days=7),
            course_start_date=self.now + timedelta(days=8),
            course_end_date=self.now + timedelta(days=50),
        )

    def test_course_creation_and_fields(self):
        """Test that Course fields are saved properly."""
        self.assertEqual(self.course.instructor, self.instructor)
        self.assertEqual(self.course.course_title, 'Django Masterclass')
        self.assertEqual(self.course.category, 'Web Development')
        self.assertEqual(self.course.duration, '6 Weeks')

    def test_course_str_representation(self):
        """Course __str__ method must return the course_title."""
        self.assertEqual(str(self.course), 'Django Masterclass')

    def test_cascade_delete_when_instructor_deleted(self):
        """Deleting the instructor User must delete their created courses."""
        self.instructor.delete()
        self.assertEqual(Course.objects.count(), 0)