# Capstone Defense — Full Question Bank, Answered

**Project:** Rocky Mountain Coalition Hunt Planner (Django 6.1 / Python 3.14)
**Live:** https://rmcplanner.onrender.com
Companion to `docs/DEFENSE_PREP.md` (deep-dive traces). Every answer here names the
real file in this repo so you can open it live during the defense.

---

## 1. Project overview

**Purpose?** A hunt-planning web app for Colorado hunters. It combines an
interactive hunt planner (species/method/season/GMU → license guidance), a
Leaflet map with Colorado Parks & Wildlife GIS layers and harvest statistics, a
pre-trip packing checklist, and a group chat with email notifications for
planning crews.

**Problem it solves?** Planning a Colorado hunt currently means jumping between
CPW's PDF regs, scattered GIS viewers, group texts, and handwritten packing
lists. This app puts license guidance, GMU harvest data, and crew coordination
in one logged-in place — so a group can share one hunt plan instead of
forwarding screenshots.

**Target audience?** Colorado resident and nonresident hunters (from first-timer
planning their first elk tag to recurring crews); secondarily, anyone studying
how a Django app is structured.

**Why this project?** It's a domain I actually use, which made requirements real
instead of invented — and it forced both halves of modern web work: a normal
form/database web app _and_ a data pipeline (parsing CPW harvest PDFs with
pdfplumber in `scripts/` into `static/hunting/elk_stats.json`).

**Main features?** (README §Features — be able to point at each live)

1. Hunt Planner (`hunting/` app)
2. Interactive hunting map (`static/js/maps.js`, CPW FeatureServer layers)
3. "Your Trip" checklist (`your_trip_view`, localStorage persistence)
4. Group chat with shared cards, likes, edit, creator moderation
   (`pages/views.py:130–268`)
5. Email notifications (`pages/notifications.py`)
5. Site-wide **search** was removed from the feature set at the owner's
   request (navbar form, `/search/` route, `search_view`, template and
   tests deleted). The remaining in-app "search" is the GMU unit lookup
   on the Hunting Map / Hunt Planner — unrelated.
6. Hunter profiles + account self-deletion with password re-confirmation
   (`profile_view`, `account_delete_view`)

**Most challenging part?** Deployment-environment debugging — email worked
locally and silently failed on Render because the free tier blocks outbound
SMTP port 587; I reproduced the SMTP handshake from the Render shell and
switched to port 465 implicit SSL (`EMAIL_USE_SSL=true`,
`config/settings.py:210-214`). Close second: catching that chat messages with
`group=NULL` were globally visible — an authorization bug I found during my own
permission testing and fixed (`views.py:147-151`).

**With more time?** From my own audit backlog (`docs/CODE_REVIEW.md` §E):
chat pagination ("load older" — messages past the newest 50 are unreachable),
real-time chat via Django Channels, durable S3/Cloudinary media so profile
photos survive redeploys, and refactoring the duplicated membership guard into a
decorator.

---

## 2. Front-end development

**Technologies?** Django templates (server-rendered HTML), Bootstrap 5,
vanilla JavaScript (`static/js/`: `chat_sidebar.js`, `maps.js`, `your_trip.js`,
`resources.js`), Leaflet + MapTiler for the map, custom CSS in
`static/css/base.css` plus per-page stylesheets.

**Why these?** The product is content- and form-heavy, not app-state-heavy.
Server-rendered templates mean no build step and every JS interaction (likes,
edit, share) keeps a plain-form fallback, so the site still works with
JavaScript off — realistic for poor cell coverage in the field. Bootstrap gives
responsive layout/components for free; Leaflet is the standard open-source map
library; I deliberately avoided React because a SPA would add client-state
complexity the app doesn't need.

**Responsive how?** Bootstrap 5 grid + its navbar collapse, card grids, and
form classes, with a small custom CSS layer. Chat sidebar collapses on narrow
screens; map and stat cards stack vertically. Tested in devtools responsive
mode plus real phones.

**Navigation bar?** One shared partial, `templates/navbar.html`, included by
`templates/base.html`, which every page template `{% extends %}`. Bootstrap's
collapse plugin handles the hamburger on mobile. Links are conditional on
`request.user.is_authenticated`, so logged-out visitors see login/signup while
members see tools/chat/groups/profile. Active state + logout go through
Django's auth URLs.

**Template organization?**

```
templates/
  base.html navbar.html footer.html   # shared shell, included once
  pages/     one template per view (home, maps, group_chat, profile, …)
  hunting/   planner
  partials/  _avatar.html — reusable photo-or-initials component used by 3 templates
  emails/    15 notification email templates
  registration/  login/signup/password pages (Django's conventional name)
```

Presentation is separated from logic: views render context; templates contain
no queries.

**HTML vs CSS vs JavaScript?** HTML is the structure/content (what's on the
page); CSS is presentation (how it looks); JavaScript is behavior (what happens
on interaction). In my app: `group_chat.html` defines the message list markup,
`static/css/group_chat.css` styles the bubbles, and `chat_sidebar.js` handles
the like toggle with `fetch` and updates the DOM without a reload.

**Forms and user input?** Two paths:

- _Django Forms_ (`pages/forms.py`: `SignupForm`, `ProfileForm`,
  `ChatGroupForm`) — the form class declares fields/validation; the template
  renders it; on POST the view checks `form.is_valid()` and either saves or
  re-renders with field-level errors. Signup and profile use this.
- _Plain POSTs with manual handling_ for chat post/edit/delete/join — validated
  in the view (truncate to 2000 chars, whitelist `kind`, JSON-parse payloads)
  then Post/Redirect/Get so a browser refresh can't double-post
  (`views.py:89-128`).
  The AJAX like is a third path: `fetch` POST with the CSRF token in an
  `X-CSRFToken` header, JSON back.

**User-friendly how?** Feedback on every action (Django `messages` flashes,
inline form errors, a friendly 429 page instead of a raw rate-limit error),
consistent navbar/footer on every page, avatar partial for visual identity,
mobile-first responsive layout, checklist state persists between visits, and
error states degrade gracefully (map works even if harvest stats fail to load —
try/catch in `maps.js`).

---

## 3. Back-end development

**Language?** Python 3.14 — my strongest language, and the right fit since the
data pipeline (CPW PDF parsing) is Python too.

**Framework and why?** Django 6.1. The riskiest parts of my app — password
hashing, sessions, CSRF, SQL-injection-safe ORM, migrations, admin — are exactly
what Django ships hardened out of the box. Building those on a microframework
would be a security gamble, not extra learning. Its "batteries included"
convention (models/forms/views/templates/tests per app) also kept the project
organized.

**Back-end ↔ front-end communication?** Server-side rendering: views query the
ORM and pass context into templates, which return HTML. Two async exceptions:
the like toggle returns `JsonResponse` JSON to a `fetch` call, and the map page
serves GeoJSON-derived data fetched client-side from CPW's FeatureServer.
Emails are sent on a background thread so the HTTP response isn't blocked on
SMTP (`notifications.py`).

**What happens when a user submits a form?** Full trace (posting a chat
message):

1. Browser POSTs the form (with hidden CSRF token) to `/group_chat/<id>/`.
2. Middleware runs: CSRF middleware rejects the request without a valid token;
   session middleware resolves `request.user`.
3. Routing (`config/urls.py` → `pages/urls.py`) dispatches to
   `group_chat_view` (`pages/views.py:132`).
4. Decorators: `@login_required` then `@ratelimit(10/m)`.
5. View validates and sanitizes: truncate text to 2000, whitelist `kind`,
   parse shared-card JSON payload (invalid → degrade to plain text).
6. `Message.objects.create(...)` — the ORM issues a parameterized INSERT.
7. Email notification fires on a background thread.
8. 302 redirect back to the group page (Post/Redirect/Get prevents refresh
   duplicates); the GET re-renders with the new message included.
   For _validation-failure_ forms (signup/profile), the view re-renders the same
   template with bound form errors instead of redirecting.

**Routes/URLs?** Declarative two-tier URLconf: `config/urls.py` includes
`pages/urls.py` and `hunting/urls.py`; each path pattern maps to a view
function, e.g. `messages/<int:message_id>/like/` → `message_like_view`
(`pages/urls.py:19`). `<int:...>` converters type-check and capture URL params.
Django tries patterns top-down; `name=` kwargs enable `reverse()`/`{% url %}` so
templates never hardcode paths.

**Purpose of views/controllers?** A view is the controller: it takes the
`HttpRequest`, decides auth/permission, talks to models, and returns an
`HttpResponse` (rendered page, redirect, or JSON). Mine are deliberately thin —
auth gate → model operation → render — with validation in forms, data logic in
models, email in `notifications.py`, so no layer does another's job.

**Error handling?** Layered: forms catch bad input and re-render with field
errors; views use `get_object_or_404` (404 page), redirect non-members instead
of leaking, and return 403 JSON for unauthorized likes; `@ratelimit` +
`ratelimited_view` gives a friendly 429; with `DEBUG=False` (always, in prod)
Django serves a generic 500 while emailing admins the traceback; try/catch in
the frontend JS keeps partial failures (stats load) non-fatal.

**Input validation?** Server-side, always — client `maxlength` is UX only.
Three mechanisms: Django form field validators (`ProfileForm.clean_state`
rejects anything but two letters), model constraints (`Message.kind` via
`TextChoices` choices, `max_length=2000`), and explicit view checks (truncate
chat text, JSON-parse payloads, type-check shared cards). Documented case:
state `maxlength=2` was client-only until I added the server check — tampering
past it worked before that (`docs/CODE_REVIEW.md`).

---

## 4. Database

**Which database?** SQLite (`db.sqlite3`) locally; PostgreSQL on Render in
production, chosen automatically by `config/settings.py:112-124` — `DATABASE_URL`
env var present → Postgres (via `dj-database-url`, with `ssl_require`), absent
→ SQLite.

**Why?** Relational fits the data: users, groups, messages, likes, profiles are
inherently interlinked and need joins + referential integrity (delete a user →
their messages/memberships go too; delete a group → its messages go). SQLite
gives zero-setup local dev; Postgres is the real production engine. Django's ORM
means identical app code against either.

**Tables/models?** Django's built-in `auth_user` plus three app tables in
`pages/models.py`: `Message`, `ChatGroup`, `Profile`. (Plus two implicit join
tables Django creates for the ManyToMany relations: memberships and likes.)

**Relationships?**
| Relationship | Field | On delete |
|---|---|---|
| Profile → User | OneToOneField (`models.py:85`) | CASCADE |
| Message → ChatGroup | ForeignKey (`models.py:8`) | CASCADE |
| Message → User (author) | ForeignKey (`models.py:15`) | CASCADE |
| ChatGroup → User (creator) | ForeignKey (`models.py:52`) | **SET_NULL** — the group outlives its creator so members keep their room |
| ChatGroup ↔ Users (members) | ManyToManyField (`models.py:58`) | join rows vanish with either side |
| Message ↔ Users (likes) | ManyToManyField (`models.py:31`) | same |

Normalized: no message stores the author's name — templates resolve via FK with
`select_related("user", "group")`. One intentional denormalization:
`Message.payload` JSONField holds shared-card content — a value object, never
joined against, so embedding avoids a fourth table.

**Primary key?** The column that uniquely identifies each row. Django adds an
auto-incrementing `id` to every model automatically; I use it in URLs like
`/group_chat/<int:group_id>/`. It must be unique and non-null, and FKs point at it.

**Foreign key?** A column referencing another table's primary key, enforcing
referential integrity. `Message.group` is an FK to `ChatGroup` — a message
cannot exist pointing at a nonexistent group, and `on_delete=CASCADE` defines
what happens when the referenced row dies.

**Retrieving information?** Through the ORM — never raw SQL. Examples: chat
loads `Message.objects.select_related("user", "group").filter(group=g)[:50]`;
search uses `filter(text__icontains=q)` which becomes a parameterized SQL
`LIKE`; the membership check is
`self.members.filter(pk=user.pk).exists()` (`models.py:71-72`). `select_related`
joins in one query to avoid N+1.

**CRUD?**

- **Create:** `Message.objects.create(...)` or `form.save()` on a ModelForm
  (signup creates User + Profile together).
- **Read:** querysets above; detail via `get_object_or_404(ChatGroup, pk=...)`.
- **Update:** `message.text = ...; message.save()` in `message_edit_view`;
  profile edit via ModelForm `form.save()`.
- **Delete:** `message.delete()` in `message_delete_view`;
  `request.user.delete()` in `account_delete_view` — Django cascades that to
  profile, messages, memberships automatically.

**Invalid data?** Depends on entry point: form routes → `is_valid()` fails, form
re-renders with per-field errors, nothing touches the DB. Chat route →
sanitized in code (too-long text truncated, bad `kind` coerced, corrupt payload
→ plain text message). Direct ORM/level constraint violations raise
`IntegrityError`/`ValidationError`. Crucially, tampered POSTs can't corrupt the
schema because validation lives server-side, not in the browser.

---

## 5. Security

**Protecting sensitive information?** No secrets in the repo —
`DJANGO_SECRET_KEY`, `DATABASE_URL`, email creds, `MAPTILER_API_KEY` all come
from environment variables (`.env`, git-ignored, locally; Render env in prod),
loaded via python-dotenv (`settings.py:23`). Settings **fail fast**: with no
secret key and no debug flag the process refuses to boot rather than running
with a weak committed key (`settings.py:34-40`). Passwords are only ever stored
hashed. `DEBUG=False` in production so tracebacks never leak to users.

**Authentication?** Django's built-in system: passwords hashed with PBKDF2
(SHA-256, 600k iterations), four password validators (`settings.py:130-143`),
login via `django.contrib.auth` views. Sessions are server-side (DB) with a
signed, HttpOnly session cookie; the session key rotates on login to defeat
fixation. Account deletion requires re-entering the password and re-running
`authenticate()` (`views.py:510+`).

**Authentication vs authorization?** Authentication = who you are (login);
authorization = what you're allowed to do (permissions). In my app:
authentication is session login; authorization is the membership invariant —
`ChatGroup.is_member()` gates every read/write of group content at five entry
points (chat view, like, edit, delete, search). You can be authenticated and
still get a 403/redirect on another group's chat.

**SQL injection prevention?** By construction: 100% of DB access goes through
Django's ORM, which parameterizes every query — user input is never
string-concatenated into SQL. There is no raw SQL anywhere in the repo (I can
grep it live). Django's `filter(text__icontains=q)` becomes a safe parameterized
`LIKE`.

**CSRF?** Cross-Site Request Forgery — an attacker's page makes your browser
submit an authenticated form to my site using your session cookie. Prevention:
`CsrfViewMiddleware` on every POST (`settings.py:79`); every form includes
`{% csrf_token %}`; the AJAX like sends the token in the `X-CSRFToken` header.
A cross-origin form posting to `/messages/<id>/like/` fails the token check → 403.

**Password protection?** Never stored in plaintext — PBKDF2-SHA256 with 600k
iterations and a per-password salt, so even a DB leak doesn't reveal passwords.
Validators enforce strength; Django's authenticate/check_password handle
comparison safely. Email uses a Gmail **App Password** on a 2FA account, not the
real account password.

**Preventing unauthorized page access?** Three layers:

1. `@login_required` on every private view → redirects to login.
2. The membership gate: non-members are redirected (chat), get 403 JSON
   (likes), or are excluded from the queryset entirely (search filters through
   `request.user.chat_groups`, `views.py:466-480`).
3. Object-level identity checks: edit = author only; delete = author or group
   creator; group admin actions = `created_by == request.user`; removing the
   creator from their own group is blocked so it can't be orphaned.
   Plus rate limiting (10 posts/min, 30 likes/min) to bound abuse.

---

## 6. Testing and debugging

**How did you test?** Two tiers:

- **Automated:** 55 Django `TestCase` tests in `pages/tests.py` (run with
  `python manage.py test pages`), covering page routes, signup/profile flows,
  account-deletion cascades, group membership gating, like/edit/delete
  permissions, search visibility scoping, and the email-backend fallback.
- **Manual:** scripted cases in `docs/manual_test_cases.md`, plus real-device
  checks. Permission bugs (like the `group=NULL` chat leak) were caught by
  deliberately trying to access other users' content.

**Bugs encountered?** My four best stories (full detail in
`docs/DEFENSE_PREP.md` §5):

1. Render blocked SMTP port 587 → emails worked locally, failed in prod; fixed
   with port 465 implicit SSL.
2. Django `{# #}` template comments rendered as literal text inside sent
   emails — found by reading an actual email; fixed and swept all 15 email
   templates.
3. Orphan chat messages (`group=NULL`) were globally visible — fixed by
   redirecting and excluding orphans from search.
4. Malformed `requirements.txt` (two package names fused) would have failed
   deploy; caught by rehearsing a clean-venv install before deploying.

**How did you troubleshoot?** Reproduce reliably → isolate the layer (browser
network tab → Django logs → shell) → test the hypothesis directly (e.g.,
running the SMTP handshake from the Render shell to prove it was egress, not
credentials) → fix at the cause → add a test or sweep for the same bug class.

**How do you know forms work?** Automated tests assert both paths (valid POST →
object created/redirect; invalid POST → no object, errors rendered). Manual test
cases cover each form. And Post/Redirect/Get means a refresh can't create
duplicates.

**If the server errors?** With `DEBUG=False` (production default): user sees a
branded 500 page, never a traceback; the full traceback goes to the
`ADMINS` email; gunicorn logs the stack; other requests are unaffected since
each is handled independently. Locally `DEBUG=True` shows the interactive
Django error page for debugging.

**Cross-browser testing?** Bootstrap 5 + vanilla JS with standard APIs
(`fetch`, `localStorage`) — no browser-specific code paths to diverge. I'd test
Chrome/Firefox/Safari/Edge on the responsive breakpoints, watch the console for
JS errors, and verify the map tiles and CSRF-header fetch behave identically.
Would automate with Playwright if the project continued.

**Bug reported after deployment?** Reproduce it (same env/browser/account
state) → check the error logs → fix on a Git branch with a failing-then-passing
test → deploy via Render (push to GitHub triggers build + migrate) → verify on
prod → communicate the fix. If severe: roll back by redeploying the previous
commit first, then fix forward.

---

## 7. Git and deployment

**Used Git?** Yes — the repo is version-controlled with feature work committed
incrementally (`.git` active; commit history available).

**Why version control matters:** full history of who/what/when for every
change; safe experimentation on branches; instant rollback to a known-good
commit when a deploy misbehaves; and it's the collaboration substrate (pull
requests, review).

**Git vs GitHub?** Git is the version-control _tool_ (local, offline — commits,
branches, history). GitHub _hosts_ Git repositories and adds collaboration
around them (remote backup, PRs, issues, CI). I use Git locally and GitHub as
the remote that Render deploys from.

**Deployment / hosting?** **Render** (free tier), deployed from GitHub.

- Build command: `pip install -r requirements.txt && python manage.py
collectstatic --noinput && python manage.py migrate --noinput`
- Start command: `gunicorn config.wsgi:application --bind 0.0.0.0:$PORT`
- Managed PostgreSQL instance in the same region; `DATABASE_URL` wired via env.
- Static files: `collectstatic` at build → **WhiteNoise** serves them
  compressed with cache-fingerprinting (no CDN/nginx needed).

**What happens when someone visits the URL?**

1. DNS resolves `rmcplanner.onrender.com` to Render's edge; TLS terminates.
2. Render routes to a gunicorn worker running my Django app.
3. Middleware stack runs (security → WhiteNoise for static → sessions → CSRF →
   auth).
4. URLconf matches; the view queries Postgres via the ORM and renders a
   template.
5. HTML (+ WhiteNoise-served CSS/JS/images) returns to the browser; the browser
   then fetches map tiles from MapTiler and GeoJSON layers from CPW's
   FeatureServer.
   Known trade-off: free-tier cold start makes the first request after idle slow.

**Updating after deployment?** `git push` to the main branch → Render rebuilds:
installs pinned deps, runs `collectstatic` and `migrate --noinput` before the
new process serves traffic, so schema changes ship atomically with code.
Rollback = redeploy a previous commit.

**Environment variables?** All config is env-driven and never committed:
`DJANGO_SECRET_KEY` (required, fail-fast), `DJANGO_ALLOWED_HOSTS`,
`DATABASE_URL`, `MAPTILER_API_KEY`, Gmail App Password creds, `SITE_BASE_URL`
(for links built in emails), `EMAIL_PORT=465`/`EMAIL_USE_SSL=true`. Locally a
git-ignored `.env` via python-dotenv; in production, Render's environment UI.
Debug is opt-in (`DJANGO_DEBUG=true` locally) and never set in prod.

---

## 8. Live-code demonstration answers

- **"Where is this feature implemented?"** — anchor map:
  | Feature | File |
  |---|---|
  | Hunt planner | `hunting/views.py`, `templates/hunting/` |
  | Map + layers | `static/js/maps.js`, `templates/pages/maps.html`, `static/css/maps.css` |
  | Checklist | `pages/views.py:76`, `static/js/your_trip.js` |
  | Chat post/like/edit/delete | `pages/views.py:130–268`, `templates/pages/group_chat.html`, `static/js/chat_sidebar.js` |
  | Emails | `pages/notifications.py`, `templates/emails/` |
  | Search | `pages/views.py:441` |
  | Models/schema | `pages/models.py` |
  | Validation | `pages/forms.py` + view guards |
  | Security config | `config/settings.py` |

- **"Walk me through clicking this button."** Use the like-button trace in
  `docs/DEFENSE_PREP.md` §1 (click → fetch POST with CSRF header → decorators →
  membership gate → M2M toggle → count re-read → JSON → DOM update).

- **"Where is this data stored?"** In PostgreSQL on Render (SQLite locally):
  tables `pages_message`, `pages_chatgroup`, `pages_profile` + Django's
  `auth_user` + two implicit M2M join tables. Show `pages/models.py`; migrations
  in `pages/migrations/`.

- **"What file controls this page?"** URL in `pages/urls.py` → view function in
  `pages/views.py` → template in `templates/pages/<name>.html` → styles/JS in
  `static/css|js/`.

- **"What happens behind the scenes when I submit this form?"** The 8-step
  trace in §3 above (CSRF → middleware → routing → decorators → validation →
  ORM INSERT → email thread → redirect).

- **"Explain this function."** Be fluent in: `ChatGroup.is_member()`
  (`models.py:71`), `_handle_chat_post` (`views.py:89`),
  `message_like_view` (`views.py:177`), `account_delete_view`
  (`views.py:510`), `Profile.display_name` (`models.py:110`).

- **"Why did you write it this way?"** Ready reasons: SET_NULL on group creator
  (group outlives its creator); count re-read after like write (no stale
  totals on double-click); JSONField payload (value object, avoids a fourth
  table); email on background thread (SMTP latency off the request path);
  Post/Redirect/Get (no refresh duplicates); membership checks repeated rather
  than centralized (explicit over clever — first refactor if I had more time).

- **"Can you change this right now?"** Yes-ready examples: change message limit
  = edit `max_length=2000` + the truncation in `_handle_chat_post` + migration;
  change like rate = the `@ratelimit` argument; rename a group field = edit
  model + migration (template refs use `{% url %}` so routing survives).

- **"Show me adding a field to a form."** Demo on Profile: add
  `favorite_gmu = models.CharField(max_length=3, blank=True)` to
  `pages/models.py:82` → `python manage.py makemigrations && migrate` → add the
  field to `ProfileForm` in `pages/forms.py` → it renders automatically in
  `profile.html` since the form loops fields. Three files, one command.

- **"Demonstrate invalid input."** Live: (1) signup with a 1-letter state or
  mismatched passwords → field errors re-render, nothing saved; (2) post a chat
  message past 2000 chars via devtools → server truncates; (3) tamper the share
  payload to invalid JSON → degrades to plain text; (4) open another group's
  URL while logged in as a non-member → redirect; (5) hammer the like button →
  friendly 429 page.

---

## The 10 to practice first

1. **Project + problem:** §1 above — planner/map/checklist/chat replacing
   scattered CPW PDFs and group texts.
2. **Front to back:** like-button trace (`DEFENSE_PREP.md` §1) or chat-post
   trace (§3 here).
3. **Form submission:** the 8-step lifecycle in §3.
4. **Database interaction:** ORM examples in §4 + the relationship table.
5. **Why these technologies:** §1 + §3 (Django for hardened batteries, SQL for
   relational integrity, server-rendered for graceful degradation).
6. **One model and its relations:** `Message` — FK to ChatGroup (CASCADE), FK
   to author (CASCADE), M2M `liked_by`, JSONField payload; shown in §4.
7. **Hardest bug:** SMTP port 587 vs 465 story (§6.1) — or the chat-leak bug if
   you want the security-flavored one.
8. **How you tested:** 55 automated tests + manual cases in §6.
9. **Adding a feature:** the Profile-field demo in §8 — concrete, three files.
10. **Rebuild differently:** paginate chat properly from day one, extract a
    `chat` app and a `@group_member_required` decorator earlier, S3 media from
    the start, Channels for real-time — all already in my audit backlog
    (`docs/CODE_REVIEW.md` §E), which proves the reflection is genuine.
