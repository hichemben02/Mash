from django.urls import re_path
import group.consumers

websocket_urlpatterns = [
    re_path(r'ws/(?P<room_name>\w+)/$', group.consumers.ChatConsumer.as_asgi()),
]