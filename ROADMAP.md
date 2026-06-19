# Aegis Roadmap

Built in public, one phase at a time. Each phase ships tested code + a `docs/NOTES_<phase>.md`
design note. The daily build routine picks up the next unchecked phase.

> Convention: `[ ]` not started · `[~]` in progress · `[x]` done.

## Foundations
- [x] **Phase 0 — Scaffold.** Packaging, geospatial risk primitives (haversine,
  distance-decay proximity, asset risk), canonical `HazardEvent` schema + dedup key,
  tests, ruff, CI, Docker skeleton, roadmap.
- [x] **Phase 1 — USGS earthquake ingestor.** Pull the GeoJSON feed, normalize to
  `HazardEvent`, tests against a recorded fixture.
- [x] **Phase 2 — NASA FIRMS wildfire ingestor.** Active-fire feed → `HazardEvent`
  (handles FRP/confidence fields).
- [x] **Phase 3 — NOAA / NWS alerts ingestor.** Severe-weather alerts → `HazardEvent`.

## Event-driven core
- [ ] **Phase 4 — Change-detection + dedup store.** State by `dedup_key`; only new/changed
  events advance (no reprocessing).
- [ ] **Phase 5 — Event-driven trigger layer.** Feed-state hashing → emit only on change,
  replacing naive polling.
- [ ] **Phase 6 — Airflow orchestration.** Scheduled sweeps + backfill DAGs with retries.

## Enrichment & scoring
- [ ] **Phase 7 — Agentic enrichment workflow.** LangChain pipeline: reverse-geocode,
  classify hazard subtype, estimate severity, write analyst summary — with output
  validation/guards.
- [ ] **Phase 8 — Geospatial risk scoring.** Asset registry + proximity risk; H3 cells
  for spatial bucketing and aggregation.
- [ ] **Phase 9 — Severity model.** Calibrated severity/escalation score combining
  magnitude, trend, and proximity.

## Retrieval & serving
- [ ] **Phase 10 — Embedding + FAISS index.** Embed enriched events for semantic search.
- [ ] **Phase 11 — RAG query API (FastAPI).** "What's escalating near <area>?" with
  cited source events.
- [ ] **Phase 12 — Situational dashboard.** Map view, escalation feed, asset risk table.

## Hardening & polish
- [ ] **Phase 13 — Backfill + replay tooling.** Reconstruct state from history.
- [ ] **Phase 14 — Rate-limit & resilience.** Backoff, caching, partial-feed handling.
- [ ] **Phase 15 — Dockerized demo + sample feeds.** One-command reproducible run.
- [ ] **Phase 16 — Architecture deep-dive + demo GIF.** Recruiter-ready walkthrough.
