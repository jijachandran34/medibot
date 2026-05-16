from django.urls import path
from .views import StartSessionView, SendMessageView, SessionDetailView

urlpatterns = [
    path("sessions/", StartSessionView.as_view(), name="start-session"),
    path("sessions/<uuid:token>/messages/", SendMessageView.as_view(), name="send-message"),
    path("sessions/<uuid:token>/", SessionDetailView.as_view(), name="session-detail"),
]
