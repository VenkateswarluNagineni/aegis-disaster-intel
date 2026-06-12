"""NASA FIRMS active-fire ingestor.

FIRMS (Fire Information for Resource Management System) publishes active fire/thermal
anomaly detections as **CSV** (the area API at https://firms.modaps.eosdis.nasa.gov/api/),
not GeoJSON -- so this ingestor parses CSV rows instead of JSON features, but follows the
same pure-parse + fixture-tested pattern as the USGS ingestor.

Two FIRMS specifics handled here:
- there is no stable per-detection id, so we derive a deterministic ``source_id`` by hashing
  satellite + acquisition timestamp + rounded coordinates (stable across re-ingests),
- ``acq_date`` (YYYY-MM-DD) and ``acq_time`` (UTC HHMM, sometimes un-padded like "48") are
  combined into one tz-aware UTC timestamp; FRP (fire radiative power) is used as magnitude.
"""

from __future__ import annotations

import csv
import hashlib
import io
from datetime import UTC, datetime
from typing import Any

import httpx

from aegis.schema import HazardEvent, HazardType

FIRMS_AREA_API = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"


def _firms_source_id(row: dict[str, Any], observed_at: datetime, lat: float, lon: float) -> str:
    """Deterministic id for a detection: same detection -> same id (basis for dedup)."""
    sat = row.get("satellite", row.get("instrument", "?"))
    key = f"{sat}|{observed_at.isoformat()}|{lat:.4f}|{lon:.4f}"
    return hashlib.md5(key.encode()).hexdigest()[:12]  # noqa: S324 - non-security id hash


def parse_firms_row(row: dict[str, Any]) -> HazardEvent:
    """Normalize one FIRMS CSV row into a wildfire ``HazardEvent``."""
    lat = float(row["latitude"])
    lon = float(row["longitude"])

    time_str = str(row["acq_time"]).strip().zfill(4)
    hh, mm = int(time_str[:2]), int(time_str[2:])
    y, mo, d = (int(p) for p in str(row["acq_date"]).split("-"))
    observed_at = datetime(y, mo, d, hh, mm, tzinfo=UTC)

    frp = row.get("frp")
    return HazardEvent(
        source="firms",
        source_id=_firms_source_id(row, observed_at, lat, lon),
        hazard_type=HazardType.WILDFIRE,
        latitude=lat,
        longitude=lon,
        observed_at=observed_at,
        magnitude=float(frp) if frp not in (None, "") else None,
        raw=dict(row),
    )


def parse_firms_csv(text: str) -> list[HazardEvent]:
    """Parse a FIRMS CSV payload, skipping malformed rows (resilient by design)."""
    events: list[HazardEvent] = []
    for row in csv.DictReader(io.StringIO(text)):
        try:
            events.append(parse_firms_row(row))
        except (KeyError, TypeError, ValueError):
            continue
    return events


def fetch_firms(
    map_key: str,
    *,
    source: str = "VIIRS_SNPP_NRT",
    area: str = "world",
    day_range: int = 1,
    timeout: float = 20.0,
) -> list[HazardEvent]:
    """Fetch live FIRMS detections (requires a free FIRMS ``map_key``).

    See https://firms.modaps.eosdis.nasa.gov/api/area/ for source codes and area syntax.
    """
    url = f"{FIRMS_AREA_API}/{map_key}/{source}/{area}/{day_range}"
    response = httpx.get(url, timeout=timeout)
    response.raise_for_status()
    return parse_firms_csv(response.text)
