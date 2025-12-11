"""
关键词统计分析

提供关键词频率统计、趋势分析等功能。
"""

from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass, field

from database.repository import DatabaseRepository, get_repository


@dataclass
class VenueStats:
    """会议统计数据"""
    venue: str
    year: int
    paper_count: int
    top_keywords: List[Tuple[str, int]] = field(default_factory=list)


@dataclass
class TrendData:
    """趋势数据"""
    keyword: str
    years: List[int] = field(default_factory=list)
    counts: List[int] = field(default_factory=list)
    
    @property
    def growth_rate(self) -> float:
        """计算增长率"""
        if len(self.counts) < 2 or self.counts[0] == 0:
            return 0.0
        return (self.counts[-1] - self.counts[0]) / self.counts[0]


@dataclass
class AnalysisResult:
    """分析结果"""
    generated_at: str
    total_papers: int
    total_keywords: int
    venues: List[str]
    years: List[int]
    venue_stats: Dict[str, Dict[int, VenueStats]] = field(default_factory=dict)
    overall_top_keywords: List[Tuple[str, int]] = field(default_factory=list)
    keyword_trends: List[TrendData] = field(default_factory=list)
    emerging_keywords: List[str] = field(default_factory=list)


class KeywordAnalyzer:
    """关键词分析器"""
    
    def __init__(self, repository: DatabaseRepository = None):
        """
        初始化分析器
        
        Args:
            repository: 数据库仓库
        """
        self.repo = repository or get_repository()
    
    def get_top_keywords(
        self,
        venue: str = None,
        year: int = None,
        limit: int = 50,
    ) -> List[Tuple[str, int]]:
        """获取 Top-K 关键词"""
        return self.repo.get_top_keywords(venue=venue, year=year, limit=limit)
    
    def get_keyword_trend(
        self,
        keyword: str,
        venue: str = None,
    ) -> TrendData:
        """获取关键词趋势"""
        trend_dict = self.repo.get_keyword_trend(keyword, venue)
        
        years = sorted(trend_dict.keys())
        counts = [trend_dict[y] for y in years]
        
        return TrendData(
            keyword=keyword,
            years=years,
            counts=counts,
        )
    
    def get_keyword_trends(
        self,
        keywords: List[str],
        venue: str = None,
    ) -> List[TrendData]:
        """批量获取关键词趋势"""
        return [self.get_keyword_trend(kw, venue) for kw in keywords]
    
    def get_venue_comparison(
        self,
        year: int,
        limit: int = 10,
    ) -> Dict[str, List[Tuple[str, int]]]:
        """获取会议对比"""
        return self.repo.get_venue_comparison(year, limit)
    
    def get_emerging_keywords(
        self,
        min_growth: float = 1.5,
        min_count: int = 5,
        top_n: int = 20,
    ) -> List[str]:
        """
        获取新兴关键词（增长率高的关键词）
        
        Args:
            min_growth: 最小增长率（如 1.5 表示增长 50%）
            min_count: 最新年份最小出现次数
            top_n: 返回数量
            
        Returns:
            新兴关键词列表
        """
        # 获取所有年份
        years = self.repo.get_all_years()
        if len(years) < 2:
            return []
        
        latest_year = years[0]
        previous_year = years[1]
        
        # 获取最新年份的关键词
        latest_keywords = self.repo.get_top_keywords(year=latest_year, limit=200)
        
        emerging = []
        for keyword, count in latest_keywords:
            if count < min_count:
                continue
            
            # 获取上一年的数量
            trend = self.repo.get_keyword_trend(keyword)
            prev_count = trend.get(previous_year, 0)
            
            if prev_count == 0:
                # 新出现的关键词
                emerging.append((keyword, float('inf'), count))
            else:
                growth = count / prev_count
                if growth >= min_growth:
                    emerging.append((keyword, growth, count))
        
        # 按增长率排序
        emerging.sort(key=lambda x: (-x[1], -x[2]))
        
        return [kw for kw, _, _ in emerging[:top_n]]
    
    def get_venue_stats(self, venue: str, year: int) -> VenueStats:
        """获取会议统计"""
        paper_count = self.repo.get_paper_count(venue=venue, year=year)
        top_keywords = self.repo.get_top_keywords(venue=venue, year=year, limit=20)
        
        return VenueStats(
            venue=venue,
            year=year,
            paper_count=paper_count,
            top_keywords=top_keywords,
        )
    
    def analyze(self, top_k: int = 50) -> AnalysisResult:
        """
        运行完整分析
        
        Args:
            top_k: Top-K 关键词数量
            
        Returns:
            分析结果
        """
        from datetime import datetime
        
        venues = self.repo.get_all_venues()
        years = self.repo.get_all_years()
        
        # 收集各会议各年份的统计
        venue_stats = {}
        for venue in venues:
            venue_stats[venue] = {}
            for year in years:
                stats = self.get_venue_stats(venue, year)
                if stats.paper_count > 0:
                    venue_stats[venue][year] = stats
        
        # 获取总体 Top-K
        overall_top = self.get_top_keywords(limit=top_k)
        
        # 获取 Top 关键词的趋势
        top_keyword_names = [kw for kw, _ in overall_top[:20]]
        trends = self.get_keyword_trends(top_keyword_names)
        
        # 获取新兴关键词
        emerging = self.get_emerging_keywords()
        
        # 统计总数
        total_papers = self.repo.get_paper_count()
        total_keywords = len(self.repo.get_top_keywords(limit=10000))
        
        return AnalysisResult(
            generated_at=datetime.now().isoformat(),
            total_papers=total_papers,
            total_keywords=total_keywords,
            venues=venues,
            years=years,
            venue_stats=venue_stats,
            overall_top_keywords=overall_top,
            keyword_trends=trends,
            emerging_keywords=emerging,
        )


def get_analyzer() -> KeywordAnalyzer:
    """获取分析器"""
    return KeywordAnalyzer()
