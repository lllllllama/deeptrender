# Static Export Schema

Canonical exporter: `src/tools/export_static_site.py`

## Directory layout
- `docs/data/venues/`
- `docs/data/arxiv/`

## Venues files
1. `venues_index.json`
- Array of venue objects:
  - `name`
  - `full_name`
  - `domain`
  - `tier`
  - `years_available`
  - `paper_count`
  - `top_keywords`

2. `venue_<VENUE>_top_keywords.json`
- Object keyed by year:
  - `<year>` -> array of `{ keyword, count, rank }`

3. `venue_<VENUE>_keyword_trends.json`
- Object keyed by keyword:
  - `<keyword>` -> array of `{ year, count, rank }`

4. `venue_<VENUE>_keywords_index.json`
- Array of keyword strings.

## arXiv files
1. `arxiv_timeseries_<granularity>_<category>.json`
- `granularity`
- `category`
- `data`
- `cached`
- `exported_at`

2. `arxiv_emerging_<category>.json`
- Array of emerging topic objects:
  - `category`
  - `keyword`
  - `growth_rate`
  - `first_seen`
  - `recent_count`
  - `trend`
  - `updated_at`

3. `arxiv_stats.json`
- `total_papers`
- `categories`
- `date_range`
- `latest_update`
- `exported_at`

## Compatibility rule
File names are stable.
Schema changes should be additive (new fields allowed, existing fields preserved).
