from django.contrib import admin, messages
from django.contrib.auth.models import User
from django.shortcuts import redirect, render
from django.urls import path

from .forms import BulkParticipantCreateForm
from .models import ParticipantProfile


@admin.register(ParticipantProfile)
class ParticipantProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "display_name", "batch", "region", "updated_at")
    list_filter = ("batch", "gender", "organization_type")
    search_fields = ("user__username", "display_name", "region", "contact")
    change_list_template = "admin/accounts/participantprofile/change_list.html"

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path("bulk-create/", self.admin_site.admin_view(self.bulk_create), name="accounts_bulk_create"),
        ]
        return custom + urls

    def bulk_create(self, request):
        if request.method == "POST":
            form = BulkParticipantCreateForm(request.POST)
            if form.is_valid():
                batch = form.cleaned_data["batch"]
                password = form.cleaned_data["initial_password"]
                created = []
                for username in form.cleaned_data["usernames"]:
                    user = User.objects.create_user(username=username, password=password)
                    user.participant_profile.batch = batch
                    user.participant_profile.save(update_fields=["batch"])
                    created.append(username)
                messages.success(request, f"已创建 {len(created)} 个参与者账号。")
                return redirect("admin:accounts_participantprofile_changelist")
        else:
            form = BulkParticipantCreateForm()
        return render(request, "admin/accounts/bulk_create_participants.html", {"form": form})
