from django.urls import path

from . import views


app_name = "accounts"

urlpatterns = [
    path("first-name/", views.profile_prompt, name="profile_prompt"),
    path("me/", views.profile_edit, name="profile_edit"),
]
