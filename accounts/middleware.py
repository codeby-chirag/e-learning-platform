from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied

from .models import UserActivityLog


class ActivityLogMiddleware:
    SKIP = ('/static/', '/media/', '/favicon.ico')
    
    # __init__ is called only once, when the web server starts.
    def __init__(self, get_response):
        self.get_response = get_response

    # __call__() method which is called once per request
    def __call__(self, request):
        user_before = request.user if request.user.is_authenticated else None
        response = self.get_response(request)

        if not request.path.startswith(self.SKIP):
            # request.user changes during login/logout, so fall back to the earlier value
            user = request.user if request.user.is_authenticated else user_before
            ip = (request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip()
                    or request.META.get('REMOTE_ADDR'))
            try:
                UserActivityLog.objects.create(
                    user=user, path=request.path[:255], method=request.method,
                    status_code=response.status_code, ip_address=ip or None,
                    user_agent=request.META.get('HTTP_USER_AGENT', '')[:255],
                )
            except Exception:  # noqa: BLE001, S110
                pass    # logging must never break the website
            
        return response


ADMIN_ONLY_URLS = {
    'course_create',
    'course_update',
    'course_delete',
    'request_platform_report',
}

def get_role(user):
    if not user.is_authenticated:
        return 'anonymous'
    if user.is_staff or user.is_superuser:
        return 'admin'
    return 'student'

class RoleAccessMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.role = get_role(request.user)    # templates can use request.role
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        match = request.resolver_match
        if not match or match.url_name not in ADMIN_ONLY_URLS:
            return None                               # not a protected view
        if request.role == 'anonymous':
            return redirect_to_login(request.get_full_path())
        if request.role != 'admin':
            raise PermissionDenied                    # shows 403
        return None