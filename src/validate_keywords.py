#!/usr/bin/env python
"""
关键词提取完整验收脚本

验收项目：
A. 覆盖率（Coverage）
B. 每篇关键词数量分布（Quantity）
C. 噪声率（Noise）
D. 分数健康（Score Sanity）
E. 幂等性（Idempotency）
"""
import sqlite3
import sys
from pathlib import Path
from collections import Counter

sys.path.insert(0, str(Path(__file__).parent))
from config import DATABASE_PATH
from extractor.keyword_filter import BANNED_WORDS, ENGLISH_STOPWORDS, DOMAIN_NOISE_WORDS


def main():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    
    print("=" * 70)
    print("📊 关键词提取完整验收报告")
    print("=" * 70)
    
    # ========================================
    # 验收 A：覆盖率
    # ========================================
    print("\n" + "-" * 70)
    print("A. 覆盖率（Coverage）")
    print("-" * 70)
    
    # 有摘要的论文数
    cur = conn.execute("""
        SELECT COUNT(*) FROM papers 
        WHERE abstract IS NOT NULL AND abstract != ''
    """)
    papers_with_abstract = cur.fetchone()[0]
    
    # 有 YAKE 关键词的论文数
    cur = conn.execute("""
        SELECT COUNT(DISTINCT paper_id) FROM paper_keywords WHERE method = 'yake'
    """)
    papers_with_yake = cur.fetchone()[0]
    
    coverage = papers_with_yake / papers_with_abstract * 100 if papers_with_abstract else 0
    print(f"   有摘要的论文: {papers_with_abstract}")
    print(f"   已提取 YAKE 关键词: {papers_with_yake}")
    print(f"   覆盖率: {coverage:.1f}% {'✅' if coverage >= 95 else '⚠️'}")
    
    # ========================================
    # 验收 B：每篇关键词数量分布
    # ========================================
    print("\n" + "-" * 70)
    print("B. 每篇关键词数量分布（Quantity）")
    print("-" * 70)
    
    cur = conn.execute("""
        SELECT paper_id, COUNT(*) as kw_count
        FROM paper_keywords WHERE method = 'yake'
        GROUP BY paper_id
    """)
    counts = [r["kw_count"] for r in cur.fetchall()]
    
    if counts:
        avg_count = sum(counts) / len(counts)
        min_count = min(counts)
        max_count = max(counts)
        zero_count = sum(1 for c in counts if c == 0)
        
        print(f"   平均每篇关键词数: {avg_count:.1f} {'✅' if 10 <= avg_count <= 20 else '⚠️'}")
        print(f"   范围: [{min_count}, {max_count}]")
        print(f"   关键词为 0 的论文: {zero_count} ({zero_count/len(counts)*100:.1f}%)")
        
        # 分布直方图
        bins = Counter()
        for c in counts:
            if c <= 5:
                bins["0-5"] += 1
            elif c <= 10:
                bins["6-10"] += 1
            elif c <= 15:
                bins["11-15"] += 1
            else:
                bins["16+"] += 1
        
        print("   分布:")
        for bin_name in ["0-5", "6-10", "11-15", "16+"]:
            pct = bins[bin_name] / len(counts) * 100
            print(f"      {bin_name}: {bins[bin_name]} ({pct:.1f}%)")
    
    # ========================================
    # 验收 C：噪声率
    # ========================================
    print("\n" + "-" * 70)
    print("C. 噪声率（Noise）")
    print("-" * 70)
    
    # 获取 Top-50 关键词
    cur = conn.execute("""
        SELECT keyword, COUNT(*) as cnt
        FROM paper_keywords WHERE method = 'yake'
        GROUP BY keyword
        ORDER BY cnt DESC
        LIMIT 50
    """)
    top_keywords = [(r["keyword"], r["cnt"]) for r in cur.fetchall()]
    
    all_noise = BANNED_WORDS | ENGLISH_STOPWORDS | DOMAIN_NOISE_WORDS
    
    noise_count = 0
    noise_keywords = []
    for kw, cnt in top_keywords:
        if kw in all_noise:
            noise_count += 1
            noise_keywords.append(kw)
    
    noise_rate = noise_count / len(top_keywords) * 100 if top_keywords else 0
    print(f"   Top-50 中噪声词数: {noise_count}")
    print(f"   噪声率: {noise_rate:.1f}% {'✅' if noise_rate < 10 else '❌'}")
    
    if noise_keywords:
        print(f"   噪声词: {', '.join(noise_keywords[:10])}")
    
    print("\n   Top-20 关键词:")
    for kw, cnt in top_keywords[:20]:
        marker = "⚠️" if kw in all_noise else ""
        print(f"      [{cnt:3d}] {kw} {marker}")
    
    # 检查纯数字/符号
    cur = conn.execute("""
        SELECT keyword FROM paper_keywords WHERE method = 'yake'
    """)
    all_keywords = [r["keyword"] for r in cur.fetchall()]
    
    import re
    numeric_keywords = [kw for kw in all_keywords if re.match(r'^[\d\s.,%-]+$', kw)]
    numeric_rate = len(numeric_keywords) / len(all_keywords) * 100 if all_keywords else 0
    print(f"\n   纯数字/符号关键词: {len(numeric_keywords)} ({numeric_rate:.2f}%) {'✅' if numeric_rate < 1 else '⚠️'}")
    
    # ========================================
    # 验收 D：分数健康
    # ========================================
    print("\n" + "-" * 70)
    print("D. 分数健康（Score Sanity）")
    print("-" * 70)
    
    cur = conn.execute("""
        SELECT MIN(score) as min_s, MAX(score) as max_s, AVG(score) as avg_s
        FROM paper_keywords WHERE method = 'yake'
    """)
    row = cur.fetchone()
    
    print(f"   YAKE 分数分布:")
    print(f"      MIN: {row['min_s']:.4f}")
    print(f"      MAX: {row['max_s']:.4f}")
    print(f"      AVG: {row['avg_s']:.4f}")
    
    # 检查极端值
    cur = conn.execute("""
        SELECT COUNT(*) FROM paper_keywords 
        WHERE method = 'yake' AND (score < 0.01 OR score > 0.99)
    """)
    extreme_count = cur.fetchone()[0]
    extreme_rate = extreme_count / len(all_keywords) * 100 if all_keywords else 0
    print(f"   极端值 (<0.01 或 >0.99): {extreme_count} ({extreme_rate:.1f}%)")
    
    # ========================================
    # 验收 E：幂等性
    # ========================================
    print("\n" + "-" * 70)
    print("E. 幂等性（Idempotency）")
    print("-" * 70)
    
    cur = conn.execute("""
        SELECT paper_id, keyword, method, COUNT(*) as cnt
        FROM paper_keywords
        GROUP BY paper_id, keyword, method
        HAVING cnt > 1
    """)
    duplicates = cur.fetchall()
    
    print(f"   重复记录数: {len(duplicates)} {'✅' if len(duplicates) == 0 else '❌'}")
    
    # ========================================
    # 验收 F：同义归并效果
    # ========================================
    print("\n" + "-" * 70)
    print("F. 同义归并效果")
    print("-" * 70)
    
    # 检查常见归并词
    synonym_targets = ["large language model", "diffusion model", "transformer", "vision transformer"]
    for target in synonym_targets:
        cur = conn.execute("""
            SELECT COUNT(*) FROM paper_keywords 
            WHERE method = 'yake' AND keyword = ?
        """, (target,))
        cnt = cur.fetchone()[0]
        if cnt > 0:
            print(f"   '{target}': {cnt} 次")
    
    # ========================================
    # 总结
    # ========================================
    print("\n" + "=" * 70)
    print("📋 验收总结")
    print("=" * 70)
    
    issues = []
    if coverage < 95:
        issues.append(f"覆盖率不足 ({coverage:.1f}%)")
    if noise_rate >= 10:
        issues.append(f"噪声率过高 ({noise_rate:.1f}%)")
    if len(duplicates) > 0:
        issues.append(f"存在重复记录 ({len(duplicates)})")
    
    if not issues:
        print("✅ 全部通过！")
    else:
        print("❌ 存在问题:")
        for issue in issues:
            print(f"   - {issue}")
    
    conn.close()


if __name__ == "__main__":
    main()
