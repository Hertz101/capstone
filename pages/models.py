from django.conf import settings
from django.db import models


class Message(models.Model):
    """A single group-chat post, tied to the user who wrote it."""

    group = models.ForeignKey(
        "ChatGroup",
        on_delete=models.CASCADE,
        related_name="messages",
        null=True,
        blank=True,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="chat_messages",
    )
    text = models.TextField(max_length=2000)
    # Shared-content messages (plan / packing / gmu) are rendered as cards.
    # kind == "text" is a normal typed message with no payload.
    kind = models.CharField(
        max_length=20,
        choices=[("text", "Text"), ("plan", "Hunt plan"),
                 ("packing", "Packing list"), ("gmu", "Selected GMU")],
        default="text",
    )
    payload = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user}: {self.text[:50]}"


class ChatGroup(models.Model):
    """A named group of users with its own chat room."""

    name = models.CharField(max_length=100)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="groups_created",
        null=True,
    )
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="chat_groups",
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def is_member(self, user):
        return user.is_authenticated and self.members.filter(pk=user.pk).exists()


class HuntingMethod(models.TextChoices):
    RIFLE = "rifle", "Rifle"
    BLACKPOWDER = "blackpowder", "Black Powder"
    ARCHERY = "archery", "Archery"
    MULTIPLE = "multiple", "Multiple Methods"


class Profile(models.Model):
    """Extra hunter details beyond Django's built-in User model."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=2, blank=True, help_text="Two-letter state code, e.g. CO")
    method = models.CharField(
        max_length=20,
        choices=HuntingMethod.choices,
        blank=True,
    )
    photo = models.ImageField(
        upload_to="profile_photos/%Y/%m/",
        blank=True,
        null=True,
        help_text="Optional profile photo",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.get_username()} profile"

    @property
    def display_name(self):
        """Prefer the full name, fall back to the username."""
        full = f"{self.first_name} {self.last_name}".strip()
        return full or self.user.get_username()
