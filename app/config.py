"""Configuration: venue, POI fetch area, map defaults, category taxonomy.

Everything an organizer is likely to tweak for their own event lives here.
"""

# --- Venue / POI fetch area -------------------------------------------------
# Default: central Hiroshima (Kamiyacho / Hatchobori downtown area).
# Change these to your actual venue, then re-run `python -m app.poi`.
VENUE_LAT = 34.3917
VENUE_LNG = 132.4595
# Radius (meters) around the venue to pull POIs from OpenStreetMap.
POI_RADIUS_M = 1500

# --- Map defaults (sent to the frontend via /api/meta) ----------------------
MAP_CENTER = [VENUE_LAT, VENUE_LNG]
MAP_ZOOM = 15

# --- Category taxonomy ------------------------------------------------------
# Top-level categories drive marker colors and the filter chips.
# Subcategories are optional; only Food & Drink defines them.
CATEGORIES = {
    "Food & Drink": {
        "color": "#e8590c",
        "emoji": "🍽",
        "subcategories": ["Lunch", "Dinner", "Drinks", "Sweets"],
    },
    "Sightseeing": {
        "color": "#2f9e44",
        "emoji": "⛩",
        "subcategories": [],
    },
    "Other": {
        "color": "#5c7cfa",
        "emoji": "📍",
        "subcategories": [],
    },
}

DEFAULT_CATEGORY = "Other"


def subcategories_for(category: str) -> list[str]:
    """Return the allowed subcategories for a top-level category."""
    return CATEGORIES.get(category, {}).get("subcategories", [])


def is_valid_category(category: str) -> bool:
    return category in CATEGORIES


def is_valid_subcategory(category: str, subcategory: str) -> bool:
    return subcategory in subcategories_for(category)
