"""
会议发现命令行工具

使用方法:
    python discover_venues.py --min-year 2022
"""

import sys
import argparse
from pathlib import Path

# 添加 src 到路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from scraper.venue_discovery import VenueDiscovery
from database import get_repository


def main():
    parser = argparse.ArgumentParser(description="从 OpenReview 发现和保存会议")
    parser.add_argument("--min-year", type=int, default=2022, help="最早年份")
    parser.add_argument("--include-workshops", action="store_true", help="包含 Workshop")
    parser.add_argument("--dry-run", action="store_true", help="只发现不保存")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("会议发现工具")
    print("=" * 60)
    
    # 发现会议
    discovery = VenueDiscovery()
    venues = discovery.discover_conferences(
        min_year=args.min_year,
        include_workshops=args.include_workshops
    )
    
    # 按会议名称分组
    venues_by_name = {}
    for venue in venues:
        if venue.name not in venues_by_name:
            venues_by_name[venue.name] = {
                "obj": venue,
                "openreview_ids": [],
                "years": []
            }
        venues_by_name[venue.name]["openreview_ids"].append(venue.venue_id)
        venues_by_name[venue.name]["years"].append(venue.year)
    
    print(f"\n发现 {len(venues_by_name)} 个独立会议（共 {len(venues)} 个会议年份）")
    
    # 显示统计
    summary = discovery.get_summary_by_domain(venues)
    print("\n按领域统计：")
    for domain, data in sorted(summary.items()):
        print(f"  {domain}: {data['count']} 个会议年份, "
              f"{len(data['venues'])} 个会议")
        print(f"    会议: {', '.join(data['venues'][:10])}")
        if len(data['venues']) > 10:
            print(f"    ... 还有 {len(data['venues']) - 10} 个")
    
    if args.dry_run:
        print("\n[Dry Run] 跳过保存到数据库")
        return
    
    # 保存到数据库
    print("\n保存到数据库...")
    repo = get_repository()
    saved_count = 0
    
    for name, data in venues_by_name.items():
        venue_obj = data["obj"]
        years = sorted(set(data["years"]), reverse=True)
        
        repo.structured.save_discovered_venue(
            name=name,
            full_name=venue_obj.full_name,
            domain=venue_obj.domain,
            tier=venue_obj.tier,
            venue_type="workshop" if venue_obj.is_workshop else "conference",
            openreview_ids=data["openreview_ids"],
            years=years
        )
        saved_count += 1
        
        if saved_count % 20 == 0:
            print(f"  已保存 {saved_count}/{len(venues_by_name)}...")
    
    print(f"\n✅ 保存完成！共保存 {saved_count} 个会议")
    
    # 显示最终统计
    stats = repo.structured.get_venue_stats()
    print("\n数据库统计：")
    print(f"  总计: {stats['total']} 个会议")
    print(f"  按领域: {stats['by_domain']}")
    print(f"  按等级: {stats['by_tier']}")


if __name__ == "__main__":
    main()
