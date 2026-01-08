-- ========================================
-- Data Quality Report SQL Queries
-- 可直接在 SQLite 中运行
-- ========================================

-- 0. 检查架构版本
SELECT 'Schema Check' as section;
SELECT 
    CASE 
        WHEN EXISTS(SELECT 1 FROM pragma_table_info('papers') WHERE name='paper_id') 
        THEN 'NEW' 
        ELSE 'LEGACY' 
    END as schema_version;

-- 1. Raw Layer 统计
SELECT '1. Raw Layer Stats' as section;
SELECT COUNT(*) as raw_total FROM raw_papers;

SELECT source, COUNT(*) as count, 
       ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM raw_papers), 1) as pct
FROM raw_papers GROUP BY source ORDER BY count DESC;

-- 近 7 天增量
SELECT COUNT(*) as recent_7d,
       ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM raw_papers), 1) as pct
FROM raw_papers 
WHERE retrieved_at >= datetime('now', '-7 days');

-- 2. Structured Layer 统计
SELECT '2. Structured Layer Stats' as section;
SELECT COUNT(*) as papers_total FROM papers;

-- 结构化成功率
SELECT ROUND(
    (SELECT COUNT(*) FROM papers) * 100.0 / 
    NULLIF((SELECT COUNT(*) FROM raw_papers), 0), 
    1
) as structuring_rate_pct;

-- 3. 摘要缺失率
SELECT '3. Abstract Missing Rate' as section;

SELECT 'raw_papers' as layer, 
       COUNT(*) as missing,
       ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM raw_papers), 1) as pct
FROM raw_papers WHERE abstract IS NULL OR abstract = '';

SELECT 'papers' as layer,
       COUNT(*) as missing,
       ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM papers), 1) as pct  
FROM papers WHERE abstract IS NULL OR abstract = '';

-- 4. Venue 识别率
SELECT '4. Venue Recognition' as section;

SELECT COUNT(*) as unknown_venue,
       ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM papers), 1) as pct
FROM papers WHERE venue_id IS NULL;

SELECT 
    COALESCE(v.canonical_name, '(UNKNOWN)') as venue_name, 
    COUNT(*) as count,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM papers), 1) as pct
FROM papers p
LEFT JOIN venues v ON p.venue_id = v.venue_id
GROUP BY p.venue_id 
ORDER BY count DESC 
LIMIT 10;

-- 5. 去重合并率
SELECT '5. Deduplication Stats' as section;

SELECT COUNT(*) as paper_sources_count FROM paper_sources;

SELECT ROUND(
    (SELECT COUNT(*) FROM paper_sources) * 1.0 / 
    NULLIF((SELECT COUNT(*) FROM papers), 0), 
    2
) as avg_sources_per_paper;

SELECT COUNT(*) as multi_source_papers
FROM (
    SELECT paper_id, COUNT(*) as source_count 
    FROM paper_sources 
    GROUP BY paper_id 
    HAVING source_count > 1
);

-- 6. 近 30 天 venue 分布
SELECT '6. Recent 30d Venue Distribution' as section;

SELECT 
    COALESCE(v.canonical_name, '(UNKNOWN)') as venue_name, 
    COUNT(*) as count,
    ROUND(COUNT(*) * 100.0 / (
        SELECT COUNT(*) FROM papers WHERE created_at >= datetime('now', '-30 days')
    ), 1) as pct
FROM papers p
LEFT JOIN venues v ON p.venue_id = v.venue_id
WHERE p.created_at >= datetime('now', '-30 days')
GROUP BY p.venue_id 
ORDER BY count DESC;

-- 7. 数据源质量检查
SELECT '7. Source Quality Check' as section;

SELECT 
    source,
    COUNT(*) as total,
    SUM(CASE WHEN abstract IS NULL OR abstract = '' THEN 1 ELSE 0 END) as no_abstract,
    SUM(CASE WHEN title IS NULL OR title = '' THEN 1 ELSE 0 END) as no_title,
    ROUND(AVG(LENGTH(abstract)), 0) as avg_abstract_len
FROM raw_papers
GROUP BY source;

-- 8. 验收结论
SELECT '8. Validation Summary' as section;

SELECT 
    (SELECT COUNT(*) FROM raw_papers) as raw_count,
    (SELECT COUNT(*) FROM papers) as papers_count,
    (SELECT COUNT(*) FROM venues) as venues_count,
    (SELECT COUNT(*) FROM paper_sources) as links_count,
    CASE 
        WHEN (SELECT COUNT(*) FROM raw_papers) > 0 
         AND (SELECT COUNT(*) FROM papers) > 0 
        THEN 'PASS'
        ELSE 'FAIL'
    END as validation_result;
