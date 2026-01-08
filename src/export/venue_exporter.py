"""
Venue Data Exporter for Static Site

Exports JSON files for GitHub Pages:
- venues_index.json: All venues with metadata
- venue_{name}_top_keywords.json: Top keywords per year
- venue_{name}_keyword_trends.json: Keyword trends over years
"""

import json
import logging
from pathlib import Path
from typing import Dict, List
from collections import defaultdict

logger = logging.getLogger(__name__)


class VenueExporter:
    """Export venue analysis data for static site"""
    
    def __init__(self, output_dir: str = "docs/data/venues"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        from database.repository import get_repository, get_structured_repository
        from config import VENUES
        
        self.repo = get_repository()
        self.structured_repo = get_structured_repository()
        self.venues_config = VENUES
    
    def export_venues_index(self) -> int:
        """
        Export venues index with metadata
        
        Returns:
            Number of venues exported
        """
        logger.info("Exporting venues index")
        
        venues_data = []
        
        # Get all venues from config
        for venue_key, venue_config in self.venues_config.items():
            venue_name = venue_config.name
            
            try:
                # Get statistics
                paper_count = self.repo.get_paper_count(venue=venue_name)
                years = self.repo.get_all_years(venue=venue_name)
                
                # Get top keywords (overall)
                top_keywords = self.repo.get_top_keywords(venue=venue_name, limit=10)
                
                venue_data = {
                    "name": venue_name,
                    "full_name": venue_config.full_name,
                    "domain": getattr(venue_config, 'domain', 'ML'),
                    "tier": "A",  # Default, can be enhanced
                    "years_available": sorted(years, reverse=True) if years else [],
                    "paper_count": paper_count,
                    "top_keywords": [
                        {"keyword": kw, "count": count}
                        for kw, count in top_keywords
                    ]
                }
                
                venues_data.append(venue_data)
                logger.info(f"  ✅ {venue_name}: {paper_count} papers, {len(years)} years")
                
            except Exception as e:
                logger.error(f"  ❌ Failed to process {venue_name}: {e}")
        
        # Export
        output_file = self.output_dir / "venues_index.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(venues_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"✅ Exported {output_file.name}: {len(venues_data)} venues")
        return len(venues_data)
    
    def export_venue_top_keywords(self, venue_name: str, top_n: int = 50) -> bool:
        """
        Export top keywords per year for a venue
        
        Args:
            venue_name: Venue canonical name
            top_n: Number of top keywords per year
        
        Returns:
            Success status
        """
        try:
            years = self.repo.get_all_years(venue=venue_name)
            if not years:
                logger.warning(f"No data for venue: {venue_name}")
                return False
            
            yearly_data = {}
            
            for year in sorted(years):
                top_keywords = self.repo.get_top_keywords(
                    venue=venue_name,
                    year=year,
                    limit=top_n
                )
                
                # Add rank
                yearly_data[str(year)] = [
                    {
                        "keyword": kw,
                        "count": count,
                        "rank": rank + 1
                    }
                    for rank, (kw, count) in enumerate(top_keywords)
                ]
            
            # Export
            output_file = self.output_dir / f"venue_{venue_name}_top_keywords.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(yearly_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"  ✅ {venue_name}: {len(yearly_data)} years")
            return True
            
        except Exception as e:
            logger.error(f"  ❌ Failed to export {venue_name} top keywords: {e}")
            return False
    
    def export_venue_keyword_trends(
        self,
        venue_name: str,
        max_keywords: int = 300
    ) -> bool:
        """
        Export keyword trends for a venue (yearly)
        
        Args:
            venue_name: Venue canonical name
            max_keyw Maximum keywords to export
        
    rns:
            Success status
        """
        try:
            years = self.repo.get_all_years(venue=venue_name)
            if not years:
                return False
            
            # Collect all keywords across years
            keyword_yearly_counts = defaultdict(dict)
            
            for year in sorted(years):
                top_keywords = self.repo.get_top_keywords(
                    venue=venue_name,
                    year=year,
                    limit=100  # Get more to ensure coverage
                )
                
                for kw, couneywords:
                    keyword_yearly_counts[kw][str(year)] = count
            
            # Calculate total counts and filter
            keyword_totals = {
                kw: sum(yearly_counts.values())
                for kw, yearly_counts in keyword_yearly_counts.items()
            }
            
            # Sort by total and limit
            top_keywords = sorted(
                keyword_totals.keys(),
                key=lambda k: keyword_totals[k],
                reverse=True
          words]
            
            # Build trends with ranks
            trends_data = {}
            for kw in top_keywords:
                yearly_data = []
                for year in sorted(years):
                    year_str = str(year)
                    count = keyword_yearly_counts[kw].get(year_str, 0)
                    
                    # Calculate rank for this year
                    year_keywords = self.repo.get_top_keywords(
                        venue=venue_name,
                        year=year,
                        limit=1000
                    )
                    rank = next(
                        , (k, _) in enumerate(year_keywords) if k == kw),
                        None
                    )
                    
                    yearly_data.append({
                        "year": year,
                        "count": count,
                        "rank": rank
                    })
                
                trends_data[kw] = yearly_data
            
            # Export
            output_file = self.output_dir / f"venue_{venue_name}_keyword_trends.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(trends_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"  ✅ {venue_name}: {len(trends_data)} keywords")
            return True
            
        except Exception as e:
            logger.error(f"  ❌ Failed to export {venue_name} trends: {e}")
            return False
    
    def export_all(self) -> Dict:
        """
        Export all venue data
        
        Returns:
            Summary statistics
        """
        logger.info("=" * 60)
        logger.info("📊 Exporting venue data for static site")
        logger.info("=" * 60)
        
        summary = {
            "venues_count": 0,
            "venues_exported": [],
            "output_dir": str(self.output_dir)
        }
        
        # Export venues index
        summary["venues_count"] = self.export_venues_index()
        
        # Export per-venue data
        logger.info("\nExporting per-venue data...")
        for venue_key, venue_config in self.venues_config.items():
            venue_name = venue_config.name
            
            logger.info(f"\n📊 Processing {venue_name}...")
            
            # Export top keywords
            success_top = self.export_venue_topeywords(venue_name)
            
            # Export trends
            success_trends = self.export_venue_keyword_trends(venue_name)
            
            if success_top and success_trends:
                summary["venues_exported"].append(venue_name)
        
        # Calculate total size
        total_size = sum(
            f.stat().st_size
            for f in self.output_dir.glob("*.json")
        )
        summary["total_size_mb"] = round(total_size / (1024 * 1024), 2)
        
        logger.info("\n" + "=" * 60)
        logger.info("✅ Venue export complete!")
        logger.info(f"   Output directory: {self.output_dir}")
        logger.info(f"   Total size: {summary['total_size_mb']} MB")
        logger.info(f"   Venues exported: {len(summary['venues_exported'])}")
        logger.info("=" * 60)
        
        return summary


def export_venue_data(output_dir: str = "docs/data/venues") -> Dict:
    """Convenience function to export venue data"""
    exporter = VenueExporter(output_dir)
    return exporter.export_all()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    exporter = VenueExporter()
    summary = exporter.export_all()
    
    print("\n📊 Export Summary:")
    print(json.dumps(summary, indent=2))
