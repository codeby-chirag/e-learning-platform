from datetime import timedelta

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.utils import timezone

from courses.forms import CourseForm

VALID_GIF_BYTES = (
    b"\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\x05\x04\x04"
    b"\x00\x00\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02\x44"
    b"\x01\x00\x3b"
)


class TestCourseForm(TestCase):

    def setUp(self):
        self.now = timezone.now()
        self.valid_image = SimpleUploadedFile(
            name='form_test.gif',
            content=VALID_GIF_BYTES,
            content_type='image/gif'
        )
        self.valid_data = {
            'course_title': 'Python for Data Science',
            'category': 'Data Science',
            'description': 'Comprehensive Python course.',
            'duration': '8 Weeks',
            'enrollment_start_date': self.now.strftime('%Y-%m-%dT%H:%M'),
            'enrollment_end_date': (self.now + timedelta(days=5)).strftime('%Y-%m-%dT%H:%M'),
            'course_start_date': (self.now + timedelta(days=6)).strftime('%Y-%m-%dT%H:%M'),
            'course_end_date': (self.now + timedelta(days=60)).strftime('%Y-%m-%dT%H:%M'),
        }

    def test_course_form_valid_data(self):
        """CourseForm must be valid when all required fields and image are provided."""
        form = CourseForm(data=self.valid_data, files={'course_image': self.valid_image})
        self.assertTrue(form.is_valid(), msg=form.errors.as_text())

    def test_course_form_missing_required_fields(self):
        """CourseForm must fail validation when required fields are empty."""
        form = CourseForm(data={}, files={})
        self.assertFalse(form.is_valid())
        self.assertIn('course_title', form.errors)
        self.assertIn('category', form.errors)
        self.assertIn('course_image', form.errors)