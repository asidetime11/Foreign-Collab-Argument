from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from apps.experiments.models import ExperimentBatch

from .forms import NicknameForm, ParticipantProfileForm, ParticipantRegistrationForm


def register(request):
    if request.user.is_authenticated:
        return redirect("survey:start")
    if request.method == "POST":
        form = ParticipantRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            profile = user.participant_profile
            profile.batch = ExperimentBatch.objects.filter(is_active=True).first()
            profile.save(update_fields=["batch"])
            login(request, user)
            return redirect("accounts:profile_prompt")
    else:
        form = ParticipantRegistrationForm()
    return render(request, "accounts/register.html", {"form": form})


@login_required
def profile_prompt(request):
    profile = request.user.participant_profile
    if request.method == "POST":
        form = NicknameForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            return redirect("survey:start")
    else:
        form = NicknameForm(instance=profile)
    return render(request, "accounts/profile_prompt.html", {"form": form})


@login_required
def profile_edit(request):
    profile = request.user.participant_profile
    if request.method == "POST":
        form = ParticipantProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "资料已保存。")
            return redirect("accounts:profile_edit")
    else:
        form = ParticipantProfileForm(instance=profile)
    return render(request, "accounts/profile.html", {"form": form})
