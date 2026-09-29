from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode

from .forms import UserRegistrationForm


def home_view(request):
    return render(request, 'accounts/welcome.html')

def signup_view(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save() 
            
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            
            relative_activation_url = reverse('activate', kwargs={'uidb64': uid, 'token': token})
            activation_link = request.build_absolute_uri(relative_activation_url)
            
            subject = "Email for account Activation!"
            message = f"Hi {user.first_name},\n\nPlease click the link below to activate your account:\n{activation_link}"
            
            send_mail(
                subject, 
                message, 
                settings.DEFAULT_FROM_EMAIL, 
                [user.email], 
                fail_silently=DEBUG_MODE_CHECK(settings.DEBUG)
            )
            
            return redirect('signup_success') 
    else:
        form = UserRegistrationForm()
    
    return render(request, 'accounts/signup.html', {'form': form})

def DEBUG_MODE_CHECK(debug_val):
    return not debug_val

def signup_success_view(request):
    return render(request, 'accounts/signup_success.html')

@login_required
def profile_view(request):
    return render(request, 'accounts/profile.html')

def activate_email_view(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        user.is_active = True  
        user.save()
        return HttpResponse("Email activated successfully! <a href='/accounts/login/'>Click here to log in</a>.")
    else:
        return HttpResponse("Activation link is invalid or has expired.", status=400)
