# Phase 2 — NASA FIRMS wildfire ingestor (design notes)

## What landed
- `aegis/ingest/firms.py`:
  - `parse_firms_row` / `parse_firms_csv` — FIRMS **CSV** rows → wildfire `HazardEvent`s,
    skipping malformed rows.
  - `fetch_firms(map_key, ...)` — live area-API wrapper (FIRMS needs a free map key).
- `tests/fixtures/firms_sample.csv` — a 4-row sample (3 valid, 1 with a bad latitude).
- 5 tests; ruff + pytest green, no network.

## Decisions & trade-offs
- **CSV, not GeoJSON.** Unlike USGS, FIRMS serves CSV, so this ingestor uses
  `csv.DictReader` rather than JSON parsing — but keeps the exact same shape as the USGS
  ingestor (pure parse functions + fixture, thin live `fetch_*` wrapper). Consistency across
  sources is what makes the change-detection layer (Phase 4) source-agnostic.
- **Derived deterministic `source_id`.** FIRMS detections have no stable id, so dedup would
  be impossible as-is. We hash satellite + UTC timestamp + rounded coordinates into a stable
  id, so re-ingesting the same detection yields the same `dedup_key` (`firms:<hash>`). md5 is
  used purely as a content fingerprint, not for security.
- **Timestamp assembly + zero-padding.** `acq_date` (YYYY-MM-DD) and `acq_time` (UTC HHMM)
  are combined into one tz-aware UTC datetime. FIRMS sometimes drops the leading zero on
  `acq_time` (e.g. `48` meaning 00:48), so the field is zero-padded to 4 digits before
  parsing — a test pins this, since getting it wrong shifts a fire's time by hours.
- **FRP as magnitude.** Fire Radiative Power is the natural intensity signal, mapped to the
  schema's `magnitude` (empty FRP → `None`), so severity scoring (Phase 9) can rank fires.

## Next
Phase 3: the NOAA / NWS severe-weather alerts ingestor (same pattern), completing the three
sources before the change-detection + dedup store in Phase 4 consumes them via `dedup_key`.
