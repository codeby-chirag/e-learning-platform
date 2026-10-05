from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.mixins import (
    LoginRequiredMixin,
    PermissionRequiredMixin,
)
from django.http import HttpResponse
from django.urls import reverse_lazy
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)

from accounts.tasks import generate_platform_report_task
from enrollment.models import Enrollment

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
    context_object_name = 'course' 
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        if user.is_authenticated:
            # Check if an enrollment record exists for this user and course
            context['is_enrolled'] = Enrollment.objects.filter(student=user, course=self.object).exists()
        else:
            context['is_enrolled'] = False
        return context

class CourseUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = Course
    form_class = CourseForm
    template_name = 'courses/course_form.html'
    permission_required = 'courses.can_edit_courses'
    success_url = '/courses/'
    
class CourseDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = Course
    template_name = 'courses/course_confirm_delete.html'
    permission_required = 'courses.can_delete_courses'
    success_url = '/courses/'

@staff_member_required
def trigger_report_view(request):
    generate_platform_report_task.delay("chirag.ms46@gmail.com")
    
    return HttpResponse("Report generation started! Check your inbox.")