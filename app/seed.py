"""Insert a few demo recommendations so a fresh install looks alive.

    uv run python -m app.seed
"""

from __future__ import annotations

from .db import init_db
from .repository import create_post

_DEMO_POSTS = [
    {
        "spot_name": "Okonomimura",
        "lat": 34.3919, "lng": 132.4607,
        "category": "Food & Drink", "subcategory": "Dinner",
        "author": "Kenji", "tags": "okonomiyaki,local,must-try",
        "comment": "Three floors of Hiroshima-style okonomiyaki. Go hungry!",
    },
    {
        "spot_name": "Hondori Cafe",
        "lat": 34.3922, "lng": 132.4575,
        "category": "Food & Drink", "subcategory": "Sweets",
        "author": "Aoi", "tags": "coffee,parfait,quiet",
        "comment": "Great spot for an afternoon coffee between sessions.",
    },
    {
        "spot_name": "Nagarekawa Bar Street",
        "lat": 34.3905, "lng": 132.4623,
        "category": "Food & Drink", "subcategory": "Drinks",
        "author": "Sam", "tags": "craft-beer,nightlife",
        "comment": "Lots of small bars — perfect for the post-conference meetup.",
    },
    {
        "spot_name": "Hiroshima Peace Memorial (Genbaku Dome)",
        "lat": 34.3955, "lng": 132.4536,
        "category": "Sightseeing", "subcategory": None,
        "author": "Maria", "tags": "unesco,history,a-must",
        "comment": "A moving World Heritage site, 10 min walk from downtown.",
    },
    {
        "spot_name": "Shukkeien Garden",
        "lat": 34.3989, "lng": 132.4669,
        "category": "Sightseeing", "subcategory": None,
        "author": "Taro", "tags": "garden,relax,photo",
        "comment": "Beautiful traditional garden, calm break from the city.",
    },
]


def main() -> None:
    init_db()
    for p in _DEMO_POSTS:
        create_post(p)
    print(f"Seeded {len(_DEMO_POSTS)} demo recommendations.")


if __name__ == "__main__":
    main()
