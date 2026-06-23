"""FastAPI application: REST API + static frontend."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from . import config, repository
from .db import init_db
from .models import PoiOut, PostIn, PostOut

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

app = FastAPI(title="FOSS4G Hiroshima Spot Map")

# Permissive CORS for local development / demo use.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup() -> None:
    init_db()


@app.get("/api/meta")
def get_meta() -> dict:
    """Category taxonomy + map defaults for the frontend to render itself."""
    return {
        "categories": config.CATEGORIES,
        "map": {"center": config.MAP_CENTER, "zoom": config.MAP_ZOOM},
    }


@app.get("/api/pois", response_model=list[PoiOut])
def get_pois(
    q: str | None = Query(default=None),
    bbox: str | None = Query(default=None, description="min_lng,min_lat,max_lng,max_lat"),
) -> list[dict]:
    return repository.list_pois(q=q, bbox=bbox)


@app.get("/api/posts", response_model=list[PostOut])
def get_posts(
    category: str | None = Query(default=None),
    subcategory: str | None = Query(default=None),
    tag: str | None = Query(default=None),
    q: str | None = Query(default=None),
) -> list[dict]:
    return repository.list_posts(category=category, subcategory=subcategory, tag=tag, q=q)


@app.post("/api/posts", response_model=PostOut, status_code=201)
def create_post(payload: PostIn) -> dict:
    return repository.create_post(payload.model_dump())


@app.get("/api/posts/{post_id}", response_model=PostOut)
def get_single_post(post_id: int) -> dict:
    post = repository.get_post(post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="post not found")
    return post


# Serve the static frontend at the root. Mounted LAST so /api/* routes win.
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
