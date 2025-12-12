"""
DepthTrender - 顶会论文关键词追踪系统

主程序入口，提供完整的工作流：
1. 爬取论文（支持 OpenReview 和 Semantic Scholar）
2. 提取关键词
3. 存储到数据库
4. 统计分析
5. 生成可视化
6. 生成报告
"""

import argparse
import sys
from pathlib import Path
from typing import List, Optional
from datetime import datetime

# 添加 src 目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from scraper import scrape_all_venues, scrape_venue
from scraper.semantic_scholar import scrape_all_s2_venues, S2_VENUES
from scraper.models import Paper
from extractor import extract_keywords_batch
from database import get_repository
from analysis import get_analyzer
from visualization import generate_all_charts
from report import generate_report
from config import VENUES, VenueConfig


def run_pipeline(
    venues: Optional[List[str]] = None,
    years: Optional[List[int]] = None,
    limit: Optional[int] = None,
    extractor: str = "yake",
    skip_scrape: bool = False,
    source: str = "all",  # "openreview", "s2", "all"
) -> str:
    """
    运行完整的处理流程
    
    Args:
        venues: 要处理的会议列表（默认全部）
        years: 要处理的年份列表（默认使用配置）
        limit: 每个会议年份的论文限制
        extractor: 提取器类型（"yake", "keybert", "both"）
        skip_scrape: 是否跳过爬取（直接使用数据库中的数据）
        source: 数据源（"openreview", "s2", "all"）
        
    Returns:
        报告文件路径
    """
    print("=" * 60)
    print("🚀 DepthTrender - 顶会论文关键词追踪系统")
    print("=" * 60)
    print(f"⏰ 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 初始化组件
    repo = get_repository()
    analyzer = get_analyzer()
    
    all_papers = []
    
    if not skip_scrape:
        # 1. 爬取论文
        print("\n📥 步骤 1/5: 爬取论文")
        print("-" * 40)
        
        # ========== OpenReview 数据源 ==========
        if source in ("openreview", "all"):
            print("\n📚 数据源: OpenReview")
            venue_configs = VENUES
            if venues:
                venue_configs = {k: v for k, v in VENUES.items() if k in venues}
            
            if venue_configs:
                or_papers = scrape_all_venues(
                    venues=venue_configs,
                    years=years,
                    limit_per_venue=limit,
                )
                all_papers.extend(or_papers)
        
        # ========== Semantic Scholar 数据源 ==========
        if source in ("s2", "all"):
            print("\n📚 数据源: Semantic Scholar")
            s2_venues = S2_VENUES
            if venues:
                s2_venues = {k: v for k, v in S2_VENUES.items() if k in venues}
            
            if s2_venues:
                s2_papers = scrape_all_s2_venues(
                    venues=s2_venues,
                    years=years,
                    limit_per_venue=limit,
                )
                all_papers.extend(s2_papers)
        
        papers = all_papers
        
        if not papers:
            print("⚠️ 未获取到任何论文，请检查网络连接和会议配置")
            return None
        
        # 2. 提取关键词
        print("\n🔑 步骤 2/5: 提取关键词")
        print("-" * 40)
        
        papers = extract_keywords_batch(papers, extractor_type=extractor)
        
        # 3. 保存到数据库
        print("\n💾 步骤 3/5: 保存到数据库")
        print("-" * 40)
        
        saved_count = repo.save_papers(papers)
        print(f"✅ 成功保存 {saved_count} 篇论文")
        
        # 记录爬取日志
        for paper in papers:
            pass  # 日志已在 save_paper 中处理
    else:
        print("\n⏭️ 跳过爬取，使用数据库中的现有数据")
    
    # 4. 统计分析
    print("\n📊 步骤 4/5: 统计分析")
    print("-" * 40)
    
    result = analyzer.analyze()
    print(f"✅ 分析完成")
    print(f"   - 论文总数: {result.total_papers:,}")
    print(f"   - 关键词总数: {result.total_keywords:,}")
    print(f"   - 覆盖会议: {', '.join(result.venues)}")
    
    # 5. 生成可视化
    print("\n🎨 步骤 5/5: 生成图表和报告")
    print("-" * 40)
    
    charts = generate_all_charts(result)
    
    # 生成报告
    report_path = generate_report(result, charts)
    print(f"\n📄 报告已生成: {report_path}")
    
    # 完成
    print("\n" + "=" * 60)
    print(f"✅ 完成！耗时: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    return str(report_path)


def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(
        description="DepthTrender - 顶会论文关键词追踪系统",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 运行完整流程（所有会议，所有年份）
  python -m src.main
  
  # 只处理 ICLR 2024
  python -m src.main --venue ICLR --year 2024
  
  # 限制每个会议年份只处理 10 篇论文（测试用）
  python -m src.main --limit 10
  
  # 使用 KeyBERT 提取器
  python -m src.main --extractor keybert
  
  # 跳过爬取，只重新生成报告
  python -m src.main --skip-scrape
        """,
    )
    
    parser.add_argument(
        "--venue",
        type=str,
        nargs="+",
        help="要处理的会议（如 ICLR NeurIPS ICML）",
    )
    
    parser.add_argument(
        "--year",
        type=int,
        nargs="+",
        help="要处理的年份（如 2024 2023）",
    )
    
    parser.add_argument(
        "--limit",
        type=int,
        help="每个会议年份的论文数量限制",
    )
    
    parser.add_argument(
        "--extractor",
        type=str,
        choices=["yake", "keybert", "both"],
        default="yake",
        help="关键词提取器（默认: yake）",
    )
    
    parser.add_argument(
        "--skip-scrape",
        action="store_true",
        help="跳过爬取，使用数据库中的现有数据",
    )
    
    parser.add_argument(
        "--source",
        type=str,
        choices=["openreview", "s2", "all"],
        default="all",
        help="数据源（openreview/s2/all，默认: all）",
    )
    
    args = parser.parse_args()
    
    run_pipeline(
        venues=args.venue,
        years=args.year,
        limit=args.limit,
        extractor=args.extractor,
        skip_scrape=args.skip_scrape,
        source=args.source,
    )


if __name__ == "__main__":
    main()
