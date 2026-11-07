"""Email notifications for group-chat activity.

send_group_notification() emails every member of a chat group when someone
posts a message or likes one. Gmail SMTP is configured in settings.MAILERS;
when no credentials are present the console backend prints the email to the
runserver log instead, so the flow is testable offline.
"""
import logging

from django.conf import settings
from django.core.mail import mailers
from django.template.loader import render_to_string
from django.urls import reverse

logger = logging.getLogger(__name__)


def _active_mailer():
    """The 'default' mailer when Gmail creds exist, else 'console'.

    Opens the connection lazily: the SMTP handshake happens on send, not here,
    so a Gmail outage surfaces as a logged send failure, not a startup crash.
    """
    cfg = settings.MAILERS.get("default", {}).get("OPTIONS", {})
    if cfg.get("username") and cfg.get("password"):
        return mailers.default
    return mailers["console"]


def _deliver(email):
    """Send one email, retrying connection errors with backoff.

    Runs in a background thread so posting/liking never waits on Gmail's
    SMTP handshake (1-3s). Gmail rate-limits rapid connections; a short
    backoff and a fresh connection usually clears it.
    """
    import time
    for attempt in range(3):
        try:
            with _active_mailer() as connection:
                sent = connection.send_messages([email])
                if sent:
                    return
                raise OSError("SMTP send returned 0 messages")
        except OSError as exc:
            if attempt == 2:
                logger.error(
                    "group notification email failed after 3 attempts: %s", exc
                )
                return
            time.sleep(1.5 * (attempt + 1))
    

def send_group_notification_async(group, actor, subject_line, body_lines, group_url=None, request=None):
    """Build the email now, deliver in a daemon thread, return immediately.

    Use this from views. Any exception in the thread is logged, never raised —
    a mail outage must never break posting or liking.
    """
    import threading
    recipients = [
        m.email for m in group.members.all()
        if m.email and m.pk != actor.pk
    ]
    if not recipients:
        return
    email = _build(group, actor, subject_line, body_lines, group_url, request, recipients)
    threading.Thread(target=_deliver, args=(email,), daemon=True).start()


def _build(group, actor, subject_line, body_lines, group_url, request, recipients):
    from django.core.mail import EmailMultiAlternatives

    if request is not None and group_url:
        request_url = request.build_absolute_uri(group_url)
    elif group_url:
        request_url = f"http://127.0.0.1:8000{group_url}"
    else:
        request_url = None
    text = "\n".join([
        f"{_actor_display(actor)} {subject_line}:",
        "",
        *body_lines,
    ])
    if request_url:
        text += f"\n\nView it here: {request_url}"
    text += "\n\n— Rocky Mountain Coalition group chat"

    # The real posting time, in the viewer's time zone (America/Denver),
    # instead of a hardcoded "just now" that a throttled send would make a lie.
    from django.utils import timezone as dj_tz
    posted_time = dj_tz.localtime().strftime("%b %d at %I:%M %p %Z")

    html = render_to_string("emails/group_notification.html", {
        "group_name": group.name,
        "actor_name": _actor_display(actor),
        "action": subject_line,
        "body_lines": body_lines,
        "request_url": request_url,
        "posted_time": posted_time,
    })
    return EmailMultiAlternatives(
        subject=f"[{group.name}] {_actor_display(actor)} {subject_line}"[:120],
        body=text,
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "webmaster@localhost"),
        to=recipients,
        alternatives=[(html, "text/html")],
    )


def _actor_display(actor):
    """'Firstname Lastname (username)' — falls back to username alone."""
    try:
        profile = actor.profile
        full = f"{profile.first_name} {profile.last_name}".strip()
    except Exception:
        full = ""
    username = actor.get_username()
    return f"{full} ({username})" if full and full.lower() != username.lower() else username


def actor_display(actor):
    """Public helper so views can embed the same readable name in text."""
    return _actor_display(actor)


def send_group_notification(group, actor, subject_line, body_lines, group_url=None, request=None):
    """Synchronous variant: email all members except the actor, return count.

    Kept for tests and shell use; views should call the async version.
    """
    recipients = [
        m.email for m in group.members.all()
        if m.email and m.pk != actor.pk
    ]
    if not recipients:
        return 0
    email = _build(group, actor, subject_line, body_lines, group_url, request, recipients)
    try:
        with _active_mailer() as connection:
            return connection.send_messages([email])
    except Exception:
        logger.exception("group notification email failed for group %s", group.pk)
        return 0
