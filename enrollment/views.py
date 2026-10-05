from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views.generic import ListView

from courses.models import Course

from .models import Enrollment


@login_required
def enroll_course(request, pk):
    course = get_object_or_404(Course, pk=pk)
    
    # Check if enrollment period has started or not
    if course.enrollment_start_date and timezone.now() < course.enrollment_start_date:
        messages.error(request, "Enrollment failed: The enrollment period has not started yet.")
        return redirect('course_detail', pk=course.pk)

    # Check if enrollment end date has PASSED
    if course.enrollment_end_date and timezone.now() > course.enrollment_end_date:
        messages.error(request, "Enrollment failed: The deadline for this course has passed.")
        return redirect('course_detail', pk=course.pk)
    
    # Attempt enrollment
    Enrollment.objects.get_or_create(student=request.user, course=course)
    messages.success(request, "Successfully enrolled in the course!")
    return redirect('student_dashboard')

class StudentDashboardView(LoginRequiredMixin, ListView):
    model = Enrollment
    template_name = 'enrollment/dashboard.html'
    context_object_name = 'enrollment'

    def get_queryset(self):
        # students only see their own enrolled courses
        return Enrollment.objects.filter(student=self.request.user)


