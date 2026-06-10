import json
from datetime import UTC, datetime
from pathlib import Path

from aegis.ingest.usgs import FEEDS, parse_usgs_feature, parse_usgs_feed
from aegis.schema import HazardType

FIXTURE = Path(__file__).parent / "fixtures" / "usgs_sample.geojson"


def _load() -> dict:
    return json.loads(FIXTURE.read_text())


def test_parse_single_feature_maps_fields():
    feature = _load()["features"][0]
    ev = parse_usgs_feature(feature)
    assert ev.source == "usgs"
    assert ev.source_id == "us6000abcd"
    assert ev.hazard_type is HazardType.EARTHQUAKE
    assert ev.magnitude == 6.2


def test_coordinates_are_lon_lat_order():
    # GeoJSON is [lon, lat]; we must not flip them.
    ev = parse_usgs_feature(_load()["features"][0])
    assert ev.longitude == -122.45
    assert ev.latitude == 37.77


def test_time_is_parsed_from_epoch_millis_utc():
    ev = parse_usgs_feature(_load()["features"][0])
    assert ev.observed_at == datetime.fromtimestamp(1717459200000 / 1000, tz=UTC)
    assert ev.observed_at.tzinfo is not None


def test_feed_skips_malformed_features():
    events = parse_usgs_feed(_load())
    # 3 features in, but one has null geometry -> dropped.
    assert len(events) == 2
    assert {e.source_id for e in events} == {"us6000abcd", "ak0231xyz"}


def test_dedup_key_uses_source_and_id():
    ev = parse_usgs_feature(_load()["features"][1])
    assert ev.dedup_key == "usgs:ak0231xyz"


def test_known_feeds_are_full_urls():
    assert FEEDS["significant_day"].startswith("https://earthquake.usgs.gov/")
    assert FEEDS["m45_day"].endswith("4.5_day.geojson")
