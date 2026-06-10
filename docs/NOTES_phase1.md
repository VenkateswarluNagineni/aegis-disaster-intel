# Phase 1 — USGS earthquake ingestor (design notes)

## What landed
- `aegis/ingest/usgs.py`:
  - `parse_usgs_feature(feature)` — one GeoJSON feature → `HazardEvent`.
  - `parse_usgs_feed(geojson)` — a full FeatureCollection → list, **skipping malformed
    features** instead of failing the batch.
  - `fetch_usgs(feed)` — thin live wrapper (httpx) over the parsers; `FEEDS` maps friendly
    names (`significant_day`, `m45_day`, …) to URLs, or you can pass a full URL.
- `tests/fixtures/usgs_sample.geojson` — a recorded 3-feature sample (2 valid, 1 broken).
- 6 tests; ruff + pytest green, **no network in CI**.

## Decisions & trade-offs
- **Pure parse functions, separate from fetch.** All the logic (and the gotchas) live in
  dict-in/event-out functions tested against a fixture. `fetch_usgs` is a trivial wrapper.
  This is what makes the ingestor testable offline and deterministic.
- **GeoJSON coordinate order.** Coordinates are `[longitude, latitude, depth]` — lon
  first. A test pins this so a future refactor can't silently swap lat/lon (a bug that
  would put every quake in the wrong hemisphere).
- **Epoch-millisecond UTC time.** USGS `properties.time` is ms since epoch; converted to
  tz-aware UTC, matching the `HazardEvent` schema's UTC assumption.
- **Resilient batch parsing.** Real feeds occasionally contain features with null geometry.
  One bad record shouldn't drop a whole sweep, so `parse_usgs_feed` skips unparseable
  features (the fixture includes one to prove it).
- **`.gitignore` exception.** The repo ignores `*.geojson` (raw data shouldn't be committed),
  but the tiny test fixture is whitelisted with `!tests/fixtures/*.geojson`.

## Next
Phase 2: the NASA FIRMS wildfire ingestor (same pure-parse + fixture pattern), then NOAA
alerts in Phase 3 — after which Phase 4's change-detection/dedup store consumes all three
via each event's `dedup_key`.
