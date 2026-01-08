# arXiv Data Collection Guide

## Overview

This guide explains how to collect arXiv papers for the DeepTrender project. We provide two collection scripts:

1. **collect_arxiv_latest.py** - Collect recent papers (last N days)
2. **collect_arxiv_bulk.py** - Collect historical papers by year range

---

## Quick Start

### Collect Latest Papers (Recommended for Regular Updates)

```bash
# Collect papers from last 7 days (default)
python collect_arxiv_latest.py

# Collect papers from last 30 days
python collect_arxiv_latest.py --days 30

# Collect up to 2000 papers from last 14 days
python collect_arxiv_latest.py --days 14 --max-results 2000

# Collect only cs.LG and cs.CV papers
python collect_arxiv_latest.py --categories cs.LG cs.CV
```

### Test Collection (Small Sample)

```bash
# Test with 50 papers from last 3 days
python collect_arxiv_latest.py --days 3 --max-results 50
```

---

## Collection Scripts

### 1. collect_arxiv_latest.py

**Purpose**: Collect recent arXiv papers for regular updates

**Features**:
- ✅ Collect papers from last N days
- ✅ Support multiple AI categories
- ✅ Auto-save to database
- ✅ Skip duplicates automatically
- ✅ Show progress and statistics
- ✅ Display sample papers

**Parameters**:
```
--days N              Collect papers from last N days (default: 7)
--categories CAT...   arXiv categories (default: cs.CV cs.CL cs.LG cs.AI cs.RO cs.NE stat.ML)
--max-results N       Maximum number of papers (default: 1000)
--quiet               Quiet mode, no detailed output
```

**Examples**:
```bash
# Daily update: collect last 1 day
python collect_arxiv_latest.py --days 1 --max-results 500

# Weekly update: collect last 7 days
python collect_arxiv_latest.py --days 7 --max-results 2000

# Monthly update: collect last 30 days
python collect_arxiv_latest.py --days 30 --max-results 5000

# Specific categories only
python collect_arxiv_latest.py --days 7 --categories cs.LG cs.CV
```

**Output Example**:
```
======================================================================
arXiv Latest Data Collection
======================================================================
Time range: Last 3 days
Categories: cs.CV, cs.CL, cs.LG, cs.AI, cs.RO, cs.NE, stat.ML
Target: 50 papers
Start time: 2026-01-03 00:37:00
======================================================================

Fetching papers from arXiv (last 3 days)...
   Categories: cs.CV, cs.CL, cs.LG, cs.AI, cs.RO, cs.NE, stat.ML
   Fetched 50 papers...
SUCCESS: Fetched 50 papers from arXiv

======================================================================
Saving to database...
======================================================================
   Progress: 10/50 (20.0%)
   Progress: 20/50 (40.0%)
   Progress: 30/50 (60.0%)
   Progress: 40/50 (80.0%)
   Progress: 50/50 (100.0%)

======================================================================
Collection Statistics
======================================================================
Fetched: 50 papers
Saved: 50 papers
Duplicates: 0 papers
Errors: 0 papers
Completed: 2026-01-03 00:37:00
======================================================================

Sample Papers:
----------------------------------------------------------------------

1. SpaceTimePilot: Generative Rendering of Dynamic Scenes
   Year: 2025
   Categories: cs.CV,cs.AI,cs.RO
   Authors: Zhening Huang, Hyeonho Jeong, Xuelin Chen...
```

---

### 2. collect_arxiv_bulk.py

**Purpose**: Collect historical papers by year range (for initial data loading)

**Features**:
- ✅ Collect papers by year (2020-2025)
- ✅ Target papers per year (e.g., 2000/year)
- ✅ Support multiple categories
- ✅ Auto-save to database
- ✅ Resume from interruption
- ✅ Year-bstics

**Parameters**:
```
--start-year YEAR     Start year (default: 2020)
--end-year YEAR       End year (default: 2025)
--categories CAT...   arXiv categories
--per-year N          Papers per year (default: 2000)
--quiet               Quiet mode
```

**Examples**:
```bash
# Collect 2020-2025 data (12,000+ papers)
python collect_arxiv_bulk.py --start-year 2020 --end-year 2025

# Collect only 2024 data
python collect_arxiv_bulk.py --start-year 2024 --end-year 2024

# Collect 2022-2023, 3000 papers per year
python collect_arxiv_bulk.py --start-year 2022 --end-year 2023 --per-year 3000

# Specific categories only
python collect_arxiv_bulk.py --categories cs.LG cs.CV --per-year 1000
```

**Note**: This script is designed for initial bulk loading. For regular updates, use `collect_arxiv_latest.py` instead.

---

## Supported Categories

Default AI-related categories:
- **cs.CV** - Computer Vision
- **cs.CL** - Computation and Language (NLP)
- **cs.LG** - Machine Learning
- **cs.AI** - Artificial Intelligence
- **cs.RO** - Robotics
- **cs.NE** - Neural and Evolutionary Computing
- **stat.ML** - Machine Learning (Statistics)

You can specify custom categories using `--categories` parameter.

---

## Data Quality

### What Gets Collected

Each paper includes:
- ✅ **Title** - Full paper title
- ✅ **Abstract** - Complete abstract
- ✅ **Authors** - List of all authors
- ✅ **Year** - Publication year
- ✅ **Categories** - arXiv categories (cs.LG, cs.CV, etc.)
- ✅ **Comments** - May contain conference information
- ✅ **Journal Reference** - If available
- ✅ **DOI** - If available
- ✅ **Raw JSON** - Complete API response
- ✅ **Retrieved At** - Collection timestamp

### Quality Checks

After collection, verify data quality:

```bash
# Run data quality check
python src/dq_arxiv.py

# Check database statistics
sqlite3 data/keywords.db "
SELECT
    COUNT(*) as total,
    COUNT(CASE WHEN abstract IS NOT NULL THEN 1 END) as with_abstract,
    COUNT(CASE WHEN comments IS NOT NULL THEN 1 END) as with_comments
FROM raw_papers
WHERE source = 'arxiv';
"
```

---

## Best Practices

### For Initial Setup

1. **Start with recent data** (last 30 days):
   ```bash
   python collect_arxiv_latest.py --days 30 --max-results 5000
   ```

2. **Then collect historical data** (2020-2025):
   ```bash
   python collect_arxiv_bulk.py --start-year 2020 --end-year 2025
   ```

3. **Verify data quality**:
   ```bash
   python src/dq_arxiv.py
   ```

### For Regular Updates

**Daily Update** (recommended):
```bash
# Run every day to collect yesterday's papers
python collect_arxiv_latest.py --days 1 --max-results 500
```

**Weekly Update**:
```bash
# Run every week to collect last 7 days
python collect_arxiv_latest.py --days 7 --max-results 2000
```

**Monthly Update**:
```bash
# Run every month to collect last 30 days
python collect_arxiv_latest.py --days 30 --max-results 5000
```

### Automation with Cron

Add to crontab for daily updates:
```bash
# Run daily at 2 AM
0 2 * * * cd /path/to/deeptrender && python collect_arxiv_latest.py --days 1 --max-results 500 >> logs/arxiv_daily.log 2>&1
```

---

## Troubleshooting

### Issue: "UNIQUE constraint failed"

**Cause**: Paper already exists in database (duplicate)

**Solution**: This is normal and expected. The script automatically skips duplicates.

### Issue: "No papers fetched"

**Possible causes**:
1. Network connection issue
2. arXiv API is down
3. Date range has no papers

**Solution**:
- Check internet connection
- Try again later
- Adjust date range or categories

### Issue: Rate limit errors

**Cause**: Too many requests to arXiv API

**Solution**: The script automatically respects arXiv's 3-second delay. If you still get rate limit errors:
- Reduce `--max-results`
- Add longer delays between runs
- Contact arXiv for higher rate limits

### Issue: Slow collection

**Cause**: arXiv API has rate limits (3 seconds between requests)

**Expected speed**:
- ~20 papers/minute
- ~1,200 papers/hour
- ~10,000 papers in 8-10 hours

**Solution**: This is normal. For large collections, run overnight.

---

## Database Schema

Papers are saved to `data/keywords.db` in the `rawrs` table:

```sql
CREATE TABLE raw_papers (
    raw_id INTEGER PRIMARY KEY,
    source TEXT NOT NULL,           -- 'arxiv'
    source_paper_id TEXT NOT NULL,  -- arXiv ID (e.g., '2312.12345')
    title TEXT,
    abstract TEXT,
    authors TEXT,                   -- JSON array
    year INTEGER,
    venue_raw TEXT,                 -- NULL for arXiv
    journal_ref TEXT,               -- arXiv journal reference
    comments TEXT,                  -- May contain conference info
    categories TEXT,                -- 'cs.LG,cs.CV'
    doi TEXT,
    raw_json TEXT,                  -- Complete API response
    retrieved_at DATETIME,
    UNIQUE(source, source_paper_id)
);
```

---

## Next Steps

After collecting arXiv data:

1. **Run Structuring Agent** to process raw data:
   ```bash
   python -c "from src.agents.structuring_agent import run_structuring; run_structuring()"
   ```

2. **Run Analysis Agent** to extract keywords and trends:
   ```bash
   python -c "from src.analysis.arxiv_agent import ArxivAnalysisAgent; ArxivAnalysisAgent().run_all_granularities(force=True)"
   ```

3. **Start Web Server** to visualize data:
   ```bash
   python src/web/app.py
   ```

4. **Build Vector Index** for RAG:
   ```bash
   # TODO: Add vector indexing script
   ```

---

## Performance Metrics

### Collection Speed

| Papers | Time | Speed |
|--------|------|-------|
| 50 | ~3 seconds | 16.7 papers/sec |
| 500 | ~25 minutes | 20 papers/min |
| 2,000 | ~1.7 hours | 20 papers/min |
| 10,000 | ~8.3 hours | 20 papers/min |

### Database Size

| Papers | Database Size |
|--------|---------------|
| 100 | ~5 MB |
| 1,000 | ~50 MB |
| 10,000 | ~500 MB |
| 100,000 | ~5 GB |

---

## FAQ

**Q: How many papers should I collect?**

A: For a good RAG system:
- Minimum: 5,000 papers
- Recommended: 10,000+ papers
- Optimal: 50,000+ papers

**Q: How often should I update?**

A:
- Daily updates: Best for staying current
- Weekly updates: Good balance
- Monthly updates: Minimum recommended

**Q: Can I collect papers from specific conferences?**

A: arXiv doesn't directly support conference filtering. However:
1. Collect all papers
2. Use Structuring Agent to detect conferences from comments
3. Filter by conference in Analysis Layer

**Q: What if I want papers before 2020?**

A: Modify `collect_arxibulk.py`:
```bash
python collect_arxiv_bulk.py --start-year 2015 --end-year 2019
```

**Q: Can I pause and resume collection?**

A: Yes! The script automatically skips duplicates, so you can:
1. Stop the script (Ctrl+C)
2. Run it again later
3. It will skip already collected papers

---

## Support

For issues or questions:
1. Check this guide
2. Run data quality check: `python src/dq_arxiv.py`
3. Check database: `sqlite3 data/keywords.db`
4. Review logs and error messages

---

**Last Updated**: 2026-01-03
**Version**: 1.0
**Status**: ✅ Production Ready
