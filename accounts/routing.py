from django.urls import re_path

from . import consumers

# Defines the connection URL entry points for browser
websocket_urlpatterns = [
    re_path(r'ws/notifications/$', consumers.NotificationConsumer.as_asgi()),
]
