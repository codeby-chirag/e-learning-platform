from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib.auth.mixins import (
    LoginRequiredMixin,
    PermissionRequiredMixin,
)
from django.core.cache import cache
from django.urls import reverse_lazy
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)

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
    success_url = reverse_lazy('course_list') 
    
    permission_required = 'courses.can_create_courses'
    raise_exception = True  

    def form_valid(self, form):
        # Assign the current logged-in user as the instructor
        form.instance.instructor = self.request.user
        
        # Let the default CreateView finish saving the object to the database cleanly
        response = super().form_valid(form)
        
        # TRIGGER Extract the newly saved course title
        course_title = self.object.course_title
        
        channel_layer = get_channel_layer()
        
        async_to_sync(channel_layer.group_send)(
            "global_announcements",
            {
                "type": "send_notification",
                "notification_type": "new_course",
                "message": f"New Course Launch: '{course_title}' is now available!"
            }
        )
        
        return response


class CourseDetailView(DetailView):
    model = Course
    template_name = 'courses/course_detail.html'
    context_object_name = 'course' 
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        if user.is_authenticated:
            # Create a unique cache key for this user and course enrollment status
            cache_key = f"enrollment_status_{user.id}_{self.object.pk}"
            is_enrolled = cache.get(cache_key)
            
            if is_enrolled is None:
                is_enrolled = Enrollment.objects.filter(student=user, course=self.object).exists()
                cache.set(cache_key, is_enrolled, timeout=900)
                
            context['is_enrolled'] = is_enrolled
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