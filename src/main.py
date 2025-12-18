"""
DepthTrender - 顶会论文关键词追踪系统

三阶段工作流架构：
1. Ingestion Agent: 采集原始数据 → Raw Layer
2. Structuring Agent: 结构化处理 → Structured Layer
3. Analysis Agent: 关键词提取与分析 → Analysis Layer
"""

import argparse
import sys
from pathlib import Path
from typing import List, Optional, Dict
from datetime import datetime

# 添加 src 目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from agents import IngestionAgent, StructuringAgent, run_ingestion, run_structuring
from scraper import scrape_all_venues, scrape_all_s2_venues, S2_VENUES
from scraper.models import Paper
from extractor import extract_keywords_batch
from database import get_repository, get_analysis_repository
from analysis import get_analyzer
from visualization import generate_all_charts
from report import generate_report
from config import VENUES


def run_new_pipeline(
    sources: List[str] = None,
    arxiv_days: int = 7,
    venues: List[str] = None,
    years: List[int] = None,
    extractor: str = "yake",
    skip_ingestion: bool = False,
    skip_structuring: bool = False,
) -> str:
    """
    运行新的三阶段流程
    
    Args:
        sources: 数据源列表 ["arxiv", "openalex", "s2", "openreview"]
        arxiv_days: arXiv 采集天数
        venues: 会议列表
        years: 年份列表
        extractor: 提取器类型
        skip_ingestion: 跳过采集阶段
        skip_structuring: 跳过结构化阶段
        
    Returns:
        报告路径
    """
    print("=" * 60)
    print("🚀 DepthTrender - 三阶段工作流")
    print("=" * 60)
    print(f"⏰ 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Stage 1: Ingestion (Raw Layer)
    if not skip_ingestion:
        print("\n📥 阶段 1/3: 数据采集 (Ingestion)")
        print("-" * 40)
        
        ingestion_agent = IngestionAgent()
        ingestion_stats = ingestion_agent.run(
            sources=sources or ["arxiv", "openalex"],
            arxiv_days=arxiv_days,
            venues=venues,
            years=years,
        )
    else:
        print("\n⏭️ 跳过采集阶段")
    
    # Stage 2: Structuring (Structured Layer)
    if not skip_structuring:
        print("\n📝 阶段 2/3: 数据结构化 (Structuring)")
        print("-" * 40)
        
        structuring_agent = StructuringAgent()
        structuring_stats = structuring_agent.run()
    else:
        print("\n⏭️ 跳过结构化阶段")
    
    # Stage 3: Analysis (Analysis Layer)
    print("\n🔑 阶段 3/3: 关键词分析 (Analysis)")
    print("-" * 40)
    
    from agents.analysis_agent import AnalysisAgent
    
    # 运行关键词提取 (YAKE)
    analysis_agent = AnalysisAgent()
    extraction_result = analysis_agent.run(method="yake", limit=5000)
    print(f"   - YAKE 提取: {extraction_result['processed']} 篇, {extraction_result['keywords']} 个关键词")
    
    # 运行统计分析
    repo = get_repository()
    analyzer = get_analyzer()
    result = analyzer.analyze()
    
    print(f"✅ 分析完成")
    print(f"   - 论文总数: {result.total_papers:,}")
    print(f"   - 关键词总数: {result.total_keywords:,}")
    if result.venues:
        print(f"   - 覆盖会议: {', '.join(result.venues)}")
    if result.emerging_keywords:
        print(f"   - 新兴关键词: {', '.join(result.emerging_keywords[:5])}...")
    
    # 生成可视化
    print("\n🎨 生成图表和报告")
    print("-" * 40)
    
    charts = generate_all_charts(result)
    report_path = generate_report(result, charts)
    print(f"📄 报告已生成: {report_path}")
    
    # 完成
    print("\n" + "=" * 60)
    print(f"✅ 完成！{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    return str(report_path)


def run_pipeline(
    venues: Optional[List[str]] = None,
    years: Optional[List[int]] = None,
    limit: Optional[int] = None,
    extractor: str = "yake",
    skip_scrape: bool = False,
    source: str = "all",
    max_age_days: int = 7,
) -> str:
    """
    运行完整的处理流程（兼容旧接口）
    
    Args:
        venues: 要处理的会议列表
        years: 要处理的年份列表
        limit: 每个会议年份的论文限制
        extractor: 提取器类型
        skip_scrape: 跳过爬取
        source: 数据源
        max_age_days: 爬取间隔
        
    Returns:
        报告文件路径
    """
    print("=" * 60)
    print("🚀 DepthTrender - 顶会论文关键词追踪系统")
    print("=" * 60)
    print(f"⏰ 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    repo = get_repository()
    analyzer = get_analyzer()
    
    all_papers = []
    
    if not skip_scrape:
        print("\n📥 步骤 1/5: 爬取论文")
        print("-" * 40)
        
        # OpenReview 数据源
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
                    max_age_days=max_age_days,
                    repository=repo,
                )
                all_papers.extend(or_papers)
        
        # Semantic Scholar 数据源
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
                    max_age_days=max_age_days,
                    repository=repo,
                )
                all_papers.extend(s2_papers)
        
        papers = all_papers
        
        if not papers:
            print("⚠️ 未获取到任何论文")
            return None
        
        # 提取关键词
        print("\n🔑 步骤 2/5: 提取关键词")
        print("-" * 40)
        
        papers = extract_keywords_batch(papers, extractor_type=extractor)
        
        # 保存到数据库
        print("\n💾 步骤 3/5: 保存到数据库")
        print("-" * 40)
        
        saved_count = repo.save_papers(papers)
        print(f"✅ 成功保存 {saved_count} 篇论文")
    else:
        print("\n⏭️ 跳过爬取，使用数据库中的现有数据")
    
    # 统计分析
    print("\n📊 步骤 4/5: 统计分析")
    print("-" * 40)
    
    result = analyzer.analyze()
    print(f"✅ 分析完成")
    print(f"   - 论文总数: {result.total_papers:,}")
    print(f"   - 关键词总数: {result.total_keywords:,}")
    if result.venues:
        print(f"   - 覆盖会议: {', '.join(result.venues)}")
    
    # 生成可视化
    print("\n🎨 步骤 5/5: 生成图表和报告")
    print("-" * 40)
    
    charts = generate_all_charts(result)
    report_path = generate_report(result, charts)
    print(f"\n📄 报告已生成: {report_path}")
    
    print("\n" + "=" * 60)
    print(f"✅ 完成！{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    return str(report_path)


def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(
        description="DepthTrender - 顶会论文关键词追踪系统",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 新架构：三阶段工作流
  python -m src.main --new-pipeline
  
  # 新架构：仅采集 arXiv 最近 7 天
  python -m src.main --new-pipeline --source arxiv --arxiv-days 7
  
  # 旧接口：运行完整流程
  python src/main.py
  
  # 旧接口：指定会议和年份
  python src/main.py --venue ICLR --year 2024
        """,
    )
    
    # 新架构参数
    parser.add_argument(
        "--new-pipeline",
        action="store_true",
        help="使用新的三阶段工作流",
    )
    
    parser.add_argument(
        "--arxiv-days",
        type=int,
        default=7,
        help="arXiv 采集天数（默认: 7）",
    )
    
    parser.add_argument(
        "--skip-ingestion",
        action="store_true",
        help="跳过采集阶段",
    )
    
    parser.add_argument(
        "--skip-structuring",
        action="store_true",
        help="跳过结构化阶段",
    )
    
    # 原有参数
    parser.add_argument(
        "--venue",
        type=str,
        nargs="+",
        help="要处理的会议",
    )
    
    parser.add_argument(
        "--year",
        type=int,
        nargs="+",
        help="要处理的年份",
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
        help="跳过爬取",
    )
    
    parser.add_argument(
        "--source",
        type=str,
        choices=["openreview", "s2", "arxiv", "openalex", "all"],
        default="all",
        help="数据源",
    )
    
    parser.add_argument(
        "--max-age",
        type=int,
        default=7,
        help="爬取间隔天数",
    )
    
    args = parser.parse_args()
    
    if args.new_pipeline:
        # 新架构
        sources = None
        if args.source != "all":
            sources = [args.source]
        
        run_new_pipeline(
            sources=sources,
            arxiv_days=args.arxiv_days,
            venues=args.venue,
            years=args.year,
            extractor=args.extractor,
            skip_ingestion=args.skip_ingestion,
            skip_structuring=args.skip_structuring,
        )
    else:
        # 旧接口
        run_pipeline(
            venues=args.venue,
            years=args.year,
            limit=args.limit,
            extractor=args.extractor,
            skip_scrape=args.skip_scrape,
            source=args.source,
            max_age_days=args.max_age,
        )


if __name__ == "__main__":
    main()
