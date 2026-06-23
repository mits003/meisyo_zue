"""Data access for pois and posts (raw SQL over sqlite3)."""

from __future__ import annotations

from datetime import datetime, timezone

from .db import connect


# --- tags helpers -----------------------------------------------------------
def _tags_to_list(raw: str) -> list[str]:
    return [t.strip() for t in (raw or "").split(",") if t.strip()]


def _normalize_tags(raw: str) -> str:
    """Store tags as a clean comma-separated string."""
    return ",".join(_tags_to_list(raw))


# --- posts ------------------------------------------------------------------
def _row_to_post(row) -> dict:
    d = dict(row)
    d["tags"] = _tags_to_list(d.get("tags", ""))
    return d


def list_posts(
    category: str | None = None,
    subcategory: str | None = None,
    tag: str | None = None,
    q: str | None = None,
) -> list[dict]:
    sql = "SELECT * FROM posts WHERE 1=1"
    params: list = []
    if category:
        sql += " AND category = ?"
        params.append(category)
    if subcategory:
        sql += " AND subcategory = ?"
        params.append(subcategory)
    if tag:
        sql += " AND (',' || lower(tags) || ',') LIKE ?"
        params.append(f"%,{tag.strip().lower()},%")
    if q:
        like = f"%{q.strip().lower()}%"
        sql += (
            " AND (lower(spot_name) LIKE ? OR lower(comment) LIKE ?"
            " OR lower(author) LIKE ? OR lower(tags) LIKE ?)"
        )
        params.extend([like, like, like, like])
    sql += " ORDER BY created_at DESC, id DESC"

    with connect() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [_row_to_post(r) for r in rows]


def create_post(data: dict) -> dict:
    created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO posts
                (poi_id, spot_name, lat, lng, category, subcategory,
                 author, tags, comment, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data.get("poi_id"),
                data["spot_name"],
                data["lat"],
                data["lng"],
                data["category"],
                data.get("subcategory"),
                data["author"],
                _normalize_tags(data.get("tags", "")),
                data.get("comment", ""),
                created_at,
            ),
        )
        conn.commit()
        new_id = cur.lastrowid
        row = conn.execute("SELECT * FROM posts WHERE id = ?", (new_id,)).fetchone()
    return _row_to_post(row)


def get_post(post_id: int) -> dict | None:
    with connect() as conn:
        row = conn.execute("SELECT * FROM posts WHERE id = ?", (post_id,)).fetchone()
    return _row_to_post(row) if row else None


# --- pois -------------------------------------------------------------------
def list_pois(q: str | None = None, bbox: str | None = None, limit: int = 200) -> list[dict]:
    sql = "SELECT * FROM pois WHERE 1=1"
    params: list = []
    if q:
        sql += " AND lower(name) LIKE ?"
        params.append(f"%{q.strip().lower()}%")
    if bbox:
        try:
            min_lng, min_lat, max_lng, max_lat = (float(x) for x in bbox.split(","))
            sql += " AND lat BETWEEN ? AND ? AND lng BETWEEN ? AND ?"
            params.extend([min_lat, max_lat, min_lng, max_lng])
        except ValueError:
            pass  # ignore malformed bbox
    sql += " ORDER BY name LIMIT ?"
    params.append(limit)

    with connect() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def count_pois() -> int:
    with connect() as conn:
        return conn.execute("SELECT COUNT(*) FROM pois").fetchone()[0]


def upsert_pois(items: list[dict]) -> int:
    """Insert or update POIs keyed by (osm_type, osm_id). Returns count written."""
    with connect() as conn:
        conn.executemany(
            """
            INSERT INTO pois (osm_type, osm_id, name, lat, lng, category,
                              suggested_subcat, tags_json)
            VALUES (:osm_type, :osm_id, :name, :lat, :lng, :category,
                    :suggested_subcat, :tags_json)
            ON CONFLICT(osm_type, osm_id) DO UPDATE SET
                name=excluded.name,
                lat=excluded.lat,
                lng=excluded.lng,
                category=excluded.category,
                suggested_subcat=excluded.suggested_subcat,
                tags_json=excluded.tags_json
            """,
            items,
        )
        conn.commit()
    return len(items)
