"""Pydantic request/response models and validation."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator, model_validator

from . import config


class PostIn(BaseModel):
    """Incoming recommendation from a participant."""

    poi_id: int | None = None
    spot_name: str = Field(..., min_length=1, max_length=120)
    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)
    category: str
    subcategory: str | None = Field(default=None, max_length=40)
    author: str = Field(..., min_length=1, max_length=40)
    tags: str = Field(default="", max_length=160)
    comment: str = Field(default="", max_length=1000)

    @field_validator("spot_name", "author", "tags", "comment", mode="before")
    @classmethod
    def _strip(cls, v):
        return v.strip() if isinstance(v, str) else v

    @field_validator("category")
    @classmethod
    def _check_category(cls, v: str) -> str:
        if not config.is_valid_category(v):
            allowed = ", ".join(config.CATEGORIES)
            raise ValueError(f"category must be one of: {allowed}")
        return v

    @model_validator(mode="after")
    def _check_subcategory(self):
        sub = (self.subcategory or "").strip()
        if not sub:
            self.subcategory = None
            return self
        if not config.is_valid_subcategory(self.category, sub):
            allowed = ", ".join(config.subcategories_for(self.category)) or "(none)"
            raise ValueError(
                f"subcategory for '{self.category}' must be one of: {allowed}"
            )
        self.subcategory = sub
        return self


class PostOut(BaseModel):
    """A stored recommendation returned to the client."""

    id: int
    poi_id: int | None
    spot_name: str
    lat: float
    lng: float
    category: str
    subcategory: str | None
    author: str
    tags: list[str]
    comment: str
    created_at: str


class PoiOut(BaseModel):
    """A candidate place sourced from OpenStreetMap."""

    id: int
    osm_type: str
    osm_id: int
    name: str
    lat: float
    lng: float
    category: str
    suggested_subcat: str | None
