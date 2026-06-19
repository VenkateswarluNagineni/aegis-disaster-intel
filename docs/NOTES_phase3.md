# Phase 3 — NOAA / NWS alerts ingestor (design notes)

## What landed
- `aegis/ingest/nws.py`:
  - `parse_nws_feature` / `parse_nws_feed` — pure GeoJSON-in, `HazardEvent`-out, matching
    the USGS/FIRMS shape so the change-detection layer stays source-agnostic.
  - `_centroid` — area-weighted (shoelace) polygon centroid with a vertex-mean fallback.
  - `fetch_nws` — the thin live wrapper around https://api.weather.gov/alerts/active.
- `tests/fixtures/nws_sample.geojson` (4 alerts: polygon severe-weather, polygon flood,
  point tornado, and a zone-only null-geometry alert) + `tests/test_nws.py` (12).
  ruff + pytest green; the third source now feeds the same canonical schema.

## Decisions & trade-offs
- **Categorical severity → numeric magnitude.** CAP severity is `Extreme/Severe/Moderate/
  Minor/Unknown`. Mapping the first four to `4..1` (and `Unknown → None`, like a missing
  reading) lets weather alerts sort and threshold alongside quake magnitude and fire FRP
  without a special case downstream. `magnitude` stays nullable, so "Unknown" is honestly
  absent rather than silently a zero.
- **Polygons reduced to one representative point.** `HazardEvent` is point-based (it's what
  proximity/H3 scoring in Phases 8–9 consume), so each alert polygon collapses to its
  **area-weighted centroid** via the shoelace formula — correct for non-convex rings, unlike
  a naive vertex average. Degenerate rings (zero signed area: a line or repeated point) fall
  back to the vertex mean instead of dividing by zero. The full polygon is preserved in
  `raw` for later spatial work.
- **Zone-only alerts are dropped, not guessed.** A large share of NWS alerts carry *no*
  geometry — they reference affected NWS zones by URI. Inventing a centroid for those would
  fabricate a location, so (exactly like a USGS feature with null geometry) `parse_nws_feed`
  drops them. Resolving zone URIs to shapes is a deliberate later enhancement, not a guess
  made here.
- **`User-Agent` is mandatory.** api.weather.gov refuses requests without a descriptive
  `User-Agent`; `fetch_nws` always sends one (overridable) plus `Accept: application/geo+json`.
- **Timestamp precedence onset → effective → sent.** "When the hazard is in effect" is the
  most decision-relevant time, so `onset` wins, then `effective`, then `sent`; all are ISO-8601
  with an offset and normalized to UTC. Parsing is fixture-tested (14:00 −05:00 → 19:00 UTC).
- **Flood family routed to its own type.** Flood/flash-flood/coastal-flood/hydrologic events
  map to `HazardType.FLOOD`; everything else is `SEVERE_WEATHER`. Keeps the flood track
  separable for scoring without a second ingestor.

## Next
Phase 4: the change-detection + dedup store keyed by `dedup_key` — now that three sources
emit the same schema, only genuinely new or changed events should advance, so enrichment and
scoring never reprocess a feed that hasn't moved.
