from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.models import User

from .models import ChatGroup, Message, Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    """Standalone profile list: names, location, method, photo."""

    list_display = ("user", "first_name", "last_name", "city", "state", "method", "photo_tiny")
    search_fields = ("user__username", "first_name", "last_name", "city")
    list_filter = ("state", "method")
    readonly_fields = ("created_at",)

    @admin.display(description="Photo")
    def photo_tiny(self, obj):
        if obj.photo:
            return f'<img src="{obj.photo.url}" style="height:40px;border-radius:50%;">'
        return "—"


class ProfileInline(admin.StackedInline):
    """Show the hunter profile directly on each user's admin page."""

    model = Profile
    can_delete = False
    verbose_name_plural = "Hunter profile"
    fields = ("first_name", "last_name", "city", "state", "method", "photo")


class UserAdmin(DjangoUserAdmin):
    """The default User admin, plus the profile inline and extra columns."""

    inlines = [ProfileInline]
    list_display = ("username", "email", "full_name", "state", "method", "is_staff", "date_joined")
    list_filter = ("is_staff", "is_superuser", "profile__state", "profile__method")
    search_fields = (
        "username",
        "email",
        "profile__first_name",
        "profile__last_name",
        "profile__city",
    )

    @admin.display(description="Full name")
    def full_name(self, obj):
        return obj.profile.display_name if hasattr(obj, "profile") else "—"

    @admin.display(description="State")
    def state(self, obj):
        return obj.profile.state if hasattr(obj, "profile") else "—"

    @admin.display(description="Method")
    def method(self, obj):
        return obj.profile.get_method_display() if hasattr(obj, "profile") else "—"


# Re-register the built-in User with our extended admin class.
admin.site.unregister(User)
admin.site.register(User, UserAdmin)


@admin.register(ChatGroup)
class ChatGroupAdmin(admin.ModelAdmin):
    """Manage groups and their members."""

    list_display = ("name", "created_by", "created_at", "member_count")
    search_fields = ("name", "created_by__username")
    filter_horizontal = ("members",)

    @admin.display(description="Members")
    def member_count(self, obj):
        return obj.members.count()


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    """Review chat messages, e.g. for moderation."""

    list_display = ("user", "text", "created_at")
    search_fields = ("user__username", "text")
    date_hierarchy = "created_at"
