# API Contract (Core Endpoints)

All endpoints return JSON.

## Health
- `GET /api/health`
- Response:
  - `status: string` (`healthy`)
  - `service: string`

## Status
- `GET /api/status`
- Response:
  - `database: { path, size_bytes, last_modified }`
  - `data: { total_papers, total_venues, venues, year_range }`
  - `server_time: ISO datetime`

## Overview
- `GET /api/stats/overview`
- Response:
  - `total_papers: int`
  - `total_keywords: int`
  - `total_venues: int`
  - `venues: string[]`
  - `years: int[]`
  - `year_range: string | "N/A"`

## Venue Stats
- `GET /api/stats/venues`
- Response: array of
  - `name: string`
  - `paper_count: int`
  - `years: int[]`

## Venue Detail
- `GET /api/stats/venue/<venue>`
- Response:
  - `venue: string`
  - `total_papers: int`
  - `years: int[]`
  - `yearly_stats: [{ year, paper_count, top_keywords: [{keyword, count}] }]`

## Top Keywords
- `GET /api/keywords/top?venue=&year=&limit=`
- Response: `[{ keyword: string, count: int }]`

## Keyword Trends
- `GET /api/keywords/trends?keyword=k1&keyword=k2&venue=`
- Response: `[{ keyword, years: int[], counts: int[] }]`

## Comparison
- `GET /api/keywords/comparison?year=&limit=`
- Response:
  - `year: int`
  - `venues: { [venueName]: [{keyword, count}] }`

## analysis_venue_summary year semantics
- Storage layer uses `year=0` to represent all-years summary.
- API/domain contract represents this as `year: null` when returning summary objects.

## Empty Data Behavior
When no data is present:
- Endpoints return valid JSON with empty arrays/objects where applicable.
- No contract field should be omitted due to empty result sets.
