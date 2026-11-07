
import datetime
import json
import logging
import os

from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.staticfiles import finders
from django_ratelimit import UNSAFE
from django_ratelimit.decorators import ratelimit
from django_ratelimit.exceptions import Ratelimited
from django.shortcuts import get_object_or_404, redirect, render
from django.db.models import Q
from django.http import JsonResponse
from django.urls import reverse

from .content import PRE_HUNT_CHECKLIST, RESOURCE_CARDS
from .forms import ChatGroupForm, ProfileForm, SignupForm
from .models import ChatGroup, Message, Profile
from .notifications import actor_display, send_group_notification_async
from config.maptiler import get_maptiler_key

logger = logging.getLogger(__name__)


def home_view(request):
    animal_cards = [
        ("Elk", "img/elk.jpeg", "Elk"),
        ("Deer", "img/mule.jpeg", "Mule Deer"),
        ("Deer", "img/whitetail.jpeg", "Whitetail Deer"),
        ("Bear", "img/bear.jpeg", "Bear"),
        ("Pronghorn", "img/pronghorn.jpeg", "Pronghorn"),
    ]

    return render(request, "pages/home.html", {
        "animal_cards": animal_cards,
    })


def tools_view(request):
    return render(request, "pages/tools.html")


def maps_view(request):
    """Hunting map page. Logged-in users also get their chat groups so the
    'Share to group chat' button can target a specific group."""
    context = {
        "maptiler_key": get_maptiler_key(),
    }
    if request.user.is_authenticated:
        context["chat_groups"] = request.user.chat_groups.all()
    try:
        context["maps_js_mtime"] = int(
            os.path.getmtime(
                finders.find("js/maps.js") or "js/maps.js"
            )
        )
    except OSError:
        context["maps_js_mtime"] = 1
    return render(request, "pages/maps.html", context)


def your_trip_view(request):
    """Interactive pre-hunt checklist, grouped like the classic pre-hunt lists."""
    return render(request, "pages/your_trip.html", {
        "checklist": PRE_HUNT_CHECKLIST,
    })


def blog_view(request):
    return render(request, "pages/blog.html")


@login_required
@ratelimit(key="user", rate="10/m", method="POST", block=False)
def group_chat_view(request, group_id=None):
    """Group chat: list the latest messages in a group, let users post one.

    POST is the only write path; a redirect back to the page afterwards
    keeps the browser's back button working (Post/Redirect/Get).
    """
    if group_id:
        group = get_object_or_404(ChatGroup, pk=group_id)
        if not group.is_member(request.user):
            return redirect("group_chat")
    elif request.user.is_authenticated and request.user.chat_groups.exists():
        # No group requested: drop the user into their first group so the
        # heading shows a real name instead of the generic "Group Chat".
        first_group = request.user.chat_groups.order_by("name").first()
        return redirect("group_chat_group", group_id=first_group.pk)
    else:
        group = None

    try:
        sidebar_mtime = int(
            os.path.getmtime(finders.find("js/chat_sidebar.js") or "js/chat_sidebar.js")
        )
    except OSError:
        sidebar_mtime = 1

    if request.method == "POST":
        text = request.POST.get("text", "").strip()
        # Shared cards (plan / packing / gmu) carry a kind + JSON payload;
        # anything else is a plain typed message.
        kind = request.POST.get("kind", "text")
        if kind not in {"text", "plan", "packing", "gmu"}:
            kind = "text"
        if request.limited:
            from django.http import HttpResponse
            return HttpResponse(
                "<h1>Slow down 🐎</h1><p>You're posting too quickly. "
                "Wait a minute and try again.</p>",
                status=429,
            )
        payload = None
        if kind != "text":
            try:
                payload = json.loads(request.POST.get("payload", ""))
            except (json.JSONDecodeError, TypeError):
                kind = "text"
            if not isinstance(payload, dict):
                kind, payload = "text", None
        if text:
            message = Message.objects.create(
                group=group, user=request.user, text=text, kind=kind, payload=payload,
            )
            if group:
                send_group_notification_async(
                    group,
                    request.user,
                    "posted a message",
                    [message.text[:500]],
                    group_url=reverse("group_chat_group", args=[group.pk]),
                    request=request,
                )
        if group:
            return redirect("group_chat_group", group_id=group.pk)
        return redirect("group_chat")

    messages = Message.objects.select_related("user").filter(group=group).order_by("-created_at")[:50]
    liked_ids = set(
        Message.objects.filter(liked_by=request.user).values_list("pk", flat=True)
    ) & {m.pk for m in messages}
    # Which messages the current user may moderate (delete) — creator only.
    deletable_ids = set()
    if group and group.created_by_id == request.user.pk:
        deletable_ids = {m.pk for m in messages}
    return render(request, "pages/group_chat.html", {
        "chat_messages": messages,
        "chat_group": group,
        "chat_sidebar_mtime": sidebar_mtime,
        "liked_ids": liked_ids,
        "deletable_ids": deletable_ids,
    })


@login_required
@ratelimit(key="user", rate="30/m", method="POST", block=False)
def message_like_view(request, message_id):
    """Toggle the signed-in user's like on a chat message (AJAX POST).

    Returns JSON: {liked: bool, count: n} so the button can update
    in place without a page reload. Messages with no group are only
    likeable by anyone signed in; group messages by members only.
    """
    message = get_object_or_404(Message.objects.select_related("group"), pk=message_id)
    if message.group and not message.group.is_member(request.user):
        return JsonResponse({"error": "not a member"}, status=403)

    if request.limited:
        return JsonResponse({"error": "slow down"}, status=429)

    if request.method == "POST":
        if message.liked_by.filter(pk=request.user.pk).exists():
            message.liked_by.remove(request.user)
            liked = False
        else:
            message.liked_by.add(request.user)
            liked = True
            if message.group:
                send_group_notification_async(
                    message.group,
                    request.user,
                    "liked a message",
                    [f"\u201c{message.text[:200]}\u201d by {actor_display(message.user)}"],
                    group_url=reverse("group_chat_group", args=[message.group.pk]),
                    request=request,
                )
    else:
        liked = message.liked_by.filter(pk=request.user.pk).exists()

    return JsonResponse({"liked": liked, "count": message.liked_by.count()})


@login_required
def message_delete_view(request, message_id):
    """Delete a chat message: author or group creator only (POST).

    Silent by design — deleting must not email the group.
    """
    message = get_object_or_404(Message.objects.select_related("group"), pk=message_id)
    back = reverse("group_chat")
    if message.group:
        if not message.group.is_member(request.user):
            return redirect("group_chat")
        back = reverse("group_chat_group", args=[message.group.pk])

    is_author = message.user_id == request.user.pk
    is_creator = message.group and message.group.created_by_id == request.user.pk
    if request.method == "POST" and (is_author or is_creator):
        from django.contrib import messages
        if is_author:
            messages.info(request, "Your message was deleted.")
        else:
            messages.info(
                request,
                f"Moderated: deleted a message by {actor_display(message.user)}.",
            )
        message.delete()
    return redirect(back)


@login_required
def message_edit_view(request, message_id):
    """Edit a chat message: author only (POST, text messages only).

    Shared cards (plan/packing/gmu) aren't editable — their content comes
    from the payload, not the text. Silent: no notification email.
    """
    message = get_object_or_404(Message.objects.select_related("group"), pk=message_id)
    back = reverse("group_chat")
    if message.group:
        if not message.group.is_member(request.user):
            return redirect("group_chat")
        back = reverse("group_chat_group", args=[message.group.pk])

    if (
        request.method == "POST"
        and message.user_id == request.user.pk
        and message.kind == "text"
    ):
        text = request.POST.get("text", "").strip()
        if text and len(text) <= 2000:
            message.text = text
            message.edited = True
            message.save(update_fields=["text", "edited", "updated_at"])
    return redirect(back)


def ratelimited_view(request, exception):
    """Friendly 429 page shown when a user posts/likes too fast."""
    from django.http import HttpResponse
    return HttpResponse(
        "<h1>Slow down 🐎</h1><p>You're doing that too quickly. "
        "Wait a minute and try again.</p>",
        status=429,
    )


@login_required
def group_list_view(request):
    """Groups the user belongs to, plus groups they can join."""
    my_groups = request.user.chat_groups.all()
    other_groups = ChatGroup.objects.exclude(members=request.user)
    return render(request, "pages/group_list.html", {
        "my_groups": my_groups,
        "other_groups": other_groups,
    })


@login_required
def group_join_view(request, group_id):
    """Join a group from the group list page."""
    group = get_object_or_404(ChatGroup, pk=group_id)
    if request.method == "POST":
        newly_added = not group.is_member(request.user)
        group.members.add(request.user)
        if newly_added and request.user.email:
            send_group_notification_async(
                group,
                group.created_by or request.user,
                "joined the group",
                [f"{actor_display(request.user)} just joined \u201c{group.name}\u201d. Say hi!"],
                group_url=reverse("group_chat_group", args=[group.pk]),
                request=request,
            )
    return redirect("group_chat_group", group_id=group.pk)


@login_required
def group_create_view(request):
    """Create a new group and pick the users to add."""
    if request.method == "POST":
        form = ChatGroupForm(request.POST, current_user=request.user)
        if form.is_valid():
            group = form.save()
            for member in group.members.exclude(pk=request.user.pk):
                # Announcement message for each initial member.
                Message.objects.create(
                    group=group,
                    user=request.user,
                    text=f"👋 {actor_display(member)} was added to the group by "
                         f"{actor_display(request.user)} — say hi!",
                    kind="system",
                )
                if member.email:
                    send_group_notification_async(
                        group,
                        request.user,
                        "welcomed you to the group",
                        [
                            f"{actor_display(request.user)} created \u201c{group.name}\u201d "
                            "and added you as one of its first members.",
                            "Open the chat and say hi!",
                        ],
                        group_url=reverse("group_chat_group", args=[group.pk]),
                        request=request,
                    )
            return redirect("group_chat_group", group_id=group.pk)
    else:
        form = ChatGroupForm(current_user=request.user)
    return render(request, "pages/group_create.html", {"form": form})


@login_required
def group_detail_view(request, group_id):
    """Group info: members, and add/remove users (creator only)."""
    group = get_object_or_404(ChatGroup, pk=group_id)
    if not group.is_member(request.user):
        return redirect("group_chat")

    if request.method == "POST":
        if request.POST.get("action") == "delete":
            # Creator-only group deletion. Cascades to the group's messages.
            if group.created_by == request.user:
                group.delete()
                return redirect("group_list")
            return redirect("group_detail", group_id=group.pk)
        if request.POST.get("action") == "add":
            user_id = request.POST.get("user_id")
            if user_id and group.created_by == request.user:
                user = get_object_or_404(User, pk=user_id)
                if not group.is_member(user):
                    group.members.add(user)
                    # Post a chat message announcing the new member so the
                    # whole group sees who arrived, even without email.
                    Message.objects.create(
                        group=group,
                        user=request.user,
                        text=f"👋 {actor_display(user)} was added to the group by "
                             f"{actor_display(request.user)} — say hi!",
                        kind="system",
                    )
                    if user.email:
                                send_group_notification_async(
                            group,
                            request.user,
                            "welcomed you to the group",
                            [
                                f"{actor_display(request.user)} added you to "
                                f"\u201c{group.name}\u201d — the hunt-planning crew.",
                                "Open the chat and introduce yourself!",
                            ],
                            group_url=reverse("group_chat_group", args=[group.pk]),
                            request=request,
                        )
        elif request.POST.get("action") == "remove":
            user_id = request.POST.get("user_id")
            if user_id and group.created_by == request.user:
                group.members.remove(user_id)
        return redirect("group_detail", group_id=group.pk)

    non_members = User.objects.exclude(pk__in=group.members.all())
    return render(request, "pages/group_detail.html", {
        "group": group,
        "is_creator": group.created_by == request.user,
        "non_members": non_members,
    })


def _resolve_links(card):
    """Turn "{name}" link targets into real paths via django.urls.reverse."""
    card["links"] = [
        (label, reverse(placeholder[1:-1]) if placeholder.startswith("{") else placeholder)
        for label, placeholder in card.get("links", [])
    ]


def resource_view(request):
    """Resources page. Content lives in pages/content.py — this view only
    wires up internal URLs and verifies PDF paths exist."""
    resources = [dict(card) for card in RESOURCE_CARDS]  # shallow copy per request
    for card in resources:
        _resolve_links(card)
        pdf = card.get("pdf")
        if pdf and not finders.find(pdf):
            logger.warning("resource_view: missing PDF %r for card %r", pdf, card["id"])

    return render(request, "pages/resource.html", {
        "resources": resources,
    })

def search_view(request):
    """Site-wide search: chat groups, chat messages the user can see,
    resource cards, and static pages. Safe for anonymous users."""
    query = (request.GET.get("q") or "").strip()
    results = {"groups": [], "messages": [], "resources": [], "pages": []}

    if query:
        # Static pages are always searchable.
        pages_catalog = [
            ("Home", "home"), ("Hunting Map", "maps"),
            ("Your Trip Checklist", "your_trip"), ("Resources", "resource"),
            ("Blog", "blog"), ("Group Chat", "group_chat"),
        ]
        results["pages"] = [
            (label, name) for label, name in pages_catalog
            if query.lower() in label.lower()
        ]

        # Resource cards match on title/body.
        results["resources"] = [
            card for card in RESOURCE_CARDS
            if query.lower() in card.get("title", "").lower()
            or query.lower() in card.get("body", "").lower()
        ]

        if request.user.is_authenticated:
            # Only groups the user belongs to.
            results["groups"] = request.user.chat_groups.filter(
                name__icontains=query
            )
            # Only messages in groups the user belongs to (or global chat).
            visible_groups = request.user.chat_groups.all()
            results["messages"] = (
                Message.objects.select_related("user", "group")
                .filter(Q(group__in=visible_groups) | Q(group__isnull=True))
                .filter(text__icontains=query)
                .order_by("-created_at")[:25]
            )

    return render(request, "pages/search.html", {
        "query": query,
        "results": results,
        "result_count": (len(results["groups"]) + len(results["messages"])
                         + len(results["resources"]) + len(results["pages"])),
    })


def logged_out_view(request):
    """Friendly "see you next time" page shown after logging out."""
    return render(request, "registration/logged_out.html")


def signup_view(request):
    if request.method == "POST":
        form = SignupForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("group_chat")
    else:
        form = SignupForm()
    return render(request, "registration/signup.html", {"form": form})


@login_required
def account_delete_view(request):
    """Permanently delete the signed-in account after password confirmation.

    Deleting the User cascades to their Profile, chat Messages, and chat group
    memberships. Groups they created keep running (created_by is SET_NULL).
    The user is logged out first so the session doesn't dangle, then redirected
    to the "logged out" farewell page.
    """
    from django.contrib.auth import authenticate, logout

    if request.method == "POST":
        password = request.POST.get("password", "")
        user = authenticate(request, username=request.user.get_username(), password=password)
        if user is not None and user.pk == request.user.pk:
            user = request.user
            logout(request)
            user.delete()
            return redirect("logged_out")
        form_error = "Incorrect password — nothing was deleted."
    else:
        form_error = None
    return render(request, "pages/account_delete.html", {
        "form_error": form_error,
        "message_count": request.user.chat_messages.count(),
        "group_count": request.user.chat_groups.count(),
    })


@login_required
def profile_view(request):
    """View and edit the signed-in user's hunter profile."""
    profile, _ = Profile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        form = ProfileForm(request.POST, request.FILES, instance=profile, user=request.user)
        if form.is_valid():
            form.save()
            shared = getattr(form, "shared_with", [])
            if shared:
                from django.contrib import messages
                messages.info(
                    request,
                    "Saved. Note: " + ", ".join(f"@{u}" for u in shared)
                    + " already use this email — you'll both get the same notifications.",
                )
            return redirect("profile")
    else:
        form = ProfileForm(instance=profile, user=request.user)

    return render(request, "pages/profile.html", {
        "form": form,
        "profile": profile,
    })