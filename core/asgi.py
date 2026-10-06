"""
ASGI config for core project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.1/howto/deployment/asgi/
"""

import os

import accounts.routing
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

# Tells Django where your settings live
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'e_learning_webplatform.settings')

# The main switchboard that inspects the type of incoming connection
application = ProtocolTypeRouter({
    # If it is a standard web traffic request, handle it via normal Django rules
    "http": get_asgi_application(),
    
    # If it is a real-time WebSocket connection, route it through our custom sockets
    "websocket": AuthMiddlewareStack(
        URLRouter(
            accounts.routing.websocket_urlpatterns
        )
    ),
})
