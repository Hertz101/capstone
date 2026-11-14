# Rocky Mountain Coalition — Hunt Planner

A Django web app for Colorado hunters: an interactive hunt planner, a GMU
hunting map with CPW GIS layers and harvest stats, a pre-trip packing
checklist, and a group chat with email notifications for planning crews.

**Live site:** https://rmcplanner.onrender.com

## Features

- **Hunt Planner** — pick species, method, season, and GMU; get license
  guidance and a shareable hunt-plan summary (with CPW license links).
- **Hunting Map** — Leaflet map with Colorado Parks & Wildlife FeatureServer
  layers (GMU boundaries, public access, Walk-In Access, elk/deer DAUs),
  clickable feature details, and per-GMU harvest statistics.
- **Your Trip** — interactive pre-hunt checklist; checked items persist in
  `localStorage` and can be shared into the chat.
- **Group Chat** — per-group chat rooms with text messages, shared cards
  (hunt plan / packing list / selected GMU), likes, editing, and
  creator-only moderation. Rate-limited to 10 posts/min and 30 likes/min.
- **Email notifications** — members are emailed when someone posts, likes,
  joins, or is added (Gmail SMTP over port 465; console backend in dev).
- **Search** — site-wide search over static pages, resource cards, and chat
  content (scoped to groups the user belongs to).
- **Profiles** — hunter profile with photo upload, city/state, and preferred
  hunting method; account self-deletion with password confirmation.

## Tech stack

| Layer | Choice |
|---|---|
| Framework | Django 6.1 (Python 3.14) |
| Database | PostgreSQL (Render) in prod, SQLite for local dev |
| Templates | Django templates + Bootstrap + Leaflet |
| Static/media | WhiteNoise (compressed, cache-fingerprinted) |
| Email | Django SMTP backend via Gmail App Password |
| Rate limiting | django-ratelimit |
| Tests | Django TestCase (55 tests), pytest/pytest-django |

## Local development

```bash
# 1. Create a virtualenv and install pinned dependencies
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. Create a local .env (never committed):
#    DJANGO_DEBUG=true
#    DJANGO_SECRET_KEY=<any string>
#    MAPTILER_API_KEY=<from maptiler.com>
#    EMAIL_HOST_USER / EMAIL_HOST_PASSWORD  (optional; console email without)
# 3. Migrate and run
python manage.py migrate
python manage.py runserver
```

Settings fall back to `db.sqlite3` automatically when `DATABASE_URL` is
unset, so no database setup is needed locally. Debug mode is opt-in only —
production must never set `DJANGO_DEBUG=true`.

## Running the tests

```bash
python manage.py test pages
```

Covers page routes, signup/profile flows, account deletion cascades,
group membership gating, message like/edit/delete permissions, search
visibility scoping, resource-card data integrity, and the email-backend
fallback logic.

## Deployment (Render)

1. **PostgreSQL**: create a Render Postgres instance in the same region as
   the web service; copy the *Internal Database URL*.
2. **Web Service**: connect the GitHub repo. Build command:
   ```
   pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate --noinput
   ```
   Start command:
   ```
   gunicorn config.wsgi:application --bind 0.0.0.0:$PORT
   ```
3. **Environment variables**:

   | Key | Purpose |
   |---|---|
   | `DJANGO_SECRET_KEY` | Required — settings fail fast without it |
   | `DJANGO_ALLOWED_HOSTS` | Bare hostname, e.g. `rmcplanner.onrender.com` |
   | `DATABASE_URL` | The Postgres Internal Database URL |
   | `SITE_BASE_URL` | `https://<app>.onrender.com` (links in emails) |
   | `MAPTILER_API_KEY` | Map tile provider key |
   | `EMAIL_PORT` | `465` (Render free tier blocks outbound 587) |
   | `EMAIL_USE_SSL` | `true` (port 465 is implicit SSL) |
   | `EMAIL_HOST_USER` / `EMAIL_HOST_PASSWORD` | Gmail + App Password |
   | `DEFAULT_FROM_EMAIL` | Sender shown on notifications |

   Do **not** set `DJANGO_DEBUG` in production.

## Project structure

```
config/       Django settings, URLs, WSGI (settings reads all config from env)
pages/        Main app: views, models (ChatGroup, Message, Profile),
              notifications, forms, tests
hunting/      Hunt planner page
templates/    Page + email templates
static/       CSS, JS (maps, chat sidebar, hunt planner), vendor libs
scripts/      CPW data parsing / stats extraction utilities
docs/         Code review notes and manual test cases
```

## Known limitations

- **User-uploaded media is ephemeral** on Render's free tier — profile
  photos reset on every deploy. Durable uploads need S3/Cloudinary.
- **Free Postgres expires** after ~30 days; upgrade or back up before then.
- **Emails can't send if the provider blocks SMTP egress** — the deployed
  configuration uses port 465 implicit SSL, which works on Render free.
