"""
数据库仓库测试
"""

import pytest
import sqlite3
from pathlib import Path

from scraper.models import Paper
from database.repository import DatabaseRepository


class TestDatabaseRepository:
    """DatabaseRepository 测试类"""
    
    def test_database_init(self, repo):
        """测试数据库初始化"""
        # 验证表已创建
        with repo._get_connection() as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
            tables = [row[0] for row in cursor.fetchall()]
        
        assert "papers" in tables
        assert "keywords" in tables
        assert "paper_keywords" in tables
    
    def test_save_paper(self, repo, sample_paper):
        """测试保存单篇论文"""
        sample_paper.extracted_keywords = ["test keyword"]
        result = repo.save_paper(sample_paper)
        
        assert result is True
    
    def test_get_paper(self, repo, sample_paper):
        """测试获取论文"""
        sample_paper.extracted_keywords = ["deep learning"]
        repo.save_paper(sample_paper)
        
        retrieved = repo.get_paper(sample_paper.id)
        
        assert retrieved is not None
        assert retrieved.id == sample_paper.id
        assert retrieved.title == sample_paper.title
        assert retrieved.venue == sample_paper.venue
        assert retrieved.year == sample_paper.year
    
    def test_get_paper_not_found(self, repo):
        """测试获取不存在的论文"""
        result = repo.get_paper("non_existent_id")
        
        assert result is None
    
    def test_save_papers_batch(self, repo, sample_papers):
        """测试批量保存论文"""
        for paper in sample_papers:
            paper.extracted_keywords = ["machine learning"]
        
        saved_count = repo.save_papers(sample_papers)
        
        assert saved_count == len(sample_papers)
    
    def test_get_paper_count(self, repo_with_data):
        """测试获取论文数量"""
        count = repo_with_data.get_paper_count()
        
        assert count == 3
    
    def test_get_paper_count_by_venue(self, repo_with_data):
        """测试按会议获取论文数量"""
        iclr_count = repo_with_data.get_paper_count(venue="ICLR")
        neurips_count = repo_with_data.get_paper_count(venue="NeurIPS")
        
        assert iclr_count == 2  # paper_002 和 paper_003
        assert neurips_count == 1  # paper_001
    
    def test_get_paper_count_by_year(self, repo_with_data):
        """测试按年份获取论文数量"""
        count_2023 = repo_with_data.get_paper_count(year=2023)
        count_2024 = repo_with_data.get_paper_count(year=2024)
        
        assert count_2023 == 2
        assert count_2024 == 1
    
    def test_get_top_keywords(self, repo_with_data):
        """测试获取 Top-K 关键词"""
        keywords = repo_with_data.get_top_keywords(limit=10)
        
        assert isinstance(keywords, list)
        assert len(keywords) > 0
        
        # 验证返回格式 (keyword, count)
        for kw, count in keywords:
            assert isinstance(kw, str)
            assert isinstance(count, int)
            assert count > 0
    
    def test_get_top_keywords_by_venue(self, repo_with_data):
        """测试按会议获取 Top-K 关键词"""
        keywords = repo_with_data.get_top_keywords(venue="ICLR", limit=10)
        
        assert isinstance(keywords, list)
    
    def test_get_keyword_trend(self, repo_with_data):
        """测试获取关键词趋势"""
        # transformer 在 sample_papers 中出现
        trend = repo_with_data.get_keyword_trend("transformer")
        
        assert isinstance(trend, dict)
        # 返回年份到数量的映射
        for year, count in trend.items():
            assert isinstance(year, int)
            assert isinstance(count, int)
    
    def test_get_all_venues(self, repo_with_data):
        """测试获取所有会议"""
        venues = repo_with_data.get_all_venues()
        
        assert isinstance(venues, list)
        assert "ICLR" in venues
        assert "NeurIPS" in venues
    
    def test_get_all_years(self, repo_with_data):
        """测试获取所有年份"""
        years = repo_with_data.get_all_years()
        
        assert isinstance(years, list)
        assert 2023 in years
        assert 2024 in years
    
    def test_get_all_years_by_venue(self, repo_with_data):
        """测试按会议获取所有年份"""
        iclr_years = repo_with_data.get_all_years(venue="ICLR")
        
        assert isinstance(iclr_years, list)
        assert 2023 in iclr_years
        assert 2024 in iclr_years
    
    def test_get_papers_by_venue_year(self, repo_with_data):
        """测试按会议和年份获取论文"""
        papers = repo_with_data.get_papers_by_venue_year("ICLR", 2024)
        
        assert isinstance(papers, list)
        assert len(papers) == 1
        assert papers[0].venue == "ICLR"
        assert papers[0].year == 2024
    
    def test_save_duplicate_paper(self, repo, sample_paper):
        """测试重复保存论文（应该更新）"""
        sample_paper.extracted_keywords = ["keyword1"]
        repo.save_paper(sample_paper)
        
        # 修改关键词后再保存
        sample_paper.extracted_keywords = ["keyword2"]
        result = repo.save_paper(sample_paper)
        
        assert result is True
        
        # 论文数量应该还是 1
        count = repo.get_paper_count()
        assert count == 1
    
    def test_get_venue_comparison(self, repo_with_data):
        """测试获取会议对比"""
        comparison = repo_with_data.get_venue_comparison(year=2023, limit=5)
        
        assert isinstance(comparison, dict)
        # 应该包含 2023 年的会议
        assert "ICLR" in comparison or "NeurIPS" in comparison
