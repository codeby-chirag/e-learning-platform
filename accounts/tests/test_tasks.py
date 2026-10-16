from django.contrib.auth import get_user_model
from django.core import mail
from django.core.cache import cache
from django.test import TestCase

from accounts.tasks import (
    generate_course_report_task,
    generate_enrollment_report_task,
    generate_student_report_task,
    send_activation_email_task,
    send_password_reset_email_task,
)

User = get_user_model()


class TestEmailNotificationTasks(TestCase):

    def test_send_activation_email_task(self):
        """Task must send an activation email with the user's first name and activation link."""
        send_activation_email_task(
            user_email='student@example.com',
            activation_link='http://localhost:8000/activate/uid/token/',
            first_name='John'
        )

        self.assertEqual(len(mail.outbox), 1)
        sent_email = mail.outbox[0]
        self.assertEqual(sent_email.subject, "Email for account Activation!")
        self.assertEqual(sent_email.to, ['student@example.com'])
        self.assertIn("Hi John,", sent_email.body)
        self.assertIn("http://localhost:8000/activate/uid/token/", sent_email.body)

    def test_send_password_reset_email_task(self):
        """Task must send the password reset email to the recipient list."""
        send_password_reset_email_task(
            subject="Password reset on localhost",
            message="Reset your password here.",
            from_email="webmaster@localhost",
            recipient_list=['reset@example.com']
        )

        self.assertEqual(len(mail.outbox), 1)
        sent_email = mail.outbox[0]
        self.assertEqual(sent_email.subject, "Password reset on localhost")
        self.assertEqual(sent_email.to, ['reset@example.com'])
        self.assertEqual(sent_email.body, "Reset your password here.")


class TestReportTasksAndCaching(TestCase):

    def setUp(self):
        cache.clear()
        self.admin_email = 'admin@example.com'
        self.student = User.objects.create_user(
            username='johndoe',
            email='johndoe@example.com',
            first_name='John',
            last_name='Doe',
            password='StrongPassword123!',
            is_staff=False
        )

    def tearDown(self):
        cache.clear()

    def test_generate_student_report_task_cache_miss_and_email(self):
        """On cache miss, task must generate student CSV, cache it, and email the attachment."""
        self.assertIsNone(cache.get("student_report_csv"))

        result = generate_student_report_task(self.admin_email)

        self.assertEqual(result, f"Student report sent to {self.admin_email}")
        # Verify cache was populated
        cached_csv = cache.get("student_report_csv")
        self.assertIsNotNone(cached_csv)
        self.assertIn("johndoe", cached_csv)

        # Verify email and CSV attachment
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.subject, "Student Details Report")
        self.assertEqual(email.to, [self.admin_email])
        self.assertEqual(len(email.attachments), 1)
        filename, content, mimetype = email.attachments[0]
        self.assertEqual(filename, "student_report.csv")
        self.assertIn("johndoe@example.com", content)
        self.assertEqual(mimetype, "text/csv")

    def test_generate_student_report_task_uses_cached_data(self):
        """On cache hit, task must attach the existing cached CSV without regenerating it."""
        custom_cached_csv = "Username,First Name,Last Name,Email,Date Joined\ncached_user,Cached,User,c@example.com,2026-01-01\n"
        cache.set("student_report_csv", custom_cached_csv, timeout=3600)

        generate_student_report_task(self.admin_email)

        self.assertEqual(len(mail.outbox), 1)
        _, content, _ = mail.outbox[0].attachments[0]
        self.assertEqual(content, custom_cached_csv)

    def test_generate_course_report_task_caches_and_sends_email(self):
        """Task must generate course_report.csv, store it in cache, and send email."""
        self.assertIsNone(cache.get("course_report_csv"))

        result = generate_course_report_task(self.admin_email)

        self.assertEqual(result, f"Course report sent to {self.admin_email}")
        self.assertIsNotNone(cache.get("course_report_csv"))
        self.assertEqual(len(mail.outbox), 1)
        filename, content, _ = mail.outbox[0].attachments[0]
        self.assertEqual(filename, "course_report.csv")
        self.assertIn("Course Title,Description,Created At", content)

    def test_generate_enrollment_report_task_caches_and_sends_email(self):
        """Task must generate enrollment_report.csv, store it in cache, and send email."""
        self.assertIsNone(cache.get("enrollment_report_csv"))

        result = generate_enrollment_report_task(self.admin_email)

        self.assertEqual(result, f"Enrollment report sent to {self.admin_email}")
        self.assertIsNotNone(cache.get("enrollment_report_csv"))
        self.assertEqual(len(mail.outbox), 1)
        filename, content, _ = mail.outbox[0].attachments[0]
        self.assertEqual(filename, "enrollment_report.csv")
        self.assertIn("Student Username,Student Email,Course Title,Enrolled At,Status", content)
        
        
        
        
        