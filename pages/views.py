
import datetime
import json
import logging
import os

from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.staticfiles import finders
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from .content import PRE_HUNT_CHECKLIST, RESOURCE_CARDS
from .forms import ChatGroupForm, ProfileForm, SignupForm
from .models import ChatGroup, Message, Profile
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
def group_chat_view(request, group_id=None):
    """Group chat: list the latest messages in a group, let users post one.

    POST is the only write path; a redirect back to the page afterwards
    keeps the browser's back button working (Post/Redirect/Get).
    """
    if group_id:
        group = get_object_or_404(ChatGroup, pk=group_id)
        if not group.is_member(request.user):
            return redirect("group_chat")
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
        payload = None
        if kind != "text":
            try:
                payload = json.loads(request.POST.get("payload", ""))
            except (json.JSONDecodeError, TypeError):
                kind = "text"
            if not isinstance(payload, dict):
                kind, payload = "text", None
        if text:
            Message.objects.create(
                group=group, user=request.user, text=text, kind=kind, payload=payload,
            )
        if group:
            return redirect("group_chat_group", group_id=group.pk)
        return redirect("group_chat")

    messages = Message.objects.select_related("user").filter(group=group).order_by("-created_at")[:50]
    return render(request, "pages/group_chat.html", {
        "chat_messages": messages,
        "chat_group": group,
        "chat_sidebar_mtime": sidebar_mtime,
    })


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
        group.members.add(request.user)
    return redirect("group_chat_group", group_id=group.pk)


@login_required
def group_create_view(request):
    """Create a new group and pick the users to add."""
    if request.method == "POST":
        form = ChatGroupForm(request.POST, current_user=request.user)
        if form.is_valid():
            group = form.save()
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
        if request.POST.get("action") == "add":
            user_id = request.POST.get("user_id")
            if user_id and group.created_by == request.user:
                user = get_object_or_404(User, pk=user_id)
                group.members.add(user)
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
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            return redirect("profile")
    else:
        form = ProfileForm(instance=profile)

    return render(request, "pages/profile.html", {
        "form": form,
        "profile": profile,
    })