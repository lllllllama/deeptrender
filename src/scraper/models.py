"""
Data models for three-layer architecture.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime


# ============================================================
# RAW LAYER MODELS
# ============================================================

@dataclass
class RawPaper:
    """Raw paper payload from upstream sources."""

    source: str  # arxiv / openalex / s2 / openreview
    source_paper_id: str
    title: str
    abstract: str = ""
    authors: List[str] = field(default_factory=list)
    year: Optional[int] = None
    venue_raw: Optional[str] = None
    journal_ref: Optional[str] = None
    comments: Optional[str] = None
    categories: Optional[str] = None
    doi: Optional[str] = None
    raw_json: Optional[Dict[str, Any]] = None
    published_at: Optional[datetime] = None
    retrieved_at: datetime = field(default_factory=datetime.now)
    raw_id: Optional[int] = None

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "source_paper_id": self.source_paper_id,
            "title": self.title,
            "abstract": self.abstract,
            "authors": self.authors,
            "year": self.year,
            "venue_raw": self.venue_raw,
            "journal_ref": self.journal_ref,
            "comments": self.comments,
            "categories": self.categories,
            "doi": self.doi,
            "raw_json": self.raw_json,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "retrieved_at": self.retrieved_at.isoformat() if self.retrieved_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "RawPaper":
        retrieved_at = data.get("retrieved_at")
        if isinstance(retrieved_at, str):
            retrieved_at = datetime.fromisoformat(retrieved_at)

        published_at = data.get("published_at")
        if isinstance(published_at, str):
            published_at = datetime.fromisoformat(published_at)

        return cls(
            source=data["source"],
            source_paper_id=data["source_paper_id"],
            title=data.get("title", ""),
            abstract=data.get("abstract", ""),
            authors=data.get("authors", []),
            year=data.get("year"),
            venue_raw=data.get("venue_raw"),
            journal_ref=data.get("journal_ref"),
            comments=data.get("comments"),
            categories=data.get("categories"),
            doi=data.get("doi"),
            raw_json=data.get("raw_json"),
            published_at=published_at,
            retrieved_at=retrieved_at or datetime.now(),
            raw_id=data.get("raw_id"),
        )


# ============================================================
# STRUCTURED LAYER MODELS
# ============================================================

@dataclass
class Venue:
    """Canonical venue model."""

    canonical_name: str
    full_name: Optional[str] = None
    domain: Optional[str] = None
    venue_type: Optional[str] = None
    first_year: Optional[int] = None
    last_year: Optional[int] = None
    venue_id: Optional[int] = None


@dataclass
class Paper:
    """Structured/deduplicated paper model."""

    canonical_title: str
    abstract: str = ""
    authors: List[str] = field(default_factory=list)
    year: Optional[int] = None
    venue_id: Optional[int] = None
    venue_type: str = "unknown"
    domain: Optional[str] = None
    quality_flag: str = "unknown"
    doi: Optional[str] = None
    url: Optional[str] = None
    pdf_url: Optional[str] = None
    paper_id: Optional[int] = None
    created_at: datetime = field(default_factory=datetime.now)

    source_ids: List[int] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    extracted_keywords: List[str] = field(default_factory=list)
    venue_name: Optional[str] = None
    legacy_id: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "venue": self.venue,
            "paper_id": self.paper_id,
            "canonical_title": self.canonical_title,
            "abstract": self.abstract,
            "authors": self.authors,
            "year": self.year,
            "venue_id": self.venue_id,
            "venue_type": self.venue_type,
            "domain": self.domain,
            "quality_flag": self.quality_flag,
            "doi": self.doi,
            "url": self.url,
            "pdf_url": self.pdf_url,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "keywords": self.keywords,
            "extracted_keywords": self.extracted_keywords,
            "venue_name": self.venue_name,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Paper":
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)

        return cls(
            canonical_title=data.get("canonical_title") or data.get("title", ""),
            abstract=data.get("abstract", ""),
            authors=data.get("authors", []),
            year=data.get("year"),
            venue_id=data.get("venue_id"),
            venue_type=data.get("venue_type", "unknown"),
            domain=data.get("domain"),
            quality_flag=data.get("quality_flag", "unknown"),
            doi=data.get("doi"),
            url=data.get("url", ""),
            pdf_url=data.get("pdf_url"),
            paper_id=data.get("paper_id"),
            created_at=created_at or datetime.now(),
            keywords=data.get("keywords", []),
            extracted_keywords=data.get("extracted_keywords", []),
            venue_name=data.get("venue_name") or data.get("venue"),
            legacy_id=data.get("id"),
        )

    @property
    def title(self) -> str:
        return self.canonical_title

    @property
    def venue(self) -> str:
        return self.venue_name or ""

    @property
    def id(self) -> str:
        if self.legacy_id:
            return self.legacy_id
        return str(self.paper_id) if self.paper_id else ""

    @property
    def text_for_extraction(self) -> str:
        return f"{self.canonical_title}. {self.abstract}"

    @property
    def all_keywords(self) -> List[str]:
        return list(set(self.keywords + self.extracted_keywords))


@dataclass
class PaperSource:
    """Link between structured paper and raw payload."""

    paper_id: int
    raw_id: int
    source: str
    confidence: float = 1.0
    id: Optional[int] = None


# ============================================================
# ANALYSIS LAYER MODELS
# ============================================================

@dataclass
class PaperKeyword:
    """Extracted keyword per paper."""

    paper_id: int
    keyword: str
    method: str
    score: float = 1.0
    id: Optional[int] = None


@dataclass
class TrendData:
    """Trend series model."""

    keyword: str
    years: List[int] = field(default_factory=list)
    counts: List[int] = field(default_factory=list)
    venue_id: Optional[int] = None

    @property
    def growth_rate(self) -> float:
        if len(self.counts) < 2 or self.counts[0] == 0:
            return 0.0
        return (self.counts[-1] - self.counts[0]) / self.counts[0]


def create_legacy_paper(
    id: str,
    title: str,
    abstract: str,
    authors: List[str],
    venue: str,
    year: int,
    url: str,
    keywords: List[str] = None,
    extracted_keywords: List[str] = None,
    pdf_url: str = None,
) -> Paper:
    """Create a Paper with legacy id/title/venue semantics."""

    return Paper(
        canonical_title=title,
        abstract=abstract,
        authors=authors,
        year=year,
        venue_type="unknown",
        url=url,
        pdf_url=pdf_url,
        keywords=keywords or [],
        extracted_keywords=extracted_keywords or [],
        venue_name=venue,
        legacy_id=id,
    )
