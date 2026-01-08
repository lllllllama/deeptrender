"""
Structuring Agent

负责将 Raw Layer 的数据处理为 Structured Layer。

职责：
- 标题标准化
- 会议识别（从 comments、venue_raw 等字段）
- 领域分类
- 跨源去重
- 创建 paper_sources 关联
"""

import sys
import re
from pathlib import Path
from typing import List, Optional, Dict, Tuple
from datetime import datetime

# 确保 src 目录在路径中
_src_dir = Path(__file__).parent.parent
if str(_src_dir) not in sys.path:
    sys.path.insert(0, str(_src_dir))

from database import (
    get_raw_repository, get_structured_repository,
    RawRepository, StructuredRepository
)
from scraper.models import RawPaper, Paper, Venue, PaperSource


# 会议识别模式
VENUE_PATTERNS = {
    # ML 顶会
    "ICML": [r"\bICML\b", r"International Conference on Machine Learning"],
    "NeurIPS": [r"\bNeurIPS\b", r"\bNIPS\b", r"Neural Information Processing"],
    "ICLR": [r"\bICLR\b", r"International Conference on Learning Representations"],
    
    # CV 顶会
    "CVPR": [r"\bCVPR\b", r"Computer Vision and Pattern Recognition"],
    "ICCV": [r"\bICCV\b", r"International Conference on Computer Vision"],
    "ECCV": [r"\bECCV\b", r"European Conference on Computer Vision"],
    
    # NLP 顶会
    "ACL": [r"\bACL\s*20\d{2}\b", r"Annual Meeting of the Association for Computational Linguistics"],
    "EMNLP": [r"\bEMNLP\b", r"Empirical Methods in Natural Language Processing"],
    "NAACL": [r"\bNAACL\b", r"North American.*ACL"],
    
    # AI 综合
    "AAAI": [r"\bAAAI\b", r"AAAI Conference on Artificial Intelligence"],
    "IJCAI": [r"\bIJCAI\b", r"International Joint Conference on Artificial Intelligence"],
    
    # 其他
    "CoRL": [r"\bCoRL\b", r"Conference on Robot Learning"],
    "AISTATS": [r"\bAISTATS\b", r"Artificial Intelligence and Statistics"],
}

# 领域分类
DOMAIN_CATEGORIES = {
    "CV": ["cs.CV", "computer vision", "image", "video", "visual"],
    "NLP": ["cs.CL", "natural language", "nlp", "text", "language model"],
    "ML": ["cs.LG", "stat.ML", "machine learning", "deep learning"],
    "RL": ["cs.AI", "reinforcement learning", "robot", "control"],
    "AI": ["artificial intelligence", "neural network"],
}


class StructuringAgent:
    """
    数据结构化 Agent
    
    负责将 Raw Layer 转换为 Structured Layer。
    """
    
    def __init__(
        self,
        raw_repo: RawRepository = None,
        structured_repo: StructuredRepository = None,
    ):
        self.raw_repo = raw_repo or get_raw_repository()
        self.structured_repo = structured_repo or get_structured_repository()
        self._venue_cache: Dict[str, int] = {}  # canonical_name -> venue_id
    
    def process_raw_paper(self, raw_paper: RawPaper) -> Optional[Paper]:
        """
        处理单篇原始论文
        
        Args:
            raw_paper: 原始论文
            
        Returns:
            结构化论文（如果处理成功）
        """
        # 1. 标题标准化
        canonical_title = self._normalize_title(raw_paper.title)
        if not canonical_title:
            return None
        
        # 2. 会议识别
        venue_name, confidence = self._detect_venue(raw_paper)
        
        # 3. 领域分类
        domain = self._classify_domain(raw_paper)
        
        # 4. 确定 venue_type
        venue_type = self._determine_venue_type(raw_paper, venue_name)
        
        # 5. 确定 quality_flag
        quality_flag = self._determine_quality(raw_paper, venue_name)
        
        # 6. 获取或创建 venue
        venue_id = None
        if venue_name:
            venue_id = self._get_or_create_venue(venue_name, domain)
        
        return Paper(
            canonical_title=canonical_title,
            abstract=raw_paper.abstract or "",
            authors=raw_paper.authors,
            year=raw_paper.year,
            venue_id=venue_id,
            venue_type=venue_type,
            domain=domain,
            quality_flag=quality_flag,
            doi=raw_paper.doi,
            venue_name=venue_name,
        )
    
    def _normalize_title(self, title: str) -> str:
        """标准化标题"""
        if not title:
            return ""
        
        # 移除多余空格
        title = " ".join(title.split())
        
        # 移除首尾空格
        title = title.strip()
        
        return title
    
    def _detect_venue(self, raw_paper: RawPaper) -> Tuple[Optional[str], float]:
        """
        检测会议
        
        Returns:
            (venue_name, confidence)
        """
        # 来源优先级：OpenReview > venue_raw > comments > journal_ref
        
        # 1. OpenReview 来源直接信任
        if raw_paper.source == "openreview" and raw_paper.venue_raw:
            return (raw_paper.venue_raw, 1.0)
        
        # 2. 检查 venue_raw
        if raw_paper.venue_raw:
            venue = self._match_venue_patterns(raw_paper.venue_raw)
            if venue:
                return (venue, 0.9)
        
        # 3. 检查 comments（arXiv 常用）
        if raw_paper.comments:
            venue = self._match_venue_patterns(raw_paper.comments)
            if venue:
                return (venue, 0.7)
        
        # 4. 检查 journal_ref
        if raw_paper.journal_ref:
            venue = self._match_venue_patterns(raw_paper.journal_ref)
            if venue:
                return (venue, 0.8)
        
        return (None, 0.0)
    
    def _match_venue_patterns(self, text: str) -> Optional[str]:
        """匹配会议模式"""
        text_lower = text.lower()
        
        for venue_name, patterns in VENUE_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    return venue_name
        
        return None
    
    def _classify_domain(self, raw_paper: RawPaper) -> Optional[str]:
        """分类领域"""
        # 检查 arXiv categories
        if raw_paper.categories:
            categories = raw_paper.categories.lower()
            for domain, keywords in DOMAIN_CATEGORIES.items():
                for kw in keywords:
                    if kw in categories:
                        return domain
        
        # 检查标题和摘要
        text = f"{raw_paper.title} {raw_paper.abstract}".lower()
        
        domain_scores = {}
        for domain, keywords in DOMAIN_CATEGORIES.items():
            score = sum(1 for kw in keywords if kw in text)
            if score > 0:
                domain_scores[domain] = score
        
        if domain_scores:
            return max(domain_scores, key=domain_scores.get)
        
        return None
    
    def _determine_venue_type(self, raw_paper: RawPaper, venue_name: str) -> str:
        """确定 venue 类型"""
        if venue_name:
            return "conference"
        
        if raw_paper.source == "arxiv":
            if raw_paper.journal_ref:
                return "journal"
            return "preprint"
        
        if raw_paper.categories and "article" in raw_paper.categories.lower():
            return "journal"
        
        return "unknown"
    
    def _determine_quality(self, raw_paper: RawPaper, venue_name: str) -> str:
        """确定质量标志"""
        # OpenReview 默认为 accepted
        if raw_paper.source == "openreview":
            return "accepted"
        
        # 有明确会议的视为 accepted
        if venue_name:
            # 检查是否有 "accepted" 关键词
            comments = raw_paper.comments or ""
            if "accepted" in comments.lower():
                return "accepted"
            # 有会议名但不确定是否接受
            return "unknown"
        
        return "unknown"
    
    def _get_or_create_venue(self, venue_name: str, domain: str) -> int:
        """获取或创建 venue"""
        # 检查缓存
        if venue_name in self._venue_cache:
            return self._venue_cache[venue_name]
        
        # 检查数据库
        venue = self.structured_repo.get_venue_by_name(venue_name)
        if venue:
            self._venue_cache[venue_name] = venue.venue_id
            return venue.venue_id
        
        # 创建新 venue
        new_venue = Venue(
            canonical_name=venue_name,
            domain=domain,
            venue_type="conference",
        )
        venue_id = self.structured_repo.save_venue(new_venue)
        self._venue_cache[venue_name] = venue_id
        return venue_id
    
    def _find_existing_paper(self, title: str, year: int) -> Optional[int]:
        """
        查找已存在的论文（基于标题去重）
        
        Args:
            title: 标准化标题
            year: 年份
            
        Returns:
            paper_id 如果存在，否则 None
        """
        # 标准化标题用于匹配
        normalized = self._normalize_title(title).lower()
        
        # 查询数据库
        paper_id = self.structured_repo.find_paper_by_title(normalized, year)
        return paper_id
    
    def process_batch(
        self,
        source: str = None,
        limit: int = 1000,
    ) -> Dict[str, int]:
        """
        批量处理未处理的原始论文
        
        Args:
            source: 限定数据源
            limit: 批量大小
            
        Returns:
            处理统计
        """
        print(f"\n📝 [Structuring] 正在处理未结构化的论文...")
        
        raw_papers = self.raw_repo.get_unprocessed_raw_papers(source=source, limit=limit)
        
        if not raw_papers:
            print("   没有需要处理的论文")
            return {"processed": 0, "success": 0, "failed": 0, "merged": 0}
        
        print(f"   找到 {len(raw_papers)} 篇待处理论文")
        
        success = 0
        failed = 0
        merged = 0  # 多源合并计数
        
        for raw_paper in raw_papers:
            try:
                paper = self.process_raw_paper(raw_paper)
                if paper:
                    # 尝试查找已存在的论文（基于标题去重）
                    existing_paper_id = self._find_existing_paper(paper.canonical_title, paper.year)
                    
                    if existing_paper_id:
                        # 已存在，只添加 source 关联
                        self.structured_repo.link_paper_source(
                            paper_id=existing_paper_id,
                            raw_id=raw_paper.raw_id,
                            source=raw_paper.source,
                        )
                        merged += 1
                    else:
                        # 新论文，保存并关联
                        paper_id = self.structured_repo.save_paper(paper)
                        self.structured_repo.link_paper_source(
                            paper_id=paper_id,
                            raw_id=raw_paper.raw_id,
                            source=raw_paper.source,
                        )
                    
                    success += 1
                else:
                    failed += 1
            except Exception as e:
                print(f"   处理失败: {e}")
                failed += 1
        
        print(f"✅ [Structuring] 处理完成: 成功 {success}, 失败 {failed}, 合并 {merged}")
        
        return {
            "processed": len(raw_papers),
            "success": success,
            "failed": failed,
            "merged": merged,
        }
    
    def run(self, limit: int = None) -> Dict[str, int]:
        """
        运行结构化流程
        
        Args:
            limit: 处理数量限制
            
        Returns:
            处理统计
        """
        print("\n" + "=" * 60)
        print("📝 [Structuring Agent] 开始结构化处理")
        print("=" * 60)
        
        total_stats = {"processed": 0, "success": 0, "failed": 0}
        
        # 按数据源分批处理
        for source in ["openreview", "arxiv", "openalex", "s2"]:
            batch_limit = limit or 1000
            stats = self.process_batch(source=source, limit=batch_limit)
            
            total_stats["processed"] += stats["processed"]
            total_stats["success"] += stats["success"]
            total_stats["failed"] += stats["failed"]
            
            if limit and total_stats["processed"] >= limit:
                break
        
        paper_count = self.structured_repo.get_paper_count()
        print(f"\n📊 [Structuring] Structured Layer 现有 {paper_count} 篇论文")
        
        return total_stats


def run_structuring(limit: int = None) -> Dict[str, int]:
    """运行结构化的便捷函数"""
    agent = StructuringAgent()
    return agent.run(limit=limit)
