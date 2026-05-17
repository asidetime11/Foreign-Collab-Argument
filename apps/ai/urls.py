from django.urls import path

from . import views


app_name = "ai"

urlpatterns = [
    path("chat/<int:round_id>/", views.chat, name="chat"),
    path("interrupt/<int:round_id>/", views.interrupt_chat, name="interrupt"),
    path("transcribe/", views.transcribe, name="transcribe"),
]
