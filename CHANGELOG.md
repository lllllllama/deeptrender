# Changelog

## 2026-02-16 - Baseline Recovery and Compatibility Alignment

### Fixed
- Repaired `src/export/venue_exporter.py` (previously non-compilable) and converted it to a compatibility wrapper delegating to static exporter.
- Fixed `sqlite3.Row` access bug in `StructuredRepository._row_to_venue` (`row.get` -> safe row-key access).
- Added `published_at` support to raw paper model and ingestion path for arXiv.
- Restored test compatibility with new architecture through model serialization/fixtures updates.
- Fixed broken tests with typos/import errors in arXiv timeseries test suite.
- Updated database tests to validate current schema (`paper_keywords`) instead of removed legacy table (`keywords`).

### Changed
- `Paper` compatibility behavior now includes legacy-friendly `id/title/venue` serialization while keeping canonical fields.
- `DatabaseRepository` compatibility wrappers improved:
  - graceful string handling for `get_paper`
  - `get_papers_by_venue_year(venue_name, year)` wrapper
  - dedupe-aware save path using title/year lookup
- Added `published_at` column to schema definition and runtime column backfill in `RawRepository`.

### CI / Process
- Added baseline failure report: `baseline_failures.md`.
- Added architecture and interface docs:
  - `docs/ARCHITECTURE.md`
  - `docs/API_CONTRACT.md`
  - `docs/EXPORT_SCHEMA.md`

### Verification
- `python -m compileall -q src` passes.
- `pytest -q` passes (`84 passed`).
