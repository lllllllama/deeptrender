#!/usr/bin/env python
"""
Data Quality (DQ) Report

验收 Raw Layer 和 Structured Layer 的数据质量。
通过后才能进入分析层；不通过先修规则（dedup/venue alias/domain 映射）。

支持新旧两种数据库架构：
- 旧架构: papers(id, title, venue, ...)
- 新架构: papers(paper_id, canonical_title, venue_id, ...)
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

# 确保 src 目录在路径中
_src_dir = Path(__file__).parent
if str(_src_dir) not in sys.path:
    sys.path.insert(0, str(_src_dir))

from config import DATABASE_PATH


def detect_schema_version(cursor):
    """检测数据库架构版本"""
    cursor.execute("PRAGMA table_info(papers)")
    columns = {r[1] for r in cursor.fetchall()}
    
    if "paper_id" in columns and "canonical_title" in columns:
        return "new"
    elif "id" in columns and "title" in columns:
        return "legacy"
    else:
        return "unknown"


def run_dq_report(db_path: Path = None):
    """运行 DQ 报告"""
    import sqlite3
    
    db_path = db_path or DATABASE_PATH
    
    print("=" * 70)
    print("📊 Data Quality (DQ) Report")
    print(f"   Database: {db_path}")
    print(f"   Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    if not db_path.exists():
        print("\n❌ 数据库文件不存在！请先运行数据采集。")
        return {"passed": False, "reason": "Database not found"}
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 检查表是否存在
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    existing_tables = {row["name"] for row in cursor.fetchall()}
    
    has_raw_layer = "raw_papers" in existing_tables
    has_venues = "venues" in existing_tables
    has_paper_sources = "paper_sources" in existing_tables
    
    schema_version = detect_schema_version(cursor)
    print(f"\n📋 架构版本: {schema_version.upper()}")
    print(f"   Raw Layer 表: {'✅' if has_raw_layer else '❌'}")
    print(f"   Venues 表: {'✅' if has_venues else '❌'}")
    print(f"   Paper Sources 表: {'✅' if has_paper_sources else '❌'}")
    
    issues = []
    
    # ========================================
    # 1. Raw Layer 统计
    # ========================================
    print("\n" + "-" * 70)
    print("📦 1. Raw Layer 统计")
    print("-" * 70)
    
    raw_total = 0
    if has_raw_layer:
        cursor.execute("SELECT COUNT(*) as count FROM raw_papers")
        raw_total = cursor.fetchone()["count"]
        print(f"   总量: {raw_total:,}")
        
        if raw_total == 0:
            print("   ⚠️ Raw Layer 为空！请先运行 Ingestion Agent。")
            issues.append("Raw Layer is empty")
        else:
            # 近 7 天增量
            seven_days_ago = (datetime.now() - timedelta(days=7)).isoformat()
            cursor.execute(
                "SELECT COUNT(*) as count FROM raw_papers WHERE retrieved_at >= ?",
                (seven_days_ago,)
            )
            recent_count = cursor.fetchone()["count"]
            print(f"   近 7 天增量: {recent_count:,} ({recent_count/raw_total*100:.1f}%)")
            
            # 按 source 占比
            cursor.execute("""
                SELECT source, COUNT(*) as count 
                FROM raw_papers 
                GROUP BY source 
                ORDER BY count DESC
            """)
            print("   按数据源分布:")
            for row in cursor.fetchall():
                pct = row["count"] / raw_total * 100
                print(f"      - {row['source']}: {row['count']:,} ({pct:.1f}%)")
    else:
        print("   ⚠️ raw_papers 表不存在（使用旧架构）")
    
    # ========================================
    # 2. Structured Layer 统计
    # ========================================
    print("\n" + "-" * 70)
    print("📝 2. Structured Layer 统计")
    print("-" * 70)
    
    cursor.execute("SELECT COUNT(*) as count FROM papers")
    papers_total = cursor.fetchone()["count"]
    print(f"   总量: {papers_total:,}")
    
    # 结构化成功率
    if raw_total > 0:
        success_rate = papers_total / raw_total * 100
        print(f"   结构化成功率 (papers/raw): {success_rate:.1f}%")
        
        if success_rate < 50:
            issues.append(f"Low structuring rate: {success_rate:.1f}%")
    elif papers_total > 0:
        print("   (无 Raw Layer 对比数据)")
    
    # ========================================
    # 3. 摘要缺失率
    # ========================================
    print("\n" + "-" * 70)
    print("📄 3. 摘要缺失率")
    print("-" * 70)
    
    if raw_total > 0:
        cursor.execute("""
            SELECT COUNT(*) as count FROM raw_papers 
            WHERE abstract IS NULL OR abstract = ''
        """)
        raw_missing = cursor.fetchone()["count"]
        raw_missing_pct = raw_missing / raw_total * 100
        print(f"   Raw Layer 摘要缺失: {raw_missing:,} ({raw_missing_pct:.1f}%)")
        
        if raw_missing_pct > 30:
            issues.append(f"High abstract missing rate in raw: {raw_missing_pct:.1f}%")
    
    if papers_total > 0:
        cursor.execute("""
            SELECT COUNT(*) as count FROM papers 
            WHERE abstract IS NULL OR abstract = ''
        """)
        papers_missing = cursor.fetchone()["count"]
        papers_missing_pct = papers_missing / papers_total * 100
        print(f"   Structured Layer 摘要缺失: {papers_missing:,} ({papers_missing_pct:.1f}%)")
        
        if papers_missing_pct > 20:
            issues.append(f"High abstract missing rate in structured: {papers_missing_pct:.1f}%")
    
    # ========================================
    # 4. Venue 识别率
    # ========================================
    print("\n" + "-" * 70)
    print("🏛️ 4. Venue 识别率")
    print("-" * 70)
    
    if papers_total > 0:
        if schema_version == "new" and has_venues:
            cursor.execute("""
                SELECT COUNT(*) as count FROM papers 
                WHERE venue_id IS NULL
            """)
            no_venue = cursor.fetchone()["count"]
            no_venue_pct = no_venue / papers_total * 100
            print(f"   未识别 venue_id: {no_venue:,} ({no_venue_pct:.1f}%)")
            
            cursor.execute("""
                SELECT v.canonical_name, COUNT(*) as count 
                FROM papers p
                LEFT JOIN venues v ON p.venue_id = v.venue_id
                GROUP BY p.venue_id
                ORDER BY count DESC
                LIMIT 10
            """)
            print("   Top 10 Venue 分布:")
            for row in cursor.fetchall():
                name = row["canonical_name"] or "(UNKNOWN)"
                print(f"      - {name}: {row['count']:,}")
        else:
            # 旧架构：直接使用 venue 字段
            cursor.execute("""
                SELECT venue, COUNT(*) as count 
                FROM papers 
                GROUP BY venue 
                ORDER BY count DESC
                LIMIT 10
            """)
            print("   Top 10 Venue 分布 (旧架构):")
            for row in cursor.fetchall():
                print(f"      - {row['venue']}: {row['count']:,}")
    
    # ========================================
    # 5. 去重合并率
    # ========================================
    print("\n" + "-" * 70)
    print("🔗 5. 去重合并率 (Paper-Source 关联)")
    print("-" * 70)
    
    if has_paper_sources:
        cursor.execute("SELECT COUNT(*) as count FROM paper_sources")
        links_total = cursor.fetchone()["count"]
        print(f"   paper_sources 关联数: {links_total:,}")
        
        if papers_total > 0 and links_total > 0:
            avg_sources = links_total / papers_total
            print(f"   平均每篇论文对应 raw 记录数: {avg_sources:.2f}")
            
            cursor.execute("""
                SELECT paper_id, COUNT(*) as source_count 
                FROM paper_sources 
                GROUP BY paper_id 
                HAVING source_count > 1
            """)
            multi_source = len(cursor.fetchall())
            print(f"   多源合并的论文数: {multi_source:,}")
    else:
        print("   ⚠️ paper_sources 表不存在（使用旧架构）")
    
    # ========================================
    # 6. 近 30 天新增 paper 的 venue 分布
    # ========================================
    print("\n" + "-" * 70)
    print("📅 6. 近 30 天新增 Paper 的 Venue 分布")
    print("-" * 70)
    
    thirty_days_ago = (datetime.now() - timedelta(days=30)).isoformat()
    
    if schema_version == "new" and has_venues:
        cursor.execute("""
            SELECT v.canonical_name, COUNT(*) as count 
            FROM papers p
            LEFT JOIN venues v ON p.venue_id = v.venue_id
            WHERE p.created_at >= ?
            GROUP BY p.venue_id
            ORDER BY count DESC
        """, (thirty_days_ago,))
    else:
        cursor.execute("""
            SELECT venue, COUNT(*) as count 
            FROM papers
            WHERE created_at >= ?
            GROUP BY venue
            ORDER BY count DESC
        """, (thirty_days_ago,))
    
    recent_venue_dist = cursor.fetchall()
    if recent_venue_dist:
        total_recent = sum(r["count"] for r in recent_venue_dist)
        print(f"   近 30 天新增总量: {total_recent:,}")
        print("   分布:")
        for row in recent_venue_dist[:10]:
            if schema_version == "new" and has_venues:
                name = row["canonical_name"] or "(UNKNOWN)"
            else:
                name = row["venue"] or "(UNKNOWN)"
            pct = row["count"] / total_recent * 100
            print(f"      - {name}: {row['count']:,} ({pct:.1f}%)")
        
        # 检查是否异常偏斜（仅作为警告，不阻塞）
        if recent_venue_dist and recent_venue_dist[0]["count"] / total_recent > 0.95:
            print("   ⚠️ 警告: 数据偏向单一会议 (>95%)，建议补充更多来源")
    else:
        print("   无近期数据")
    
    conn.close()
    
    # ========================================
    # 验收结果
    # ========================================
    print("\n" + "=" * 70)
    print("🏁 验收结果")
    print("=" * 70)
    
    if schema_version == "legacy":
        print("⚠️ 当前使用旧架构，建议迁移到新的三层架构。")
        print("   迁移步骤：")
        print("   1. 备份现有数据库")
        print("   2. 运行 Ingestion Agent 重新采集数据")
        print("   3. 运行 Structuring Agent 处理数据")
    
    if not issues:
        print("✅ 通过！可以进入分析层。")
        return {"passed": True, "issues": [], "schema": schema_version}
    else:
        print("❌ 未通过，需要修复以下问题：")
        for i, issue in enumerate(issues, 1):
            print(f"   {i}. {issue}")
        print("\n建议操作：")
        print("   - 运行 Ingestion Agent 补充数据")
        print("   - 检查 Structuring Agent 的 venue 识别规则")
        print("   - 添加更多 venue alias 映射")
        return {"passed": False, "issues": issues, "schema": schema_version}


if __name__ == "__main__":
    result = run_dq_report()
    sys.exit(0 if result.get("passed", False) else 1)
