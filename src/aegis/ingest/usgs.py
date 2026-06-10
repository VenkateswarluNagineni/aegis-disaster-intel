"""USGS earthquake feed ingestor.

USGS publishes earthquakes as GeoJSON
(https://earthquake.usgs.gov/earthquakes/feed/v1.0/geojson.php). The parsing functions
are pure (dict in, ``HazardEvent`` out) so they're tested against a recorded fixture with
no network; ``fetch_usgs`` is the thin live wrapper around them.

Two GeoJSON gotchas this module gets right:
- coordinates are ``[longitude, latitude, depth]`` (lon first — easy to flip),
- ``properties.time`` is epoch **milliseconds** in UTC.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import httpx

from aegis.schema import HazardEvent, HazardType

# USGS summary feeds keyed by a friendly name -> feed slug under this base.
_FEED_BASE = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary"
FEEDS = {
    "significant_day": f"{_FEED_BASE}/significant_day.geojson",
    "significant_week": f"{_FEED_BASE}/significant_week.geojson",
    "all_day": f"{_FEED_BASE}/all_day.geojson",
    "m45_day": f"{_FEED_BASE}/4.5_day.geojson",
}


def parse_usgs_feature(feature: dict[str, Any]) -> HazardEvent:
    """Normalize a single USGS GeoJSON feature into a ``HazardEvent``."""
    props = feature.get("properties") or {}
    coords = (feature.get("geometry") or {}).get("coordinates") or [None, None]
    longitude, latitude = coords[0], coords[1]

    time_ms = props.get("time")
    observed_at = (
        datetime.fromtimestamp(time_ms / 1000, tz=UTC)
        if time_ms is not None
        else datetime.now(tz=UTC)
    )

    return HazardEvent(
        source="usgs",
        source_id=str(feature["id"]),
        hazard_type=HazardType.EARTHQUAKE,
        latitude=float(latitude),
        longitude=float(longitude),
        observed_at=observed_at,
        magnitude=props.get("mag"),
        raw=feature,
    )


def parse_usgs_feed(geojson: dict[str, Any]) -> list[HazardEvent]:
    """Parse a full USGS FeatureCollection, skipping malformed features.

    Resilient by design: one bad feature (missing geometry/coords) shouldn't sink the whole
    batch, so unparseable features are dropped rather than raising.
    """
    events: list[HazardEvent] = []
    for feature in geojson.get("features", []):
        try:
            events.append(parse_usgs_feature(feature))
        except (KeyError, TypeError, ValueError):
            continue
    return events


def fetch_usgs(feed: str = "significant_day", *, timeout: float = 10.0) -> list[HazardEvent]:
    """Fetch a named USGS feed live and return normalized ``HazardEvent``s.

    ``feed`` may be a key in :data:`FEEDS` or a full GeoJSON URL.
    """
    url = FEEDS.get(feed, feed)
    response = httpx.get(url, timeout=timeout)
    response.raise_for_status()
    return parse_usgs_feed(response.json())
