from django.urls import path

from . import views


app_name = "ai"

urlpatterns = [
    path("chat/<int:round_id>/", views.chat, name="chat"),
    path("intro/<int:round_id>/", views.intro, name="intro"),
    path("interrupt/<int:round_id>/", views.interrupt_chat, name="interrupt"),
    path("transcribe-debug/", views.transcribe_debug, name="transcribe_debug"),
    path("transcribe/", views.transcribe, name="transcribe"),
]
