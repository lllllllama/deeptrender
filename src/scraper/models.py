"""
数据模型定义

包含三层架构的数据模型：
- Raw Layer: RawPaper
- Structured Layer: Paper, Venue
- Analysis Layer: Keyword, TrendData
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime
import json


# ============================================================
# RAW LAYER MODELS
# ============================================================

@dataclass
class RawPaper:
    """
    原始论文数据（Raw Layer）
    
    保存从各数据源获取的原始数据，不做任何解释或标准化。
    """
    source: str  # arxiv / openalex / s2 / openreview
    source_paper_id: str
    title: str
    abstract: str = ""
    authors: List[str] = field(default_factory=list)
    year: Optional[int] = None
    venue_raw: Optional[str] = None  # 原始 venue 字符串
    journal_ref: Optional[str] = None
    comments: Optional[str] = None  # arXiv comments（用于会议识别）
    categories: Optional[str] = None  # arXiv categories
    doi: Optional[str] = None
    raw_json: Optional[Dict[str, Any]] = None  # 完整原始响应
    retrieved_at: datetime = field(default_factory=datetime.now)
    raw_id: Optional[int] = None  # 数据库 ID
    
    def to_dict(self) -> dict:
        """转换为字典"""
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
            "retrieved_at": self.retrieved_at.isoformat() if self.retrieved_at else None,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "RawPaper":
        """从字典创建"""
        retrieved_at = data.get("retrieved_at")
        if isinstance(retrieved_at, str):
            retrieved_at = datetime.fromisoformat(retrieved_at)
        
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
            retrieved_at=retrieved_at or datetime.now(),
            raw_id=data.get("raw_id"),
        )


# ============================================================
# STRUCTURED LAYER MODELS
# ============================================================

@dataclass
class Venue:
    """
    会议/期刊（Structured Layer）
    
    标准化的会议或期刊信息。
    """
    canonical_name: str  # CVPR, ICML, NeurIPS 等
    full_name: Optional[str] = None
    domain: Optional[str] = None  # CV / NLP / ML / RL / AI
    venue_type: Optional[str] = None  # conference / journal / workshop
    first_year: Optional[int] = None
    last_year: Optional[int] = None
    venue_id: Optional[int] = None  # 数据库 ID


@dataclass
class Paper:
    """
    论文数据模型（Structured Layer）
    
    标准化、去重后的论文数据。
    """
    canonical_title: str
    abstract: str = ""
    authors: List[str] = field(default_factory=list)
    year: Optional[int] = None
    venue_id: Optional[int] = None
    venue_type: str = "unknown"  # conference / journal / preprint / unknown
    domain: Optional[str] = None  # CV / NLP / ML / RL / AI
    quality_flag: str = "unknown"  # accepted / unknown / filtered
    doi: Optional[str] = None
    url: Optional[str] = None
    pdf_url: Optional[str] = None
    paper_id: Optional[int] = None  # 数据库 ID
    created_at: datetime = field(default_factory=datetime.now)
    
    # 关联的原始数据源
    source_ids: List[int] = field(default_factory=list)  # raw_paper IDs
    
    # 运行时填充的字段（不存储）
    keywords: List[str] = field(default_factory=list)
    extracted_keywords: List[str] = field(default_factory=list)
    venue_name: Optional[str] = None  # 从 venue_id 解析
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
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
        """从字典创建"""
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
            venue_name=data.get("venue_name"),
        )
    
    @property
    def title(self) -> str:
        """兼容旧接口"""
        return self.canonical_title
    
    @property
    def venue(self) -> str:
        """兼容旧接口"""
        return self.venue_name or ""
    
    @property
    def id(self) -> str:
        """兼容旧接口"""
        return str(self.paper_id) if self.paper_id else ""
    
    @property
    def text_for_extraction(self) -> str:
        """用于关键词提取的文本"""
        return f"{self.canonical_title}. {self.abstract}"
    
    @property
    def all_keywords(self) -> List[str]:
        """所有关键词（作者提交 + 自动提取）"""
        return list(set(self.keywords + self.extracted_keywords))


@dataclass
class PaperSource:
    """
    论文-原始数据源关联（Structured Layer）
    
    记录结构化论文与原始数据的对应关系。
    """
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
    """
    论文关键词（Analysis Layer）
    
    分析阶段提取的关键词。
    """
    paper_id: int
    keyword: str
    method: str  # yake / keybert / llm / author
    score: float = 1.0
    id: Optional[int] = None


@dataclass
class TrendData:
    """趋势数据"""
    keyword: str
    years: List[int] = field(default_factory=list)
    counts: List[int] = field(default_factory=list)
    venue_id: Optional[int] = None
    
    @property
    def growth_rate(self) -> float:
        """计算增长率"""
        if len(self.counts) < 2 or self.counts[0] == 0:
            return 0.0
        return (self.counts[-1] - self.counts[0]) / self.counts[0]


# ============================================================
# LEGACY COMPATIBILITY
# ============================================================

# 保持向后兼容的别名
# 旧代码中使用的 Paper 类现在指向新的 Paper 类
# 如果需要创建用于旧接口的对象，可以使用以下函数

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
    """
    创建兼容旧接口的 Paper 对象
    
    用于迁移期间保持与旧代码的兼容性。
    """
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
    )
