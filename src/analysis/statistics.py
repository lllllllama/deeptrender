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
        window_years: int = 3,
        use_relative_freq: bool = True,
    ) -> List[str]:
        """
        获取新兴关键词（相对频率增长 + 新词检测）
        
        升级特性：
        - 相对频率：关键词数/该年论文数，消除论文数量增长的干扰
        - 3 年窗口：比较最近 N 年的趋势，而非仅两年对比
        - 新词阈值：识别"首次出现"或"近期爆发"的关键词
        
        Args:
            min_growth: 最小增长率（相对频率）
            min_count: 最新年份最小绝对出现次数
            top_n: 返回数量
            window_years: 对比窗口年数
            use_relative_freq: 是否使用相对频率
            
        Returns:
            新兴关键词列表
        """
        years = self.repo.get_all_years()
        if len(years) < 2:
            return []
        
        # 获取每年的论文数（用于计算相对频率）
        paper_counts = {}
        for year in years[:window_years + 1]:
            paper_counts[year] = self.repo.get_paper_count(year=year) or 1
        
        latest_year = years[0]
        
        # 确定对比窗口
        compare_years = years[1:window_years] if len(years) > window_years else years[1:]
        if not compare_years:
            compare_years = [years[1]] if len(years) > 1 else []
        
        # 获取最新年份的关键词
        latest_keywords = self.repo.get_top_keywords(year=latest_year, limit=300)
        
        emerging = []
        for keyword, count in latest_keywords:
            if count < min_count:
                continue
            
            # 获取趋势数据
            trend = self.repo.get_keyword_trend(keyword)
            
            # 计算相对频率（每千篇论文出现次数）
            if use_relative_freq:
                latest_freq = count / paper_counts.get(latest_year, 1) * 1000
            else:
                latest_freq = count
            
            # 计算窗口期平均频率
            window_freqs = []
            for year in compare_years:
                prev_count = trend.get(year, 0)
                if use_relative_freq:
                    freq = prev_count / paper_counts.get(year, 1) * 1000
                else:
                    freq = prev_count
                window_freqs.append(freq)
            
            avg_prev_freq = sum(window_freqs) / len(window_freqs) if window_freqs else 0
            
            # 计算增长率
            if avg_prev_freq < 0.1:
                # 新词（窗口期内几乎不存在）
                # 使用特殊标记：is_new=True, growth=inf
                is_new = True
                growth = float('inf')
            else:
                is_new = False
                growth = latest_freq / avg_prev_freq
            
            # 判断是否为新兴关键词
            if is_new or growth >= min_growth:
                emerging.append({
                    'keyword': keyword,
                    'growth': growth,
                    'count': count,
                    'is_new': is_new,
                    'latest_freq': latest_freq,
                    'avg_prev_freq': avg_prev_freq,
                })
        
        # 排序策略：新词优先，然后按增长率
        emerging.sort(key=lambda x: (
            0 if x['is_new'] else 1,  # 新词排前
            -x['growth'] if x['growth'] != float('inf') else 0,
            -x['count'],
        ))
        
        return [item['keyword'] for item in emerging[:top_n]]
    
    def get_emerging_keywords_detailed(
        self,
        min_growth: float = 1.5,
        min_count: int = 5,
        top_n: int = 20,
    ) -> List[Dict]:
        """获取新兴关键词详细信息（用于报告）"""
        years = self.repo.get_all_years()
        if len(years) < 2:
            return []
        
        paper_counts = {y: self.repo.get_paper_count(year=y) or 1 for y in years[:4]}
        latest_year = years[0]
        compare_years = years[1:3] if len(years) > 2 else years[1:2]
        
        latest_keywords = self.repo.get_top_keywords(year=latest_year, limit=300)
        
        results = []
        for keyword, count in latest_keywords:
            if count < min_count:
                continue
            
            trend = self.repo.get_keyword_trend(keyword)
            latest_freq = count / paper_counts.get(latest_year, 1) * 1000
            
            prev_counts = [trend.get(y, 0) for y in compare_years]
            prev_freqs = [c / paper_counts.get(y, 1) * 1000 for y, c in zip(compare_years, prev_counts)]
            avg_prev_freq = sum(prev_freqs) / len(prev_freqs) if prev_freqs else 0
            
            if avg_prev_freq < 0.1:
                is_new = True
                growth = None
            else:
                is_new = False
                growth = latest_freq / avg_prev_freq
                if growth < min_growth:
                    continue
            
            results.append({
                'keyword': keyword,
                'count': count,
                'is_new': is_new,
                'growth': growth,
                'trend': {y: trend.get(y, 0) for y in years[:4]},
            })
        
        results.sort(key=lambda x: (0 if x['is_new'] else 1, -(x['growth'] or 999), -x['count']))
        return results[:top_n]
    
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
