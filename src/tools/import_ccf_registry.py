"""
Import CCF Venue Registry

Reads CCF venue registry CSV and imports into structured database layer.
"""

import csv
import sys
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.repository import get_structured_repository

logger = logging.getLogger(__name__)


def import_ccf_registry(csv_path: str = "data/registry/ccf_venues.csv") -> int:
    """
    Import CCF venue registry from CSV
    
    Args:
        csv_path: Path to CSV file
    
    Returns:
        Number of venues imported
    """
    csv_file = Path(csv_path)
    if not csv_file.exists():
        logger.error(f"CSV file not found: {csv_path}")
        return 0
    
    repo = get_structured_repository()
    count = 0
    
    logger.info(f"Importing venues from {csv_path}")
    
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            try:
                # Parse openreview IDs
                openreview_ids = []
                if row.get("openreview_id_pattern"):
                    openreview_ids = [row["openreview_id_pattern"]]
                
                # Parse aliases
                aliases_str = row.get("aliases", "")
                aliases = [a.strip() for a in aliases_str.split(",") if a.strip()]
                
                # Save venue
                repo.save_discovered_venue(
                    name=row["canonical_name"],
                    full_name=row["full_name"],
                    domain=row["domain"],
                    tier=row["tier"],
                    venue_type="conference",
                    openreview_ids=openreview_ids,
                    years=[]  # Will be populated during scraping
                )
                
                count += 1
                logger.info(f"✅ Imported: {row['canonical_name']} ({row['tier']}, {row['domain']})")
                
            except Exception as e:
                logger.error(f"Failed to import {row.get('canonical_name', 'unknown')}: {e}")
    
    logger.info(f"\n✅ Successfully imported {count} venues")
    return count


def main():
    """CLI entry point"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    import argparse
    parser = argparse.ArgumentParser(description="Import CCF venue registry")
    parser.add_argument(
        "--csv",
        default="data/registry/ccf_venues.csv",
        help="Path to CSV file (default: data/registry/ccf_venues.csv)"
    )
    
    args = parser.parse_args()
    
    count = import_ccf_registry(args.csv)
    
    if count > 0:
        print(f"\n✅ Import complete: {count} venues")
        sys.exit(0)
    else:
        print("\n❌ Import failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
