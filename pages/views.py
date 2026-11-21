
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


def _rate_limited_response(message="You're doing that too quickly."):
    """Friendly 429 page shown when a user posts/likes too fast."""
    from django.http import HttpResponse
    return HttpResponse(
        f"<h1>Slow down 🐎</h1><p>{message} "
        "Wait a minute and try again.</p>",
        status=429,
    )


def _static_mtime(asset_path):
    """int mtime of a static asset for cache-busting, 1 if it can't be stat'd."""
    try:
        return int(os.path.getmtime(finders.find(asset_path) or asset_path))
    except OSError:
        return 1


def _get_visible_message(request, message_id):
    """Fetch a message and apply the group-membership invariant.

    Returns (message, back_url, visible). The membership guard lives here —
    the security rule is enforced once, not re-typed per view. Callers decide
    the rejection shape: silent redirect for form posts, 403 JSON for AJAX.
    """
    message = get_object_or_404(Message.objects.select_related("group"), pk=message_id)
    back = reverse("group_chat")
    visible = True
    if message.group:
        visible = message.group.is_member(request.user)
        back = reverse("group_chat_group", args=[message.group.pk])
    return message, back, visible


def home_view(request):
    return render(request, "pages/home.html")





def maps_view(request):
    """Hunting map page. Logged-in users also get their chat groups so the
    'Share to group chat' button can target a specific group."""
    context = {
        "maptiler_key": get_maptiler_key(),
    }
    if request.user.is_authenticated:
        context["chat_groups"] = request.user.chat_groups.all()
    # Cache-busters: browsers pick up edits to these scripts without a hard
    # refresh. Needed on every script the map page loads — a stale cached
    # cpw-config.js next to a fresh maps.js breaks the tile layer.
    for name, path in (("maps_js_mtime", "js/maps.js"),
                       ("cpw_config_mtime", "js/cpw-config.js"),
                       ("csrf_js_mtime", "js/csrf.js")):
        context[name] = _static_mtime(path)
    return render(request, "pages/maps.html", context)


def your_trip_view(request):
    """Interactive pre-hunt checklist, grouped like the classic pre-hunt lists."""
    return render(request, "pages/your_trip.html", {
        "checklist": PRE_HUNT_CHECKLIST,
    })





@login_required
@ratelimit(key="user", rate="10/m", method="POST", block=False)
def _handle_chat_post(request, group):
    """Process a POSTed chat message. Returns an HttpResponse (redirect or 429).

    Shared cards (plan / packing / gmu) carry a kind + JSON payload;
    anything else is a plain typed message. Invalid payloads degrade to text.
    """
    text = request.POST.get("text", "").strip()
    # The model's max_length isn't enforced by SQLite for raw POSTs (no form
    # validation here), so truncate server-side. Matches the edit path's limit.
    text = text[:2000]
    kind = request.POST.get("kind", "text")
    if kind not in {"text", "plan", "packing", "gmu"}:
        kind = "text"
    if request.limited:
        return _rate_limited_response("You're posting too quickly.")
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
        # No group and no memberships: send the user to the group list.
        # Previously this fell through to a listing of messages with
        # group=NULL, which leaked those messages to everyone.
        return redirect("group_list")

    sidebar_mtime = _static_mtime("js/chat_sidebar.js")

    if request.method == "POST":
        return _handle_chat_post(request, group)

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
    message, back, visible = _get_visible_message(request, message_id)
    if not visible:
        return JsonResponse({"error": "not a member"}, status=403)

    if request.limited:
        return JsonResponse({"error": "slow down"}, status=429)

    # The toggle is POST-only (the chat JS always POSTs). Rejecting other
    # methods makes the state change explicit and keeps GET read-only.
    if request.method != "POST":
        return JsonResponse({"error": "method not allowed"}, status=405)

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
    # Re-read the count after the write so a rapid double-click (or
    # concurrent tab) can't return a stale total.
    return JsonResponse({"liked": liked, "count": message.liked_by.count()})


@login_required
def message_delete_view(request, message_id):
    """Delete a chat message: author or group creator only (POST).

    Silent by design — deleting must not email the group.
    """
    message, back, visible = _get_visible_message(request, message_id)
    if not visible:
        return redirect(back)

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
    message, back, visible = _get_visible_message(request, message_id)
    if not visible:
        return redirect(back)

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
    return _rate_limited_response()


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
@ratelimit(key="user", rate="10/m", method="POST", block=False)
def group_join_view(request, group_id):
    """Join a group from the group list page.

    Rate-limited because joining fires a notification email to every
    member — without it, rapid join/leave cycling could flood inboxes.
    """
    group = get_object_or_404(ChatGroup, pk=group_id)
    if request.method == "POST":
        if request.limited:
            return _rate_limited_response("You're joining groups too quickly.")
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


def announce_new_member(group, actor, member, request, welcome_body):
    """Post the "👋 ... was added" system message and fire the welcome email.

    Shared by group_create_view (initial members) and group_detail_view
    (creator adds someone later); welcome_body is the email's second line.
    """
    # Post a chat message announcing the new member so the
    # whole group sees who arrived, even without email.
    Message.objects.create(
        group=group,
        user=actor,
        text=f"👋 {actor_display(member)} was added to the group by "
             f"{actor_display(actor)} — say hi!",
        kind="system",
    )
    if member.email:
        send_group_notification_async(
            group,
            actor,
            "welcomed you to the group",
            [welcome_body, "Open the chat and say hi!"],
            group_url=reverse("group_chat_group", args=[group.pk]),
            request=request,
        )


def _add_group_member(request, group, user, welcome_body):
    """Add a user to a group, then announce it via announce_new_member."""
    group.members.add(user)
    announce_new_member(group, request.user, user, request, welcome_body)


@login_required
def group_create_view(request):
    """Create a new group and pick the users to add."""
    if request.method == "POST":
        form = ChatGroupForm(request.POST, current_user=request.user)
        if form.is_valid():
            group = form.save()
            for member in group.members.exclude(pk=request.user.pk):
                _add_group_member(
                    request,
                    group,
                    member,
                    f"{actor_display(request.user)} created \u201c{group.name}\u201d "
                    "and added you as one of its first members.",
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
        action = request.POST.get("action")
        if action == "delete":
            # Creator-only group deletion. Cascades to the group's messages.
            if group.created_by == request.user:
                group.delete()
                return redirect("group_list")
            return redirect("group_detail", group_id=group.pk)
        if action == "add":
            user_id = request.POST.get("user_id")
            if user_id and group.created_by == request.user:
                try:
                    user = User.objects.get(pk=user_id)
                except (User.DoesNotExist, ValueError, TypeError):
                    return redirect("group_detail", group_id=group.pk)
                if not group.is_member(user):
                    _add_group_member(
                        request,
                        group,
                        user,
                        f"{actor_display(request.user)} added you to "
                        f"\u201c{group.name}\u201d — the hunt-planning crew.",
                    )
        elif action == "remove":
            user_id = request.POST.get("user_id")
            if user_id and group.created_by == request.user:
                # Coerce/validate the raw pk so garbage input can't 500, and
                # keep the creator in their own group — otherwise the group
                # becomes orphaned (created_by is SET_NULL) with no one able
                # to manage it.
                try:
                    target = User.objects.get(pk=user_id)
                except (User.DoesNotExist, ValueError, TypeError):
                    target = None
                if target and target.pk != group.created_by_id:
                    group.members.remove(target)
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
            # New users have no groups yet, so send them to the group list
            # (group_chat would just bounce there anyway).
            return redirect("group_list")
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