from django.conf import settings
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
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
from .tasks import (
    generate_course_report_task,
    generate_enrollment_report_task,
    generate_student_report_task,
    send_activation_email_task,
)


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

            send_activation_email_task.delay(user.email, activation_link, user.first_name)
            
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

@staff_member_required
def request_platform_report_view(request):
    if request.method == "POST":
        report_type = request.POST.get("report_type")
        admin_email = request.user.email 

        if report_type == "enrollment":
            generate_enrollment_report_task.delay(admin_email)
            messages.success(request, "Enrollment report is being generated and will be emailed shortly!")
        elif report_type == "course":
            generate_course_report_task.delay(admin_email)
            messages.success(request, "Course details report is being generated and will be emailed shortly!")
        elif report_type == "student":
            generate_student_report_task.delay(admin_email)
            messages.success(request, "Student details report is being generated and will be emailed shortly!")
        else:
            messages.error(request, "Please select a valid report type.")
            
    return redirect(request.META.get('HTTP_REFERER', 'home'))