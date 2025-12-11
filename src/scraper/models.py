"""
论文数据模型
"""

from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime


@dataclass
class Paper:
    """论文数据模型"""
    id: str  # OpenReview 论文 ID
    title: str  # 论文标题
    abstract: str  # 摘要
    authors: List[str]  # 作者列表
    venue: str  # 会议名称 (如 ICLR, NeurIPS)
    year: int  # 年份
    url: str  # 论文链接
    keywords: List[str] = field(default_factory=list)  # 作者提交的关键词
    extracted_keywords: List[str] = field(default_factory=list)  # 自动提取的关键词
    pdf_url: Optional[str] = None  # PDF 链接
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "title": self.title,
            "abstract": self.abstract,
            "authors": self.authors,
            "venue": self.venue,
            "year": self.year,
            "url": self.url,
            "keywords": self.keywords,
            "extracted_keywords": self.extracted_keywords,
            "pdf_url": self.pdf_url,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Paper":
        """从字典创建"""
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        
        return cls(
            id=data["id"],
            title=data["title"],
            abstract=data.get("abstract", ""),
            authors=data.get("authors", []),
            venue=data["venue"],
            year=data["year"],
            url=data.get("url", ""),
            keywords=data.get("keywords", []),
            extracted_keywords=data.get("extracted_keywords", []),
            pdf_url=data.get("pdf_url"),
            created_at=created_at or datetime.now(),
        )
    
    @property
    def text_for_extraction(self) -> str:
        """用于关键词提取的文本"""
        return f"{self.title}. {self.abstract}"
    
    @property
    def all_keywords(self) -> List[str]:
        """所有关键词（作者提交 + 自动提取）"""
        return list(set(self.keywords + self.extracted_keywords))
