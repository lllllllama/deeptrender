#!/usr/bin/env python3
"""Static site export tool.

Exports data and static assets into a docs-friendly folder layout.
"""

import sys
import json
import shutil
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict
from collections import defaultdict

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(errors="replace")

sys.path.insert(0, str(Path(__file__).parent.parent))

from database import get_repository
from config import VENUES, ROOT_DIR


class StaticSiteExporter:
    """Exporter for static website data and assets."""

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
        venues_data = []
        all_summaries = self.repo.analysis.get_all_venue_summaries()
        summary_map = {s["venue"]: s for s in all_summaries if s.get("year") is None}

        for _, venue_config in VENUES.items():
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
        return len(venues_data)

    def export_venue_top_keywords(self, venue_name: str, top_n: int = 50) -> bool:
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
        top_keywords = sorted(keyword_totals.keys(), key=lambda k: keyword_totals[k], reverse=True)[:max_keywords]

        trends_data = {}
        for kw in top_keywords:
            yearly_points = []
            for year in sorted(years):
                yearly_points.append(
                    {
                        "year": year,
                        "count": keyword_yearly_counts[kw].get(year, 0),
                        "rank": keyword_yearly_ranks[kw].get(year, 0),
                    }
                )
            trends_data[kw] = yearly_points

        output_file = self.venues_data_dir / f"venue_{venue_name}_keyword_trends.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(trends_data, f, indent=2, ensure_ascii=False)

        self.stats["total_size_bytes"] += output_file.stat().st_size
        return True

    def export_venue_keywords_index(self, venue_name: str) -> bool:
        top_keywords = self.repo.get_top_keywords(venue=venue_name, limit=self.top_keywords)
        if not top_keywords:
            return False

        output_file = self.venues_data_dir / f"venue_{venue_name}_keywords_index.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump([kw for kw, _ in top_keywords], f, indent=2, ensure_ascii=False)

        self.stats["total_size_bytes"] += output_file.stat().st_size
        return True

    def export_all_venues(self) -> Dict:
        venues_count = self.export_venues_index()
        exported_venues = []

        for _, venue_config in VENUES.items():
            venue_name = venue_config.name
            if self.export_venue_top_keywords(venue_name, top_n=50):
                if self.export_venue_keyword_trends(venue_name, max_keywords=self.top_keywords):
                    self.export_venue_keywords_index(venue_name)
                    exported_venues.append(venue_name)

        self.stats["venues_exported"] = len(exported_venues)
        return {"venues_count": venues_count, "venues_exported": exported_venues}

    def export_arxiv_timeseries(self) -> int:
        granularities = ["day", "week", "month", "year"]
        categories = ["ALL", "cs.LG", "cs.CV", "cs.CL", "cs.AI", "cs.RO"]
        exported_count = 0

        for granularity in granularities:
            for category in categories:
                data = self.repo.analysis.get_arxiv_timeseries(category, granularity)
                if not data:
                    continue

                output_data = {
                    "granularity": granularity,
                    "category": category,
                    "data": data,
                    "cached": True,
                    "exported_at": datetime.now().isoformat(),
                }
                output_file = self.arxiv_data_dir / f"arxiv_timeseries_{granularity}_{category}.json"
                with open(output_file, "w", encoding="utf-8") as f:
                    json.dump(output_data, f, indent=2, ensure_ascii=False)

                self.stats["total_size_bytes"] += output_file.stat().st_size
                exported_count += 1

        return exported_count

    def export_arxiv_emerging(self) -> int:
        categories = ["ALL", "cs.LG", "cs.CV", "cs.CL", "cs.AI", "cs.RO"]
        exported_count = 0

        for category in categories:
            topics = self.repo.analysis.get_emerging_topics(category=category, limit=50, min_growth_rate=1.5)
            if not topics:
                continue

            output_file = self.arxiv_data_dir / f"arxiv_emerging_{category}.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(topics, f, indent=2, ensure_ascii=False)

            self.stats["total_size_bytes"] += output_file.stat().st_size
            exported_count += 1

        return exported_count

    def export_arxiv_stats(self) -> bool:
        total_papers = self.repo.raw.get_raw_paper_count(source="arxiv")

        categories_stats = {}
        for category in ["cs.LG", "cs.CL", "cs.CV", "cs.AI", "cs.RO"]:
            with self.repo._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT COUNT(*) as count
                    FROM raw_papers
                    WHERE source = 'arxiv' AND categories LIKE ?
                    """,
                    (f"%{category}%",),
                )
                categories_stats[category] = cursor.fetchone()["count"]

        with self.repo._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT MIN(retrieved_at) as min_date, MAX(retrieved_at) as max_date
                FROM raw_papers
                WHERE source = 'arxiv'
                """
            )
            row = cursor.fetchone()

        stats_data = {
            "total_papers": total_papers,
            "categories": categories_stats,
            "date_range": {"min": row["min_date"] if row else None, "max": row["max_date"] if row else None},
            "latest_update": self.repo.analysis.get_meta("arxiv_last_run_ALL_year"),
            "exported_at": datetime.now().isoformat(),
        }

        output_file = self.arxiv_data_dir / "arxiv_stats.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(stats_data, f, indent=2, ensure_ascii=False)

        self.stats["total_size_bytes"] += output_file.stat().st_size
        return True

    def export_all_arxiv(self) -> Dict:
        results = {
            "timeseries": self.export_arxiv_timeseries(),
            "emerging": self.export_arxiv_emerging(),
            "stats": self.export_arxiv_stats(),
        }
        self.stats["arxiv_exported"] = sum(1 for v in results.values() if v)
        return results

    def copy_static_assets(self) -> int:
        src_static = ROOT_DIR / "src" / "web" / "static"
        if not src_static.exists():
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
        return copied_count

    def export_manifest(self):
        manifest = {
            "generated_at": datetime.now().isoformat(),
            "stats": self.stats,
        }
        manifest_file = self.output_dir / "data" / "manifest.json"
        with open(manifest_file, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)

    def export_all(self):
        self.export_all_venues()
        self.export_all_arxiv()
        self.copy_static_assets()
        self.export_manifest()
        return self.stats


def main() -> int:
    parser = argparse.ArgumentParser(description="Export DeepTrender static site")
    parser.add_argument("--output-dir", type=str, default="docs", help="Output directory")
    parser.add_argument("--top-keywords", type=int, default=300, help="Max keywords per venue")
    args = parser.parse_args()

    exporter = StaticSiteExporter(output_dir=args.output_dir, top_keywords=args.top_keywords)
    try:
        exporter.export_all()
        print(f"Static export complete: {args.output_dir}")
        return 0
    except Exception as e:
        print(f"Export failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
