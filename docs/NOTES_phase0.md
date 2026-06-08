# Phase 0 — Scaffold (design notes)

## What landed
- `src/` package `aegis` with two real, tested pieces:
  - `geo.py`: haversine great-circle distance + a **distance-decay proximity risk** score
    (exponential, `radius_km` = one e-folding). Validated against the known College
    Station→Austin distance (~135 km).
  - `schema.py`: canonical `HazardEvent` with a **`dedup_key`** property — the foundation
    of change-detection (phase 4).
- ruff + pytest CI green from commit one.

## Decisions & trade-offs
- **`dedup_key` from day zero.** The whole "event-driven, not polling" thesis depends on
  knowing when an event is the *same* event. Baking the dedup identity into the schema
  forces every ingestor to declare it.
- **Distance-decay over a hard radius.** A binary "within 50 km" flag throws away signal;
  exponential decay gives a smooth, explainable risk that ranks assets sensibly.
- **Pure-numpy/math core, geo libs later.** GeoPandas/H3/Shapely are heavy; the core risk
  math doesn't need them, so CI stays fast and the math stays readable. They arrive in
  phase 8 for polygon ops and spatial indexing.
- **Agentic enrichment with guards (phase 7).** LLM enrichment is powerful but must be
  validated — the plan treats schema-validated, guarded output as non-negotiable.

## Next
Phase 1: the USGS earthquake ingestor (cleanest public GeoJSON feed) → first real
`HazardEvent` records flowing through the schema.
