"""
统计分析测试
"""

import pytest
from analysis.statistics import (
    TrendData,
    VenueStats,
    AnalysisResult,
    KeywordAnalyzer,
    get_analyzer,
)


class TestTrendData:
    """TrendData 测试类"""
    
    def test_trend_data_creation(self):
        """测试创建 TrendData"""
        trend = TrendData(
            keyword="deep learning",
            years=[2021, 2022, 2023, 2024],
            counts=[10, 20, 40, 80],
        )
        
        assert trend.keyword == "deep learning"
        assert len(trend.years) == 4
        assert len(trend.counts) == 4
    
    def test_growth_rate_positive(self):
        """测试正增长率计算"""
        trend = TrendData(
            keyword="transformer",
            years=[2022, 2023, 2024],
            counts=[100, 150, 200],  # 100% 增长
        )
        
        rate = trend.growth_rate
        
        assert rate == 1.0  # (200 - 100) / 100 = 1.0
    
    def test_growth_rate_negative(self):
        """测试负增长率计算"""
        trend = TrendData(
            keyword="rnn",
            years=[2022, 2023, 2024],
            counts=[100, 80, 50],  # 50% 下降
        )
        
        rate = trend.growth_rate
        
        assert rate == -0.5  # (50 - 100) / 100 = -0.5
    
    def test_growth_rate_zero_start(self):
        """测试起始为零的增长率"""
        trend = TrendData(
            keyword="new_tech",
            years=[2023, 2024],
            counts=[0, 100],
        )
        
        rate = trend.growth_rate
        
        assert rate == 0.0  # 除零保护
    
    def test_growth_rate_single_year(self):
        """测试单年份增长率"""
        trend = TrendData(
            keyword="single",
            years=[2024],
            counts=[50],
        )
        
        rate = trend.growth_rate
        
        assert rate == 0.0  # 不足两年无法计算


class TestVenueStats:
    """VenueStats 测试类"""
    
    def test_venue_stats_creation(self):
        """测试创建 VenueStats"""
        stats = VenueStats(
            venue="ICLR",
            year=2024,
            paper_count=1500,
            top_keywords=[("transformer", 500), ("llm", 300)],
        )
        
        assert stats.venue == "ICLR"
        assert stats.year == 2024
        assert stats.paper_count == 1500
        assert len(stats.top_keywords) == 2


class TestKeywordAnalyzer:
    """KeywordAnalyzer 测试类"""
    
    def test_analyzer_creation(self, repo_with_data):
        """测试创建分析器"""
        analyzer = KeywordAnalyzer(repository=repo_with_data)
        
        assert analyzer is not None
        assert analyzer.repo is repo_with_data
    
    def test_get_top_keywords(self, repo_with_data):
        """测试获取 Top 关键词"""
        analyzer = KeywordAnalyzer(repository=repo_with_data)
        
        keywords = analyzer.get_top_keywords(limit=10)
        
        assert isinstance(keywords, list)
    
    def test_get_keyword_trend(self, repo_with_data):
        """测试获取关键词趋势"""
        analyzer = KeywordAnalyzer(repository=repo_with_data)
        
        trend = analyzer.get_keyword_trend("transformer")
        
        assert isinstance(trend, TrendData)
        assert trend.keyword == "transformer"
    
    def test_get_keyword_trends_batch(self, repo_with_data):
        """测试批量获取关键词趋势"""
        analyzer = KeywordAnalyzer(repository=repo_with_data)
        
        trends = analyzer.get_keyword_trends(["transformer", "bert"])
        
        assert isinstance(trends, list)
        assert len(trends) == 2
        for trend in trends:
            assert isinstance(trend, TrendData)
    
    def test_get_venue_stats(self, repo_with_data):
        """测试获取会议统计"""
        analyzer = KeywordAnalyzer(repository=repo_with_data)
        
        stats = analyzer.get_venue_stats("ICLR", 2024)
        
        assert isinstance(stats, VenueStats)
        assert stats.venue == "ICLR"
        assert stats.year == 2024
    
    def test_analyze_full(self, repo_with_data):
        """测试完整分析"""
        analyzer = KeywordAnalyzer(repository=repo_with_data)
        
        result = analyzer.analyze(top_k=20)
        
        assert isinstance(result, AnalysisResult)
        assert result.total_papers > 0
        assert len(result.venues) > 0
        assert len(result.years) > 0
        assert "generated_at" in result.__dict__


class TestGetAnalyzer:
    """get_analyzer 函数测试"""
    
    def test_get_analyzer(self):
        """测试获取分析器单例"""
        analyzer = get_analyzer()
        
        assert analyzer is not None
        assert isinstance(analyzer, KeywordAnalyzer)
