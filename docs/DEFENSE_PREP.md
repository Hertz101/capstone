# Capstone Defense Prep — Question Bank Answers

**Project:** Rocky Mountain Coalition Hunt Planner (Django 6.1 / Python 3.14)
**Live:** https://rmcplanner.onrender.com
Every answer below references real code in this repo — file/line anchors are included so you can open them live during the defense.

---

## 1. Architecture & Tech Stack Decisions

### Q: "Walk me through the lifecycle of a single request."

**Best trace: liking a chat message** (touches frontend → AJAX → DB → JSON → DOM) or **posting a message** (touches form → redirect → DB → email thread). Trace the like:

1. **Click (frontend).** User clicks the ❤ button in `templates/pages/group_chat.html`. JS in the chat sidebar binds a fetch handler: `POST /messages/<id>/like/` with the CSRF token from the page's hidden input (`static/js/` chat code; the shared plumbing pattern is noted in `docs/CODE_REVIEW.md` §A5).
2. **Routing.** `config/urls.py` includes `pages/urls.py`; the URL `messages/<int:message_id>/like/` maps to `message_like_view` (`pages/urls.py:19`).
3. **Middleware.** The request passes Django's middleware stack in order (`config/settings.py:72-83`): SecurityMiddleware → WhiteNoise (static only) → SessionMiddleware (loads the session cookie → `request.user`) → CsrfViewMiddleware (rejects the POST without a valid token) → AuthenticationMiddleware → MessagesMiddleware → XFrameOptions.
4. **Authorization.** The view is wrapped in `@login_required` (unauthenticated → redirect to login) and `@ratelimit(key="user", rate="30/m", method="POST")` (`pages/views.py:176-177`).
5. **Business logic.** `pages/views.py:message_like_view`:
   - Fetch the message with `get_object_or_404(Message.objects.select_related("group"), pk=...)` — `select_related` avoids an N+1 query for the group.
   - **Membership gate:** if the message belongs to a group and the user isn't a member, return 403 JSON. This is the app's core security invariant.
   - Toggle: `message.liked_by.filter(pk=request.user.pk).exists()` → `add()` or `remove()` on the M2M table.
   - If liked and group-scoped, fire an email notification on a background thread (`send_group_notification_async`) so the response isn't blocked on SMTP.
6. **Database.** Django's ORM writes one INSERT/DELETE into the implicit M2M table `pages_message_liked_by`. Nothing else is written — the "count" is re-read after the write (`message.liked_by.count()`) so a rapid double-click can't return a stale total.
7. **Response.** `JsonResponse({"liked": bool, "count": n})`.
8. **UI update.** The fetch handler updates the heart's class and count in place — no page reload. If JS had failed, the fallback story: all other writes (post/edit/delete) are plain form POSTs with Post/Redirect/Get, so the app degrades gracefully.

For a *form* trace instead, use **posting a message**: form POST → `group_chat_view` (POST branch) → `_handle_chat_post` → truncate to 2000 chars, whitelist `kind`, JSON-parse the shared-card `payload` (invalid → degrade to plain text) → `Message.objects.create(...)` → async notification email → 302 redirect back to the group page (Post/Redirect/Get prevents refresh-duplicates).

### Q: "Why did you choose this specific tech stack?"

- **Django (backend framework).** The app's risk areas are exactly what Django ships solved out of the box: authentication and password hashing, CSRF protection, ORM with migrations, session handling, and an admin for data fixes. Building those by hand on Flask/FastAPI would be security risk, not learning.
- **Python (language).** Strongest language for me; also the right fit for the *data* half of the project — the CPW harvest PDFs are parsed with Python (pdfplumber + regex) at build time, so one language covers web + data pipeline.
- **Relational SQL (PostgreSQL) over NoSQL.** The data is inherently relational: `Profile ←1:1→ User`, `ChatGroup ←M:N→ Users (members)`, `Message → group & author (FKs)`, `Message ←M:N→ liked_by`. Referential integrity matters (deleting a user must cascade to their messages and memberships; deleting a group must cascade to its messages). A document store would push that integrity into application code and give up joins — e.g., the search view joins messages → groups → membership in one queryset filter.
- **Server-rendered Django templates + Bootstrap over a SPA.** The product is content- and form-heavy; every JS interaction (likes, edit, share) keeps a plain-form fallback so the app works without JavaScript (relevant in the field on poor connections). No build step, no client state library needed.
- **SQLite locally / PostgreSQL in production,** chosen automatically: `settings.py` uses `DATABASE_URL` when present, SQLite otherwise — zero-setup dev, real database in prod.
- **WhiteNoise + Render free tier** over a k8s-sized platform: compressed, fingerprinted static serving without running a CDN or nginx.

### Q: "How did you structure your project files and separate concerns?"

Django's MVT (Model-View-Template, Django's flavor of MVC where the "view" is the controller and the template is the view):

```
config/      settings, root URLs, WSGI — configuration only, no business logic
pages/       the main app
  models.py    data layer (Message, ChatGroup, Profile, HuntingMethod)
  forms.py     input validation layer (SignupForm, ProfileForm, ChatGroupForm)
  views.py     request/response logic — thin: auth gate → model op → render
  content.py   static content data (checklist, resource cards) out of code paths
  notifications.py  email composition + async sending — isolated so views
                    never touch SMTP directly
  tests.py     55 tests
hunting/     second app — the planner page (deliberately separate concern)
templates/   presentation: base/navbar/footer, pages/, emails/, partials/
             (_avatar.html is a reusable component used by 3 templates)
static/      css/, js/ (maps, chat sidebar, planner), vendored libs
scripts/     build-time data pipeline — NOT runtime code (CPW PDF→JSON)
docs/        review notes, manual test cases, quote
```

Separation points worth naming:
- **URLs → views → models:** routing is declarative in `urls.py`; views contain no SQL and models contain no HTTP.
- **Email isolated** in `notifications.py` — views call `send_group_notification_async(...)` and never build MIME or touch SMTP.
- **Reusable UI:** `templates/partials/_avatar.html` (photo-or-initials, parameterized by user + size) eliminates three copies of that markup.
- **Build-time vs runtime:** `scripts/` runs offline to produce `static/hunting/elk_stats.json`; the deployed app never parses PDFs.

---

## 2. Database & Data Management

### Q: "Show me your schema and explain the relationships."

Four tables (Django's built-in `auth_user` plus three app tables in `pages/models.py`):

| Relationship | Implementation | Deletion behavior |
| --- | --- | --- |
| `Profile → User` | **OneToOneField** (`pages/models.py:85-89`) | `CASCADE` — profile dies with the user |
| `Message → ChatGroup` | **ForeignKey** (`models.py:8-14`) | `CASCADE` — deleting a group deletes its messages |
| `Message → User (author)` | **ForeignKey** (`models.py:15-19`) | `CASCADE` — user deletion removes their messages |
| `ChatGroup → User (creator)` | **ForeignKey** (`models.py:52-57`) | **`SET_NULL`** — deliberate: a group survives its creator leaving/deleting, so other members keep their room |
| `ChatGroup ↔ User (members)` | **ManyToManyField** (`models.py:58-62`) | implicit join table; memberships vanish with either side |
| `Message ↔ User (likes)` | **ManyToManyField** (`models.py:31-35`) | same |

Redundancy prevention: everything normalized — no message stores its author's name or group's name; templates resolve them via FK (`select_related("user", "group")`). The one intentional denormalization: `Message.payload` is a **JSONField** holding the shared-card content (plan/packing/GMU data) — that payload is a *value object*, never joined against, so embedding it avoids a fourth table for low-structure data.

Also mention the safety rules attached to the schema: `Profile.state` validated to exactly two letters server-side; `Message.kind` constrained by `TextChoices`; ordering guaranteed via `Meta.ordering`.

### Q: "How do you handle file uploads and persistent media?"

- Upload path: `ImageField(upload_to="profile_photos/%Y/%m/")` (`pages/models.py:99-104`) — sharded by year/month so no directory gets huge. Pillow (via `ImageField`) validates that the upload is actually an image, not a renamed executable.
- **Honest answer (this is a strength, not a weakness, if framed right):** media goes to local disk (`MEDIA_ROOT`, `settings.py:191`) via Django's `FileSystemStorage`. On **Render's free tier the disk is ephemeral** — every redeploy resets uploaded photos. This is a documented known limitation (README "Known limitations") with a planned fix: move to an S3-compatible object store with `django-storages`, which requires only a settings swap because all file access already goes through Django's storage API, not raw filesystem paths. Frame it as: *"I know where the abstraction boundary is, and the fix is contained to the storage backend."*

### Q: "What happens if your database grows to 100,000 records?"

What's already done:
- **Server-side filtering and slicing everywhere.** Chat shows only the latest 50 (`[:50]` in `group_chat_view`), search results cap at 25 messages; the client never receives unbounded lists.
- **Query-shape discipline:** `select_related("user")` / `select_related("group")` on message fetches kills N+1 queries; search filters with `icontains` in SQL, not Python.
- Indexed automatically: every primary key, every FK column, and `Meta.ordering` columns (`created_at`, group `name`) get B-tree indexes.

What I'd add at that scale (say this proactively):
1. **Composite index** on `(group, created_at)` for the chat query — that's the hot path, and the ordering column alone isn't enough once a group has deep history.
2. **Real pagination** (cursor-based `created_at` cursor, since keyset pagination beats OFFSET at depth) plus a "load older" button.
3. `liked_ids`/`deletable_ids` are currently built with two extra queries per request — replace with `Exists()` subquery annotations (already flagged in `docs/CODE_REVIEW.md` §C4).
4. Postgres-level work: `pg_trgm`/full-text search to replace `icontains` (`LIKE '%q%'` can't use a B-tree index at scale).
5. Object counts this app will realistically hit make most of this theoretical — and I can say *why* each matters rather than cargo-culting them.

---

## 3. Security & Authentication

### Q: "How does authentication and authorization work?"

**Authentication (who you are):**
- Django's built-in `auth` system: passwords are **hashed with PBKDF2 (SHA-256, 600k iterations by default in current Django)** — never stored or logged in plaintext. Four password validators enforce length/similarity/commonness (`settings.py:130-143`).
- **Session cookies, not JWTs.** Server-side sessions in the DB, a signed session id in an HttpOnly cookie — the right choice for a server-rendered app (JWTs would add token-storage/revocation problems for zero benefit here). CSRF middleware pairs with the session cookie.

**Authorization (what you may do)** — the invariant I can defend hardest: **group membership gates every read and write of group content.** The same rule is enforced at five separate entry points (`ChatGroup.is_member()` — chat view, like, delete, edit, search):

- User A cannot read group B's messages by **typing the URL** (`/group_chat/<id>/` → non-member redirect, `views.py:140-141`).
- Cannot **like** B's messages (403 JSON, `views.py:185-186`).
- Cannot **edit** B's messages — edit additionally requires author identity *and* `kind == "text"` (`views.py:258-262`).
- Cannot **delete** B's messages — author-or-group-creator only (`views.py:229-231`); the creator distinction is creator-only moderation.
- Cannot see B's content in **search** — the queryset is filtered through `request.user.chat_groups` (`views.py:466-480`), including the fix where orphan messages (`group=NULL`) were deliberately excluded because they'd otherwise leak to everyone.
- Group admin actions (add/remove members, delete group) are gated on `created_by == request.user`; removing the creator from their own group is blocked so the group can't be orphaned (`views.py:397-408`).
- Account self-deletion requires **password re-confirmation** via `authenticate()` (`views.py:520-527`).

### Q: "How did you validate user input and prevent common vulnerabilities?"

- **Backend validation even with frontend limits:** the profile form's `maxlength=2` on state was client-side only — tampering past it worked until I added `ProfileForm.clean_state` server-side (rejects wrong lengths and digits; documented as FIXED in `docs/CODE_REVIEW.md`). Chat text is truncated to 2000 server-side too, because SQLite doesn't enforce `max_length` on raw POSTs bypassing forms (`views.py:95-98`). Share-card payloads are JSON-parsed and type-checked server-side, degrading to plain text on tampering.
- **SQL injection:** impossible by construction — all access goes through the ORM's parameterized queries; no raw SQL anywhere in the repo.
- **XSS:** Django templates auto-escape all interpolated values by default; there is no `|safe` filter and no `innerHTML` assignment on user content in the JS. A `<script>` posted to chat renders as text.
- **CSRF:** `CsrfViewMiddleware` on every POST; all forms carry `{% csrf_token %}`, and the AJAX like POST sends the token in the `X-CSRFToken` header. A cross-origin form posting to `/messages/<id>/like/` fails the token check.
- **Other hardening:** `DEBUG=False` by default (opt-in locally only, `settings.py:46-49`); `ALLOWED_HOSTS` from env; rate limiting (django-ratelimit: 10 posts/min, 30 likes/min) with a friendly 429 page so floods of notification emails are bounded; membership-guard + rate-limit on group join because joins fire emails; session fixation handled by Django rotating session keys on login.

### Q: "How are you managing API keys and environment variables?"

- **No secrets in the repo.** Everything comes from the environment via `load_dotenv(BASE_DIR/".env")` locally (`settings.py:23`) and Render env vars in production: `DJANGO_SECRET_KEY`, `DATABASE_URL`, `DJANGO_ALLOWED_HOSTS`, `MAPTILER_API_KEY`, `EMAIL_HOST_USER/PASSWORD`, `SITE_BASE_URL`, `EMAIL_PORT`/`EMAIL_USE_SSL`. `.env` is git-ignored.
- **Fail-fast, not fail-insecure:** with no `DJANGO_SECRET_KEY` and `DJANGO_DEBUG` unset, the process refuses to boot (`settings.py:34-40`) rather than silently running with a committed dev key. Debug mode likewise defaults to False and must be *opted into* locally.
- **Defense in depth on the map key:** the MapTiler key is necessarily public (it's used in browser tile URLs), but it's passed per-request from the server into the template (`config/maptiler.py`), can be domain-restricted in the MapTiler dashboard, and rotating it is a one-variable change — no redeploy of code.
- Gmail uses an **App Password on a 2FA account** (never the real account password), spaces stripped because Google displays it grouped (`settings.py:207-209`).
- One honest footnote: a dev-only `SECRET_KEY` fallback string exists in settings for the explicit `DJANGO_DEBUG=true` path — flagged in the deploy checklist; production gets the key from Render env only.

---

## 4. Frontend & User Experience (UX)

### Q: "How do you manage state across your frontend?"

- **Server is the source of truth for app state.** State lives in Postgres; each page render receives it as template context (chat messages, liked ids, deletable ids, group membership flags). No client state library — there's nothing to synchronize.
- **Two kinds of client-side state, each deliberate:**
  1. *Ephemeral UI state* (open/closed sidebar, edit-mode) — DOM-only, lost on reload by design.
  2. *Persistent personal state* — the **Your Trip checklist**, stored in `localStorage` keyed per item, because packing progress is per-browser, not shared data. The *shared* copy of the packing list is a different mechanism (a chat card with JSON payload) — intentionally separate systems, documented as such.
- **Async calls:** vanilla `fetch` with JSON responses (like toggle) or awaited GeoJSON/stat loads (`static/js/maps.js:364`). Loading states: the map shows a status line via `updateStatus()` for layer errors, and stats are treated as optional (try/catch — the map works if stats fail). Like failures return JSON errors surfaced inline; form failures re-render the Django form with field errors.
- **Concurrency detail worth citing:** after a like write, the count is **re-read** before responding, so a double-click or second tab can't echo a stale total (`views.py:211-213`).

### Q: "Is the application responsive, and how did you test it?"

- **Bootstrap 5 grid + components** for the responsive strategy (navbar collapse, card grids, forms) with a custom `static/css/base.css` layer for app-specific styling (chat bubbles, like button, stat card).
- Layout adapts: chat sidebar collapses on narrow screens; map/stat-card stack vertically; tables/cards reflow through Bootstrap's grid classes rather than custom media queries everywhere.
- Tested via browser devtools responsive mode across common breakpoints (and real phones during hunting-season use — say this if true), plus checking that the tap targets and the checklist remain usable one-handed. Be ready to demo one narrow view live.

---

## 5. Deployment, Debugging & Reflection

### Q: "Hardest bug you encountered and how did you solved it?"

Strong candidates from the repo — pick the one you can retell most naturally:

1. **Render blocking outbound SMTP port 587.** Emails worked locally, failed in production with connection errors (Errno 101). Debugging path: confirmed credentials were fine → reproduced the SMTP handshake from the Render shell → realized the free tier blocks outbound 587 egress → switched to **port 465 implicit SSL** (`EMAIL_USE_SSL=true`; the settings code deliberately supports both modes: STARTTLS on 587 vs implicit SSL on 465, `settings.py:210-214`). Lesson: cloud platforms constrain egress, and TLS-on-connect vs STARTTLS is a real protocol difference, not a config typo.
2. **Template comments leaking into sent email.** Multi-line `{# ... #}` Django comments in the email template rendered as **literal text in Gmail** — recipients saw raw template source. Found by actually reading a sent email; fixed by removing the comments and parse-checking all 15 email templates for the same class of bug (`docs/CODE_REVIEW.md` §C7).
3. **The chat leak.** `/group_chat/` with no group previously rendered messages with `group=NULL` — which were globally visible. Caught during permission testing; fixed by redirecting to the group list instead (`views.py:147-151`). This one doubles as an authorization story.
4. **Malformed requirements.txt** (`python-dotenvDjango` fused into one package name) — deploy would have failed at install; found only by doing a clean-venv install rehearsal before deploying.

### Q: "Challenges deploying to production?"

- **Ephemeral disk:** SQLite wouldn't survive redeploys → managed Postgres with `DATABASE_URL` (+`ssl_require`, `conn_max_age=600`); user media still ephemeral (documented).
- **Static files in production:** `DEBUG=False` turns off Django's static serving → `collectstatic` into `STATIC_ROOT` at build time + WhiteNoise compressed/fingerprinted serving; verified with a full gunicorn run, styles loading, zero 4xx.
- **Env differences:** debug opt-in only, `ALLOWED_HOSTS` env-driven, `SITE_BASE_URL` needed for email links built without a request object.
- **Migrations on deploy:** Render's build command runs `collectstatic` and `migrate --noinput` before the new process serves traffic, so schema changes ship atomically with code.
- **Email egress:** port 587 blocked → 465 SSL (above).
- **Free-tier cold starts:** first request after idle is slow — acceptable for a capstone; be ready to name it as a known trade-off.
- **Timezone honesty:** UTC defaults made chat timestamps wrong for Coloradans → `TIME_ZONE=America/Denver` with `USE_TZ=True` (DB stays UTC, display converts), including real timestamps in email headers instead of a hardcoded "just now."

### Q: "Two more weeks — what would you refactor or add?"

Use the audit backlog — it proves self-awareness with receipts (`docs/CODE_REVIEW.md` §E):

**Refactors (technical debt I've already identified and ranked):**
1. Membership-guard helper: `_get_visible_message(request, id)` + a `@group_member_required` decorator to collapse 5–6 copies of the same guard (~40 lines, and makes forgetting the check structurally impossible).
2. Shared `static/js/csrf.js` exposing `postJSON(url, data)` — the CSRF plumbing is duplicated between the chat like handler and maps.js.
3. Derive the message-`kind` whitelist from `Message._meta` choices instead of a parallel literal so model and view can't drift.
4. Split the growing `base.css` into per-feature files; split the ~500-line `pages` app into a dedicated `chat` app for a cleaner architecture story.

**Features (scope cuts, not afterthoughts):**
5. Chat pagination with "load older messages" (older posts are currently unreachable past 50).
6. Live like counts (polling or Channels) and WebSockets for real-time chat.
7. Durable media storage (S3/Cloudinary) so profile photos survive redeploys.
8. Saved hunt plans as first-class models with history.
9. CPW GeoJSON response caching (1-hour Cache-Control) — every visitor currently re-fetches layers.
10. Port the inline permission/tamper tests into `tests.py` and add an async-email-path test using the locmem backend.

Prioritization framing: items 1–2 are cheap and reduce future bug surface, so they'd go first; 5–7 are user-visible; the rest follow.

---

## Quick-fire anchors (if you need to open a file mid-defense)

| Claim | Proof |
| --- | --- |
| CSRF on all POSTs | `settings.py:79`, `{% csrf_token %}` in every form |
| Membership invariant | `ChatGroup.is_member()` + 5 call sites in `pages/views.py` |
| Rate limiting | `@ratelimit` decorators, `views.py:88, 131, 176, 288` |
| Password hashing / validators | `settings.py:130-143` |
| Fail-fast secret key | `settings.py:34-40` |
| Postgres-vs-SQLite switch | `settings.py:112-124` |
| SET_NULL creator survival | `pages/models.py:52-57` |
| Offline CPW pipeline | `scripts/cpw_parse.py`, output `static/hunting/elk_stats.json` |
| Server-side slicing | `[:50]` chat, `[:25]` search |
| Test suite | 55 tests, `python manage.py test pages` |
