"""Geospatial primitives for hazard risk scoring.

Great-circle distance + a distance-decay proximity risk score. Pure-numpy so the core
risk math has no heavy geo dependencies (GeoPandas/H3 arrive in later phases for the
polygon/indexing work).
"""

from __future__ import annotations

import math

EARTH_RADIUS_KM = 6371.0088


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two (lat, lon) points in kilometres."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


def proximity_risk(distance_km: float, radius_km: float = 50.0) -> float:
    """Distance-decay risk in [0, 1].

    1.0 at the hazard, decaying exponentially with distance. ``radius_km`` is the
    characteristic scale at which risk falls to ~37% (one e-folding). Negative distances
    are treated as 0 (at the event).
    """
    if radius_km <= 0:
        raise ValueError("radius_km must be positive")
    d = max(distance_km, 0.0)
    return math.exp(-d / radius_km)


def asset_risk(
    asset: tuple[float, float],
    hazard: tuple[float, float],
    radius_km: float = 50.0,
) -> float:
    """Convenience: proximity risk of a hazard to an asset, both as (lat, lon)."""
    return proximity_risk(haversine_km(*asset, *hazard), radius_km=radius_km)
