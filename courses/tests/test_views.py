from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from courses.models import Course

User = get_user_model()

VALID_GIF_BYTES = (
    b"\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\x05\x04\x04"
    b"\x00\x00\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02\x44"
    b"\x01\x00\x3b"
)


class TestCourseViewsAndPermissions(TestCase):

    def setUp(self):
        cache.clear()
        self.now = timezone.now()

        # Admin / Instructor with all custom course permissions
        self.instructor = User.objects.create_user(
            username='instructor@example.com',
            email='instructor@example.com',
            password='StrongPassword123!',
            is_staff=True
        )
        perms = Permission.objects.filter(
            codename__in=['can_create_courses', 'can_edit_courses', 'can_delete_courses']
        )
        self.instructor.user_permissions.add(*perms)

        # Staff user WITHOUT custom course permissions
        self.staff_without_perms = User.objects.create_user(
            username='staff_no_perm@example.com',
            email='staff_no_perm@example.com',
            password='StrongPassword123!',
            is_staff=True
        )

        # Regular Student user
        self.student = User.objects.create_user(
            username='student@example.com',
            email='student@example.com',
            password='StrongPassword123!',
            is_staff=False
        )

        self.dummy_image = SimpleUploadedFile(
            name='test_course.gif',
            content=VALID_GIF_BYTES,
            content_type='image/gif'
        )

        self.course = Course.objects.create(
            instructor=self.instructor,
            course_title='Initial Course',
            category='Programming',
            description='Initial Description',
            duration='4 Weeks',
            course_image=self.dummy_image,
            enrollment_start_date=self.now - timedelta(days=1),
            enrollment_end_date=self.now + timedelta(days=5),
            course_start_date=self.now + timedelta(days=6),
            course_end_date=self.now + timedelta(days=30),
        )

    def tearDown(self):
        cache.clear()

    def test_course_list_view(self):
        """CourseListView must return 200 and display existing courses."""
        response = self.client.get(reverse('course_list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'courses/course_list.html')
        self.assertIn(self.course, response.context['courses'])

    def test_course_create_denied_for_student_and_unprivileged_staff(self):
        """Students and staff without 'can_create_courses' permission must get 403."""
        self.client.login(username='student@example.com', password='StrongPassword123!')
        response = self.client.get(reverse('course_create'))
        self.assertEqual(response.status_code, 403)

        self.client.login(username='staff_no_perm@example.com', password='StrongPassword123!')
        response = self.client.get(reverse('course_create'))
        self.assertEqual(response.status_code, 403)

    @patch('courses.views.get_channel_layer')
    def test_course_create_success_with_permission(self, mock_get_channel_layer):
        """Authorized instructor can create a course and trigger WebSocket announcement."""
        mock_layer = MagicMock()
        mock_layer.group_send = AsyncMock()
        mock_get_channel_layer.return_value = mock_layer

        self.client.login(username='instructor@example.com', password='StrongPassword123!')

        new_image = SimpleUploadedFile(
            name='new_course.gif',
            content=VALID_GIF_BYTES,
            content_type='image/gif'
        )
        post_data = {
            'course_title': 'Advanced FastAPI',
            'category': 'Backend',
            'description': 'Build async APIs.',
            'duration': '5 Weeks',
            'course_image': new_image,
            'enrollment_start_date': self.now.strftime('%Y-%m-%dT%H:%M'),
            'enrollment_end_date': (self.now + timedelta(days=5)).strftime('%Y-%m-%dT%H:%M'),
            'course_start_date': (self.now + timedelta(days=6)).strftime('%Y-%m-%dT%H:%M'),
            'course_end_date': (self.now + timedelta(days=40)).strftime('%Y-%m-%dT%H:%M'),
        }

        response = self.client.post(reverse('course_create'), data=post_data)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Course.objects.filter(course_title='Advanced FastAPI').exists())
        mock_layer.group_send.assert_called_once()

    def test_course_update_view_with_permission(self):
        """Authorized instructor can update a course."""
        self.client.login(username='instructor@example.com', password='StrongPassword123!')
        update_image = SimpleUploadedFile(
            name='updated.gif',
            content=VALID_GIF_BYTES,
            content_type='image/gif'
        )
        update_data = {
            'course_title': 'Updated Course Title',
            'category': 'Programming',
            'description': 'Updated Description',
            'duration': '4 Weeks',
            'course_image': update_image,
            'enrollment_start_date': self.now.strftime('%Y-%m-%dT%H:%M'),
            'enrollment_end_date': (self.now + timedelta(days=5)).strftime('%Y-%m-%dT%H:%M'),
            'course_start_date': (self.now + timedelta(days=6)).strftime('%Y-%m-%dT%H:%M'),
            'course_end_date': (self.now + timedelta(days=30)).strftime('%Y-%m-%dT%H:%M'),
        }
        url = reverse('course_update', kwargs={'pk': self.course.pk})
        response = self.client.post(url, data=update_data)

        self.assertEqual(response.status_code, 302)
        self.course.refresh_from_db()
        self.assertEqual(self.course.course_title, 'Updated Course Title')

    def test_course_delete_view_with_permission(self):
        """Authorized instructor can delete a course."""
        self.client.login(username='instructor@example.com', password='StrongPassword123!')
        url = reverse('course_delete', kwargs={'pk': self.course.pk})
        response = self.client.post(url)

        self.assertEqual(response.status_code, 302)
        self.assertFalse(Course.objects.filter(pk=self.course.pk).exists())

    def test_course_detail_view_caches_enrollment_status(self):
        """CourseDetailView must cache 'enrollment_status_<user_id>_<course_pk>'."""
        self.client.login(username='student@example.com', password='StrongPassword123!')
        cache_key = f"enrollment_status_{self.student.id}_{self.course.pk}"

        self.assertIsNone(cache.get(cache_key))

        # 1st request: Cache miss -> computes False and stores in cache
        response = self.client.get(reverse('course_detail', kwargs={'pk': self.course.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['is_enrolled'])
        self.assertEqual(cache.get(cache_key), False)

        # 2nd request: Cache hit -> force cache value to True and verify context uses cache
        cache.set(cache_key, True, timeout=900)
        response2 = self.client.get(reverse('course_detail', kwargs={'pk': self.course.pk}))
        self.assertTrue(response2.context['is_enrolled'])