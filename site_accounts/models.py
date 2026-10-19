import re

from django.conf import settings
from django.db import models


class UserIdentity(models.Model):
    EMAIL = "email"
    PHONE = "phone"
    COGNITO = "cognito"
    GOOGLE = "google"
    FACEBOOK = "facebook"
    INSTAGRAM = "instagram"
    KINDS = [
        (EMAIL, "Email"),
        (PHONE, "Phone"),
        (COGNITO, "Cognito subject"),
        (GOOGLE, "Google"),
        (FACEBOOK, "Facebook"),
        (INSTAGRAM, "Instagram"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="site_identities",
    )
    kind = models.CharField(max_length=24, choices=KINDS)
    identifier = models.CharField(max_length=320)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("user__email", "kind", "identifier")
        constraints = [
            models.UniqueConstraint(
                fields=("kind", "identifier"),
                name="unique_site_identity",
            ),
        ]
        verbose_name_plural = "User identities"

    def save(self, *args, **kwargs):
        self.identifier = self.normalize_identifier(self.kind, self.identifier)
        super().save(*args, **kwargs)

    @classmethod
    def normalize_identifier(cls, kind, identifier):
        value = str(identifier or "").strip()
        if kind == cls.EMAIL:
            return value.casefold()
        if kind == cls.PHONE:
            digits = re.sub(r"\D", "", value)
            if len(digits) == 10:
                digits = f"1{digits}"
            return f"+{digits}" if digits else ""
        return value

    def __str__(self):
        return f"{self.get_kind_display()}: {self.identifier}"
