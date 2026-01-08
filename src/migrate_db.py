#!/usr/bin/env python
"""
数据库迁移脚本

将旧架构（papers with id, title, venue）迁移到新架构（三层架构）。
"""

import sys
import sqlite3
from pathlib import Path
from datetime import datetime

# 确保 src 目录在路径中
_src_dir = Path(__file__).parent
if str(_src_dir) not in sys.path:
    sys.path.insert(0, str(_src_dir))

from config import DATABASE_PATH


def migrate_database(db_path: Path = None, backup: bool = True):
    """迁移数据库到新架构"""
    db_path = db_path or DATABASE_PATH
    
    print("=" * 60)
    print("🔧 数据库迁移工具")
    print(f"   Database: {db_path}")
    print("=" * 60)
    
    if not db_path.exists():
        print("❌ 数据库不存在，无需迁移")
        return False
    
    # 备份
    if backup:
        backup_path = db_path.with_suffix(f".backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db")
        import shutil
        shutil.copy(db_path, backup_path)
        print(f"✅ 已备份到: {backup_path}")
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 获取现有表
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    existing_tables = {row["name"] for row in cursor.fetchall()}
    print(f"\n现有表: {', '.join(existing_tables)}")
    
    # 检查 papers 表结构
    cursor.execute("PRAGMA table_info(papers)")
    papers_columns = {row[1] for row in cursor.fetchall()}
    print(f"papers 列: {', '.join(papers_columns)}")
    
    is_legacy = "id" in papers_columns and "paper_id" not in papers_columns
    
    if not is_legacy:
        print("\n✅ 数据库已是新架构，无需迁移")
        conn.close()
        return True
    
    print("\n📦 检测到旧架构，开始迁移...")
    
    try:
        # 1. 创建 Raw Layer 表（如果不存在）
        print("\n1️⃣ 创建 Raw Layer 表...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS raw_papers (
                raw_id          INTEGER PRIMARY KEY AUTOINCREMENT,
                source          TEXT NOT NULL,
                source_paper_id TEXT NOT NULL,
                title           TEXT,
                abstract        TEXT,
                authors         TEXT,
                year            INTEGER,
                venue_raw       TEXT,
                journal_ref     TEXT,
                comments        TEXT,
                categories      TEXT,
                doi             TEXT,
                raw_json        TEXT,
                retrieved_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(source, source_paper_id)
            )
        """)
        print("   ✅ raw_papers 表已创建/存在")
        
        # 2. 创建 venues 表
        print("\n2️⃣ 创建 venues 表...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS venues (
                venue_id        INTEGER PRIMARY KEY AUTOINCREMENT,
                canonical_name  TEXT UNIQUE NOT NULL,
                full_name       TEXT,
                domain          TEXT,
                venue_type      TEXT,
                first_year      INTEGER,
                last_year       INTEGER,
                created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("   ✅ venues 表已创建/存在")
        
        # 3. 从旧 papers 表提取 venues
        print("\n3️⃣ 提取 venues...")
        cursor.execute("SELECT DISTINCT venue FROM papers WHERE venue IS NOT NULL")
        venues = [row["venue"] for row in cursor.fetchall()]
        for venue in venues:
            cursor.execute(
                "INSERT OR IGNORE INTO venues (canonical_name) VALUES (?)",
                (venue,)
            )
        print(f"   ✅ 已提取 {len(venues)} 个 venue")
        
        # 4. 创建新的 papers 表（papers_new）
        print("\n4️⃣ 创建新架构 papers 表...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS papers_new (
                paper_id        INTEGER PRIMARY KEY AUTOINCREMENT,
                canonical_title TEXT NOT NULL,
                abstract        TEXT,
                authors         TEXT,
                year            INTEGER,
                venue_id        INTEGER REFERENCES venues(venue_id),
                venue_type      TEXT DEFAULT 'unknown',
                domain          TEXT,
                quality_flag    TEXT DEFAULT 'unknown',
                doi             TEXT,
                url             TEXT,
                pdf_url         TEXT,
                created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 5. 迁移数据
        print("\n5️⃣ 迁移数据...")
        cursor.execute("""
            INSERT INTO papers_new (canonical_title, abstract, authors, year, venue_id, url, pdf_url, created_at, updated_at)
            SELECT 
                p.title,
                p.abstract,
                p.authors,
                p.year,
                v.venue_id,
                p.url,
                p.pdf_url,
                p.created_at,
                p.updated_at
            FROM papers p
            LEFT JOIN venues v ON p.venue = v.canonical_name
        """)
        
        migrated_count = cursor.rowcount
        print(f"   ✅ 已迁移 {migrated_count} 篇论文")
        
        # 6. 替换表
        print("\n6️⃣ 替换表...")
        cursor.execute("DROP TABLE papers")
        cursor.execute("ALTER TABLE papers_new RENAME TO papers")
        print("   ✅ 表已替换")
        
        # 7. 创建 paper_sources 表
        print("\n7️⃣ 创建 paper_sources 表...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS paper_sources (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                paper_id        INTEGER NOT NULL REFERENCES papers(paper_id),
                raw_id          INTEGER NOT NULL REFERENCES raw_papers(raw_id),
                source          TEXT NOT NULL,
                confidence      REAL DEFAULT 1.0,
                created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(paper_id, raw_id)
            )
        """)
        print("   ✅ paper_sources 表已创建")
        
        # 8. 创建/更新 paper_keywords 表
        print("\n8️⃣ 更新 paper_keywords 表...")
        # 检查是否需要添加 method 列
        cursor.execute("PRAGMA table_info(paper_keywords)")
        pk_columns = {row[1] for row in cursor.fetchall()}
        
        if "method" not in pk_columns:
            # 需要重建表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS paper_keywords_new (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    paper_id        INTEGER NOT NULL,
                    keyword         TEXT NOT NULL,
                    method          TEXT NOT NULL DEFAULT 'yake',
                    score           REAL DEFAULT 1.0,
                    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(paper_id, keyword, method)
                )
            """)
            # 迁移现有关键词数据（如果有）
            cursor.execute("""
                INSERT OR IGNORE INTO paper_keywords_new (paper_id, keyword, method, score)
                SELECT paper_id, keyword_id, 'legacy', score
                FROM paper_keywords
            """)
            cursor.execute("DROP TABLE IF EXISTS paper_keywords")
            cursor.execute("ALTER TABLE paper_keywords_new RENAME TO paper_keywords")
        print("   ✅ paper_keywords 表已更新")
        
        # 9. 创建 trend_cache 表
        print("\n9️⃣ 创建 trend_cache 表...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trend_cache (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                keyword         TEXT NOT NULL,
                venue_id        INTEGER,
                year            INTEGER NOT NULL,
                count           INTEGER NOT NULL,
                updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(keyword, venue_id, year)
            )
        """)
        print("   ✅ trend_cache 表已创建")
        
        # 10. 创建 ingestion_logs 表
        print("\n🔟 创建 ingestion_logs 表...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ingestion_logs (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                source          TEXT NOT NULL,
                query_params    TEXT,
                paper_count     INTEGER NOT NULL,
                started_at      DATETIME,
                completed_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
                status          TEXT DEFAULT 'success'
            )
        """)
        print("   ✅ ingestion_logs 表已创建")
        
        # 11. 创建索引
        print("\n1️⃣1️⃣ 创建索引...")
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_raw_papers_source ON raw_papers(source, source_paper_id)",
            "CREATE INDEX IF NOT EXISTS idx_papers_venue_year ON papers(venue_id, year)",
            "CREATE INDEX IF NOT EXISTS idx_paper_sources_paper ON paper_sources(paper_id)",
            "CREATE INDEX IF NOT EXISTS idx_paper_keywords_paper ON paper_keywords(paper_id)",
        ]
        for idx in indexes:
            try:
                cursor.execute(idx)
            except Exception as e:
                print(f"   ⚠️ 索引创建警告: {e}")
        print("   ✅ 索引已创建")
        
        conn.commit()
        print("\n" + "=" * 60)
        print("✅ 迁移完成！")
        print("=" * 60)
        
        conn.close()
        return True
        
    except Exception as e:
        conn.rollback()
        conn.close()
        print(f"\n❌ 迁移失败: {e}")
        return False


if __name__ == "__main__":
    success = migrate_database()
    sys.exit(0 if success else 1)
