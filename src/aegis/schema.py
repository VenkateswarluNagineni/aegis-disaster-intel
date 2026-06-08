"""Canonical hazard-event schema.

Every source (FIRMS fires, USGS quakes, NOAA alerts) is normalized into ``HazardEvent``
so enrichment, scoring, and RAG stay source-agnostic. ``dedup_key`` is the basis for
change-detection: two ingests producing the same key are the same real-world event.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class HazardType(StrEnum):
    WILDFIRE = "wildfire"
    EARTHQUAKE = "earthquake"
    SEVERE_WEATHER = "severe_weather"
    FLOOD = "flood"
    OTHER = "other"


class HazardEvent(BaseModel):
    """A normalized hazard observation."""

    source: str = Field(description="Originating feed, e.g. 'firms', 'usgs', 'noaa'")
    source_id: str = Field(description="Stable id within the source feed")
    hazard_type: HazardType
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    observed_at: datetime
    magnitude: float | None = Field(default=None, description="Quake magnitude / fire FRP / etc.")
    raw: dict = Field(default_factory=dict, description="Original source payload")

    @property
    def dedup_key(self) -> str:
        """Stable identity for change-detection across re-ingests."""
        return f"{self.source}:{self.source_id}"
