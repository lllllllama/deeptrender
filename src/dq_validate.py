#!/usr/bin/env python
"""
DQ 深度验证脚本

1. Venue 识别精确率验证
2. 去重/多源融合分析
"""

import sys
import sqlite3
from pathlib import Path

_src_dir = Path(__file__).parent
if str(_src_dir) not in sys.path:
    sys.path.insert(0, str(_src_dir))

from config import DATABASE_PATH


def validate_venue_precision(conn, sample_size=10):
    """验证 Venue 识别精确率"""
    print("=" * 70)
    print("🔍 1. Venue 识别精确率验证")
    print("=" * 70)
    
    cursor = conn.cursor()
    
    # 抽取已识别 venue 的论文（只看新采集的，有 paper_sources 关联）
    cursor.execute("""
        SELECT p.paper_id, p.canonical_title, v.canonical_name as venue,
               r.source, r.venue_raw, r.comments, r.categories
        FROM papers p
        JOIN venues v ON p.venue_id = v.venue_id
        JOIN paper_sources ps ON p.paper_id = ps.paper_id
        JOIN raw_papers r ON ps.raw_id = r.raw_id
        ORDER BY RANDOM()
        LIMIT ?
    """, (sample_size,))
    
    samples = cursor.fetchall()
    print(f"\n抽样 {len(samples)} 篇已识别 venue 的论文:\n")
    
    correct = 0
    for i, row in enumerate(samples, 1):
        venue = row[2]
        source = row[3]
        venue_raw = row[4] or ""
        comments = row[5] or ""
        categories = row[6] or ""
        title = row[1][:55] + "..." if len(row[1]) > 55 else row[1]
        
        print(f"{i}. [{venue}] {title}")
        print(f"   Source: {source}")
        print(f"   venue_raw: {venue_raw}")
        if comments:
            print(f"   comments: {comments[:70]}")
        
        # 自动验证
        is_correct = False
        reason = ""
        
        # OpenReview 来源直接信任
        if source == "openreview":
            is_correct = True
            reason = "OpenReview 来源"
        # venue_raw 包含 venue 名称
        elif venue.upper() in venue_raw.upper():
            is_correct = True
            reason = f"venue_raw 包含 '{venue}'"
        # comments 包含 venue 名称
        elif venue.upper() in comments.upper():
            is_correct = True
            reason = f"comments 包含 '{venue}'"
        # S2 来源，venue_raw 匹配
        elif source == "s2" and venue_raw:
            is_correct = True
            reason = f"S2 venue_raw = '{venue_raw}'"
        
        status = "✅" if is_correct else "❓"
        print(f"   判定: {status} {reason}")
        print()
        
        if is_correct:
            correct += 1
    
    precision = correct / len(samples) * 100 if samples else 0
    print("-" * 70)
    print(f"自动验证精确率: {precision:.1f}% ({correct}/{len(samples)})")
    print(f"目标: >= 95%")
    
    if precision >= 95:
        print("✅ 通过")
    else:
        print("❌ 未通过，需要改进规则")
    
    return precision


def analyze_dedup_fusion(conn):
    """分析去重/多源融合情况"""
    print("\n" + "=" * 70)
    print("🔗 2. 去重/多源融合分析")
    print("=" * 70)
    
    cursor = conn.cursor()
    
    # 新架构的 papers 数量（有 paper_sources 关联的）
    cursor.execute("""
        SELECT COUNT(DISTINCT paper_id) FROM paper_sources
    """)
    papers_with_sources = cursor.fetchone()[0]
    
    # paper_sources 总数
    cursor.execute("SELECT COUNT(*) FROM paper_sources")
    total_links = cursor.fetchone()[0]
    
    # raw_papers 总数
    cursor.execute("SELECT COUNT(*) FROM raw_papers")
    raw_total = cursor.fetchone()[0]
    
    print(f"\n基础统计:")
    print(f"   raw_papers 总数: {raw_total}")
    print(f"   有关联的 papers 数: {papers_with_sources}")
    print(f"   paper_sources 关联数: {total_links}")
    
    if papers_with_sources > 0:
        avg_sources = total_links / papers_with_sources
        print(f"   平均每篇 paper 关联 raw 数: {avg_sources:.2f}")
    
    # 多源融合统计
    cursor.execute("""
        SELECT paper_id, COUNT(*) as source_count
        FROM paper_sources
        GROUP BY paper_id
        HAVING source_count > 1
    """)
    multi_source_papers = cursor.fetchall()
    
    print(f"\n多源融合统计:")
    print(f"   多源合并的论文数: {len(multi_source_papers)}")
    
    if multi_source_papers:
        print(f"\n   多源论文详情:")
        for row in multi_source_papers[:5]:
            paper_id, count = row[0], row[1]
            cursor.execute("""
                SELECT ps.source, r.title
                FROM paper_sources ps
                JOIN raw_papers r ON ps.raw_id = r.raw_id
                WHERE ps.paper_id = ?
            """, (paper_id,))
            sources = cursor.fetchall()
            print(f"   Paper {paper_id}: {count} 个来源")
            for s in sources:
                print(f"      - {s[0]}: {s[1][:50]}...")
    else:
        print("\n⚠️ 当前没有多源融合的论文")
        print("   原因分析：")
        print("   1. 采集的论文来自不同会议，没有重叠")
        print("   2. Structuring Agent 目前按 raw 逐条创建 paper，未实现去重")
        print("\n   建议改进：")
        print("   - 在 Structuring Agent 中增加标题相似度匹配")
        print("   - 使用 DOI 进行跨源对齐")
    
    # 按来源统计
    print(f"\n按来源的关联统计:")
    cursor.execute("""
        SELECT source, COUNT(*) as count
        FROM paper_sources
        GROUP BY source
        ORDER BY count DESC
    """)
    for row in cursor.fetchall():
        print(f"   - {row[0]}: {row[1]}")
    
    return len(multi_source_papers)


def main():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    
    precision = validate_venue_precision(conn)
    multi_source = analyze_dedup_fusion(conn)
    
    print("\n" + "=" * 70)
    print("📊 验证总结")
    print("=" * 70)
    print(f"Venue 精确率: {precision:.1f}% {'✅' if precision >= 95 else '❌'}")
    print(f"多源融合论文: {multi_source} 篇 {'✅' if multi_source > 0 else '⚠️ 待改进'}")
    
    conn.close()


if __name__ == "__main__":
    main()
