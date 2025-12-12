"""论文爬取模块"""

from .client import OpenReviewClient
from .venues import scrape_venue, scrape_all_venues
from .models import Paper
from .semantic_scholar import (
    SemanticScholarClient,
    scrape_s2_venue,
    scrape_all_s2_venues,
    S2_VENUES,
)

__all__ = [
    "OpenReviewClient",
    "scrape_venue",
    "scrape_all_venues",
    "Paper",
    "SemanticScholarClient",
    "scrape_s2_venue",
    "scrape_all_s2_venues",
    "S2_VENUES",
]
