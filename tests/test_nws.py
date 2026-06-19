import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from aegis.ingest.nws import (
    NWS_ACTIVE_ALERTS,
    _centroid,
    parse_nws_feature,
    parse_nws_feed,
)
from aegis.schema import HazardType

FIXTURE = Path(__file__).parent / "fixtures" / "nws_sample.geojson"


def _load() -> dict:
    return json.loads(FIXTURE.read_text())


def test_parse_feature_maps_severe_weather_fields():
    ev = parse_nws_feature(_load()["features"][0])
    assert ev.source == "nws"
    assert ev.source_id == "urn:oid:2.49.0.1.840.0.aaa"
    assert ev.hazard_type is HazardType.SEVERE_WEATHER
    assert ev.magnitude == 3.0  # "Severe"


def test_polygon_reduces_to_centroid():
    # Unit square [-100,-99] x [40,41] -> center (lon -99.5, lat 40.5).
    ev = parse_nws_feature(_load()["features"][0])
    assert ev.longitude == pytest.approx(-99.5)
    assert ev.latitude == pytest.approx(40.5)


def test_flood_events_routed_to_flood_type():
    ev = parse_nws_feature(_load()["features"][1])
    assert ev.hazard_type is HazardType.FLOOD
    assert ev.magnitude == 2.0  # "Moderate"


def test_point_geometry_and_extreme_severity():
    ev = parse_nws_feature(_load()["features"][2])
    assert (ev.latitude, ev.longitude) == (35.0, -120.0)
    assert ev.magnitude == 4.0  # "Extreme"


def test_onset_parsed_to_utc():
    ev = parse_nws_feature(_load()["features"][0])
    # 14:00 at -05:00 == 19:00 UTC.
    assert ev.observed_at == datetime(2026, 6, 8, 19, 0, tzinfo=UTC)
    assert ev.observed_at.tzinfo is not None


def test_falls_back_to_sent_when_no_onset():
    # Third alert has only "sent" (18:30 -05:00 -> 23:30 UTC).
    ev = parse_nws_feature(_load()["features"][2])
    assert ev.observed_at == datetime(2026, 6, 8, 23, 30, tzinfo=UTC)


def test_feed_drops_geometryless_alerts():
    events = parse_nws_feed(_load())
    # 4 alerts in; the zone-only (null geometry) one is dropped.
    assert len(events) == 3
    assert "urn:oid:2.49.0.1.840.0.ddd" not in {e.source_id for e in events}


def test_geometryless_feature_raises():
    with pytest.raises(ValueError):
        parse_nws_feature(_load()["features"][3])


def test_unknown_severity_yields_no_magnitude():
    feature = _load()["features"][0]
    feature["properties"]["severity"] = "Unknown"
    assert parse_nws_feature(feature).magnitude is None


def test_centroid_degenerate_ring_uses_vertex_mean():
    # A collinear ring has zero signed area -> fall back to the mean vertex.
    ring = [[0.0, 0.0], [2.0, 2.0], [4.0, 4.0], [0.0, 0.0]]
    geometry = {"type": "Polygon", "coordinates": [ring]}
    lat, lon = _centroid(geometry)
    assert lon == pytest.approx(1.5)
    assert lat == pytest.approx(1.5)


def test_dedup_key_uses_source_and_id():
    ev = parse_nws_feature(_load()["features"][0])
    assert ev.dedup_key == "nws:urn:oid:2.49.0.1.840.0.aaa"


def test_active_alerts_url_is_api_weather_gov():
    assert NWS_ACTIVE_ALERTS.startswith("https://api.weather.gov/")
