from django.contrib import admin
from django.contrib.auth.views import LoginView
from django.urls import include, path
from django.views.generic import RedirectView

from apps.accounts.forms import ChineseAuthenticationForm
from apps.experiments import admin_views as research_admin_views


urlpatterns = [
    path("admin/research/", research_admin_views.dashboard, name="research_admin_dashboard"),
    path("admin/research/select-batch/", research_admin_views.select_batch, name="research_admin_select_batch"),
    path("admin/research/set-register-batch/", research_admin_views.set_register_batch, name="research_admin_set_register_batch"),
    path("admin/research/delete-batch/<int:batch_id>/", research_admin_views.delete_batch, name="research_admin_delete_batch"),
    path("admin/research/copy/", research_admin_views.copy_settings, name="research_admin_copy"),
    path("admin/research/copy/preview/", research_admin_views.copy_preview, name="research_admin_copy_preview"),
    path("admin/research/bulk-register/", research_admin_views.bulk_register, name="research_admin_bulk_register"),
    path("admin/research/users/", research_admin_views.user_records, name="research_admin_users"),
    path("admin/research/users/<int:user_id>/", research_admin_views.user_detail, name="research_admin_user_detail"),
    path("admin/research/users/delete/", research_admin_views.delete_users, name="research_admin_delete_users"),
    path("admin/research/users/<int:user_id>/delete/", research_admin_views.delete_user, name="research_admin_delete_user"),
    path("admin/research/users/<int:user_id>/reset/", research_admin_views.reset_test_user, name="research_admin_reset_test_user"),
    path("admin/research/export-all/", research_admin_views.export_all, name="research_admin_export_all"),
    path("admin/", RedirectView.as_view(pattern_name="research_admin_dashboard", permanent=False)),
    path("admin/", admin.site.urls),
    path("accounts/login/", LoginView.as_view(authentication_form=ChineseAuthenticationForm), name="login"),
    path("accounts/", include("django.contrib.auth.urls")),
    path("profile/", include("apps.accounts.urls")),
    path("survey/", include("apps.survey.urls")),
    path("ai/", include("apps.ai.urls")),
    path("exports/", include("apps.exports.urls")),
    path("", RedirectView.as_view(pattern_name="login", permanent=False)),
]
