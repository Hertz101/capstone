# Manual Test Cases — Rocky Mountain Coalition (Django capstone)

**Project:** /Users/adamhertzberg/Desktop/capstone
**How to run:** `venv/bin/python manage.py runserver` → browse to `http://127.0.0.1:8000/`
**Test data setup:** create 3 users via `/accounts/signup/` (alice, bob, carol). Each fills out a profile.
**Date:** 2026-11-04

Legend: PASS / FAIL / BLOCKED. Record actual result and a note for any FAIL.

---

## 1. Authentication

| ID | Title | Steps | Expected Result | Priority | Actual / Status |
|----|-------|-------|-----------------|----------|-----------------|
| AUTH-01 | Signup with valid data | Go to `/accounts/signup/`. Fill username, email, password (valid), optional profile fields, submit | Account created, user is logged in automatically, redirected to `/group_chat/` | High | |
| AUTH-02 | Signup with weak password | Sign up with password `123` | Form re-renders with a password-validation error; no account created | Medium | |
| AUTH-03 | Signup with duplicate username | Sign up with username `alice` again | Form error "A user with that username already exists" | High | |
| AUTH-04 | Signup with photo upload | Sign up (or later edit profile) uploading a `.jpg` under ~2 MB | Photo accepted; appears as avatar in group chat | Medium | |
| AUTH-05 | Login | Log out, then log in as `alice` | Redirect to the logged-in home area; nav shows authenticated links | High | |
| AUTH-06 | Login with wrong password | Log in as `alice` with bad password | Error message shown; not logged in | High | |
| AUTH-07 | Logout | Click logout | Redirected to the "logged out" farewell page (`/accounts/logged_out/`-style route); nav shows login link | Medium | |
| AUTH-08 | Protected page redirects anonymous user | While logged out, go to `/group_chat/`, `/groups/`, `/profile/`, `/profile/delete/` | Each redirects to the login page (302), not a 500 | High | |
| AUTH-09 | Account delete with correct password | Log in as a throwaway user, go to `/profile/delete/`, enter correct password, confirm | User logged out, account deleted, redirected to logged-out page. Re-login fails | High | |
| AUTH-10 | Account delete with wrong password | On `/profile/delete/`, enter wrong password | Message "Incorrect password — nothing was deleted."; account still exists | High | |
| AUTH-11 | Account delete cascades data | Before deleting a throwaway user, note it has chat messages and group memberships | After deletion, its messages no longer render in group chat; groups it created still exist with other members intact | Medium | |

## 2. Profile

| ID | Title | Steps | Expected Result | Priority | Actual / Status |
|----|-------|-------|-----------------|----------|-----------------|
| PROF-01 | View profile | Go to `/profile/` | Form pre-filled with saved profile values | High | |
| PROF-02 | Edit and save profile | Change first/last name, city, state (e.g. `CO`), method, save | Redirect back to `/profile/`; values persist after reload | High | |
| PROF-03 | State field validation | Enter a 3+ letter "state" value and save | Validation error (field is a 2-char code) | Medium | |
| PROF-04 | Upload profile photo | Upload a valid image, save | Photo stored under `media/profile_photos/...`; avatar shows in group chat instead of initials badge | Medium | |
| PROF-05 | Display name fallback | Leave first/last name blank; post in group chat | Message shows username as display name | Low | |

## 3. Group chat

| ID | Title | Steps | Expected Result | Priority | Actual / Status |
|----|-------|-------|-----------------|----------|-----------------|
| CHAT-01 | Global chat view (no group) | Go to `/group_chat/` | Page loads (verify the earlier `else`-tag bug stays fixed); heading "Group Chat"; shows messages with no group | High | |
| CHAT-02 | Post a text message | Type "Hello" in the form, submit | Redirects back (Post/Redirect/Get — browser back button does not re-submit); message appears at top with timestamp | High | |
| CHAT-03 | Empty message is ignored | Submit the form with only spaces/empty text | No message created; page reloads without error | Medium | |
| CHAT-04 | Message ordering | Post several messages | Newest first (ordering is `-created_at`), capped at 50 shown | Medium | |
| CHAT-05 | Long message | Post a 2000-character message | Saved and rendered; a 2001-char post is rejected by the model (or truncated — confirm behavior matches intent) | Low | |
| CHAT-06 | Group chat for member | As `alice`, open `/group_chat/<group_id>/` for a group she belongs to | Heading shows group name; only that group's messages show | High | |
| CHAT-07 | Non-member blocked from group chat | As `carol` (not a member), open `/group_chat/<group_id>/` directly | Redirected to `/group_chat/`, no group messages visible | High | |
| CHAT-08 | Nonexistent group ID | Open `/group_chat/99999/` while logged in | 404 page (get_object_or_404), not a 500 | Medium | |
| CHAT-09 | Avatar rendering | Post with a profile photo, and post as a user without one | With photo: rounded avatar image. Without: initials badge with fallback styling (this is the `{% if %}` block just fixed) | Medium | |
| CHAT-10 | Share Hunt Plan card | Set up a plan, use "Share my plan" in the chat sidebar | A `plan` message with a payload card renders in chat (species/season/method/unit/license) | High | |
| CHAT-11 | Share Packing List card | Tick checklist items on `/your_trip/`, then share in chat sidebar | `packing` card message renders in chat | Medium | |
| CHAT-12 | Share Selected GMU card | Click a unit on `/maps/`, then share in chat sidebar | `gmu` card message renders, unit links to `/maps/?gmu=NNN` | Medium | |
| CHAT-13 | Tampered kind value | POST to `/group_chat/` with `kind=hacker` (curl or devtools) | Kind falls back to `text`; no crash, no weird card | Medium | |
| CHAT-14 | Tampered payload | POST with `kind=gmu` and `payload=not json` | Falls back to a plain text message; no 500 | Medium | |
| CHAT-15 | XSS attempt in message | Post `<script>alert(1)</script>` | Message renders as escaped text, no script executes | High | |
| CHAT-16 | Browser refresh after POST | Post a message, then press F5 | No duplicate message (Post/Redirect/Get) | Medium | |

## 4. Groups

| ID | Title | Steps | Expected Result | Priority | Actual / Status |
|----|-------|-------|-----------------|----------|-----------------|
| GRP-01 | Group list | Go to `/groups/` | "My groups" lists groups the user belongs to; other groups listed separately | High | |
| GRP-02 | Create group | `/groups/new/`, enter name, select members, submit | Redirect to `/group_chat/<id>/`; creator is a member | High | |
| GRP-03 | Create group validation | Submit with empty name | Form error; no group created | Medium | |
| GRP-04 | Join a group | As `carol`, from `/groups/` join a group she is not in (POST to `/groups/<id>/join/`) | Redirected into that group's chat; she now appears in "My groups" | High | |
| GRP-05 | Group detail as member | As a member (not creator), open `/groups/<id>/` | Members list visible; no add/remove controls | Medium | |
| GRP-06 | Group detail as creator — add member | As creator, add `bob` via the form | Bob appears in members; can now see the group chat | High | |
| GRP-07 | Group detail as creator — remove member | As creator, remove `bob` | Bob removed; his direct `/group_chat/<id>/` access now redirects away | High | |
| GRP-08 | Non-member blocked from group detail | As `carol` (non-member), open `/groups/<id>/` | Redirected to `/group_chat/` | High | |
| GRP-09 | Creator deleted, group persists | Delete the creator's account (AUTH-09 flow) | Group still exists; members can still chat; add/remove controls disappear (no creator) | Low | |

## 5. Public pages

| ID | Title | Steps | Expected Result | Priority | Actual / Status |
|----|-------|-------|-----------------|----------|-----------------|
| PUB-01 | Home page | Open `/` | Animal cards render (Elk, Mule Deer, Whitetail, Bear, Pronghorn) with images | High | |
| PUB-02 | Tools page | Open `/tools/` | Renders without error | Low | |
| PUB-03 | Blog page | Open `/blog/` | Renders without error | Low | |
| PUB-04 | Your Trip checklist | Open `/your_trip/` | Checklist items render grouped; ticking items persists (localStorage or server — confirm intended behavior) | Medium | |
| PUB-05 | Resources page | Open `/resource/` | All resource cards render; links resolve to real URLs; PDFs download (server logs a warning for any missing PDF) | Medium | |
| PUB-06 | Old planner URL redirect | Open `/get_started/` | 302 redirect to the planner page in the hunting app | Low | |
| PUB-07 | Map page anonymous | Open `/maps/` logged out | Map renders (MapTiler tile layer loads); no chat-group share dropdown | Medium | |
| PUB-08 | Map page logged in | Open `/maps/` as a group member | Map renders; share-to-group control lists the user's groups; clicking a unit shows GMU details | Medium | |
| PUB-09 | 404 handling | Open `/nonexistent-page/` | Django 404 page (or custom one), not a 500 | Low | |

## 6. Regression watch-list (areas recently touched)

| ID | Title | Steps | Expected Result | Priority | Actual / Status |
|----|-------|-------|-----------------|----------|-----------------|
| REG-01 | Group chat template parses | Load `/group_chat/` and `/group_chat/<id>/` | No TemplateSyntaxError; the `{% with %}` / `{% if %}` avatar block renders both branches (photo and initials) | High | |
| REG-02 | Static asset cache-busting | Hard-refresh `/maps/` and `/group_chat/` after editing `js/maps.js` or `js/chat_sidebar.js` | URL includes updated `?v=<mtime>`; new JS is served | Low | |
| REG-03 | Django system check | Run `venv/bin/python manage.py check` | "System check identified no issues" | High | |

---

## Known environment notes
- Python 3.14 / Django 6.1, venv at `./venv`.
- ImageField requires Pillow — if AUTH-04 fails at upload, confirm `Pillow` is installed in the venv.
- MEDIA serving in development must be configured for profile photos to display (CHAT-09, PROF-04).

---

# Part 2 — Edge Cases by Data Type

Each edge case lists: input, where to exercise it, expected behavior. Format: `EDGE-<type>-<n>`.

## Strings / Text (message text, group name, profile names)

| ID | Input | Where | Expected |
|----|-------|-------|----------|
| STR-01 | Empty string (0 chars) | Chat message submit; group name | Silently ignored / form validation error — not saved |
| STR-02 | Whitespace only (`"   "`) | Chat message | `.strip()` in the view → not saved, no error |
| STR-03 | Exactly 2000 chars | Chat message | Saved and renders (model max_length=2000) |
| STR-04 | 2001+ chars | Chat message | Model rejects (IntegrityError/ValidationError). If a 500 appears instead of a clean error, that's a FAIL — view should truncate or validate |
| STR-05 | Single emoji, multi-codepoint emoji (family, skin-tone, ZWJ sequences) | Chat message, group name | Stored and displayed intact; no mojibake |
| STR-06 | HTML/XSS: `<script>alert(1)</script>`, `<img src=x onerror=alert(1)>` | Chat message, group name | Rendered escaped as text; no script executes (Django autoescape) |
| STR-07 | URL in text: `http://evil.example.com` | Chat message | Rendered as plain text (no auto-linking = safe) |
| STR-08 | Very long unbroken string (no spaces, 2000 chars) | Chat message | Renders; check layout doesn't overflow the card horizontally (CSS overflow) |
| STR-09 | Newlines and tabs (`line1\n\nline2`) | Chat message | Stored; check whether template preserves or collapses them — behavior must be consistent, never executed as markup |
| STR-10 | RTL text and mixed scripts (Arabic, Hebrew, CJK) | Chat message, profile name | Renders correctly; layout not broken |
| STR-11 | Null byte `\x00` and control chars | Chat message | Cleanly rejected or stripped, no 500 |
| STR-12 | HTML entity lookalikes: `<script>`, `&#x3C;` | Chat message | Double-escaped correctly, displays as literal text |
| STR-13 | Leading/trailing spaces: `"  hello  "` | Chat message | Stripped by the view (verify stored text has no padding) |
| STR-14 | 101+ chars for group name (model max_length=100) | Group create form | Form validation error, not a 500 |
| STR-15 | 151+ chars for profile first/last name | Profile form | Form validation error |

## Numbers

| ID | Input | Where | Expected |
|----|-------|-------|----------|
| NUM-01 | `0` as group_id | `/group_chat/0/`, `/groups/0/` | 404 (no record with pk 0), not a 500 |
| NUM-02 | Negative: `-1` | `/group_chat/-1/` | 404 (URL converter `<int:group_id>` rejects negative — verify it 404s, doesn't error) |
| NUM-03 | Non-numeric: `abc`, `1.5`, `1e5` | `/group_chat/abc/` | URL pattern doesn't match → 404 |
| NUM-04 | Huge integer: `99999999999999999999` | `/group_chat/<huge>/` | URL matches or 404s cleanly; if it reaches the DB, Django handles overflow with a 404/validation, never a 500 |
| NUM-05 | Leading zeros / `+`/`-` signs: `007`, `+5` | `/group_chat/007/` | Matches int converter → 404 or valid group; no weird parse |
| NUM-06 | GMU payload with non-numeric gmu: `{"gmu": "abc"}` | Shared gmu card (tampered POST) | Card renders, map link becomes `/maps/?gmu=abc` harmlessly, no 500 |
| NUM-07 | Payload with extreme numbers: `{"gmu": 1e309}` (Infinity) | Shared gmu card | JSON parses (Python allows `Infinity`), template renders something inert; no crash |
| NUM-08 | Float as user_id in group add: `user_id=1.5` | Group detail add-member (creator) | 404 from get_object_or_404, no crash |

## Booleans / Choice fields

| ID | Input | Where | Expected |
|----|-------|-------|----------|
| BOOL-01 | `kind` = each valid value (`text`, `plan`, `packing`, `gmu`) via devtools POST | Group chat POST | Each saved as that kind; payload handling as designed |
| BOOL-02 | `kind` = invalid (`TEXT`, `Text`, `plan `, `0`, `true`, `null`, empty) | Group chat POST | Falls back to `text` — case-sensitivity and whitespace mean it will NOT match the set, verify no bad value stored |
| BOOL-03 | Profile `method` = each HuntingMethod choice | Profile form | Saved and redisplayed with correct label |
| BOOL-04 | Profile `method` = invalid value injected in POST (`method=hack`) | Profile form (devtools) | Django ModelForm rejects unknown choice — form error, not saved |
| BOOL-05 | `hidden` / `checked` attributes absent vs present | Packing checklist → share | Missing checkbox produces empty list payload, shares gracefully (empty card or blocked) |

## JSON payload (Message.payload, JSONField)

| ID | Input | Where | Expected |
|----|-------|-------|----------|
| JSON-01 | Valid JSON object: `{"gmu": 401}` | Shared GMU POST | Saved; card renders |
| JSON-02 | Valid JSON non-object: `[1,2,3]`, `"string"`, `42`, `true`, `null` | Tampered POST | View coerces to `kind=text, payload=None` (isinstance dict check) — verify |
| JSON-03 | Malformed JSON: `{not json`, `{"a":`, empty string | Tampered POST | JSONDecodeError caught → plain text message; no 500 |
| JSON-04 | Deeply nested / large JSON (100 KB) | Tampered POST | Parsed but card rendering stays safe; consider whether a size limit is desired (DoS vector) |
| JSON-05 | JSON with unexpected keys: `{"evil": "<script>"}` | Shared card POST | Extra keys ignored by template; if any key is rendered, it must be escaped |
| JSON-06 | JSON with HTML in values: `{"species": "<b>Elk</b>"}` | Shared card POST | Escaped in rendering |
| JSON-07 | Duplicate keys `{"gmu":1,"gmu":2}` | Tampered POST | Last-wins per JSON spec; no crash |

## Dates / Timestamps

| ID | Input | Where | Expected |
|----|-------|-------|----------|
| DATE-01 | Message posted at 23:59:59 vs 00:00:01 | Group chat | Date format `M j, Y g:i A` renders correct day/AM-PM |
| DATE-02 | 50+ messages in one group | Group chat | Only latest 50 rendered (`[:50]` slice) — older hidden, page fast |
| DATE-03 | Two messages in same second | Group chat | Both saved; ordering between them is stable/non-crashing (ordering by created_at only — ties allowed) |
| DATE-04 | DST boundary / clock skew | Any timestamp display | Time shown matches server/local expectation; document which timezone is displayed |
| DATE-05 | `maps_js_mtime` when file missing | Rename `js/maps.js` temporarily, load `/maps/` | Falls back to `mtime=1`, page loads, no 500 (same for chat_sidebar.js) |

## Files (profile photo upload)

| ID | Input | Where | Expected |
|----|-------|-------|----------|
| FILE-01 | Valid .jpg / .png < 2 MB | Profile photo | Uploaded to `media/profile_photos/YYYY/MM/`, avatar displays |
| FILE-02 | 0-byte file | Profile photo | Rejected or handled gracefully; no broken image |
| FILE-03 | Non-image with image extension: `evil.jpg` that is a text file | Profile photo | Pillow/Django ImageField rejects ("Upload a valid image") |
| FILE-04 | Disallowed extension: `.exe`, `.svg`, `.html` | Profile photo | Rejected by validator |
| FILE-05 | Oversized image (e.g. 20 MB) | Profile photo | Either rejected by DATA_UPLOAD_MAX_MEMORY_SIZE/form limit or handled — never a hang or 500 |
| FILE-06 | Path-traversal filename: `../../etc/passwd.jpg` | Profile photo | Filename sanitized by Django storage; nothing escapes `media/profile_photos/` |
| FILE-07 | Duplicate filenames from two users (`me.jpg` both) | Profile photo | Storage auto-renames (`me_XXXX.jpg`); second upload doesn't overwrite first |
| FILE-08 | No file selected (empty upload) | Profile photo (blank=True) | Form saves without photo; initials fallback avatar used |
| FILE-09 | Unicode filename: `照片.jpg`, emoji filename | Profile photo | Stored with sanitized/safe name, displays |
| FILE-10 | Deleted photo on disk but still referenced | Manually delete media file, view chat | Broken-image icon or alt text; no 500 |
| FILE-11 | BOM/HEIC/iPhone photo | Profile photo | HEIC typically rejected unless Pillow supports it — confirm graceful error message |

## CSRF / Session / Headers (cross-cutting)

| ID | Input | Where | Expected |
|----|-------|-------|----------|
| SEC-01 | POST without CSRF token (curl) | Any POST endpoint | 403 CSRF verification failed |
| SEC-02 | Expired session cookie + submit | Any page while logged in | Redirected to login, no data lost silently beyond the abandoned POST |
| SEC-03 | Cookie tampering (`sessionid=garbage`) | Any page | Treated as anonymous; protected pages redirect to login |
| SEC-04 | Concurrent login same user two browsers | Two browsers as alice | Both work (Django default sessions); no crash |
| SEC-05 | Delete own account while open in second browser | Browser A deletes alice; browser B had alice logged in | Browser B's next request treats it as anonymous/logout; no 500 on dangling user |

---

# Part 3 — Edge Cases by User Type

Roles: **Anonymous**, **Authenticated regular user**, **Group member (non-creator)**, **Group creator**, **Deleted/ex- user**, plus adversarial "user" behaviors.

## Anonymous visitor (not logged in)

| ID | Scenario | Expected |
|----|----------|----------|
| ANON-01 | Visits every public page (`/`, `/tools/`, `/maps/`, `/your_trip/`, `/blog/`, `/resource/`) | All render; no login prompts except on protected features |
| ANON-02 | Deep-links to protected page (`/group_chat/`, `/groups/`, `/profile/`, `/profile/delete/`) | 302 → login page with `?next=` returning to the original page after login |
| ANON-03 | POSTs directly to protected endpoints (chat message, group join/create) via curl | Redirected/blocked by login_required before any DB write |
| ANON-04 | Maps page: clicks units, tries "Share to group" (if button present) | Share control absent or redirects to login — no group dropdown |
| ANON-05 | Signs up, is immediately logged in | Lands on `/group_chat/` per the view; can post right away |
| ANON-06 | Signup form resubmission (double-click submit) | Only one account created; second submit either errors on duplicate username or is idempotent |
| ANON-07 | Tries nonexistent group chat `/group_chat/1/` without account | Login redirect happens first — cannot even probe whether group 1 exists (information disclosure check) |

## Authenticated regular user (no groups)

| ID | Scenario | Expected |
|----|----------|----------|
| USER-01 | Opens `/group_chat/` (global, group=None) | Empty state or global messages; no crash from `group=None` path |
| USER-02 | Opens `/group_chat/` with zero messages ever | Empty list area renders gracefully (no "None" artifacts) |
| USER-03 | Visits `/groups/` with no memberships | "My groups" empty; only joinable groups shown |
| USER-04 | Posts a message with no group selected | Message saved with `group=NULL`; visible in global chat |
| USER-05 | Visits `/groups/99999/` (nonexistent) | 404 |
| USER-06 | Tries group detail/join for a group they're not in via URL guessing | Redirected away / blocked |
| USER-07 | Profile never created (no Profile row) — post in chat | `get_or_create` in profile view or template handles missing profile → initials fallback, no AttributeError |
| USER-08 | Rapid-fire 10 messages in 5 seconds | All saved; ordering correct; consider rate-limiting as a hardening note |

## Group member (non-creator)

| ID | Scenario | Expected |
|----|----------|----------|
| MEMB-01 | Views group chat for own group | Sees all group messages incl. other members' |
| MEMB-02 | Sees another member's shared plan/packing/GMU card | Card renders; "shared by" name correct |
| MEMB-03 | Opens group detail page | Can view members; add/remove controls absent |
| MEMB-04 | Attempts creator action via forged POST (`action=add&user_id=2`) with devtools | View checks `group.created_by == request.user` → silently ignored, redirect back, no member added |
| MEMB-05 | Removes themselves conceptually (creator removes them, session still open) | Next chat request redirects to `/group_chat/`; previous messages they wrote remain attributed |
| MEMB-06 | Tries to view chat of a group they were just removed from (stale tab open) | Redirected to global chat; no group content leaks |

## Group creator

| ID | Scenario | Expected |
|----|----------|----------|
| CREA-01 | Creates group selecting zero members | Group created with only self; chat works |
| CREA-02 | Creates group and selects themselves in the member list | No duplicate/self-conflict error; appears once |
| CREA-03 | Adds a member who is already a member | `members.add()` is idempotent — no error, no duplicate |
| CREA-04 | Removes the last other member | Group continues with just creator |
| CREA-05 | Attempts to remove themselves | `members.remove()` removes creator from own group — then their own group detail/chat access redirects away. Confirm this is intended behavior (potential lockout edge case worth flagging) |
| CREA-06 | Add/remove with tampered `user_id` (`99999`, another user's pk, `abc`) | 404 for nonexistent pk; valid pk only adds existing user; `abc` → 404. Never 500 |
| CREA-07 | Creator views another creator's group they somehow joined | Sees member list; `is_creator` false → no admin controls |
| CREA-08 | Creates two groups with the same name | Allowed (no unique constraint) — confirm desired; both appear in list |

## Ex-user / deleted account (after AUTH-09)

| ID | Scenario | Expected |
|----|----------|----------|
| DELU-01 | Deleted user's old messages in group chat | `user` FK is CASCADE → messages were deleted with the account. Confirm chat history behavior is acceptable (messages vanish) — flag if history preservation is desired |
| DELU-02 | Deleted user's profile photo file | File remains on disk (Django doesn't auto-delete media) — cosmetic cleanup note |
| DELU-03 | Deleted user who created a group | `created_by` is SET_NULL → group survives with no creator; members can still chat but nobody can add/remove members. Confirm acceptable or add transfer-ownership flow |
| DELU-04 | Deleted user tries to log in again | "Invalid credentials"; account truly gone |
| DELU-05 | Deleted user's stale session cookie used | Treated as anonymous; no dangling FK errors |

## Adversarial user (malicious behaviors across all roles)

| ID | Scenario | Expected |
|----|----------|----------|
| ADV-01 | IDOR: change hidden form field group_id / URL id to another group | Membership check blocks access; no data from non-member groups |
| ADV-02 | Mass-assignment: POST extra fields (`kind`, `payload`, plus fake `created_at`) to chat | Only whitelisted fields used; `created_at` can't be forged |
| ADV-03 | Unicode homoglyph username impersonation (`аlice` with Cyrillic а) at signup | Two distinct accounts — allowed by Django; confirm team is aware users can look alike |
| ADV-04 | SQL injection in every text field (`'; DROP TABLE--`) | ORM parameterizes; stored literally, rendered escaped |
| ADV-05 | Template injection `{{ 7*7 }}` / `{% %}` in message text | Rendered literally, never evaluated (Django templates don't evaluate user data) |
| ADV-06 | Huge POST body (10 MB message) | Rejected by DATA_UPLOAD_MAX_MEMORY_SIZE or form validation, no hang |
| ADV-07 | Malformed cookie / header injection | Django rejects or ignores; no 500 |
| ADV-08 | Replaying a join POST many times for one group | Idempotent membership add; no errors |

---

## Suggested execution order
1. Part 3 ANON-* (cheapest, no fixtures beyond sign-up)
2. AUTH-* then USER-* / MEMB-* flows
3. Part 2 type-based edge cases (can be batched into the flows above)
4. CREA-* and DELU-* (destructive — do last, with throwaway users)
