from django.contrib.auth.views import LoginView, LogoutView
from django.urls import path

from .forms import CustomAuthenticationForm
from .views import (
    activate_email_view,
    profile_view,
    signup_success_view,
    signup_view,
)

urlpatterns = [
    path('signup/', signup_view, name='signup'),
    path('signup/success/', signup_success_view, name='signup_success'),
    path('profile/', profile_view, name='profile'), 
    path('activate/<uidb64>/<token>/', activate_email_view, name='activate'), 
    
    # path('login/', LoginView.as_view(template_name='accounts/login.html'), name='login'),
    path('login/', LoginView.as_view(
            template_name='accounts/login.html', 
            authentication_form=CustomAuthenticationForm
        ), name='login'),
    
    path('logout/', LogoutView.as_view(next_page='login'), name='logout'),
]





