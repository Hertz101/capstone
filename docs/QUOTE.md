# Quote of Work — Rocky Mountain Coalition Hunt Planner

**Prepared for:** [Client Name]
**Prepared by:** [Your Name]
**Date:** November 20, 2026
**Quote valid until:** December 20, 2026 (30 days)

---

## 1. What the client will receive

A fully deployed, hosted web application for Colorado hunters, built on
Django 6.1 and PostgreSQL, including:

### Features delivered

- **Hunt Planner** — species / method / season / GMU selection with license
  guidance and a shareable hunt-plan summary (CPW license links included).
- **Interactive Hunting Map** — Leaflet map with Colorado Parks & Wildlife
  FeatureServer layers (GMU boundaries, public access, Walk-In Access,
  elk/deer DAUs), clickable feature details, and per-GMU harvest statistics.
- **Your Trip** — interactive pre-hunt checklist with persistent check
  state and share-to-chat integration.
- **Group Chat** — per-group chat rooms with text messages, shared cards,
  likes, message editing, and creator-only moderation. Rate-limited
  (10 posts/min, 30 likes/min).
- **Email notifications** — members are emailed on posts, likes, joins,
  and additions (secure SMTP over port 465).
- **Site-wide search** — scoped so users only see content from groups they
  belong to.
- **User accounts & profiles** — photo upload, city/state, preferred
  hunting method, and account self-deletion with password confirmation.

### Quality & deliverables

- **Test suite:** 55 automated Django tests covering routes, auth flows,
  permissions, moderation, and search scoping.
- **Documentation:** README with setup, deployment, and environment
  configuration; code review notes; manual test cases.
- **Deployment:** live hosting on Render (free tier) with PostgreSQL,
  WhiteNoise static serving, and automated build/migrate on deploy.
- **Source code:** full repository ownership transferred to the client
  (GitHub).

### What is _not_ included

- Custom domain registration and DNS (client provides; setup assistance
  available at hourly rate).
- Durable media storage (S3/Cloudinary) for profile photos — currently
  ephemeral on the free tier; available as an add-on.
- Future feature development beyond the warranty period.

---

## 2. Price

| Item                                          | Price      |
| --------------------------------------------- | ---------- |
| Hunt Planner web application (as specified)   | **$4,500** |
| Optional: S3/Cloudinary durable media storage | + $400     |
| Optional: custom domain + DNS setup           | + $150     |

**Total (base package): $4,500 USD**

---

## 3. Payment plan

| Milestone                                    | Due           | Amount       |
| -------------------------------------------- | ------------- | ------------ |
| 1. Project kickoff and repository handover   | Day 1         | 50% — $2,250 |
| 2. Final delivery, walkthrough, and training | At acceptance | 50% — $2,250 |

Alternative: **three monthly payments of $1,560** (total $4,680, includes
a 4% financing charge).

Payment accepted via ACH, check, or major credit card. Invoices are
net-15.

---

## 4. Bug handling & support

### Warranty period (90 days from delivery)

- **Bug classification:** any defect is classified as
  _Critical_ (site down or data loss), _Major_ (feature broken), or
  _Minor_ (cosmetic/edge case).
- **Response targets:** Critical — 24 hours; Major — 3 business days;
  Minor — next scheduled release.
- **Fixes for defects in the delivered scope are free of charge** during
  the warranty period.
- Bugs are tracked in the GitHub issue tracker; the client receives a
  link to every issue and fix.

### After the warranty period

- **Retainer option:** $120/month for up to 5 hours of support,
  maintenance, and dependency updates (Django/security patches).
- **Hourly:** $100/hour, billed in 30-minute increments, for ad-hoc
  fixes and enhancements.
- **New features** are quoted separately per project.

### Out of scope (not "bugs")

- Behavior changes caused by third-party services (CPW FeatureServer
  outages, map tile provider changes, Render/Postgres platform changes).
- Changes to third-party APIs (e.g., CPW data format changes) are quoted
  as change requests at hourly rates.

---

## 5. Acceptance

Delivery is complete when the client confirms the live site matches the
feature list above and the test suite passes. The client has 10 business
days after final walkthrough to report acceptance issues; otherwise
delivery is deemed accepted.

---

_Signed: **********\_\_********** Date: ****\_\_\_\_****_
_Client name and title: **********\_\_**********_
