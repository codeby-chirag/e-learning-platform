from django.urls import path

from .views import StudentDashboardView, enroll_course

urlpatterns = [
    # trigger enrollment in a specific course /enrollments/1/enroll/
    path('<int:pk>/enroll/', enroll_course, name='enroll_course'),
    
    # student dashboard showing all enrolled courses /enrollments/dashboard/
    path('dashboard/', StudentDashboardView.as_view(), name='student_dashboard'),
    
    path('<int:pk>/enroll/', enroll_course, name='enroll_course'),
    ]