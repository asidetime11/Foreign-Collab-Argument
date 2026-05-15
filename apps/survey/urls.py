from django.urls import path

from . import views


app_name = "survey"

urlpatterns = [
    path("", views.start, name="start"),
    path("topic-order/", views.topic_order, name="topic_order"),
    path("post/", views.post, name="post"),
    path("scale/<str:step>/", views.scale, name="scale"),
    path("text/<str:step>/", views.text_response, name="text_response"),
    path("mode/", views.mode_select, name="mode_select"),
    path("chat/", views.chat, name="chat"),
    path("done/", views.done, name="done"),
    path("quality-event/", views.quality_event, name="quality_event"),
]
