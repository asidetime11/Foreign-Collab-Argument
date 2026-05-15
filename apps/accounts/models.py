from django.conf import settings
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


class ParticipantProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="participant_profile",
    )
    display_name = models.CharField("称呼/姓名", max_length=120, blank=True)
    region = models.CharField("地区", max_length=120, blank=True)
    age_range = models.CharField("年龄段", max_length=50, blank=True)
    gender = models.CharField("性别", max_length=50, blank=True)
    organization_type = models.CharField("学校/单位类型", max_length=120, blank=True)
    education_or_work = models.CharField("教育阶段/职业状态", max_length=120, blank=True)
    contact = models.CharField("联系方式", max_length=120, blank=True)
    notes = models.TextField("备注", blank=True)
    batch = models.ForeignKey(
        "experiments.ExperimentBatch",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="participants",
        verbose_name="实验批次",
    )
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    class Meta:
        verbose_name = "参与者资料"
        verbose_name_plural = "参与者资料"

    def __str__(self):
        return self.display_name or self.user.username

    @property
    def has_required_display_name(self):
        return bool(self.display_name.strip())


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_participant_profile(sender, instance, created, **kwargs):
    if created:
        ParticipantProfile.objects.create(user=instance)
