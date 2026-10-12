from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.cache import cache
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
    
    # Attempt database record enrollment creation
    enrollment, created = Enrollment.objects.get_or_create(student=request.user, course=course)
    
    # Only fire if this is a fresh enrollment record row transaction
    if created:
        # Grab the global network engine
        channel_layer = get_channel_layer()
        
        # Build the targeting address token name based on the unique user ID
        student_room = f"user_{request.user.id}"
        
        # Blast the live notification payload down to just this specific student session lines
        async_to_sync(channel_layer.group_send)(
            student_room,
            {
                "type": "send_notification",  # Triggers method inside consumers.py
                "notification_type": "enrollment_success",
                "message": f"Enrollment Confirmed! Welcome to '{course.course_title}'."
            }
        )

    messages.success(request, "Successfully enrolled in the course!")
    return redirect('student_dashboard')


def enroll_course_view(request, pk):
    course = get_object_or_404(Course, pk=pk)
    
    # Create or get the enrollment
    Enrollment.objects.get_or_create(student=request.user, course=course)
    
    # CLEAR/INVALIDATE THE CACHE FOR THIS USER AND COURSE
    cache_key = f"enrollment_status_{request.user.id}_{course.pk}"
    cache.delete(cache_key) 
    
    messages.success(request, f"Successfully enrolled in {course.course_title}!")
    return redirect('student_dashboard')


class StudentDashboardView(LoginRequiredMixin, ListView):
    model = Enrollment
    template_name = 'enrollment/dashboard.html'
    context_object_name = 'enrollment'

    def get_queryset(self):
        # students only see their own enrolled courses
        return Enrollment.objects.filter(student=self.request.user)