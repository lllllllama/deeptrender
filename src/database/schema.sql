-- 论文表
CREATE TABLE IF NOT EXISTS papers (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    abstract TEXT,
    venue TEXT NOT NULL,
    year INTEGER NOT NULL,
    url TEXT,
    pdf_url TEXT,
    authors TEXT,  -- JSON 数组
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 关键词表
CREATE TABLE IF NOT EXISTS keywords (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    keyword TEXT UNIQUE NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 论文-关键词关联表
CREATE TABLE IF NOT EXISTS paper_keywords (
    paper_id TEXT NOT NULL,
    keyword_id INTEGER NOT NULL,
    source TEXT NOT NULL CHECK(source IN ('author', 'extracted')),
    score REAL DEFAULT 1.0,
    PRIMARY KEY (paper_id, keyword_id, source),
    FOREIGN KEY (paper_id) REFERENCES papers(id) ON DELETE CASCADE,
    FOREIGN KEY (keyword_id) REFERENCES keywords(id) ON DELETE CASCADE
);

-- 爬取记录表（用于增量更新）
CREATE TABLE IF NOT EXISTS scrape_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    venue TEXT NOT NULL,
    year INTEGER NOT NULL,
    paper_count INTEGER NOT NULL,
    scraped_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 索引优化
CREATE INDEX IF NOT EXISTS idx_papers_venue_year ON papers(venue, year);
CREATE INDEX IF NOT EXISTS idx_keywords_keyword ON keywords(keyword);
CREATE INDEX IF NOT EXISTS idx_paper_keywords_paper ON paper_keywords(paper_id);
CREATE INDEX IF NOT EXISTS idx_paper_keywords_keyword ON paper_keywords(keyword_id);
CREATE INDEX IF NOT EXISTS idx_scrape_logs_venue_year ON scrape_logs(venue, year);
