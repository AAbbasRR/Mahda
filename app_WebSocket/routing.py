from django.urls import path
from . import consumers

websocket_urlpatterns = [
    path('ws/orderprice/', consumers.OrderPrice.as_asgi())
]
