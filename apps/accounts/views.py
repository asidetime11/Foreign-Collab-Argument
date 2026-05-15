from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .forms import NicknameForm, ParticipantProfileForm


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
