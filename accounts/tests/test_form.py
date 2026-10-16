from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import RequestFactory, TestCase

from accounts.forms import (
    CustomAuthenticationForm,
    CustomPasswordResetForm,
    UserRegistrationForm,
)
from accounts.models import UserProfile

User = get_user_model()

class TestUserRegistrationFormRemaining(TestCase):

    def setUp(self):
        """Setup valid default payload data to modify for various edge cases."""
        self.valid_base_data = {
            'email': 'valid@example.com',
            'password': 'StrongPassword123!',
            'firstname': 'John',
            'lastname': 'Doe',
            'mobile_number': '1234567890',
            'birthdate': '1998-05-20',
            'gender': 'Male'
        }

    def test_clean_email_case_insensitivity(self):
        """Form must catch duplicate emails regardless of character casing (iexact)."""
        User.objects.create_user(username='JohnDoe@Example.com', email='JohnDoe@Example.com')

        form_data = self.valid_base_data.copy()
        form_data['email'] = 'johndoe@example.com'
        
        form = UserRegistrationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)
        self.assertEqual(form.errors['email'], ["An account with this email already exists."])

    def test_clean_email_duplicate_in_profile_only(self):
        """Form must check clean_email against existing UserProfile records as well."""
        # Create a user. Your post-save signal will automatically generate their userprofile.
        other_user = User.objects.create_user(username='otheruser', email='other@example.com')
        
        # Safely grab the profile generated automatically by your project signal
        profile = other_user.userprofile
        
        profile.mobile_number = '7418529635'
        profile.gender = 'Male'
        profile.birthdate = '1990-01-01'
        profile.save()
        
        # Update the user's email to the target duplicate string
        other_user.email = 'profileduplicate@example.com'
        other_user.save()

        # Attempt to register a brand new account using that same email
        form_data = self.valid_base_data.copy()
        form_data['email'] = 'profileduplicate@example.com'
        
        form = UserRegistrationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors['email'], ["An account with this email already exists."])


    def test_fields_max_length_exceeded(self):
        """Fields must reject strings that exceed character constraints."""
        form_data = self.valid_base_data.copy()
        form_data['firstname'] = 'A' * 151      
        form_data['lastname'] = 'B' * 151       
        form_data['mobile_number'] = '1' * 16   

        form = UserRegistrationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('firstname', form.errors)
        self.assertIn('lastname', form.errors)
        self.assertIn('mobile_number', form.errors)

    def test_gender_invalid_choice_selection(self):
        """ChoiceFields must throw a validation error if external arbitrary options are provided."""
        form_data = self.valid_base_data.copy()
        form_data['gender'] = 'Other'  # Not present in your defined choices ['Male', 'Female']

        form = UserRegistrationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('gender', form.errors)
        self.assertEqual(
            form.errors['gender'], 
            ['Select a valid choice. Other is not one of the available choices.']
        )

    # PASSWORD RULE BOUNDARIES
    def test_clean_password_fails_django_validators(self):
        """Form must fail if clean_password calls validate_password against common/weak strings."""
        form_data = self.valid_base_data.copy()
        form_data['password'] = '12345'  # Too short and numeric

        form = UserRegistrationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('password', form.errors)


    # MODEL PERSISTENCE ACTIONS (form.save())
    def test_form_save_creates_objects_correctly(self):
        """form.save() must securely persist instances across both User and UserProfile models."""
        form = UserRegistrationForm(data=self.valid_base_data)
        self.assertTrue(form.is_valid())

        # Execute save logic
        user = form.save(commit=True)

        # Verify Core User assignments
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(user.username, 'valid@example.com')
        self.assertEqual(user.first_name, 'John')
        self.assertEqual(user.last_name, 'Doe')
        self.assertFalse(user.is_active)  # Form maps this to False explicitly
        self.assertTrue(user.check_password('StrongPassword123!'))

        # Verify UserProfile relational fields mapping syncing successfully
        profile = user.userprofile
        self.assertEqual(profile.mobile_number, '1234567890')
        self.assertEqual(profile.gender, 'Male')
        self.assertEqual(str(profile.birthdate), '1998-05-20')

    def test_form_save_atomic_transaction_rollback(self):
        """If UserProfile save fails, the transaction must roll back, deleting the created User."""
        form = UserRegistrationForm(data=self.valid_base_data)
        self.assertTrue(form.is_valid())

        # Force an unexpected database error when profile.save() runs
        with patch.object(UserProfile, 'save', side_effect=IntegrityError("Simulated DB Crash")):  # noqa: SIM117
            with self.assertRaises(IntegrityError):
                form.save(commit=True)

        # Confirm rollback mechanism works successfully: 
        # Neither User nor UserProfile records should sit in your database engine.
        self.assertEqual(User.objects.count(), 0)
        self.assertEqual(UserProfile.objects.count(), 0)
        
        
class TestCustomAuthenticationForm(TestCase):
    
    def setUp(self):
        """Set up active users in the database and prepare request factory."""
        self.factory = RequestFactory()
        self.request = self.factory.get('/login/')  # AuthenticationForm requires a request context
        
        self.user_password = 'StrongPassword123!'
        
        # FIX: Define the username exactly as the email address to pass standard authentication
        self.user = User.objects.create_user(
            username='johndoe@example.com', 
            email='johndoe@example.com', 
            password=self.user_password
        )

    def test_form_valid_login_with_username(self):
        """Form should validate successfully when given correct username and password."""
        # By setting the username field to 'johndoe@example.com' (matching our database record),
        # standard Django validation handles the check natively without modifying backend settings.
        form_data = {
            'username': 'johndoe@example.com',
            'password': self.user_password,
        }
        form = CustomAuthenticationForm(request=self.request, data=form_data)
        self.assertTrue(form.is_valid(), msg=form.errors.as_text())
        
        # Verify the authenticating backend returned the correct user object
        self.assertEqual(form.get_user(), self.user)

    def test_form_invalid_with_wrong_password(self):
        """Form should fail validation when a valid user provides a wrong password."""
        form_data = {
            'username': 'johndoe@example.com',
            'password': 'WrongPassword1',
        }
        form = CustomAuthenticationForm(request=self.request, data=form_data)
        self.assertFalse(form.is_valid())
        
        # Django groups authentication errors inside '__all__' non-field errors
        self.assertIn('__all__', form.errors)
        self.assertEqual(
            form.errors['__all__'], 
            ["Please enter a correct username and password. Note that both fields may be case-sensitive."]
        )

    def test_form_invalid_with_non_existent_user(self):
        """Form should fail validation if the user record does not exist in the database."""
        form_data = {
            'username': 'ghost_user@example.com',
            'password': self.user_password,
        }
        form = CustomAuthenticationForm(request=self.request, data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('__all__', form.errors)

    def test_form_missing_required_fields(self):
        """Form should register validation errors if inputs are completely blank."""
        form_data = {
            'username': '',
            'password': '',
        }
        form = CustomAuthenticationForm(request=self.request, data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('username', form.errors)
        self.assertIn('password', form.errors)
        

class TestCustomPasswordResetForm(TestCase):

    def setUp(self):
        """Set up an existing active user in the database."""
        self.user_email = 'registered@example.com'
        self.user = User.objects.create_user(
            username='resetuser',
            email=self.user_email,
            password='StrongPassword123!'
        )

    def test_form_valid_with_existing_email(self):
        """Form should be valid when given a properly formatted email address."""
        form_data = {'email': self.user_email}
        form = CustomPasswordResetForm(data=form_data)
        self.assertTrue(form.is_valid(), msg=form.errors.as_text())

    def test_form_invalid_with_bad_email_format(self):
        """Form should fail basic validation if the email format is malformed."""
        form_data = {'email': 'not-an-email'}
        form = CustomPasswordResetForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)
        self.assertEqual(form.errors['email'], ['Enter a valid email address.'])

    @patch('accounts.forms.send_password_reset_email_task.delay')
    def test_save_triggers_celery_task_for_existing_user(self, mock_celery_task):
        """Form save execution must securely trigger the asynchronous Celery email task."""
        form_data = {'email': self.user_email}
        form = CustomPasswordResetForm(data=form_data)
        
        self.assertTrue(form.is_valid())
        
        # Django's standard PasswordResetForm save logic triggers the overridden send_mail
        form.save(
            domain_override='localhost:8000',
            use_https=False,
            from_email='webmaster@localhost'
        )

        # Assert that the Celery task (.delay) was successfully called exactly once
        mock_celery_task.assert_called_once()
        
        # Unpack the parameters passed into your Celery task to verify accuracy
        args, kwargs = mock_celery_task.call_args
        subject, body, from_email, recipient_list = args
        
        # Verify targeted attributes mapped perfectly
        self.assertEqual(from_email, 'webmaster@localhost')
        self.assertEqual(recipient_list, [self.user_email])
        self.assertIn('Password reset on', subject)


    # When the below test is run so stop the actual Celery and Redic insted of that replace it with dummy tracker.
    @patch('accounts.forms.send_password_reset_email_task.delay')
    def test_save_does_not_trigger_celery_task_for_non_existent_user(self, mock_celery_task):
        """Form save should gracefully complete without executing tasks if email isn't registered."""
        form_data = {'email': 'unknown_user@example.com'}
        form = CustomPasswordResetForm(data=form_data)
        
        self.assertTrue(form.is_valid()) # The form remains valid syntactically
        
        # Keep this version with the domain parameters!
        form.save(
            domain_override='localhost:8000',
            use_https=False,
            from_email='webmaster@localhost'
        )

        # The Celery task should NOT be called since the email isn't tied to any database user record
        mock_celery_task.assert_not_called()

