# Baseline Failures (Before Repair)

Date captured: 2026-02-16

## Compile failure
- `python -m compileall -q src`
- Error: `src/export/venue_exporter.py` had broken syntax (mismatched tokens/parentheses).

## Pytest baseline
- Command: `pytest -q`
- Result snapshot: `13 failed, 36 passed, 35 errors`.

## Key error categories
1. Model compatibility mismatch
- `Paper.__init__()` did not accept legacy constructor args used by tests (`id/title/venue`).
- Affected fixtures and model/database/extractor tests.

2. Repository runtime error
- `sqlite3.Row` accessed with `.get()` in `StructuredRepository._row_to_venue`, causing API endpoint failures.

3. Broken tests
- Typo/import errors in arXiv timeseries tests (`ArxivAngent`, `ArxivAnaAgent`).
- Legacy schema assertion expected `keywords` table that no longer exists.

4. Exporter module broken
- `src/export/venue_exporter.py` contained corrupted code and could not be imported/compiled.

## Baseline API impact
- Multiple endpoints failed indirectly due repository errors:
  - `/api/stats/overview`
  - `/api/stats/venues`
  - `/api/stats/venue/<venue>`
  - `/api/keywords/top`
  - `/api/keywords/comparison`
  - `/api/status`
