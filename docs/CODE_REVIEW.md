# Code Review — Duplication & Improvement Notes
_2026-11-08 · full-project audit (views, models, forms, templates, CSS, JS)_

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

### A3. Inline `from .notifications import …` — 6 copies
Every notification site re-imports inside the function (originally to dodge a
circular import that no longer exists). Now that `actor_display` is imported
at module top in `views.py`, the `send_group_notification_async` import can
move there too — **one import line, six deletions.**

### A4. Avatar-fallback markup — 3 copies
The "photo, else initials-in-a-badge" block appears in `group_chat.html`,
`group_detail.html`, and `profile.html` with slightly different sizes/styles.
**Suggested fix:** one `{% include "partials/_avatar.html" %}` partial taking
`user` and `size`.

### A5. Like-button JS bound per-button
`group_chat.html` binds a fetch handler to every `.chat-like-btn` on page
load (fine at 50 messages, but it's ~30 duplicated lines of CSRF-token
plumbing that also exists in `maps.js`). **Suggested fix:** one shared
`static/js/csrf.js` exposing `postJSON(url, data)`, used by both pages.

### A6. `display_name`-vs-username fallback logic exists in three dialects
- Template: `{{ profile.display_name|default:message.user.get_username }}`
- Model: `Profile.display_name` property
- Email: `notifications._actor_display()` (the "Name (username)" variant)
Not strictly duplication (the email variant is intentionally richer), but the
first two should converge on the model property everywhere.

---

## B. Redundant / questionable design decisions

| Area | Issue | Suggestion |
|---|---|---|
| **Edit form in template** | The edit button ships a `<form>` with a hidden input pre-filled with the message text; JS converts it to a visible input. Works, but every message carries the text twice in the DOM. | Fetch nothing — this is actually the *progressive-enhancement* choice. Keep, but note it. |
| **`hunting` app vs `pages` app** | `pages` has grown to ~500 lines of views doing auth, chat, groups, profile, search. | Split: `chat/` app (Message, ChatGroup, notification views) would make the capstone's architecture story cleaner. |
| **`MANUAL_TEST_CASES.md` claims vs code** | Test plan says `state` validation error on 3+ chars — verify the form actually enforces it (model `max_length=2` does, but only via form widget `maxlength`, which is client-side). | Add `min_length=2` server-side check in `ProfileForm.clean_state`. |
| **`Message.kind` choices vs view whitelist** | Choices list includes `system`; view whitelist `{"text","plan","packing","gmu"}` is a separate literal. | Derive the whitelist from `Message._meta.get_field("kind").choices` so they can't drift. |
| **Two checklist checkbox systems** | `your_trip` uses localStorage; group packing shares go through payload JSON. Fine, but document that they're intentionally separate. | — |
| **`ChatGroup.is_member()` does a fresh query** | Called multiple times per request for the same user. | Negligible at this scale; noted for completeness. |
| **CSS: one growing `base.css`** | Like-button, chat actions, system banner, resource buttons all live in `base.css` "temporarily." | Split into `chat.css`, `like.css` (or let Django's compress handle it). |

---

## C. Areas of improvement (ranked by value)

### C1. Security
1. **`message_like_view` returns JSON to non-members with 403 but a *message*** — fine, but the delete/edit views redirect silently. Pick one convention (silent redirect is safer — done).
2. **No rate limiting on post/like.** A script could spam FAC with 1000 messages/sec. `django-ratelimit` is ~5 lines to add per view.
3. **Session fixation** is handled by Django defaults; nothing to do.
4. **`settings.py` still contains a dev `SECRET_KEY` fallback** — flagged for production; the deploy checklist covers it.

### C2. Data integrity
5. **`Message.group` is nullable** — global-chat messages have `group=NULL`, but most features assume groups exist. Decide: is global chat a feature or an accident? If not, make `group` non-null with a migration to assign orphans.
6. **No `updated_at` on Message** — you have `edited` flag but not *when*. One line: `updated_at = models.DateTimeField(auto_now=True)` shown next to "(edited)".
7. **Group names aren't unique** — two "Elk Camp"s coexist. For a small app fine; note it in the docs if intended.

### C3. UX polish
8. **No pagination on chat** — hard `[:50]` slice with no "load older" affordance. Older messages are unreachable. (Low priority for demo; a "load more" button is a nice post-demo upgrade.)
9. **Like count doesn't live-update for other users** — already documented; would need polling or websockets.
10. **The edit UI offers no way to cancel without a page reload** — the Cancel button calls `window.location.reload()`, losing scroll position. A pure-DOM restore would be nicer.
11. **Deleted messages give no feedback** — page just reloads. A one-time flash message ("Message deleted") would clarify.

### C4. Performance (mostly theoretical at this scale)
12. **`liked_ids` + `deletable_ids` are built with extra queries** — could be a single annotated queryset (`Exists()` subquery). At 50 messages, irrelevant; worth knowing for scale.
13. **CPW GeoJSON re-fetched per browser per visit** — no HTTP caching. A 1-hour `Cache-Control` or localStorage memo would cut load time on repeat visits significantly.

### C5. Testing
14. **`pages/tests.py` is likely thin** relative to the manual test plan — the manual cases that proved most valuable (membership guards, email collisions, kind/payload tampering, edit/delete permissions) are all *automatable*. The permission tests I ran inline during development would port directly to `tests.py`.
15. **No test for the async email path** — `send_group_notification_async` spawns a thread; in tests use `send_group_notification` (sync) and assert on `django.core.mail.outbox` with the locmem backend.

---

## D. Things done well (worth keeping / mentioning in the write-up)
- **Progressive enhancement everywhere** — every JS feature (likes, edit, share) degrades to a working POST/redirect flow.
- **Post/Redirect/Get discipline** — no refresh-duplicate issues.
- **Security model consistency** — membership checks mirror across chat, likes, edits, deletes, group detail; the same rule enforced five ways *is* the duplication, but it never once leaked access during testing.
- **Offline data pipeline** (`scripts/`) — PDF→JSON at build time keeps the demo independent of CPW's website.
- **Email design** — multipart text+HTML, inline styles, honest timestamps, real reversal of URLs.

---

## E. Quick-win checklist (if you have an hour before presenting)
- [ ] A3: hoist notification import to top of views.py (5 min)
- [ ] C2#6: add `updated_at` to Message (10 min incl. migration)
- [ ] C1#2: rate-limit the chat POST with django-ratelimit (15 min)
- [ ] B: server-side `clean_state` length check (5 min)
- [ ] A4: avatar partial (15 min)
- [ ] C3#11: flash message on delete (10 min)
