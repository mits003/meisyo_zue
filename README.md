# FOSS4G Hiroshima — Spot Recommendation Map

A lightweight web map where **FOSS4G Hiroshima participants** pick a place from
**OpenStreetMap** and post it as a recommended spot — with their name, a
category, tags and a comment. A modern, crowd-sourced *meisho zue* (名所図会:
illustrated guide to famous places), built on open data.

- **Backend:** FastAPI + SQLite (Python, no build step)
- **Frontend:** plain HTML/CSS/JS + Leaflet (loaded from CDN), mobile-first, **English UI**
- **POI source:** OpenStreetMap via the Overpass API
- **Map tiles:** OpenStreetMap

## Categories

| Category | Subcategories |
|---|---|
| 🏛️ Conference venue | — |
| 🍽️ Food & Drink | Lunch · Dinner · Drinks · Sweets |
| ⛩️ Sightseeing | — |
| 📍 Other | — |

## Requirements

- Python 3.11+ and [`uv`](https://docs.astral.sh/uv/) (no Node.js needed)

## Quick start

```bash
cd foss4g_meisyo_zue

# 1. Fetch nearby POIs from OpenStreetMap into the local DB
#    (uses the area center/radius in app/config.py; falls back to a small
#     bundled sample if Overpass is unreachable)
uv run python -m app.poi

# 2. (optional) Add a few demo recommendations so the map looks alive
uv run python -m app.seed

# 3. Run the app
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
#    …or: uv run python -m app.main
```

Open <http://127.0.0.1:8000>. On a phone connected to the same network,
open `http://<your-computer-ip>:8000`.

## How to use

The map shows two kinds of markers:

- **Colored pins** = recommendations posted by participants (tap for details).
- **Small dots** = OpenStreetMap places you can recommend (visible at zoom 15+;
  zoom in to reveal more).

To recommend a spot:

1. **Tap a dot** on the map — the post form opens with that place, category and
   suggested subcategory already filled in. (Or tap **＋ Recommend a spot** to
   search a place by name, **Pick on map** for an unlisted point, or
   **Use my location**.)
2. Enter your name, confirm the category / subcategory, add tags and a comment,
   then post. Your recommendation appears instantly as a pin.

Browse with the **category / subcategory chips** and the **search box** (matches
spot name, comment, author and tags). Tap a tag in a spot's detail card to
filter by it.

## Customizing for your event

Edit [`app/config.py`](app/config.py):

- `AREA_CENTER_LAT` / `AREA_CENTER_LNG` / `POI_RADIUS_M` — where and how wide to
  pull POIs. Re-run `uv run python -m app.poi` afterwards.
- `MAP_CENTER` / `MAP_ZOOM` — the map's initial view.
- `CATEGORIES` — category names, colors, emoji and subcategories.

## Project layout

```
app/
  config.py      POI area center, map defaults, category taxonomy
  db.py          SQLite schema + connection
  models.py      Pydantic models + validation
  repository.py  CRUD / search for pois & posts
  poi.py         Overpass fetch -> pois table (CLI)
  seed.py        demo recommendations (CLI)
  main.py        FastAPI app (REST API + static hosting)
static/          index.html, css/, js/ (Leaflet frontend)
data/            app.db (created at runtime; git-ignored)
```

## API

| Method | Path | Description |
|---|---|---|
| GET | `/api/meta` | category taxonomy + map defaults |
| GET | `/api/pois?q=&bbox=` | candidate places (for the post form) |
| GET | `/api/posts?category=&subcategory=&tag=&q=` | recommendations |
| POST | `/api/posts` | create a recommendation |

## Notes / scope

- No login by design — the author name is self-reported (fine for a friendly
  event). Field lengths are capped server-side as light abuse protection.
- Built for **local / demo** use first, but kept easy to deploy to a single
  host later (it's just a FastAPI app + a SQLite file).
- Future ideas: photo uploads, marker clustering when many posts share a place,
  live Overpass search, edit/delete & moderation.
