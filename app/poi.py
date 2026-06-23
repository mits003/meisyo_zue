"""Fetch POIs from OpenStreetMap (Overpass API) into the `pois` table.

Run as a CLI:
    uv run python -m app.poi                 # use area center/radius from config
    uv run python -m app.poi --radius 2000
    uv run python -m app.poi --lat 34.39 --lng 132.46 --radius 1500

If Overpass is unreachable, a small bundled sample is inserted so the app
still works for a local demo.
"""

from __future__ import annotations

import argparse
import json

import httpx

from . import config
from .db import init_db
from .repository import upsert_pois

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
# Overpass blocks requests without a descriptive User-Agent (returns HTTP 406).
HEADERS = {"User-Agent": "foss4g-meisyo-zue/0.1 (FOSS4G Hiroshima spot map)"}

# OSM tag selectors to pull. Kept focused so the candidate list stays relevant.
_SELECTORS = [
    'node["amenity"~"^(restaurant|fast_food|cafe|bar|pub|biergarten|food_court|ice_cream)$"]',
    'way["amenity"~"^(restaurant|fast_food|cafe|bar|pub|biergarten|food_court|ice_cream)$"]',
    'node["shop"~"^(bakery|confectionery|pastry)$"]',
    'way["shop"~"^(bakery|confectionery|pastry)$"]',
    'node["tourism"~"^(attraction|museum|gallery|viewpoint|artwork|zoo|theme_park)$"]',
    'way["tourism"~"^(attraction|museum|gallery|viewpoint|artwork|zoo|theme_park)$"]',
    'node["historic"]',
    'way["historic"]',
    'node["amenity"="place_of_worship"]',
    'way["amenity"="place_of_worship"]',
    'node["leisure"="park"]',
    'way["leisure"="park"]',
]


def build_query(lat: float, lng: float, radius_m: int) -> str:
    around = f"(around:{radius_m},{lat},{lng})"
    body = "\n  ".join(f"{sel}{around};" for sel in _SELECTORS)
    return f"[out:json][timeout:60];\n(\n  {body}\n);\nout center tags;"


def classify(tags: dict) -> tuple[str, str | None]:
    """Map OSM tags to (top-level category, suggested subcategory)."""
    amenity = tags.get("amenity", "")
    shop = tags.get("shop", "")
    tourism = tags.get("tourism", "")

    if amenity in {"bar", "pub", "biergarten"}:
        return "Food & Drink", "Drinks"
    if amenity in {"cafe", "ice_cream"} or shop in {"bakery", "confectionery", "pastry"}:
        return "Food & Drink", "Sweets"
    if amenity == "fast_food":
        return "Food & Drink", "Lunch"
    if amenity in {"restaurant", "food_court"}:
        return "Food & Drink", "Dinner"

    if (
        tourism in {"attraction", "museum", "gallery", "viewpoint", "artwork", "zoo", "theme_park"}
        or "historic" in tags
        or amenity == "place_of_worship"
        or tags.get("leisure") == "park"
    ):
        return "Sightseeing", None

    return "Other", None


def _element_to_poi(el: dict) -> dict | None:
    tags = el.get("tags", {})
    name = tags.get("name") or tags.get("name:en")
    if not name:
        return None  # skip unnamed features — not useful as a recommendation

    if el["type"] == "node":
        lat, lng = el.get("lat"), el.get("lon")
    else:  # way / relation: use the computed center
        center = el.get("center", {})
        lat, lng = center.get("lat"), center.get("lon")
    if lat is None or lng is None:
        return None

    category, subcat = classify(tags)
    return {
        "osm_type": el["type"],
        "osm_id": el["id"],
        "name": name,
        "lat": lat,
        "lng": lng,
        "category": category,
        "suggested_subcat": subcat,
        "tags_json": json.dumps(tags, ensure_ascii=False),
    }


def fetch_from_overpass(lat: float, lng: float, radius_m: int) -> list[dict]:
    query = build_query(lat, lng, radius_m)
    resp = httpx.post(OVERPASS_URL, data={"data": query}, headers=HEADERS, timeout=90)
    resp.raise_for_status()
    elements = resp.json().get("elements", [])
    pois = [p for el in elements if (p := _element_to_poi(el))]
    # Deduplicate by (osm_type, osm_id) within this batch.
    seen: dict[tuple, dict] = {}
    for p in pois:
        seen[(p["osm_type"], p["osm_id"])] = p
    return list(seen.values())


# A tiny fallback so the demo works without network access to Overpass.
_SAMPLE_POIS = [
    {"osm_type": "node", "osm_id": -1, "name": "Hiroshima Peace Memorial (Genbaku Dome)",
     "lat": 34.3955, "lng": 132.4536, "category": "Sightseeing",
     "suggested_subcat": None, "tags_json": "{}"},
    {"osm_type": "node", "osm_id": -2, "name": "Shukkeien Garden",
     "lat": 34.3989, "lng": 132.4669, "category": "Sightseeing",
     "suggested_subcat": None, "tags_json": "{}"},
    {"osm_type": "node", "osm_id": -3, "name": "Okonomimura",
     "lat": 34.3919, "lng": 132.4607, "category": "Food & Drink",
     "suggested_subcat": "Dinner", "tags_json": "{}"},
    {"osm_type": "node", "osm_id": -4, "name": "Hondori Shopping Arcade Cafe",
     "lat": 34.3922, "lng": 132.4575, "category": "Food & Drink",
     "suggested_subcat": "Sweets", "tags_json": "{}"},
    {"osm_type": "node", "osm_id": -5, "name": "Nagarekawa Bar Street",
     "lat": 34.3905, "lng": 132.4623, "category": "Food & Drink",
     "suggested_subcat": "Drinks", "tags_json": "{}"},
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch OSM POIs into the local DB.")
    parser.add_argument("--lat", type=float, default=config.AREA_CENTER_LAT)
    parser.add_argument("--lng", type=float, default=config.AREA_CENTER_LNG)
    parser.add_argument("--radius", type=int, default=config.POI_RADIUS_M)
    args = parser.parse_args()

    init_db()
    print(f"Querying Overpass around ({args.lat}, {args.lng}) r={args.radius}m ...")
    try:
        pois = fetch_from_overpass(args.lat, args.lng, args.radius)
        if not pois:
            print("No POIs returned; inserting bundled sample instead.")
            pois = _SAMPLE_POIS
    except Exception as exc:  # network/timeout/HTTP errors -> fall back
        print(f"Overpass request failed ({exc}); inserting bundled sample instead.")
        pois = _SAMPLE_POIS

    written = upsert_pois(pois)
    print(f"Done. Upserted {written} POIs.")


if __name__ == "__main__":
    main()
