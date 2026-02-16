# Architecture (Three-Layer + Compatibility)

## Overview
DeepTrender uses a three-layer architecture:

1. Raw Layer
- Table: `raw_papers`
- Stores unmodified payloads from upstream sources (`arxiv/openalex/s2/openreview`).
- Includes `published_at` (when available) and `retrieved_at`.

2. Structured Layer
- Tables: `papers`, `venues`, `paper_sources`
- Normalizes title/venue/domain metadata.
- Deduplicates papers and links source records.

3. Analysis Layer
- Tables: `paper_keywords`, `trend_cache`, `analysis_*`
- Stores extracted keywords and cached trend artifacts for API/static export.

## Main Flow
1. Ingestion Agent writes raw records.
2. Structuring Agent normalizes and links paper-source relations.
3. Analysis Agent extracts keywords (YAKE/KeyBERT) and updates caches.
4. Web/API + static export read from analysis caches and repository queries.

## Compatibility Strategy
New architecture is canonical.

Compatibility is maintained via:
- `Paper` read-only compatibility properties: `title`, `venue`, `id`
- `DatabaseRepository` compatibility wrappers for legacy call patterns
- JSON serialization that includes both canonical and compatibility keys

## arXiv Time Semantics
- Prefer `published_at` for month/week/day buckets.
- Fallback to `retrieved_at` when `published_at` is missing.
- This keeps trend charts usable while preserving backward compatibility for old records.

## Export Path
Canonical static export path:
- `src/tools/export_static_site.py`

Legacy module:
- `src/export/venue_exporter.py` remains as compatibility wrapper delegating to static exporter.
