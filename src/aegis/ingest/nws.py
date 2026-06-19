"""NOAA / NWS severe-weather alerts ingestor.

The U.S. National Weather Service publishes active alerts as GeoJSON from
https://api.weather.gov/alerts/active. As with USGS and FIRMS the parsing functions are
pure (dict in, ``HazardEvent`` out) and tested against a recorded fixture; ``fetch_nws``
is the thin live wrapper.

Three NWS specifics this module gets right:
- the API **requires a descriptive ``User-Agent``** (it rejects requests without one), so
  ``fetch_nws`` always sends one,
- many alerts carry **no geometry** -- they reference affected NWS zones by URI rather than
  a polygon. Those can't be placed on the map, so (like a USGS feature with null geometry)
  they're dropped during feed parsing rather than guessed at,
- a polygon alert is reduced to a single representative point via an **area-weighted
  (shoelace) centroid**, with a vertex-mean fallback for degenerate rings.

The categorical ``severity`` (Extreme/Severe/Moderate/Minor) is mapped to a numeric
magnitude so weather alerts sort alongside quake magnitude / fire FRP downstream; flood
events are routed to :attr:`HazardType.FLOOD`, everything else to severe weather.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import httpx

from aegis.schema import HazardEvent, HazardType

NWS_ACTIVE_ALERTS = "https://api.weather.gov/alerts/active"

# NWS asks every client to identify itself; a bare request is refused.
_DEFAULT_USER_AGENT = "aegis-disaster-intel (https://github.com/VenkateswarluNagineni)"

# Categorical CAP severity -> numeric magnitude (Unknown -> None, like a missing reading).
_SEVERITY_SCALE: dict[str, float] = {
    "extreme": 4.0,
    "severe": 3.0,
    "moderate": 2.0,
    "minor": 1.0,
}

_FLOOD_KEYWORDS = ("flood", "flash flood", "coastal flood", "hydrologic")


def _classify(event_name: str) -> HazardType:
    """Route flood-family alerts to FLOOD, everything else to severe weather."""
    name = (event_name or "").lower()
    if any(kw in name for kw in _FLOOD_KEYWORDS):
        return HazardType.FLOOD
    return HazardType.SEVERE_WEATHER


def _severity_to_magnitude(severity: str | None) -> float | None:
    return _SEVERITY_SCALE.get((severity or "").lower())


def _parse_time(props: dict[str, Any]) -> datetime:
    """First present, parseable timestamp among onset/effective/sent, as UTC."""
    for field in ("onset", "effective", "sent"):
        value = props.get(field)
        if value:
            try:
                return datetime.fromisoformat(value).astimezone(UTC)
            except ValueError:
                continue
    return datetime.now(tz=UTC)


def _ring_points(coords: list) -> list[tuple[float, float]]:
    """Flatten a GeoJSON Polygon/MultiPolygon coordinate tree to (lon, lat) vertices."""
    points: list[tuple[float, float]] = []

    def _walk(node: Any) -> None:
        # A coordinate pair is [number, number]; anything else is a nested list to recurse.
        if (
            isinstance(node, (list, tuple))
            and len(node) >= 2
            and all(isinstance(v, (int, float)) for v in node[:2])
        ):
            points.append((float(node[0]), float(node[1])))
            return
        if isinstance(node, (list, tuple)):
            for child in node:
                _walk(child)

    _walk(coords)
    return points


def _centroid(geometry: dict[str, Any] | None) -> tuple[float, float] | None:
    """Representative (lat, lon) point for a polygon geometry, or ``None`` if unplaceable.

    Uses the area-weighted shoelace centroid of the first ring; falls back to the mean of
    the vertices when the ring is degenerate (zero signed area, e.g. a line or point).
    """
    if not geometry:
        return None
    geom_type = geometry.get("type")
    coords = geometry.get("coordinates")
    if coords is None:
        return None

    if geom_type == "Point":
        lon, lat = float(coords[0]), float(coords[1])
        return (lat, lon)

    # First exterior ring for a Polygon; first polygon's first ring for a MultiPolygon.
    ring = coords[0] if geom_type == "Polygon" else coords[0][0]
    pts = _ring_points(ring)
    if not pts:
        return None

    area = cx = cy = 0.0
    for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1], strict=True):
        cross = x0 * y1 - x1 * y0
        area += cross
        cx += (x0 + x1) * cross
        cy += (y0 + y1) * cross
    area *= 0.5

    if abs(area) < 1e-12:  # degenerate ring -> plain vertex mean
        lon = sum(p[0] for p in pts) / len(pts)
        lat = sum(p[1] for p in pts) / len(pts)
        return (lat, lon)

    lon = cx / (6.0 * area)
    lat = cy / (6.0 * area)
    return (lat, lon)


def parse_nws_feature(feature: dict[str, Any]) -> HazardEvent:
    """Normalize a single NWS alert feature into a ``HazardEvent``.

    Raises ``ValueError`` if the alert has no usable geometry (no point to place it).
    """
    props = feature.get("properties") or {}
    point = _centroid(feature.get("geometry"))
    if point is None:
        raise ValueError("alert has no geometry to place")
    lat, lon = point

    return HazardEvent(
        source="nws",
        source_id=str(props.get("id") or feature["id"]),
        hazard_type=_classify(props.get("event", "")),
        latitude=lat,
        longitude=lon,
        observed_at=_parse_time(props),
        magnitude=_severity_to_magnitude(props.get("severity")),
        raw=feature,
    )


def parse_nws_feed(geojson: dict[str, Any]) -> list[HazardEvent]:
    """Parse a full NWS alerts FeatureCollection, dropping unplaceable/malformed alerts."""
    events: list[HazardEvent] = []
    for feature in geojson.get("features", []):
        try:
            events.append(parse_nws_feature(feature))
        except (KeyError, TypeError, ValueError):
            continue
    return events


def fetch_nws(
    *,
    area: str | None = None,
    user_agent: str = _DEFAULT_USER_AGENT,
    timeout: float = 10.0,
) -> list[HazardEvent]:
    """Fetch live active NWS alerts and return normalized ``HazardEvent``s.

    ``area`` optionally filters to a two-letter state/marine code (e.g. ``"CA"``). The NWS
    API requires a descriptive ``User-Agent`` header, which is always sent.
    """
    params = {"area": area} if area else None
    headers = {"User-Agent": user_agent, "Accept": "application/geo+json"}
    response = httpx.get(NWS_ACTIVE_ALERTS, params=params, headers=headers, timeout=timeout)
    response.raise_for_status()
    return parse_nws_feed(response.json())
