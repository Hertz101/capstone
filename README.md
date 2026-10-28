# Rocky Mountain Coalition — Colorado Hunting Platform

A Django web platform for Colorado big-game hunters: an interactive Game
Management Unit (GMU) map with real harvest statistics, a step-by-step hunt
planner, pre-trip packing checklists, and regulation reference resources —
built entirely on public Colorado Parks & Wildlife (CPW) data.

## Stack

| Layer        | Technology                                                     |
| ------------ | -------------------------------------------------------------- |
| Backend      | Django (views, URL routing, template rendering)                |
| Frontend     | Django templates, vanilla JavaScript, Leaflet 1.x, Bootstrap 5 |
| Maps         | Leaflet + MapTiler terrain tiles                               |
| GIS data     | CPW ArcGIS FeatureServer (live GeoJSON queries)                |
| Harvest data | Static JSON produced by an offline PDF-parsing pipeline        |
| Tests        | Django test runner (22 tests)                                  |

## Getting started

```bash
python -m venv venv
./venv/bin/pip install -r requirements.txt
# add MAPTILER_API_KEY to a .env file (see Configuration below)
./venv/bin/python manage.py runserver
./venv/bin/python manage.py test          # run the test suite
```

## Pages and features

### Hunt Map (`/maps/`)

Interactive map of Colorado with toggleable CPW GIS layers: big-game GMU
boundaries, CPW public-access properties, Walk-In Access areas, and Elk/Deer
DAU boundaries. Clicking a GMU shows its harvest statistics (harvest, hunters,
success rate, sex breakdown, per-season detail) filtered live by
species / season / sex / year pickers. A GMU search box autocompletes unit
numbers and highlights + zooms to the selected polygon.

### Hunt Planner (`/hunting/plan/`)

Five-step guided form: species → method → season → GMU (picked on an
interactive map) → license status. Business rules are encoded in the UI:
choosing Archery or Black Powder as the method automatically locks the season
field (they _are_ their own seasons), while Rifle unlocks the 1st–4th rifle
choice. Submitting builds a plan summary and saves it.

### Your Trip (`/your_trip/`)

Pre-hunt packing checklist (~70 items in 4 groups) with:

- checked-state persistence via `localStorage`
- user-added custom items (also persisted)
- a live progress counter and expand/collapse controls
- a **My Packing List** card that mirrors everything checked, with
  copy-to-clipboard and print-only-the-list support
- a **My Hunt Plan** card showing the plan saved from the Hunt Planner,
  with an empty-state prompt and "Edit plan" link when none exists

### Resources (`/resource/`)

Expandable hero cards for reference content. Cards are fully data-driven —
content lives in `pages/content.py`; the template is a single loop. Two card
types are supported:

- **Expandable cards** (`sections` + optional `links`) — click to reveal
- **PDF link cards** (`pdf` key) — the whole hero opens a hosted regulation
  PDF (e.g. CPW Chapter P-5 OHV, Chapter W-2 Big Game)

The first card, **What's New**, summarizes the current year's regulation
changes and is designed to be refreshed annually (see below).

## How the CPW data gets into the app

The project uses **three distinct ingestion strategies**, chosen per data
source:

### 1. Harvest statistics — offline PDF pipeline (`scripts/extract_elk_stats.py`)

CPW publishes harvest data as PDF reports. The pipeline:

1. Download the official CPW harvest-estimate PDFs (elk, deer, bear,
   pronghorn) and the post-draw recap PDF
2. `pdfplumber` extracts raw text from each page
3. Regular expressions parse table rows (one parser per report layout:
   `parse_eight_col`, `parse_bear`, `parse_licenses`)
4. Rows aggregate into a nested structure:
   `{species → season → year → GMU → stats}`
5. Output is written to `static/hunting/elk_stats.json`

This is a **build-time ETL step**: the data is published annually and is
read-only, so re-parsing 40 PDFs per page request would be wasteful. The
browser fetches the finished JSON once per visit; all filtering happens
client-side with no server round-trips.

### 2. GIS boundaries — live ArcGIS REST queries

GMU polygons, public-access properties, Walk-In areas, and DAU boundaries
are queried directly from CPW's FeatureServer:

```
.../FeatureServer/{layerId}/query?where=1=1&outFields=*&outSR=4326&f=geojson
```

- `outSR=4326` returns WGS84 coordinates that Leaflet renders natively
- Layers load **lazily** on checkbox toggle, not upfront
- Duplicate concurrent requests for the same layer are deduplicated via a
  promise map (race-condition prevention)
- Every response is validated at three levels: HTTP status, service error
  objects, and empty feature sets — failures surface in the "Data status" panel

### 3. Basemap tiles — MapTiler

Terrain tiles served by MapTiler with an API key (512px tiles,
`zoomOffset: -1`), with attribution rendered.

## Architecture decisions worth knowing

**Why no database for hunting data.** The harvest dataset is derived,
read-only, and small enough to load wholesale. Moving it to Django models
would end in serializing the same JSON to the browser through an extra
endpoint. Models become justified for: per-user saved plans (requires
accounts), draw-odds calculations, or if the dataset outgrows a few MB.

**Why content lives in Python, not the database.** Resource cards and
checklist items are curated reference content edited by developers. Keeping
them in `pages/content.py` keeps them in version control and makes annual
updates a one-file diff. Django models would be the right call if
non-developers needed to edit content.

**Client-side state via `localStorage`.** Hunt plans
(`rmc_hunt_plan_v1`) and checklist progress (`rmc_trip_checklist_v1`)
persist per device without accounts. This is an honest limitation: state is
not shared across devices or users. The migration path to a database model
is straightforward once authentication exists.

**API key handling.** The MapTiler key is injected server-side into a
`data-maptiler-key` attribute on the map element (`{{ maptiler_key|escapejs }}`);
it never appears in a static JS file.

## Updating content

**Annual "What's New" refresh** — edit the `whats-new` card in
`pages/content.py`: update `kicker` and `title` year, replace the section
bullets, update the brochure link. No template changes needed.

**Adding a resource card** — append a dict to `RESOURCE_CARDS` (expandable
with `sections`, or PDF link with `pdf` pointing at a file under `static/`).

**Editing the checklist** — append strings to any group's `items` list in
`PRE_HUNT_CHECKLIST`. Note: saved checkboxes are keyed by group + index, so
appending is safe; inserting mid-list can shift saved checks for returning
visitors.

## Tests

```bash
./venv/bin/python manage.py test
```

- **hunting/tests.py** — planner route smoke tests: URL resolution,
  template, API key passing, graceful render with a missing key
- **pages/tests.py** — page routes, plus structural tests guarding the
  content data: checklist groups have unique ids and non-empty items; every
  resource card is expandable _or_ a PDF link (never both, never neither);
  internal `{url}` placeholders resolve against real URL names; referenced
  PDFs exist in static; the view resolves placeholders without mutating the
  shared content

## Known limitations

- PDF parsing regexes are coupled to CPW's current report layout; a format
  change requires updating the parsers
- Plans and checklists are per-device (no accounts yet)
- GIS queries download full layers (`where=1=1`); fine at Colorado scale,
  spatial filtering would be needed for larger datasets
- Checklist persistence keys are index-based (see above)

## Project layout

```
pages/          content pages (home, resources, your trip)
  content.py    ALL page content data — edit this to change what visitors see
  views.py      thin views: render templates, resolve URL placeholders
hunting/        hunt planner + interactive map
scripts/        extract_elk_stats.py — PDF → JSON pipeline
static/
  js/           map page JS, checklist, resources, shared CPW config
  hunting/      planner JS, planner map JS, elk_stats.json
  hunting/*.pdf hosted CPW regulation PDFs
templates/      Django templates
```
