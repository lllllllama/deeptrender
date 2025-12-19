"""
会议发现模块

动态从 OpenReview API 发现和分类会议，而不是使用静态配置。

功能：
1. 从 API 获取所有会议列表
2. 自动分类（ML/NLP/CV/RL/Theory 等）
3. 过滤主会议（排除 Workshop）
4. 保存到数据库供前端使用
"""

import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import json

from openreview.api import OpenReviewClient


@dataclass
class DiscoveredVenue:
    """发现的会议"""
    venue_id: str  # 如 "ICLR.cc/2024/Conference"
    name: str  # 简称 如 "ICLR"
    full_name: str  # 全称
    year: int
    domain: str  # ML/NLP/CV/RL/Theory/General
    tier: str  # A/B/C
    is_workshop: bool
    parent_venue: Optional[str] = None  # Workshop 的父会议
    discovered_at: str = field(default_factory=lambda: datetime.now().isoformat())


# 领域分类关键词
DOMAIN_KEYWORDS = {
    "ML": [
        "machine learning", "learning representations", "neural information",
        "ICLR", "NeurIPS", "ICML", "AISTATS", "AutoML"
    ],
    "NLP": [
        "natural language", "computational linguistics", "language model",
        "ACL", "EMNLP", "NAACL", "COLING", "COLM", "ARR"
    ],
    "CV": [
        "computer vision", "visual", "image", "video",
        "CVPR", "ICCV", "ECCV", "3DV"
    ],
    "RL": [
        "reinforcement learning", "robot", "control", "autonomous",
        "CoRL", "RLC", "ICRA"
    ],
    "Theory": [
        "learning theory", "algorithmic", "computational learning",
        "COLT", "ALT", "UAI"
    ],
    "Graphics": [
        "graphics", "siggraph", "rendering", "animation",
        "SIGGRAPH"
    ],
    "Data": [
        "data mining", "knowledge discovery", "database",
        "KDD", "SIGMOD", "VLDB"
    ],
}

# 知名会议 Tier 分级
VENUE_TIERS = {
    "A": [
        "ICLR", "NeurIPS", "ICML",  # ML 三大
        "ACL", "EMNLP", "NAACL",  # NLP
        "CVPR", "ICCV", "ECCV",  # CV
        "AAAI", "IJCAI",  # AI General
        "SIGGRAPH",  # Graphics
    ],
    "B": [
        "AISTATS", "UAI", "COLT", "ALT",  # Theory
        "CoRL", "COLING", "COLM",  # Specialized
        "LOG", "RLC",
    ],
    "C": []  # 其他
}


class VenueDiscovery:
    """会议发现服务"""
    
    def __init__(self, baseurl: str = "https://api2.openreview.net"):
        self.client = OpenReviewClient(baseurl=baseurl)
        self._venue_cache: List[str] = []
    
    def get_all_venue_ids(self, refresh: bool = False) -> List[str]:
        """获取 OpenReview 上所有会议 ID"""
        if self._venue_cache and not refresh:
            return self._venue_cache
        
        print("🔍 正在从 OpenReview 获取会议列表...")
        groups = self.client.get_group('venues')
        self._venue_cache = groups.members or []
        print(f"   找到 {len(self._venue_cache)} 个会议/Workshop")
        return self._venue_cache
    
    def discover_conferences(
        self,
        min_year: int = 2020,
        max_year: int = 2025,
        include_workshops: bool = False,
    ) -> List[DiscoveredVenue]:
        """
        发现所有符合条件的会议
        
        Args:
            min_year: 最早年份
            max_year: 最晚年份
            include_workshops: 是否包含 Workshop
            
        Returns:
            发现的会议列表
        """
        all_venues = self.get_all_venue_ids()
        discovered = []
        
        for venue_id in all_venues:
            parsed = self._parse_venue_id(venue_id)
            if parsed is None:
                continue
            
            name, year, is_workshop = parsed
            
            # 年份过滤
            if year < min_year or year > max_year:
                continue
            
            # Workshop 过滤
            if is_workshop and not include_workshops:
                continue
            
            # 分类和分级
            domain = self._classify_domain(venue_id, name)
            tier = self._classify_tier(name)
            
            discovered.append(DiscoveredVenue(
                venue_id=venue_id,
                name=name,
                full_name=self._get_full_name(name),
                year=year,
                domain=domain,
                tier=tier,
                is_workshop=is_workshop,
            ))
        
        # 按名称和年份排序
        discovered.sort(key=lambda v: (v.name, -v.year))
        
        print(f"✅ 发现 {len(discovered)} 个会议")
        return discovered
    
    def _parse_venue_id(self, venue_id: str) -> Optional[Tuple[str, int, bool]]:
        """
        解析会议 ID
        
        Returns:
            (简称, 年份, 是否 Workshop) 或 None
        """
        # 模式: ORG.cc/YEAR/Conference 或 domain.org/VENUE/YEAR/Conference
        
        # 检查是否为 Workshop
        is_workshop = "Workshop" in venue_id
        
        # 提取年份
        year_match = re.search(r'/(\d{4})/', venue_id)
        if not year_match:
            return None
        year = int(year_match.group(1))
        
        # 提取名称
        parts = venue_id.split('/')
        if len(parts) < 2:
            return None
        
        # 第一部分通常是组织名
        org = parts[0]
        name = org.split('.')[0].upper()
        
        # 特殊处理
        if 'aclweb.org' in venue_id:
            # ACL 系列会议
            for acl_venue in ['ACL', 'EMNLP', 'NAACL', 'COLING', 'ARR']:
                if acl_venue in venue_id:
                    name = acl_venue
                    break
        elif 'robot-learning.org' in venue_id:
            name = 'CoRL'
        elif 'logconference.org' in venue_id:
            name = 'LOG'
        
        return name, year, is_workshop
    
    def _classify_domain(self, venue_id: str, name: str) -> str:
        """根据会议名称和 ID 分类领域"""
        venue_lower = venue_id.lower() + " " + name.lower()
        
        for domain, keywords in DOMAIN_KEYWORDS.items():
            for kw in keywords:
                if kw.lower() in venue_lower:
                    return domain
        
        return "General"
    
    def _classify_tier(self, name: str) -> str:
        """分类会议等级"""
        for tier, venues in VENUE_TIERS.items():
            if name in venues:
                return tier
        return "C"
    
    def _get_full_name(self, name: str) -> str:
        """获取会议全称"""
        full_names = {
            "ICLR": "International Conference on Learning Representations",
            "NeurIPS": "Conference on Neural Information Processing Systems",
            "ICML": "International Conference on Machine Learning",
            "ACL": "Annual Meeting of the Association for Computational Linguistics",
            "EMNLP": "Conference on Empirical Methods in Natural Language Processing",
            "NAACL": "North American Chapter of the ACL",
            "CVPR": "Conference on Computer Vision and Pattern Recognition",
            "COLING": "International Conference on Computational Linguistics",
            "COLM": "Conference on Language Modeling",
            "AISTATS": "International Conference on AI and Statistics",
            "CoRL": "Conference on Robot Learning",
            "UAI": "Conference on Uncertainty in Artificial Intelligence",
            "COLT": "Conference on Learning Theory",
            "LOG": "Learning on Graphs Conference",
            "AAAI": "AAAI Conference on Artificial Intelligence",
            "IJCAI": "International Joint Conference on AI",
            "SIGGRAPH": "ACM SIGGRAPH Conference",
        }
        return full_names.get(name, name)
    
    def get_summary_by_domain(self, venues: List[DiscoveredVenue]) -> Dict:
        """按领域统计"""
        summary = {}
        for v in venues:
            if v.domain not in summary:
                summary[v.domain] = {"count": 0, "venues": set()}
            summary[v.domain]["count"] += 1
            summary[v.domain]["venues"].add(v.name)
        
        # 转换 set 为 list
        for d in summary:
            summary[d]["venues"] = sorted(summary[d]["venues"])
        
        return summary


def discover_venues(
    min_year: int = 2020,
    include_workshops: bool = False
) -> List[DiscoveredVenue]:
    """发现会议的便捷函数"""
    discovery = VenueDiscovery()
    return discovery.discover_conferences(
        min_year=min_year,
        include_workshops=include_workshops
    )


if __name__ == "__main__":
    # 测试发现功能
    discovery = VenueDiscovery()
    venues = discovery.discover_conferences(min_year=2022)
    
    print("\n" + "=" * 60)
    print("按领域统计")
    print("=" * 60)
    summary = discovery.get_summary_by_domain(venues)
    for domain, data in sorted(summary.items()):
        print(f"\n{domain}: {data['count']} 个会议年份")
        print(f"  会议: {', '.join(data['venues'][:10])}")
    
    print("\n" + "=" * 60)
    print("A 级会议")
    print("=" * 60)
    for v in venues:
        if v.tier == "A":
            print(f"  {v.name} {v.year}: {v.venue_id}")
