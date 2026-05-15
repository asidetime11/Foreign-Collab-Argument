from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView


urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("django.contrib.auth.urls")),
    path("profile/", include("apps.accounts.urls")),
    path("survey/", include("apps.survey.urls")),
    path("ai/", include("apps.ai.urls")),
    path("exports/", include("apps.exports.urls")),
    path("i18n/", include("django.conf.urls.i18n")),
    path("", RedirectView.as_view(pattern_name="survey:start", permanent=False)),
]
