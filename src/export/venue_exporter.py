"""Legacy venue exporter.

This module is kept for backward compatibility. The canonical export path is
`src/tools/export_static_site.py`.
"""

import json
import logging
from pathlib import Path
from typing import Dict

logger = logging.getLogger(__name__)


class VenueExporter:
    """Backward-compatible wrapper around StaticSiteExporter."""

    def __init__(self, output_dir: str = "docs/data/venues"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        from tools.export_static_site import StaticSiteExporter

        root_output = str(self.output_dir.parent.parent)
        self._exporter = StaticSiteExporter(output_dir=root_output)

    def export_venues_index(self) -> int:
        return self._exporter.export_venues_index()

    def export_venue_top_keywords(self, venue_name: str, top_n: int = 50) -> bool:
        return self._exporter.export_venue_top_keywords(venue_name, top_n=top_n)

    def export_venue_keyword_trends(self, venue_name: str, max_keywords: int = 300) -> bool:
        return self._exporter.export_venue_keyword_trends(venue_name, max_keywords=max_keywords)

    def export_all(self) -> Dict:
        logger.info("Delegating venue export to StaticSiteExporter")
        result = self._exporter.export_all_venues()
        total_size = 0
        if self.output_dir.exists():
            total_size = sum(f.stat().st_size for f in self.output_dir.glob("*.json"))

        return {
            "venues_count": result.get("venues_count", 0),
            "venues_exported": result.get("venues_exported", []),
            "output_dir": str(self.output_dir),
            "total_size_mb": round(total_size / (1024 * 1024), 2),
        }


def export_venue_data(output_dir: str = "docs/data/venues") -> Dict:
    exporter = VenueExporter(output_dir)
    return exporter.export_all()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    summary = export_venue_data()
    print("\nExport Summary:")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
