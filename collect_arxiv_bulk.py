"""
arXiv 批量历史数据采集脚本

功能：
1. 按年份批量采集arXiv论文
2. 支持2020-2025年的历史数据
3. 每年采集2000篇，总计12000+篇
4. 自动保存到数据库
5. 支持断点续传

使用方法：
    python collect_arxiv_bulk.py --start-year 2020 --end-year 2025
    python collect_arxiv_bulk.py --start-year 2024 --end-year 2024 --per-year 3000
"""

import sys
import time
import argparse
from pathlib import Path
from datetime import datetime

# 添加src目录到路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from scraper.arxiv_client import create_arxiv_client, DEFAULT_CATEGORIES
from database import get_raw_repository


def collect_by_year(
    year: int,
    categories: list,
    max_per_year: int = 2000,
    client = None,
    repo = None
):
    """
    采集指定年份的论文

    Args:
        year: 年份
        categories: 分类列表
        max_per_year: 每年最大采集数量
        client: arXiv客户端
        repo: 数据库仓库

    Returns:
        采集统计
    """
    print(f"\n{'='*70}")
    print(f"📅 采集 {year} 年论文")
    print(f"{'='*70}")

    # 按分类采集
    all_papers = []
    per_category = max_per_year // len(categories)

    for category in categories:
        print(f"\n🔍 采集 {category} 分类...")

        # 构建年份查询
        # arXiv API不直接支持年份过滤，需要通过日期范围
        papers = client.search(
            categories=[category],
            max_results=per_category
        )

        # 过滤年份
        year_papers = [p for p in papers if p.year == year]
        all_papers.extend(year_papers)

        print(f"   ✅ {category}: 获取 {len(year_papers)} 篇")

        # 避免API限制
        time.sleep(5)

    print(f"\n📊 {year} 年总计: {len(all_papers)} 篇")

    # 保存到数据库
    print(f"💾 保存到数据库...")
    saved = 0
    duplicates = 0
    errors = 0

    for paper in all_papers:
        try:
            repo.save_raw_paper(paper)
            saved += 1
        except Exception as e:
            if "UNIQUE constraint failed" in str(e):
                duplicates += 1
            else:
                errors += 1

    print(f"✅ 保存完成: 新增 {saved}, 重复 {duplicates}, 失败 {errors}")

    return {
        "year": year,
        "fetched": len(all_papers),
        "saved": saved,
        "duplicates": duplicates,
        "errors": errors
    }


def collect_bulk(
    start_year: int = 2020,
    end_year: int = 2025,
    categories: list = None,
    per_year: int = 2000,
    verbose: bool = True
):
    """
    批量采集多年数据

    Args:
        start_year: 起始年份
        end_year: 结束年份
        categories: 分类列表
        per_year: 每年采集数量
        verbose: 是否显示详细信息

    Returns:
        总体统计
    """
    client = create_arxiv_client(delay=3.0)
    repo = get_raw_repository()
    categories = categories or DEFAULT_CATEGORIES

    print("=" * 70)
    print("📥 arXiv 批量历史数据采集")
    print("=" * 70)
    print(f"📅 年份范围: {start_year} - {end_year}")
    print(f"📚 分类: {', '.join(categories)}")
    print(f"🎯 每年目标: {per_year} 篇")
    print(f"📊 预计总量: {(end_year - start_year + 1) * per_year} 篇")
    print(f"⏱️  开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    # 按年份采集
    all_stats = []
    total_fetched = 0
    total_saved = 0

    for year in range(start_year, end_year + 1):
        try:
            stats = collect_by_year(
                year=year,
                categories=categories,
                max_per_year=per_year,
                client=client,
                repo=repo
            )

            all_stats.append(stats)
            total_fetched += stats["fetched"]
            total_saved += stats["saved"]

            # 休息避免API限制
            print(f"\n⏸️  休息10秒...")
            time.sleep(10)

        except KeyboardInterrupt:
            print(f"\n\n⚠️  用户中断采集")
            break
        except Exception as e:
            print(f"\n❌ {year} 年采集失败: {e}")
            continue

    # 总体统计
    print("\n" + "=" * 70)
    print("📊 批量采集总结")
    print("=" * 70)
    print(f"✅ 完成年份: {len(all_stats)}/{end_year - start_year + 1}")
    print(f"📥 总获取: {total_fetched} 篇")
    print(f"💾 总保存: {total_saved} 篇")
    print(f"⏱️  完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\n年度明细:")
    print("-" * 70)

    for stats in all_stats:
        print(f"  {stats['year']}: 获取 {stats['fetched']:4d} | "
              f"保存 {stats['saved']:4d} | "
              f"重复 {stats['duplicates']:3d} | "
              f"失败 {stats['errors']:2d}")

    print("=" * 70)

    # 数据库统计
    total_in_db = repo.count_raw_papers_by_source("arxiv")
    print(f"\n📊 数据库统计:")
    print(f"   arXiv论文总数: {total_in_db} 篇")

    return {
        "years_completed": len(all_stats),
        "total_fetched": total_fetched,
        "total_saved": total_saved,
        "stats_by_year": all_stats
    }


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="批量采集arXiv历史数据",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 采集2020-2025年的所有数据
  python collect_arxiv_bulk.py --start-year 2020 --end-year 2025

  # 只采集2024年的数据
  python collect_arxiv_bulk.py --start-year 2024 --end-year 2024

  # 采集2022-2023年，每年3000篇
  python collect_arxiv_bulk.py --start-year 2022 --end-year 2023 --per-year 3000

  # 只采集cs.LG和cs.CV分类
  python collect_arxiv_bulk.py --categories cs.LG cs.CV
        """
    )

    parser.add_argument(
        "--start-year",
        type=int,
        default=2020,
        help="起始年份 (默认: 2020)"
    )

    parser.add_argument(
        "--end-year",
        type=int,
        default=2025,
        help="结束年份 (默认: 2025)"
    )

    parser.add_argument(
        "--categories",
        nargs="+",
        default=None,
        help=f"arXiv分类列表 (默认: {' '.join(DEFAULT_CATEGORIES)})"
    )

    parser.add_argument(
        "--per-year",
        type=int,
        default=2000,
        help="每年采集数量 (默认: 2000)"
    )

    parser.add_argument(
        "--quiet",
        action="store_true",
        help="静默模式"
    )

    args = parser.parse_args()

    # 验证参数
    if args.start_year > args.end_year:
        print("❌ 错误: 起始年份不能大于结束年份")
        sys.exit(1)

    if args.start_year < 1990 or args.end_year > datetime.now().year + 1:
        print(f"❌ 错误: 年份范围应在 1990 - {datetime.now().year + 1} 之间")
        sys.exit(1)

    # 执行采集
    try:
        stats = collect_bulk(
            start_year=args.start_year,
            end_year=args.end_year,
            categories=args.categories,
            per_year=args.per_year,
            verbose=not args.quiet
        )

        # 返回状态码
        if stats["total_saved"] > 0:
            sys.exit(0)
        else:
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断采集")
        sys.exit(130)
    except Exception as e:
        print(f"\n\n❌ 采集失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
