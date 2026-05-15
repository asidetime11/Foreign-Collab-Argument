from django.urls import path

from . import views


app_name = "ai"

urlpatterns = [
    path("chat/<int:round_id>/", views.chat, name="chat"),
    path("transcribe/", views.transcribe, name="transcribe"),
]
