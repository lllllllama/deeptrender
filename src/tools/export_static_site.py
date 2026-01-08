#!/usr/bin/env python3
"""
静态站点导出工具

将 DeepTrender 的数据和静态资源导出到 docs/ 目录，用于 GitHub Pages 部署。
"""

import sys
import json
import shutil
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent))

from database import get_repository
from config import VENUES, ROOT_DIR


class StaticSiteExporter:
    """静态站点导出器"""
    
    def __init__(self, output_dir: str = "docs", top_keywords: int = 300):
        self.output_dir = Path(output_dir)
        self.data_dir = self.output_dir / "data"
        self.venues_data_dir = self.data_dir / "venues"
        self.arxiv_data_dir = self.data_dir / "arxiv"
        self.top_keywords = top_keywords
        
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.venues_data_dir.mkdir(parents=True, exist_ok=True)
        self.arxiv_data_dir.mkdir(parents=True, exist_ok=True)
        
        self.repo = get_repository()
        self.stats = {
            "venues_exported": 0,
            "arxiv_exported": 0,
            "files_copied": 0,
            "total_size_bytes": 0,
        }
    
    def export_venues_index(self) -> int:
        """导出会议索引"""
        print("\n📊 导出会议索引...")
        
        venues_data = []
        all_summaries = self.repo.analysis.get_all_venue_summaries()
        summary_map = {s["venue"]: s for s in all_summaries if s.get("year") is None}
        
        for venue_key, venue_config in VENUES.items():
            venue_name = venue_config.name
            summary = summary_map.get(venue_name)
            
            if summary:
                paper_count = summary.get("paper_count", 0)
                top_keywords = summary.get("top_keywords", [])[:10]
            else:
                paper_count = self.repo.get_paper_count(venue=venue_name)
                top_kw = self.repo.get_top_keywords(venue=venue_name, limit=10)
                top_keywords = [{"keyword": kw, "count": c} for kw, c in top_kw]
            
            years = self.repo.get_all_years(venue=venue_name)
            
            venue_data = {
                "name": venue_name,
                "full_name": venue_config.full_name,
                "domain": getattr(venue_config, "domain", "ML"),
                "tier": "A",
                "years_available": sorted(years, reverse=True),
                "paper_count": paper_count,
                "top_keywords": top_keywords,
            }
            venues_data.append(venue_data)
        
        output_file = self.venues_data_dir / "venues_index.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(venues_data, f, indent=2, ensure_ascii=False)
        
        self.stats["total_size_bytes"] += output_file.stat().st_size
        print(f"   ✅ 已导出 {len(venues_data)} 个会议")
        return len(venues_data)
    
    def export_venue_top_keywords(self, venue_name: str, top_n: int = 50) -> bool:
        """导出单个会议的年度 top keywords"""
        years = self.repo.get_all_years(venue=venue_name)
        if not years:
            return False
        
        yearly_data = {}
        for year in sorted(years):
            top_keywords = self.repo.get_top_keywords(venue=venue_name, year=year, limit=top_n)
            yearly_data[str(year)] = [
                {"keyword": kw, "count": count, "rank": rank + 1}
                for rank, (kw, count) in enumerate(top_keywords)
            ]
        
        output_file = self.venues_data_dir / f"venue_{venue_name}_top_keywords.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(yearly_data, f, indent=2, ensure_ascii=False)
        
        self.stats["total_size_bytes"] += output_file.stat().st_size
        return True
    
    def export_venue_keyword_trends(self, venue_name: str, max_keywords: int = 300) -> bool:
        """导出单个会议的关键词趋势"""
        years = self.repo.get_all_years(venue=venue_name)
        if not years:
            return False
        
        keyword_yearly_counts = defaultdict(dict)
        keyword_yearly_ranks = defaultdict(dict)
        
        for year in sorted(years):
            top_keywords = self.repo.get_top_keywords(venue=venue_name, year=year, limit=100)
            for rank, (kw, count) in enumerate(top_keywords, start=1):
                keyword_yearly_counts[kw][year] = count
                keyword_yearly_ranks[kw][year] = rank
        
        keyword_totals = {kw: sum(counts.values()) for kw, counts in keyword_yearly_counts.items()}
        top_keywords_list = sorted(keyword_totals.keys(), key=lambda k: keyword_totals[k], reverse=True)[:max_keywords]
        
        trends_data = {}
        for kw in top_keywords_list:
            yearly_data = []
            for year in sorted(years):
                count = keyword_yearly_counts[kw].get(year, 0)
                rank = keyword_yearly_ranks[kw].get(year, 0)
                yearly_data.append({"year": year, "count": count, "rank": rank})
            trends_data[kw] = yearly_data
        
        output_file = self.venues_data_dir / f"venue_{venue_name}_keyword_trends.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(trends_data, f, indent=2, ensure_ascii=False)
        
        self.stats["total_size_bytes"] += output_file.stat().st_size
        return True
    
    def export_venue_keywords_index(self, venue_name: str) -> bool:
        """导出会议关键词索引"""
        top_keywords = self.repo.get_top_keywords(venue=venue_name, limit=self.top_keywords)
        if not top_keywords:
            return False
        
        keywords_list = [kw for kw, _ in top_keywords]
        output_file = self.venues_data_dir / f"venue_{venue_name}_keywords_index.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(keywords_list, f, indent=2, ensure_ascii=False)
        
        self.stats["total_size_bytes"] += output_file.stat().st_size
        return True
    
    def export_all_venues(self) -> Dict:
        """导出所有会议数据"""
        print("\n🏛️ 导出会议数据...")
        venues_count = self.export_venues_index()
        
        exported_venues = []
        for venue_key, venue_config in VENUES.items():
            venue_name = venue_config.name
            print(f"   📄 导出 {venue_name}...")
            
            if self.export_venue_top_keywords(venue_name, top_n=50):
                if self.export_venue_keyword_trends(venue_name, max_keywords=self.top_keywords):
                    self.export_venue_keywords_index(venue_name)
                    exported_venues.append(venue_name)
        
        self.stats["venues_exported"] = len(exported_venues)
        print(f"\n   ✅ 已导出 {len(exported_venues)} 个会议的详细数据")
        return {"venues_count": venues_count, "venues_exported": exported_venues}
    
    def export_arxiv_timeseries(self) -> int:
        print("\n📈 导出 arXiv 时间序列...")
        
        granularities = ["day", "week", "month", "year"]
        categories = ["ALL", "cs.LG", "cs.CV", "cs.CL", "cs.AI", "cs.RO"]
        exported_count = 0
        
        for granularity in granularities:
            for category in categories:
                try:
                    data = self.repo.analysis.get_arxiv_timeseries(category, granularity)
                    if not data:
                        continue
                    
                    output_data = {
                        "granularity": granularity,
                        "category": category,
                        "data": data,
                        "cached": True,
                        "exported_at": datetime.now().isoformat()
                    }
                    
                    filename = f"arxiv_timeseries_{granularity}_{category}.json"
                    output_file = self.arxiv_data_dir / filename
                    
                    with open(output_file, "w", encoding="utf-8") as f:
                        json.dump(output_data, f, indent=2, ensure_ascii=False)
                    
                    self.stats["total_size_bytes"] += output_file.stat().st_size
                    exported_count += 1
                except Exception as e:
                    print(f"   ⚠️  跳过 {granularity}/{category}: {e}")
        
        print(f"   ✅ 已导出 {exported_count} 个时间序列文件")
        return exported_count
    
    def export_arxiv_emerging(self) -> int:
        print("\n🚀 导出 arXiv 新兴关键词...")
        
        categories = ["ALL", "cs.LG", "cs.CV", "cs.CL", "cs.AI", "cs.RO"]
        exported_count = 0
        
        for category in categories:
            try:
                topics = self.repo.analysis.get_emerging_topics(
                    category=category,
                    limit=50,
                    min_growth_rate=1.5
                )
                
                if not topics:
                    continue
                
                filename = f"arxiv_emerging_{category}.json"
                output_file = self.arxiv_data_dir / filename
                
                with open(output_file, "w", encoding="utf-8") as f:
                    json.dump(topics, f, indent=2, ensure_ascii=False)
                
                self.stats["total_size_bytes"] += output_file.stat().st_size
                exported_count += 1
            except Exception as e:
                print(f"   ⚠️  跳过 {category}: {e}")
        
        print(f"   ✅ 已导出 {exported_count} 个新兴关键词文件")
        return exported_count
    
    def export_arxiv_stats(self) -> bool:
        print("\n📊 导出 arXiv 统计...")
        
        try:
            total_papers = self.repo.raw.get_raw_paper_count(source="arxiv")
            
            categories_stats = {}
            for category in ["cs.LG", "cs.CL", "cs.CV", "cs.AI", "cs.RO"]:
                with self.repo._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT COUNT(*) as count
                        FROM raw_papers
                        WHERE source = 'arxiv' AND categories LIKE ?
                    """, (f"%{category}%",))
                    count = cursor.fetchone()["count"]
                    categories_stats[category] = count
            
            with self.repo._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT MIN(retrieved_at) as min_date, MAX(retrieved_at) as max_date
                    FROM raw_papers
                    WHERE source = 'arxiv'
                """)
                row = cursor.fetchone()
                date_range = {
                    "min": row["min_date"] if row["min_date"] else None,
                    "max": row["max_date"] if row["max_date"] else None
                }
            
            latest_update = self.repo.analysis.get_meta("arxiv_last_run_ALL_year")
            
            stats_data = {
                "total_papers": total_papers,
                "categories": categories_stats,
                "date_range": date_range,
                "latest_update": latest_update,
                "exported_at": datetime.now().isoformat()
            }
            
            output_file = self.arxiv_data_dir / "arxiv_stats.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(stats_data, f, indent=2, ensure_ascii=False)
            
            self.stats["total_size_bytes"] += output_file.stat().st_size
            print("   ✅ 已导出 arXiv 统计")
            return True
        except Exception as e:
            print(f"   ⚠️  导出失败: {e}")
            return False
    
    def export_all_arxiv(self) -> Dict:
        print("\n📡 导出 arXiv 数据...")
        
        results = {
            "timeseries": self.export_arxiv_timeseries(),
            "emerging": self.export_arxiv_emerging(),
            "stats": self.export_arxiv_stats(),
        }
        
        self.stats["arxiv_exported"] = sum(1 for v in results.values() if v)
        return results
    
    def copy_static_assets(self) -> int:
        """复制静态资源"""
        print("\n📦 复制静态资源...")
        src_static = ROOT_DIR / "src" / "web" / "static"
        
        if not src_static.exists():
            print("   ⚠️  静态资源目录不存在")
            return 0
        
        copied_count = 0
        for item in src_static.rglob("*"):
            if item.is_file():
                rel_path = item.relative_to(src_static)
                dest_path = self.output_dir / rel_path
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, dest_path)
                copied_count += 1
                self.stats["total_size_bytes"] += dest_path.stat().st_size
        
        self.stats["files_copied"] = copied_count
        print(f"   ✅ 已复制 {copied_count} 个文件")
        return copied_count
    
    def transform_paths_in_html(self) -> int:
        """转换 HTML 路径"""
        print("\n🔧 转换 HTML 路径...")
        html_files = list(self.output_dir.glob("*.html"))
        processed_count = 0
        
        for html_file in html_files:
            content = html_file.read_text(encoding="utf-8")
            original = content
            content = content.replace('href="/static/', 'href="./static/')
            content = content.replace('src="/static/', 'src="./static/')
            
            if content != original:
                html_file.write_text(content, encoding="utf-8")
                processed_count += 1
        
        print(f"   ✅ 已处理 {processed_count} 个 HTML 文件")
        return processed_count
    
    def export_all(self) -> Dict:
        """执行完整导出"""
        start_time = datetime.now()
        print("=" * 60)
        print("🚀 开始导出静态站点")
        print("=" * 60)
        
        venues_result = self.export_all_venues()
        arxiv_result = self.export_all_arxiv()
        self.copy_static_assets()
        self.transform_paths_in_html()
        
        duration = (datetime.now() - start_time).total_seconds()
        
        summary = {
            **self.stats,
            "output_dir": str(self.output_dir.absolute()),
            "total_size_mb": self.stats["total_size_bytes"] / 1024 / 1024,
            "export_time": f"{duration:.2f}s",
            "venues": venues_result,
            "arxiv": arxiv_result,
        }
        
        print("\n" + "=" * 60)
        print("✅ 导出完成")
        print("=" * 60)
        print(f"📁 输出目录: {summary['output_dir']}")
        print(f"🏛️  会议数据: {summary['venues_exported']} 个会议")
        print(f"📡 arXiv 数据: {summary['arxiv_exported']} 个文件")
        print(f"📦 静态资源: {summary['files_copied']} 个文件")
        print(f"💾 总大小: {summary['total_size_mb']:.2f} MB")
        print(f"⏱️  耗时: {summary['export_time']}")
        print("=" * 60)
        
        summary_file = self.output_dir / "export_summary.json"
        with open(summary_file, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        return summary


def main():
    parser = argparse.ArgumentParser(description="导出 DeepTrender 静态站点")
    parser.add_argument("--output-dir", default="docs", help="输出目录")
    parser.add_argument("--top-keywords", type=int, default=300, help="最大关键词数")
    args = parser.parse_args()
    
    exporter = StaticSiteExporter(output_dir=args.output_dir, top_keywords=args.top_keywords)
    
    try:
        exporter.export_all()
        print(f"\n💡 本地测试: python -m http.server -d {args.output_dir} 8000")
        return 0
    except Exception as e:
        print(f"\n❌ 导出失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
