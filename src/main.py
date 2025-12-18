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
from typing import List, Optional
from datetime import datetime

# 添加 src 目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from agents import IngestionAgent, StructuringAgent
from agents.analysis_agent import AnalysisAgent
from database import get_repository
from analysis import get_analyzer
from visualization import generate_all_charts
from report import generate_report


def run_pipeline(
    sources: List[str] = None,
    arxiv_days: int = 7,
    venues: List[str] = None,
    years: List[int] = None,
    extractor: str = "yake",
    limit: int = 5000,
    skip_ingestion: bool = False,
    skip_structuring: bool = False,
) -> str:
    """
    运行三阶段工作流
    
    Args:
        sources: 数据源列表 ["arxiv", "openalex", "s2", "openreview"]
        arxiv_days: arXiv 采集天数
        venues: 会议列表
        years: 年份列表
        extractor: 提取器类型 ("yake", "keybert", "both")
        limit: 每阶段处理上限
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
    
    analysis_agent = AnalysisAgent()
    
    # 根据 extractor 参数运行相应的提取器
    if extractor == "yake":
        result_yake = analysis_agent.run(method="yake", limit=limit)
        print(f"   - YAKE: {result_yake['processed']} 篇, {result_yake['keywords']} 个关键词")
    elif extractor == "keybert":
        result_kb = analysis_agent.run(method="keybert", limit=limit)
        print(f"   - KeyBERT: {result_kb['processed']} 篇, {result_kb['keywords']} 个关键词")
    elif extractor == "both":
        result_yake = analysis_agent.run(method="yake", limit=limit)
        print(f"   - YAKE: {result_yake['processed']} 篇, {result_yake['keywords']} 个关键词")
        result_kb = analysis_agent.run(method="keybert", limit=limit)
        print(f"   - KeyBERT: {result_kb['processed']} 篇, {result_kb['keywords']} 个关键词")
    
    # 运行统计分析
    analyzer = get_analyzer()
    result = analyzer.analyze()
    
    print(f"\n✅ 分析完成")
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


def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(
        description="DepthTrender - 顶会论文关键词追踪系统",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 运行完整三阶段工作流
  python src/main.py
  
  # 仅采集 arXiv 最近 7 天
  python src/main.py --source arxiv --arxiv-days 7
  
  # 指定会议和年份
  python src/main.py --venue ICLR NeurIPS --year 2024
  
  # 跳过采集，只运行结构化和分析
  python src/main.py --skip-ingestion
  
  # 使用 KeyBERT 提取器
  python src/main.py --extractor keybert
        """,
    )
    
    # 数据源参数
    parser.add_argument(
        "--source",
        type=str,
        choices=["arxiv", "openalex", "s2", "openreview", "all"],
        default="all",
        help="数据源 (arxiv/openalex/s2/openreview/all，默认: all)",
    )
    
    parser.add_argument(
        "--arxiv-days",
        type=int,
        default=7,
        help="arXiv 采集天数（默认: 7）",
    )
    
    # 会议和年份
    parser.add_argument(
        "--venue",
        type=str,
        nargs="+",
        help="要处理的会议（如: ICLR NeurIPS CVPR）",
    )
    
    parser.add_argument(
        "--year",
        type=int,
        nargs="+",
        help="要处理的年份（如: 2024 2023）",
    )
    
    # 处理限制
    parser.add_argument(
        "--limit",
        type=int,
        default=5000,
        help="每阶段处理上限（默认: 5000）",
    )
    
    # 提取器
    parser.add_argument(
        "--extractor",
        type=str,
        choices=["yake", "keybert", "both"],
        default="yake",
        help="关键词提取器（默认: yake）",
    )
    
    # 跳过选项
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
    
    args = parser.parse_args()
    
    # 解析数据源
    sources = None
    if args.source != "all":
        sources = [args.source]
    
    # 运行三阶段工作流
    run_pipeline(
        sources=sources,
        arxiv_days=args.arxiv_days,
        venues=args.venue,
        years=args.year,
        extractor=args.extractor,
        limit=args.limit,
        skip_ingestion=args.skip_ingestion,
        skip_structuring=args.skip_structuring,
    )


if __name__ == "__main__":
    main()
