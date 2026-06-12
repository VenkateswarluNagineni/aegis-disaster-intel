from datetime import UTC, datetime
from pathlib import Path

from aegis.ingest.firms import parse_firms_csv, parse_firms_row
from aegis.schema import HazardType

FIXTURE = Path(__file__).parent / "fixtures" / "firms_sample.csv"


def _rows() -> list[dict]:
    import csv

    return list(csv.DictReader(FIXTURE.read_text().splitlines()))


def test_parse_row_maps_wildfire_fields():
    ev = parse_firms_row(_rows()[0])
    assert ev.source == "firms"
    assert ev.hazard_type is HazardType.WILDFIRE
    assert ev.latitude == 37.4521
    assert ev.longitude == -120.1234
    assert ev.magnitude == 12.4  # FRP used as magnitude
    assert ev.observed_at == datetime(2026, 6, 8, 10, 12, tzinfo=UTC)


def test_acq_time_is_zero_padded():
    # "48" should parse as 00:48 UTC, not 48:00.
    ev = parse_firms_row(_rows()[1])
    assert ev.observed_at == datetime(2026, 6, 8, 0, 48, tzinfo=UTC)


def test_missing_frp_yields_no_magnitude():
    ev = parse_firms_row(_rows()[3])
    assert ev.magnitude is None


def test_source_id_is_deterministic():
    row = _rows()[0]
    assert parse_firms_row(row).source_id == parse_firms_row(row).source_id
    assert parse_firms_row(row).dedup_key.startswith("firms:")


def test_csv_skips_malformed_rows():
    events = parse_firms_csv(FIXTURE.read_text())
    # 4 data rows, one has a non-numeric latitude -> dropped.
    assert len(events) == 3
    assert all(e.hazard_type is HazardType.WILDFIRE for e in events)
