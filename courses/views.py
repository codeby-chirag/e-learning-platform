from django.contrib.auth.mixins import (
    LoginRequiredMixin,
    PermissionRequiredMixin,
)
from django.urls import reverse_lazy
from django.views.generic import CreateView, DetailView, ListView

from .forms import CourseForm
from .models import Course


class CourseListView(ListView):
    model = Course
    template_name = 'courses/course_list.html'
    context_object_name = 'courses'  


class CourseCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Course
    form_class = CourseForm
    template_name = 'courses/course_form.html'
    success_url = reverse_lazy(
        'course_list'
    ) 
    
    permission_required = 'courses.can_create_courses'
    # Raises 403 Forbidden error if unauthorized
    raise_exception = (
        True  
    )

    def form_valid(self, form):
    # assign the current logged-in user as the instructor
        form.instance.instructor = self.request.user
        return super().form_valid(form)


class CourseDetailView(DetailView):
    model = Course
    template_name = 'courses/course_detail.html'
    context_object_name = (
        'course' 
    )