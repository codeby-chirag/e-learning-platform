from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from django.contrib.auth import get_user_model
from django.contrib.messages.storage.fallback import FallbackStorage
from django.core import mail
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory, TestCase
from django.urls import reverse
from django.utils import timezone

from courses.models import Course
from enrollment.models import Enrollment
from enrollment.views import enroll_course_view

User = get_user_model()


class TestEnrollmentViews(TestCase):

    def setUp(self):
        cache.clear()
        self.now = timezone.now()
        self.instructor = User.objects.create_user(
            username='instructor@example.com',
            email='instructor@example.com',
            password='StrongPassword123!',
            is_staff=True
        )
        self.student = User.objects.create_user(
            username='student@example.com',
            email='student@example.com',
            first_name='Jane',
            last_name='Student',
            password='StrongPassword123!',
            is_staff=False
        )
        self.other_student = User.objects.create_user(
            username='other@example.com',
            email='other@example.com',
            password='StrongPassword123!',
            is_staff=False
        )
        self.dummy_image = SimpleUploadedFile(
            name='course.jpg',
            content=b'\x47\x49\x46\x38\x39\x61',
            content_type='image/jpeg'
        )
        self.open_course = Course.objects.create(
            instructor=self.instructor,
            course_title='Open Course',
            category='Web',
            description='Open for enrollment',
            duration='4 Weeks',
            course_image=self.dummy_image,
            enrollment_start_date=self.now - timedelta(days=2),
            enrollment_end_date=self.now + timedelta(days=5),
            course_start_date=self.now + timedelta(days=6),
            course_end_date=self.now + timedelta(days=30),
        )

    def tearDown(self):
        cache.clear()

    @patch('enrollment.views.get_channel_layer')
    def test_enroll_course_success_workflow(self, mock_get_channel_layer):
        """Authenticated student can enroll in an open course and receive WebSocket + email alerts."""
        mock_layer = MagicMock()
        mock_layer.group_send = AsyncMock()
        mock_get_channel_layer.return_value = mock_layer

        self.client.login(username='student@example.com', password='StrongPassword123!')
        mail.outbox.clear()

        url = reverse('enroll_course', kwargs={'pk': self.open_course.pk})
        response = self.client.post(url)

        self.assertRedirects(response, reverse('student_dashboard'))
        self.assertTrue(Enrollment.objects.filter(student=self.student, course=self.open_course).exists())
        self.assertEqual(len(mail.outbox), 1)
        mock_layer.group_send.assert_called_once()

    def test_enroll_course_fails_before_start_date(self):
        """Enrolling before enrollment_start_date must fail and redirect to course_detail."""
        future_course = Course.objects.create(
            instructor=self.instructor,
            course_title='Future Course',
            category='Web',
            description='Not open yet',
            duration='4 Weeks',
            course_image=self.dummy_image,
            enrollment_start_date=self.now + timedelta(days=2),
            enrollment_end_date=self.now + timedelta(days=10),
            course_start_date=self.now + timedelta(days=11),
            course_end_date=self.now + timedelta(days=30),
        )
        self.client.login(username='student@example.com', password='StrongPassword123!')
        url = reverse('enroll_course', kwargs={'pk': future_course.pk})
        response = self.client.post(url, follow=True)

        self.assertFalse(Enrollment.objects.filter(student=self.student, course=future_course).exists())
        messages = [str(m) for m in response.context['messages']]
        self.assertIn("Enrollment failed: The enrollment period has not started yet.", messages)

    def test_enroll_course_fails_after_end_date(self):
        """Enrolling after enrollment_end_date must fail and redirect to course_detail."""
        expired_course = Course.objects.create(
            instructor=self.instructor,
            course_title='Expired Course',
            category='Web',
            description='Deadline passed',
            duration='4 Weeks',
            course_image=self.dummy_image,
            enrollment_start_date=self.now - timedelta(days=10),
            enrollment_end_date=self.now - timedelta(days=1),
            course_start_date=self.now + timedelta(days=1),
            course_end_date=self.now + timedelta(days=30),
        )
        self.client.login(username='student@example.com', password='StrongPassword123!')
        url = reverse('enroll_course', kwargs={'pk': expired_course.pk})
        response = self.client.post(url, follow=True)

        self.assertFalse(Enrollment.objects.filter(student=self.student, course=expired_course).exists())
        messages = [str(m) for m in response.context['messages']]
        self.assertIn("Enrollment failed: The deadline for this course has passed.", messages)

    def test_student_dashboard_view_shows_only_own_enrollments(self):
        """StudentDashboardView must only display courses the logged-in student is enrolled in."""
        Enrollment.objects.create(student=self.student, course=self.open_course)

        self.client.login(username='other@example.com', password='StrongPassword123!')
        response = self.client.get(reverse('student_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['enrollment']), 0)

        self.client.login(username='student@example.com', password='StrongPassword123!')
        response = self.client.get(reverse('student_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['enrollment']), 1)

    def test_enroll_course_view_invalidates_cache(self):
        """enroll_course_view must clear the enrollment_status_<user_id>_<course_pk> cache key."""
        cache_key = f"enrollment_status_{self.student.id}_{self.open_course.pk}"
        cache.set(cache_key, False, timeout=900)

        factory = RequestFactory()
        request = factory.post(f"/enrollments/{self.open_course.pk}/enroll/")
        request.user = self.student
        setattr(request, 'session', 'session')  # noqa: B010
        setattr(request, '_messages', FallbackStorage(request))  # noqa: B010

        response = enroll_course_view(request, pk=self.open_course.pk)

        self.assertEqual(response.status_code, 302)
        self.assertIsNone(cache.get(cache_key))