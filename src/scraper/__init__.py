"""
论文爬取模块

提供多数据源的论文采集功能：
- OpenReview: ML 顶会权威确认源
- Semantic Scholar: 补充与对齐源
- arXiv: 原始论文数据池（主源）
- OpenAlex: 结构化锚点源
"""

from .client import OpenReviewClient, create_client
from .venues import scrape_venue, scrape_all_venues
from .models import RawPaper, Paper, Venue, PaperSource, PaperKeyword, TrendData
from .semantic_scholar import (
    SemanticScholarClient,
    scrape_s2_venue,
    scrape_all_s2_venues,
    S2_VENUES,
)
from .arxiv_client import ArxivClient, create_arxiv_client
from .openalex_client import OpenAlexClient, create_openalex_client

__all__ = [
    # OpenReview
    "OpenReviewClient",
    "create_client",
    "scrape_venue",
    "scrape_all_venues",
    
    # Semantic Scholar
    "SemanticScholarClient",
    "scrape_s2_venue",
    "scrape_all_s2_venues",
    "S2_VENUES",
    
    # arXiv
    "ArxivClient",
    "create_arxiv_client",
    
    # OpenAlex
    "OpenAlexClient",
    "create_openalex_client",
    
    # Models
    "RawPaper",
    "Paper",
    "Venue",
    "PaperSource",
    "PaperKeyword",
    "TrendData",
]

