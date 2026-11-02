from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.test import TestCase
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

User = get_user_model()

class TestHomePage(TestCase):
    
    def test_home_view_status_and_template(self):
        response = self.client.get(reverse('home'))
        
        self.assertEqual(response.status_code, 200)
        
        self.assertTemplateUsed(response, 'accounts/welcome.html')
        
        
    def test_signup_success_view_status_and_template(self):
        response = self.client.get(reverse('signup_success'))
        
        self.assertEqual(response.status_code, 200)
        
        self.assertTemplateUsed(response, 'accounts/signup_success.html')
        

    @patch('accounts.views.send_activation_email_task.delay')
    def test_signup_view(self, mock_celery_task):
        signup_data = {
            'email': 'valid@example.com',
            'password': 'StrongPassword123!',
            'firstname': 'John',
            'lastname': 'Doe',
            'mobile_number': '1234567890',
            'birthdate': '1998-05-20',
            'gender': 'Male'
        }

        response = self.client.post(reverse('signup'), data=signup_data)


        self.assertEqual(response.status_code, 302)

        # Assert the user was actually created and saved to the database
        self.assertTrue(User.objects.filter(email='valid@example.com').exists())

        user = User.objects.get(email='valid@example.com')

        self.assertFalse(user.is_active)

        # Verify Celery activation email task was triggered
        mock_celery_task.assert_called_once()

    def test_signup_view_get_request(self):
        response = self.client.get(reverse('signup'))

        self.assertEqual(response.status_code, 200)

        self.assertTemplateUsed(response, 'accounts/signup.html')


class TestProfileView(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username='johndoe@example.com',
            email='johndoe@example.com',
            password='StrongPassword123!'
        )

    def test_profile_view_redirects_if_not_logged_in(self):
        """Unauthenticated user should be redirected to the login page."""
        response = self.client.get(reverse('profile'))

        self.assertEqual(response.status_code, 302)

    def test_profile_view_accessible_when_logged_in(self):
        """Authenticated user should see the profile page."""
        self.client.login(username='johndoe@example.com', password='StrongPassword123!')

        response = self.client.get(reverse('profile'))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/profile.html')


class TestActivateEmailView(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username='inactive@example.com',
            email='inactive@example.com',
            password='StrongPassword123!',
            is_active=False
        )
        self.uidb64 = urlsafe_base64_encode(force_bytes(self.user.pk))
        self.valid_token = default_token_generator.make_token(self.user)

    def test_activate_email_view_valid_token(self):
        """Valid uidb64 and token must activate the user account (is_active=True)."""
        url = reverse('activate', kwargs={'uidb64': self.uidb64, 'token': self.valid_token})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)

        self.user.refresh_from_db()
        self.assertTrue(self.user.is_active)
        self.assertIn(b"Email activated successfully!", response.content)

    def test_activate_email_view_invalid_token(self):
        """Invalid token must return 400 status and keep user inactive."""
        url = reverse('activate', kwargs={'uidb64': self.uidb64, 'token': 'invalid-token-123'})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 400)

        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)
        self.assertIn(b"Activation link is invalid or has expired.", response.content)

    def test_activate_email_view_invalid_uid(self):
        """Non-existent user uidb64 must return 400 status safely."""
        invalid_uid = urlsafe_base64_encode(force_bytes(99999))
        url = reverse('activate', kwargs={'uidb64': invalid_uid, 'token': self.valid_token})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 400)
        self.assertIn(b"Activation link is invalid or has expired.", response.content)


class TestRequestPlatformReportView(TestCase):

    def setUp(self):
        self.staff_user = User.objects.create_user(
            username='admin@example.com',
            email='admin@example.com',
            password='StrongPassword123!',
            is_staff=True
        )
        self.normal_user = User.objects.create_user(
            username='student@example.com',
            email='student@example.com',
            password='StrongPassword123!',
            is_staff=False
        )
        self.url = reverse('request_platform_report')

    def test_report_view_denies_non_staff_user(self):
        """Non-staff users should be redirected away by @staff_member_required."""
        self.client.login(username='student@example.com', password='StrongPassword123!')
        response = self.client.post(self.url, data={'report_type': 'enrollment'})

        self.assertEqual(response.status_code, 403)

    @patch('accounts.views.generate_enrollment_report_task.delay')
    def test_request_enrollment_report_triggers_celery(self, mock_enrollment_task):
        """Staff requesting 'enrollment' report must trigger generate_enrollment_report_task."""
        self.client.login(username='admin@example.com', password='StrongPassword123!')
        response = self.client.post(self.url, data={'report_type': 'enrollment'})

        self.assertEqual(response.status_code, 302)
        mock_enrollment_task.assert_called_once_with('admin@example.com')

    @patch('accounts.views.generate_course_report_task.delay')
    def test_request_course_report_triggers_celery(self, mock_course_task):
        """Staff requesting 'course' report must trigger generate_course_report_task."""
        self.client.login(username='admin@example.com', password='StrongPassword123!')
        response = self.client.post(self.url, data={'report_type': 'course'})

        self.assertEqual(response.status_code, 302)
        mock_course_task.assert_called_once_with('admin@example.com')

    @patch('accounts.views.generate_student_report_task.delay')
    def test_request_student_report_triggers_celery(self, mock_student_task):
        """Staff requesting 'student' report must trigger generate_student_report_task."""
        self.client.login(username='admin@example.com', password='StrongPassword123!')
        response = self.client.post(self.url, data={'report_type': 'student'})

        self.assertEqual(response.status_code, 302)
        mock_student_task.assert_called_once_with('admin@example.com')

    def test_request_invalid_report_type(self):
        """Invalid report_type should redirect without triggering any Celery task."""
        self.client.login(username='admin@example.com', password='StrongPassword123!')
        response = self.client.post(self.url, data={'report_type': 'unknown_type'}, follow=True)

        self.assertEqual(response.status_code, 200)
        messages = list(response.context['messages'])
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Please select a valid report type.")
        
        
        
        
        
        
        
