-- ============================================================
-- DepthTrender Database Schema
-- Three-Layer Architecture: Raw → Structured → Analysis
-- ============================================================

-- ========== RAW LAYER ==========
-- Preserves original data from all sources without interpretation

CREATE TABLE IF NOT EXISTS raw_papers (
    raw_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    source          TEXT NOT NULL,  -- arxiv / openalex / s2 / openreview
    source_paper_id TEXT NOT NULL,
    title           TEXT,
    abstract        TEXT,
    authors         TEXT,           -- JSON array
    year            INTEGER,
    venue_raw       TEXT,           -- Original venue string (uninterpreted)
    journal_ref     TEXT,           -- arXiv journal reference
    comments        TEXT,           -- arXiv comments (for conference detection)
    categories      TEXT,           -- arXiv categories (cs.CV, cs.LG, etc.)
    doi             TEXT,
    raw_json        TEXT,           -- Complete original API response
    retrieved_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(source, source_paper_id)
);

-- ========== STRUCTURED LAYER ==========
-- Normalized, deduplicated papers with venue identification

CREATE TABLE IF NOT EXISTS venues (
    venue_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    canonical_name  TEXT UNIQUE NOT NULL,  -- CVPR, ICML, NeurIPS, etc.
    full_name       TEXT,
    domain          TEXT,  -- CV / NLP / ML / RL / AI
    venue_type      TEXT CHECK(venue_type IN ('conference', 'journal', 'workshop')),
    first_year      INTEGER,
    last_year       INTEGER,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS papers (
    paper_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    canonical_title TEXT NOT NULL,
    abstract        TEXT,
    authors         TEXT,           -- JSON array
    year            INTEGER,
    venue_id        INTEGER REFERENCES venues(venue_id),
    venue_type      TEXT CHECK(venue_type IN ('conference', 'journal', 'preprint', 'unknown')),
    domain          TEXT,  -- CV / NLP / ML / RL / AI
    quality_flag    TEXT CHECK(quality_flag IN ('accepted', 'unknown', 'filtered')) DEFAULT 'unknown',
    doi             TEXT,
    url             TEXT,
    pdf_url         TEXT,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Links structured papers back to raw sources (many-to-many)
CREATE TABLE IF NOT EXISTS paper_sources (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    paper_id        INTEGER NOT NULL REFERENCES papers(paper_id) ON DELETE CASCADE,
    raw_id          INTEGER NOT NULL REFERENCES raw_papers(raw_id) ON DELETE CASCADE,
    source          TEXT NOT NULL,
    confidence      REAL DEFAULT 1.0,  -- Confidence of source-to-paper mapping
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(paper_id, raw_id)
);

-- ========== ANALYSIS LAYER ==========
-- Derived data from analysis processes (keywords, trends, etc.)

CREATE TABLE IF NOT EXISTS paper_keywords (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    paper_id        INTEGER NOT NULL REFERENCES papers(paper_id) ON DELETE CASCADE,
    keyword         TEXT NOT NULL,
    method          TEXT NOT NULL,  -- yake / keybert / llm / author
    score           REAL DEFAULT 1.0,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(paper_id, keyword, method)
);

-- Cache for trend queries (accelerates web visualization)
CREATE TABLE IF NOT EXISTS trend_cache (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    keyword         TEXT NOT NULL,
    venue_id        INTEGER REFERENCES venues(venue_id),
    year            INTEGER NOT NULL,
    count           INTEGER NOT NULL,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(keyword, venue_id, year)
);

-- ========== OPERATIONAL TABLES ==========
-- Ingestion tracking and system state

CREATE TABLE IF NOT EXISTS ingestion_logs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    source          TEXT NOT NULL,  -- arxiv / openalex / s2 / openreview
    query_params    TEXT,           -- JSON of query parameters
    paper_count     INTEGER NOT NULL,
    started_at      DATETIME,
    completed_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
    status          TEXT CHECK(status IN ('success', 'partial', 'failed')) DEFAULT 'success'
);

-- Legacy compatibility: scrape_logs (kept for migration)
CREATE TABLE IF NOT EXISTS scrape_logs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    venue           TEXT NOT NULL,
    year            INTEGER NOT NULL,
    paper_count     INTEGER NOT NULL,
    scraped_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ========== INDEXES ==========
-- Optimized for common query patterns

-- Raw Layer indexes
CREATE INDEX IF NOT EXISTS idx_raw_papers_source ON raw_papers(source, source_paper_id);
CREATE INDEX IF NOT EXISTS idx_raw_papers_year ON raw_papers(year);
CREATE INDEX IF NOT EXISTS idx_raw_papers_categories ON raw_papers(categories);

-- Structured Layer indexes
CREATE INDEX IF NOT EXISTS idx_papers_venue_year ON papers(venue_id, year);
CREATE INDEX IF NOT EXISTS idx_papers_domain ON papers(domain);
CREATE INDEX IF NOT EXISTS idx_papers_quality ON papers(quality_flag);
CREATE INDEX IF NOT EXISTS idx_paper_sources_paper ON paper_sources(paper_id);
CREATE INDEX IF NOT EXISTS idx_paper_sources_raw ON paper_sources(raw_id);

-- Analysis Layer indexes
CREATE INDEX IF NOT EXISTS idx_paper_keywords_paper ON paper_keywords(paper_id);
CREATE INDEX IF NOT EXISTS idx_paper_keywords_keyword ON paper_keywords(keyword);
CREATE INDEX IF NOT EXISTS idx_paper_keywords_method ON paper_keywords(method);
CREATE INDEX IF NOT EXISTS idx_trend_cache_keyword_year ON trend_cache(keyword, year);

-- Operational indexes
CREATE INDEX IF NOT EXISTS idx_ingestion_logs_source ON ingestion_logs(source, completed_at);
CREATE INDEX IF NOT EXISTS idx_scrape_logs_venue_year ON scrape_logs(venue, year);
