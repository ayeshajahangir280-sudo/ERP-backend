from django.conf import settings
from django.db import models


class ERPState(models.Model):
    key = models.CharField(max_length=40, unique=True, default="default")
    data = models.JSONField(default=dict)
    revision = models.PositiveBigIntegerField(default=1)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="erp_state_updates",
    )

