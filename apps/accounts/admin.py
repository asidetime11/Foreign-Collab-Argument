from django.contrib import admin
from django.contrib.auth.models import Group, User


for model in [User, Group]:
    try:
        admin.site.unregister(model)
    except admin.sites.NotRegistered:
        pass
