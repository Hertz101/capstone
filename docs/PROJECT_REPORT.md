# Project Report — Rocky Mountain Coalition Hunt Planner

**Author:** Adam Hertzberg
**Date:** November 21, 2026
**Live site:** https://rmcplanner.onrender.com

---

## 1. Introduction

### Overview

The Rocky Mountain Coalition Hunt Planner ("RMC Planner") is a full-stack
web application built with Django that helps Colorado hunters plan, share,
and execute their hunts. It combines an interactive hunt planner, a GIS
hunting map built on Colorado Parks & Wildlife (CPW) data, a pre-trip
packing checklist, and a group chat with email notifications — all in one
place, deployed live on Render.

### Purpose and motivation

Planning a Colorado hunt is fragmented. A hunter typically juggles the CPW
website for license and season rules, printed big-game brochures for harvest
statistics, scattered blog posts for gear lists, and a group text thread
with hunting partners who never see the same information at the same time.
I chose this project because I hunt in Colorado and experienced this
frustration directly: no single tool combines *where to hunt* (GMU maps and
data), *what to bring* (checklists), and *who to tell* (group planning).
A capstone was the right opportunity to build the tool I actually wanted,
against real public-government data, with real users in mind.

---

## 2. Project Description

### What the project is

RMC Planner is a data-driven planning hub. A user creates an account and a
hunter profile, then can:

1. **Plan a hunt** — pick species (elk, mule deer, whitetail, bear,
   pronghorn), hunting method (rifle / black powder / archery), season, and
   Game Management Unit (GMU). The planner returns license guidance with
   direct CPW license links and produces a structured "hunt plan" summary.
2. **Study the map** — an interactive Leaflet map loads live CPW
   FeatureServer layers: GMU boundaries, public and Walk-In Access areas,
   and elk/deer Data Analysis Units (DAUs). Clicking a feature shows its
   details, and per-GMU harvest statistics are available for research.
3. **Prepare for the trip** — an interactive pre-hunt checklist grouped by
   category (documents, gear, clothing, food, vehicle). Checked items
   persist in the browser's `localStorage`, and the whole list can be
   shared as a card into any group chat.
4. **Coordinate with a crew** — each hunting party gets its own chat room
   with messages, shared content cards (hunt plans, packing lists, a
   selected GMU), likes, message editing, and creator-only moderation.
   Members are emailed when someone posts, likes, joins, or is added.

### The problem it solves

- Hunters can't easily correlate license rules, unit boundaries, and harvest
  data without opening multiple state websites and PDFs.
- Planning conversations happen in text threads where nobody can find "the
  plan" later — shared decisions get lost.
- Pre-trip gear lists are re-created from scratch (or forgotten) every season.

RMC Planner consolidates the research, the plan, and the communication into
one authenticated, shareable workspace.

### Unique features

- **Real CPW GIS integration.** The map pulls live GeoJSON from Colorado
  Parks & Wildlife FeatureServer endpoints — not sample data — and pairs it
  with harvest statistics extracted offline via custom parsing scripts
  (`scripts/`) so the demo works even if CPW's site is slow or down.
- **Shared structured cards, not just text.** A hunt plan, a packing list,
  or a selected GMU can be posted into chat as a typed card with a JSON
  payload, so the crew's decisions are structured data, not a screenshot.
- **Progressive enhancement everywhere.** Every JavaScript feature (likes,
  inline edit, share-to-chat) still works as a plain POST/redirect form if
  JS fails — a deliberate accessibility and reliability choice.
- **Respectful communication design.** Rate limiting (10 posts/min,
  30 likes/min), silent moderation, honest timestamps in America/Denver
  time, and multipart text+HTML notification emails.

---

## 3. Data Entities

The application persists the following entities (models live in
`pages/models.py`; Django's built-in `User` handles authentication):

| Entity           | Purpose | Key fields |
| ---------------- | ------- | ---------- |
| **User**         | Django's built-in authentication model | username, email, password |
| **Profile**      | Hunter details beyond the built-in user; one-to-one with User | first/last name, city, state, preferred hunting method, profile photo, created_at |
| **ChatGroup**    | A named hunting crew with its own chat room | name, created_by (creator, SET_NULL), members (M2M), created_at |
| **Message**      | A single chat post, tied to its author and group | text, `kind` (text / hunt plan / packing list / selected GMU / system), `payload` (JSON for shared cards), liked_by (M2M), edited flag, created_at, updated_at |
| **Static/content data** (not in the database) | Pre-hunt checklist categories and resource cards | defined in `pages/content.py`; CPW layer + harvest data served as GeoJSON/static JSON |

Related data that is *referenced* but not stored: CPW FeatureServer layers
(GMU boundaries, public access, DAUs), MapTiler base map tiles, and per-GMU
harvest statistics parsed from CPW PDFs by the offline scripts.

---

## 4. Industry and Target Audience

### Industry context

The project sits at the intersection of:

- **Outdoor recreation / hunting** — a large Colorado economy anchored by
  big-game licensing managed by Colorado Parks & Wildlife.
- **Consumer web applications** — planning and community tools.
- **Civic/open data** — the app is a practical consumer of public
  government GIS and statistics data.

### Target audience

**Primary:** resident and non-resident Colorado big-game hunters, from
first-time applicants planning their first elk trip to seasoned rifle and
archery hunters researching units. They are comfortable with maps and mobile
web but frustrated by the current research-and-group-text workflow.

**Secondary:** hunting parties and clubs (the group chat is built for crews
of roughly 2–10 people planning a trip together), and, by extension,
anyone planning an outdoor trip in Colorado who needs checklists and
coordinated communication.

---

## 5. Elevator Pitch

**RMC Planner is the one place Colorado hunters go to plan a hunt.**
Pick your species, method, season, and unit, and get license guidance with
direct CPW links. Study real CPW map layers — GMU boundaries, public
access, Walk-In Access, and harvest statistics — on one interactive map.
Work through a pre-hunt checklist that remembers what you've packed. Then
share all of it — your plan, your packing list, your unit — as live cards
into your hunting crew's private chat room, where posts, likes, and joins
reach everyone by email. One tool replaces the CPW-website-and-group-text
scramble: research where to hunt, decide what to bring, and keep your whole
crew on the same page, in one app.

---

## 6. Technical Overview

### Tech stack

| Layer | Choice | Why |
| ----- | ------ | --- |
| Language | **Python 3.14** | My strongest language; excellent Django support |
| Framework | **Django 6.1** | Batteries included: ORM, auth, sessions, templates, admin, migrations — right-sized for a solo capstone with security-sensitive features (membership gating, self-deletion) |
| Database | **PostgreSQL** (Render) / SQLite (local dev) | Postgres for production reliability; settings read `DATABASE_URL` and fall back to SQLite so local setup needs zero configuration |
| Front end | **Django templates + Bootstrap + vanilla JS** | Server-rendered pages keep the app fast and accessible; Bootstrap handles responsive layout without a build step; Leaflet for the map |
| Maps | **Leaflet** + **MapTiler** tiles + **CPW FeatureServer** GeoJSON | Leaflet is lightweight and open-source; CPW layers are authoritative public data |
| Static/media | **WhiteNoise** (compressed, cache-fingerprinted) | Removes the need for a separate static-hosting service on a free-tier deploy |
| Email | **Django SMTP backend** via Gmail App Password (port 465 SSL) | Render's free tier blocks port 587 egress; implicit-SSL on 465 works |
| Rate limiting | **django-ratelimit** | Protects chat and notification emails from flooding |
| Testing | **Django TestCase** (55 tests), pytest/pytest-django available | Framework-native tests cover routes, permissions, and scoping |
| Deployment | **Render** (Gunicorn + WhiteNoise + managed Postgres) | Free-tier hosting with automated build/migrate on deploy |

### Reasons for the choices

Django over Flask/FastAPI because the app's risk areas are exactly what
Django ships solved: authentication, CSRF, ORM migrations, and password
handling. Server-rendered templates over a SPA (React/Vue) because the
product is content- and form-heavy rather than highly interactive, and
progressive enhancement keeps every feature usable without JavaScript.
PostgreSQL in production because Render's SQLite is ephemeral across
redeploys. The CPW GeoJSON is fetched client-side directly from
FeatureServer, which keeps my server out of the hot path for the heaviest
data.

### Architectural overview

```
 Browser
   │  Django templates + Bootstrap + vanilla JS
   │  (Leaflet map fetches CPW GeoJSON + MapTiler tiles directly)
   ▼
 Gunicorn (Render) → Django (config.wsgi)
   ├── pages/ app — views, forms, Profile / ChatGroup / Message models,
   │               search, notifications (email threads)
   ├── hunting/ app — hunt planner page
   ├── WhiteNoise — compressed static + media
   ├── django-ratelimit — chat/like throttling
   │            ▼
   └── PostgreSQL (Render)  —  users, profiles, groups, messages
        Gmail SMTP (465 SSL) ← notification emails
 scripts/ — offline CPW PDF→JSON harvest-stat extraction (build time)
```

Request flow highlights: membership-gated views check `ChatGroup.is_member()`
before any data is exposed; chat writes are POST-only with
Post/Redirect/Get; likes and edits are AJAX POSTs returning JSON.

---

## 7. Feature List

| # | Feature | Description |
| - | ------- | ----------- |
| 1 | **Hunt Planner** | Choose species, hunting method, season, and GMU. Returns license guidance, season context, and CPW license-purchase links, and generates a structured hunt-plan summary. |
| 2 | **Interactive Hunting Map** | Leaflet map with live CPW FeatureServer layers: GMU boundaries, public land access, Walk-In Access program areas, elk/deer DAUs. Clickable features show attribute details; per-GMU harvest statistics are viewable per unit. Supports sharing a selected GMU into chat. |
| 3 | **Your Trip Checklist** | Interactive pre-hunt checklist grouped by category. Check state persists in `localStorage` per browser; the entire list can be shared into a group chat as a packing-list card. |
| 4 | **Group Chat** | Private per-group rooms. Typed messages, plus shared content cards (hunt plan / packing list / selected GMU) rendered with their JSON payload. Likes with live counts, inline editing with an "(edited …)" marker, author-or-creator deletion, system announcements when members are added. |
| 5 | **Email Notifications** | Members receive multipart text+HTML emails when someone posts, likes their message context, joins, or is added to the group. Delivered asynchronously via a background thread; timestamps rendered in America/Denver time. |
| 6 | **Group Management** | Create groups and pick initial members; browse and join open groups from a group list; creators can add/remove members and delete the group; orphan protection keeps the creator in their own group. |
| 7 | **Hunter Profiles** | Photo upload, first/last name, city and two-letter state (server-validated), preferred hunting method. Shared-email detection warns when two accounts use one inbox. |
| 8 | **Accounts** | Signup with profile creation, login/logout, and full account self-deletion gated by password confirmation, with a cascade summary of what will be removed. |
| 9 | **Site-wide Search** | One search box over static pages, resource cards, and — for signed-in users — chat groups and messages, scoped strictly to groups the user belongs to. |
| 10 | **Resources Page** | Curated resource cards linking to CPW PDFs and internal pages, with build-time verification that referenced PDFs exist. |
| 11 | **Rate Limiting & Abuse Control** | 10 chat posts/min and 30 likes/min per user via django-ratelimit; exceeding limits shows a friendly "Slow down 🐎" 429 page (HTML) or JSON error. |
| 12 | **Testing & Docs** | 55 automated Django tests (routes, signup/profile flows, deletion cascades, membership gating, like/edit/delete permissions, search scoping, email fallback), plus README, manual test cases, and a code-review document. |

### Special functionalities

- **Shared structured cards:** chat messages carry a `kind` + JSON `payload`
  so shared plans/lists/units render as rich cards, with tampering handled
  gracefully (invalid payloads degrade to plain text).
- **Membership gating as a security invariant:** the same
  `ChatGroup.is_member()` rule guards chat reads, posts, likes, edits,
  deletes, and search visibility — enforced five ways so content never
  leaks across groups.
- **Offline data pipeline:** Python scripts in `scripts/` convert CPW
  harvest PDFs into JSON at build time, keeping statistics fast and
  available even when CPW's site is unreachable.

---

## 8. Screenshots and User Interface

The UI is a responsive Bootstrap layout with a persistent navbar
(`templates/navbar.html`), dark-on-light palette, and card-based content.
*(Insert screenshots here when finalizing the report — suggested captures:)*

| Screen | What it shows |
| ------ | ------------- |
| Home | Landing page with big-game animal cards (elk, mule deer, whitetail, bear, pronghorn) linking into the tools |
| Hunt Planner | Species/method/season/GMU selection and the generated hunt-plan summary |
| Hunting Map | Full-width Leaflet map with CPW layer toggles, a clicked GMU popup, and harvest statistics panel |
| Your Trip | Category-grouped checklist with persistent checkboxes |
| Group Chat | Message stream with shared-card examples, like counts, edit/delete controls, and group sidebar |
| Group Detail | Member roster with creator add/remove controls |
| Profile | Photo upload form and hunter details |
| Search | Combined results across pages, resources, groups, and messages |

### User flow

1. **Sign up** → profile created → dropped into the group list.
2. **Plan:** Hunt Planner produces a hunt plan → share it as a card into a
   group chat.
3. **Research:** Hunting Map → find public-access ground in a GMU → share
   the selected GMU to the crew.
4. **Prepare:** Your Trip checklist → pack → share the packing list card.
5. **Coordinate:** crew discusses in chat; everyone gets email updates;
   the creator moderates if needed.

Design principles carried throughout: mobile-first Bootstrap grid,
progressive enhancement (every JS interaction has a plain-form fallback),
Post/Redirect/Get on all writes, and consistent avatar partials shared
across templates.

---

## 9. Conclusion and Future Work

### Outcomes and reflection

The project delivers a complete, deployed, tested product rather than a
demo: a live site with real government-data integration, authentication,
permissions, background email, rate limiting, a 55-test automated suite,
and production deployment with a proper environment-configuration story
(settings fail fast without a secret key; debug off by default). Every
feature on the original scope shipped, and the codebase survived a full
self-audit (`docs/CODE_REVIEW.md`).

### Challenges faced and learnings

- **Real-world data is messy.** CPW publishes harvest statistics as PDFs;
  I built an offline parse pipeline rather than scraping live, which made
  the app faster and more reliable.
- **Deployment constraints shape architecture.** Render's free tier blocks
  SMTP port 587 (solved with implicit-SSL port 465) and has ephemeral disk
  (solved with Postgres + WhiteNoise). Reading all configuration from
  environment variables made local/prod parity trivial.
- **Security invariants are worth repeating.** The membership check is
  deliberately re-applied at every entry point; during testing it never
  once leaked across groups. The audit noted this duplication is the price
  of the guarantee.
- **Progressive enhancement pays off.** Keeping plain-form fallbacks for
  likes/edit/share caught real bugs during development and keeps the app
  usable on poor connections in the field.
- **Emails are a product surface.** Honest timestamps, real reversed URLs,
  multipart formatting, and duplicate-inbox warnings all came out of
  actually reading the sent mail.

### Future enhancements

1. **Durable media storage** (S3/Cloudinary) so profile photos survive
   redeploys (currently ephemeral on Render's free tier).
2. **Real-time chat** via WebSockets (Django Channels) plus chat
   pagination / "load older messages."
3. **Live like counts** across sessions (polling or channels).
4. **Hunt-plan persistence** — save plans as first-class models with
   history, instead of shareable cards only.
5. **Offline map caching** and CPW response caching for field use.
6. **Refactors from the audit backlog:** membership-guard helper decorator,
   shared CSRF/`postJSON` JS helper, deriving the message-kind whitelist
   from model choices, and splitting the CSS per feature.
7. **Mobile app wrapper** (PWA manifest + offline checklist) for
   no-signal hunting camps.

---

## 10. References and Acknowledgments

### References and resources

- **Django documentation** — https://docs.djangoproject.com/ (models, auth,
  class-free views, testing, settings)
- **Colorado Parks & Wildlife** — GMU/DAU FeatureServer GIS layers, big-game
  license and season information, and harvest statistics PDFs
  (https://cpw.state.co.us / CPW ArcGIS FeatureServices)
- **Leaflet** — https://leafletjs.com/ (interactive mapping)
- **MapTiler** — https://www.maptiler.com/ (base map tiles)
- **Bootstrap** — https://getbootstrap.com/ (layout and components)
- **django-ratelimit** — https://django-ratelimit.readthedocs.io/
- **WhiteNoise** — https://whitenoise.readthedocs.io/
- **Render** — https://render.com/docs (deployment, managed PostgreSQL)
- **PostgreSQL** — https://www.postgresql.org/docs/
- **Python Software Foundation** — https://www.python.org/

### Acknowledgments

- My capstone instructor and peers, for design reviews and the mock
  presentation feedback that shaped the scope and the code-review pass.
- Colorado Parks & Wildlife, for publishing GMU boundaries, access layers,
  and harvest data as open GIS services that made the map genuinely useful.
- The open-source community behind Django, Leaflet, Bootstrap,
  django-ratelimit, and WhiteNoise.
- Family and hunting partners who tested the group-chat flows and tolerated
  being added to test groups.
