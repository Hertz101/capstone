# Code Review — Duplication & Improvement Notes

_2026-11-08 · full-project audit (views, models, forms, templates, CSS, JS)_
_2026-11-09 · updated after the quick-win pass — 6 of 6 checklist items done_

---

## A. Actual duplicates found (and fixed where noted)

### A1. Like-button CSS overrides itself — FIXED ✅

`static/css/base.css` had **two competing `.chat-like-btn` blocks** left over from
the "make it blue / make the heart red" iterations. The second block silently
overrode the first (that's why the earlier "I don't see the blue button"
confusion happened — the file told two stories). Consolidated into one block;
visual behavior unchanged. **Lesson: when iterating on styles, delete the old
rule, don't append a new one.**

### A2. Repeated "membership guard + message fetch + back URL" — 5–6 copies

`group_chat_view`, `message_like_view`, `message_delete_view`,
`message_edit_view`, plus the group views each re-implement:

```python
message = get_object_or_404(Message.objects.select_related("group"), pk=...)
if message.group and not message.group.is_member(request.user):
    return redirect("group_chat")
back = reverse("group_chat_group", args=[message.group.pk])
```

**Suggested refactor:** one helper
`_get_visible_message(request, message_id) -> (message, back_url)` and a
`@group_member_required` decorator. Saves ~40 lines and, more importantly,
makes the security rule impossible to forget in the next view.
**Status: accepted as-is** — the views were stabilized and permission-tested
with this shape; refactoring right before the demo would churn tested code.
First post-demo refactor candidate.

### A3. Inline `from .notifications import …` — 6 copies — FIXED ✅

All inline imports removed; `actor_display` and
`send_group_notification_async` import once at module top of `views.py`.
Verified with `manage.py check` and a full render test.

### A4. Avatar-fallback markup — 3 copies — FIXED ✅

New `templates/partials/_avatar.html` (params: `user`, `size`). The
photo-or-initials block now exists once and is included from `group_chat.html`,
`group_detail.html`, and `profile.html` (sizes 32/32/96 preserved, including
the large-font variant on the profile page). All three templates render-verified.

### A5. Like-button JS bound per-button

`group_chat.html` binds a fetch handler to every `.chat-like-btn` on page
load (fine at 50 messages, but it's ~30 duplicated lines of CSRF-token
plumbing that also exists in `maps.js`). **Suggested fix:** one shared
`static/js/csrf.js` exposing `postJSON(url, data)`, used by both pages.
**Status: open** — small, safe, post-demo.

### A6. `display_name`-vs-username fallback logic exists in three dialects

- Template: `{{ profile.display_name|default:message.user.get_username }}`
- Model: `Profile.display_name` property
- Email: `notifications.actor_display()` (the "Name (username)" variant)
  Not strictly duplication (the email variant is intentionally richer), but the
  first two should converge on the model property everywhere.
  **Status: accepted** — the three variants are intentionally different layers.

---

## B. Redundant / questionable design decisions

| Area                                           | Issue                                                                                                                                                                                 | Suggestion                                                                                                        |
| ---------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| **Edit form in template**                      | The edit button ships a `<form>` with a hidden input pre-filled with the message text; JS converts it to a visible input. Works, but every message carries the text twice in the DOM. | Fetch nothing — this is actually the _progressive-enhancement_ choice. Keep, but note it.                         |
| **`hunting` app vs `pages` app**               | `pages` has grown to ~500 lines of views doing auth, chat, groups, profile, search.                                                                                                   | Split: `chat/` app (Message, ChatGroup, notification views) would make the capstone's architecture story cleaner. |
| **MANUAL_TEST_CASES state check**              | Test plan said `state` validation error on 3+ chars — the widget `maxlength` was client-side only.                                                                                    | **FIXED ✅** — `ProfileForm.clean_state` now enforces exactly-2-letters server-side (also rejects digits). Tested. |
| **`Message.kind` choices vs view whitelist**   | Choices list includes `system`; view whitelist `{"text","plan","packing","gmu"}` is a separate literal.                                                                               | Derive the whitelist from `Message._meta.get_field("kind").choices` so they can't drift.                          |
| **Two checklist checkbox systems**             | `your_trip` uses localStorage; group packing shares go through payload JSON. Fine, but document that they're intentionally separate.                                                  | —                                                                                                                 |
| **`ChatGroup.is_member()` does a fresh query** | Called multiple times per request for the same user.                                                                                                                                  | Negligible at this scale; noted for completeness.                                                                 |
| **CSS: one growing `base.css`**                | Like-button, chat actions, system banner, resource buttons all live in `base.css` "temporarily."                                                                                      | Split into `chat.css`, `like.css` (or let WhiteNoise compression handle it).                                      |
| **Email duplicate guard**                      | Originally hard-rejected two accounts sharing one address; that blocked real demo setups (a couple sharing an inbox).                                                                 | **RELAXED ✅** — sharing is allowed with an informational flash on the profile page naming the other account(s).   |

---

## C. Areas of improvement (ranked by value)

### C1. Security

1. **`message_like_view` returns JSON to non-members with 403 but a _message_** — fine, but the delete/edit views redirect silently. Pick one convention (silent redirect is safer — done).
2. **No rate limiting on post/like — FIXED ✅** — `django-ratelimit` added (also to requirements.txt): 10 posts/min and 30 likes/min per user. Exceeding returns a friendly 429 "Slow down 🐎" page (HTML for posts, JSON for like AJAX). Verified: 13 rapid posts → 10 accepted, 3 blocked.
3. **Session fixation** is handled by Django defaults; nothing to do.
4. **`settings.py` still contains a dev `SECRET_KEY` fallback** — flagged for production; the deploy checklist covers it.

### C2. Data integrity

5. **`Message.group` is nullable** — global-chat messages have `group=NULL`, but most features assume groups exist. Decide: is global chat a feature or an accident? If not, make `group` non-null with a migration to assign orphans.
6. **No `updated_at` on Message — FIXED ✅** — added (`auto_now=True`, migration 0007), saved explicitly on edit, and the chat renders "(edited 2:14 PM)" with the real time. Denver timezone (see below).
7. **Group names aren't unique** — two "Elk Camp"s coexist. For a small app fine; note it in the docs if intended.

### C3. UX polish

8. **No pagination on chat** — hard `[:50]` slice with no "load older" affordance. Older messages are unreachable. (Low priority for demo; a "load more" button is a nice post-demo upgrade.) Documented in README Known limitations.
9. **Like count doesn't live-update for other users** — already documented; would need polling or websockets.
10. **The edit UI offers no way to cancel without a page reload** — the Cancel button calls `window.location.reload()`, losing scroll position. A pure-DOM restore would be nicer.
11. **Deleted messages give no feedback — FIXED ✅** — deletes now flash a dismissible banner: authors see "Your message was deleted."; the creator sees "Moderated: deleted a message by <Name (username)>." Verified both flows.

### C4. Performance (mostly theoretical at this scale)

12. **`liked_ids` + `deletable_ids` are built with extra queries** — could be a single annotated queryset (`Exists()` subquery). At 50 messages, irrelevant; worth knowing for scale.
13. **CPW GeoJSON re-fetched per browser per visit** — no HTTP caching. A 1-hour `Cache-Control` or localStorage memo would cut load time on repeat visits significantly.

### C5. Testing

14. **`pages/tests.py` is thin** relative to the manual test plan — the manual cases that proved most valuable (membership guards, email collisions, kind/payload tampering, edit/delete permissions) are all _automatable_. The permission tests run inline during development would port directly to `tests.py`.
15. **No test for the async email path** — `send_group_notification_async` spawns a thread; in tests use `send_group_notification` (sync) and assert on `django.core.mail.outbox` with the locmem backend.

### C6. Production/deployment — FIXED ✅

- `requirements.txt` was malformed (`python-dotenvDjango` fused) and missing
  Pillow/gunicorn/whitenoise — repaired; deploy would have failed at install
- `STATIC_ROOT` + WhiteNoise compressed storage added; `collectstatic` and a
  full gunicorn run with `DEBUG=false` verified (styles load, zero 4xx)
- `DEBUG` now defaults to False (must opt in locally via `.env`)
- `ALLOWED_HOSTS` falls back to localhost defaults; Render hostname via env
- Remaining known gaps: SQLite is ephemeral on Render (data lost on redeploys)
  and uploaded media has the same issue — documented in README Deployment.

### C7. Honesty/UX details — FIXED ✅

- Email header previously said hardcoded "just now" — now renders the real
  posting time (`Nov 07 at 01:56 PM MST`) passed from the notification code
- `TIME_ZONE` set to `America/Denver` — all displayed timestamps (chat,
  profile, admin) show Colorado time instead of UTC
- Sender identity in emails upgraded from bare username to
  "Firstname Lastname (username)" via `notifications.actor_display()`
- Multi-line `{# ... #}` template comments in the email template rendered as
  literal text in sent mail (Gmail got raw template source) — comments removed
  and all 15 templates parse-checked to catch the same class elsewhere

---

## D. Things done well (worth keeping / mentioning in the write-up)

- **Progressive enhancement everywhere** — every JS feature (likes, edit, share) degrades to a working POST/redirect flow.
- **Post/Redirect/Get discipline** — no refresh-duplicate issues.
- **Security model consistency** — membership checks mirror across chat, likes, edits, deletes, group detail; the same rule enforced five ways _is_ the duplication, but it never once leaked access during testing.
- **Offline data pipeline** (`scripts/`) — PDF→JSON at build time keeps the demo independent of CPW's website.
- **Email design** — multipart text+HTML, inline styles, honest timestamps, real reversal of URLs.

---

## E. Quick-win checklist — ALL DONE ✅ (2026-11-09)

- [x] A3: hoist notification import to top of views.py — done; 5 inline imports removed
- [x] C2#6: add `updated_at` to Message — done; migration 0007; chat shows "(edited <time>)"
- [x] C1#2: rate-limit chat POST + likes with django-ratelimit — done; 10/min posts, 30/min likes, friendly 429 page
- [x] B: server-side `clean_state` check — done; rejects non-2-letter states, tested
- [x] A4: avatar partial — done; `templates/partials/_avatar.html` used in 3 templates
- [x] C3#11: flash message on delete — done; author vs moderator wording, both verified

### Remaining open items (post-demo backlog)

1. A2 membership-guard helper refactor
2. A5 shared CSRF/`postJSON` JS helper
3. B: derive the kind whitelist from model choices
4. B: split `base.css` per feature
5. C2#5: decide global-chat (nullable group) fate
6. C2#7: group-name uniqueness policy
7. C3#8–10: chat pagination, live like counts, DOM-based edit cancel
8. C4#12–13: queryset annotation; CPW response caching
9. C5: port the inline permission/tamper tests into `pages/tests.py`
