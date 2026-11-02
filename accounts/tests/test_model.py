from datetime import date
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError
from django.test import TestCase

from accounts.models import UserActivityLog, UserProfile


class UserProfileModelTest(TestCase):
    def setUp(self):
        # post_save signal automatically creates a UserProfile for self.user
        self.user = User.objects.create_user(
            username="johndoe",
            password="testpassword123",
            first_name="John",
            last_name="Doe",
        )
        self.profile = UserProfile.objects.get(user=self.user)

    def test_signal_auto_creates_user_profile(self):
        """Test that creating a User automatically creates an associated UserProfile."""
        self.assertIsNotNone(self.profile)
        self.assertEqual(self.profile.user, self.user)

    def test_update_user_profile_with_all_fields(self):
        """Test populating all optional fields on the UserProfile."""
        dummy_image = SimpleUploadedFile(
            name="test_avatar.jpg",
            content=b"\x47\x49\x46\x38\x39\x61",
            content_type="image/jpeg",
        )
        self.profile.gender = "Male"
        self.profile.birthdate = date(1998, 5, 20)
        self.profile.profile_pic = dummy_image
        self.profile.mobile_number = "9876543210"
        self.profile.save()

        self.profile.refresh_from_db()
        self.assertEqual(self.profile.user.username, "johndoe")
        self.assertEqual(self.profile.gender, "Male")
        self.assertEqual(self.profile.birthdate, date(1998, 5, 20))
        self.assertEqual(self.profile.mobile_number, "9876543210")
        self.assertTrue(self.profile.profile_pic.name.startswith("images/test_avatar"))

    def test_user_profile_str_representation(self):
        """Test the __str__ method returns '<first_name> <last_name>'s Profile'."""
        self.assertEqual(str(self.profile), "John Doe's Profile")

    def test_one_to_one_constraint(self):
        """Test that creating a second UserProfile for the same User raises IntegrityError."""
        with self.assertRaises(IntegrityError):
            UserProfile.objects.create(user=self.user)

    def test_cascade_delete_from_user(self):
        """Test that deleting the User deletes the associated UserProfile."""
        self.user.delete()
        self.assertEqual(UserProfile.objects.count(), 0)

    def test_calculate_age_without_birthdate(self):
        """Test calculate_age returns None when birthdate is not set."""
        self.profile.birthdate = None
        self.profile.save()
        self.assertIsNone(self.profile.calculate_age())

    @patch("accounts.models.date")
    def test_calculate_age_before_birthday_this_year(self, mock_date):
        """Test calculate_age when today's date is before the user's birthday this year."""
        mock_date.today.return_value = date(2026, 5, 10)
        # Birthday is October 15 (has not happened yet in May 2026)
        self.profile.birthdate = date(2000, 10, 15)
        self.profile.save()
        self.assertEqual(self.profile.calculate_age(), 25)

    @patch("accounts.models.date")
    def test_calculate_age_after_birthday_this_year(self, mock_date):
        """Test calculate_age when today's date is on or after the user's birthday."""
        mock_date.today.return_value = date(2026, 10, 20)
        # Birthday was October 15 (already passed in October 2026)
        self.profile.birthdate = date(2000, 10, 15)
        self.profile.save()
        self.assertEqual(self.profile.calculate_age(), 26)


class UserActivityLogModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="janedoe",
            password="testpassword123",
        )

    def test_create_activity_log(self):
        """Test creating an activity log entry linked to a user."""
        log = UserActivityLog.objects.create(
            user=self.user,
            path="/dashboard/",
            method="GET",
            status_code=200,
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
        )
        self.assertEqual(log.user, self.user)
        self.assertEqual(log.path, "/dashboard/")
        self.assertEqual(log.method, "GET")
        self.assertEqual(log.status_code, 200)
        self.assertEqual(log.ip_address, "192.168.1.1")
        self.assertIsNotNone(log.timestamp)
        self.assertIn(log, self.user.activity_logs.all())

    def test_set_null_on_user_delete(self):
        """Test that deleting the User keeps the activity log and sets user to None."""
        log = UserActivityLog.objects.create(
            user=self.user,
            path="/login/",
            method="POST",
            status_code=302,
        )
        self.user.delete()
        log.refresh_from_db()
        self.assertIsNone(log.user)
        self.assertEqual(UserActivityLog.objects.count(), 1)

    def test_activity_log_ordering(self):
        """Test that logs are ordered from newest to oldest (-timestamp)."""
        log1 = UserActivityLog.objects.create(
            user=self.user, path="/first/", method="GET", status_code=200
        )
        log2 = UserActivityLog.objects.create(
            user=self.user, path="/second/", method="GET", status_code=200
        )
        logs = list(UserActivityLog.objects.all())
        self.assertEqual(logs[0], log2)
        self.assertEqual(logs[1], log1)