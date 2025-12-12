"""
Paper 数据模型测试
"""

import pytest
from datetime import datetime
from scraper.models import Paper


class TestPaper:
    """Paper 模型测试类"""
    
    def test_paper_creation(self, sample_paper):
        """测试 Paper 创建"""
        assert sample_paper.id == "test_paper_001"
        assert sample_paper.title == "Deep Learning for Natural Language Processing"
        assert sample_paper.venue == "ICLR"
        assert sample_paper.year == 2024
        assert len(sample_paper.authors) == 2
        assert len(sample_paper.keywords) == 3
    
    def test_paper_to_dict(self, sample_paper):
        """测试 Paper 序列化为字典"""
        data = sample_paper.to_dict()
        
        assert isinstance(data, dict)
        assert data["id"] == "test_paper_001"
        assert data["title"] == "Deep Learning for Natural Language Processing"
        assert data["venue"] == "ICLR"
        assert data["year"] == 2024
        assert data["authors"] == ["Alice Smith", "Bob Johnson"]
        assert data["keywords"] == ["deep learning", "natural language processing", "transformer"]
        assert "created_at" in data
    
    def test_paper_from_dict(self):
        """测试从字典创建 Paper"""
        data = {
            "id": "from_dict_001",
            "title": "Test Paper Title",
            "abstract": "Test abstract",
            "authors": ["Test Author"],
            "venue": "NeurIPS",
            "year": 2023,
            "url": "https://example.com",
            "keywords": ["keyword1", "keyword2"],
            "extracted_keywords": ["extracted1"],
            "pdf_url": "https://example.com/pdf",
        }
        
        paper = Paper.from_dict(data)
        
        assert paper.id == "from_dict_001"
        assert paper.title == "Test Paper Title"
        assert paper.venue == "NeurIPS"
        assert paper.year == 2023
        assert paper.keywords == ["keyword1", "keyword2"]
        assert paper.extracted_keywords == ["extracted1"]
    
    def test_paper_from_dict_with_datetime_string(self):
        """测试从带日期字符串的字典创建 Paper"""
        data = {
            "id": "datetime_test",
            "title": "Test",
            "venue": "ICML",
            "year": 2024,
            "created_at": "2024-01-15T10:30:00",
        }
        
        paper = Paper.from_dict(data)
        
        assert paper.id == "datetime_test"
        assert isinstance(paper.created_at, datetime)
        assert paper.created_at.year == 2024
        assert paper.created_at.month == 1
        assert paper.created_at.day == 15
    
    def test_paper_text_for_extraction(self, sample_paper):
        """测试 text_for_extraction 属性"""
        text = sample_paper.text_for_extraction
        
        assert isinstance(text, str)
        assert "Deep Learning for Natural Language Processing" in text
        assert "deep learning methods for NLP" in text
        assert ". " in text  # 标题和摘要用 ". " 连接
    
    def test_paper_all_keywords(self):
        """测试 all_keywords 属性"""
        paper = Paper(
            id="kw_test",
            title="Test",
            abstract="Test abstract",
            authors=[],
            venue="ICLR",
            year=2024,
            url="",
            keywords=["keyword1", "keyword2"],
            extracted_keywords=["keyword2", "keyword3"],  # keyword2 重复
        )
        
        all_kw = paper.all_keywords
        
        assert isinstance(all_kw, list)
        # 去重后应该只有 3 个关键词
        assert len(all_kw) == 3
        assert "keyword1" in all_kw
        assert "keyword2" in all_kw
        assert "keyword3" in all_kw
    
    def test_paper_default_values(self):
        """测试 Paper 默认值"""
        paper = Paper(
            id="default_test",
            title="Test",
            abstract="",
            authors=[],
            venue="ICLR",
            year=2024,
            url="",
        )
        
        assert paper.keywords == []
        assert paper.extracted_keywords == []
        assert paper.pdf_url is None
        assert isinstance(paper.created_at, datetime)
    
    def test_paper_round_trip(self, sample_paper):
        """测试序列化和反序列化往返"""
        # 序列化
        data = sample_paper.to_dict()
        
        # 反序列化
        restored = Paper.from_dict(data)
        
        # 验证
        assert restored.id == sample_paper.id
        assert restored.title == sample_paper.title
        assert restored.abstract == sample_paper.abstract
        assert restored.venue == sample_paper.venue
        assert restored.year == sample_paper.year
        assert restored.keywords == sample_paper.keywords
