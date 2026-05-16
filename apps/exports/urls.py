from django.urls import path

from . import views


app_name = "exports"

urlpatterns = [
    path("batch/<int:batch_id>/", views.batch_export, name="batch_export"),
]
