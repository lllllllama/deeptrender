"""
关键词提取器测试
"""

import pytest
from scraper.models import Paper
from extractor.processor import KeywordProcessor, extract_keywords_batch
from extractor.yake_extractor import YakeExtractor, create_yake_extractor


class TestYakeExtractor:
    """YAKE 提取器测试类"""
    
    def test_create_yake_extractor(self):
        """测试创建 YAKE 提取器"""
        extractor = create_yake_extractor()
        
        assert extractor is not None
        assert isinstance(extractor, YakeExtractor)
    
    def test_yake_extract_keywords(self):
        """测试 YAKE 关键词提取"""
        extractor = create_yake_extractor()
        
        text = """
        Deep learning is a subset of machine learning that uses neural networks 
        with multiple layers. These deep neural networks can learn hierarchical 
        representations of data for tasks like image recognition and natural 
        language processing.
        """
        
        keywords = extractor.extract_keywords(text)
        
        assert isinstance(keywords, list)
        assert len(keywords) > 0
        # 所有关键词应该是字符串
        for kw in keywords:
            assert isinstance(kw, str)
            assert len(kw) > 0
    
    def test_yake_empty_text(self):
        """测试空文本提取"""
        extractor = create_yake_extractor()
        
        keywords = extractor.extract_keywords("")
        
        # 空文本应该返回空列表
        assert isinstance(keywords, list)


class TestKeywordProcessor:
    """KeywordProcessor 测试类"""
    
    def test_processor_creation_yake(self):
        """测试创建 YAKE 处理器"""
        processor = KeywordProcessor(extractor_type="yake")
        
        assert processor is not None
        assert processor.extractor_type == "yake"
        assert processor.yake is not None
        assert processor.keybert is None
    
    def test_extract_from_text(self):
        """测试从文本提取关键词"""
        processor = KeywordProcessor(extractor_type="yake")
        
        text = """
        Transformer models have revolutionized natural language processing 
        by using self-attention mechanisms. BERT and GPT are popular examples.
        """
        
        keywords = processor.extract_from_text(text)
        
        assert isinstance(keywords, list)
        assert len(keywords) > 0
    
    def test_normalize_keywords(self):
        """测试关键词标准化"""
        processor = KeywordProcessor(extractor_type="yake")
        
        raw_keywords = [
            "  Machine Learning  ",  # 首尾空格
            "DEEP LEARNING",  # 大写
            "NLP",  # 短关键词
            "a",  # 过短，应过滤
            "x" * 200,  # 过长，应过滤
            "neural network",  # 正常
        ]
        
        normalized = processor._normalize_keywords(raw_keywords)
        
        assert isinstance(normalized, list)
        # 检查转换为小写
        assert "machine learning" in normalized or "deep learning" in normalized
        # 过短的关键词应该被过滤（长度 < 2）
        assert "a" not in normalized
        # 过长的关键词应该被过滤（长度 > 100）
        assert "x" * 200 not in normalized
    
    def test_process_paper(self, sample_paper):
        """测试处理单篇论文"""
        processor = KeywordProcessor(extractor_type="yake")
        
        # 确保初始没有提取的关键词
        sample_paper.extracted_keywords = []
        
        processed = processor.process_paper(sample_paper)
        
        assert processed is sample_paper  # 返回同一个对象
        assert len(processed.extracted_keywords) > 0
        # 所有关键词应该是小写
        for kw in processed.extracted_keywords:
            assert kw == kw.lower()
    
    def test_process_papers(self, sample_papers):
        """测试批量处理论文"""
        processor = KeywordProcessor(extractor_type="yake")
        
        processed = processor.process_papers(sample_papers, show_progress=False)
        
        assert len(processed) == len(sample_papers)
        # 每篇论文都应该有提取的关键词
        for paper in processed:
            assert len(paper.extracted_keywords) > 0


class TestExtractKeywordsBatch:
    """批量提取函数测试类"""
    
    def test_extract_keywords_batch(self, sample_papers):
        """测试批量提取便捷函数"""
        processed = extract_keywords_batch(
            sample_papers, 
            extractor_type="yake",
            show_progress=False,
        )
        
        assert len(processed) == len(sample_papers)
        for paper in processed:
            assert isinstance(paper, Paper)
            assert len(paper.extracted_keywords) > 0
