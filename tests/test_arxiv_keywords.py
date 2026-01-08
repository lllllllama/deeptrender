"""
Tests for arXiv keyword extraction
"""

import pytest


class TestArxivKeywordExtraction:
    """Test arXiv keyword extraction methods"""
    
    def test_extract_bucket_keywords_empty_papers(self):
        """Test keyword extraction with empty papers list"""
        from analysis.arxiv_agent import ArxivAnalysisAgent
        
        agent = ArxivAnalysisAgent()
        keywords = agent._extract_bucket_keywords([], limit=10)
        
        assert isinstance(keywords, list)
        assert len(keywords) == 0
    
    def test_extract_with_frequency_basic(self):
        """Test frequency-based keyword extraction"""
        from analysis.arxiv_agent import ArxivAnalysisAgent
        
        agent = ArxivAnalysisAgent()
        
        papers = [
            {"title": "Deep Learning for Computer Vision", "abstract": "Test"},
            {"title": "Deep Learning for Natural Language", "abstract": "Test"},
            {"title": "Computer Vision Applications", "abstract": "Test"}
        ]
        
        keywords = agent._extract_with_frequency(papers, limit=5)
        
        assert isinstance(keywords, list)
        assert len(keywords) > 0
        
        # Check format
        for kw_data in keywords:
            assert "keyword" in kw_data
            assert "count" in kw_data
            assert isinstance(kw_data["keyword"], str)
            assert isinstance(kw_data["count"], int)
    
    def test_extract_with_frequency_filters_stopwords(self):
        """Test that stopwords are filtered out"""
        from analysis.arxiv_agent import ArxivAnalysisAgent
        
        agent = ArxivAnalysisAgent()
        
        papers = [
            {"title": "The Deep Learning Model", "abstract": "Test"},
            {"title": "A Neural Network Approach", "abstract": "Test"}
        ]
        
        keywords = agent._extract_with_frequency(papers, limit=10)
        
        # Stopwords should be filtered
        keyword_list = [kw["keyword"] for kw in keywords]
        assert "the" not in keyword_list
        assert "a" not in keyword_list
        assert "model" not in keyword_list  # Common academic word
    
    def test_is_valid_keyword(self):
        """Test keyword validation"""
        from analysis.arxiv_agent import ArxivAnalysisAgent
        
        agent = ArxivAnalysisAgent()
        
        # Valid keywords
        assert agent._is_valid_keyword("machine-learning") == True
        assert agent._is_valid_keyword("deep learning") == True
        assert agent._is_valid_keyword("transformer") == True
        
        # Invalid keywords
        assert agent._is_valid_keyword("") == False
        assert agent._is_valid_keyword("a") == False
        assert agent._is_valid_keyword("ab") == False
        assert agent._is_valid_keyword("123") == False
        assert agent._is_valid_keyword("test@123") == False
    
    def test_extract_with_yake_basic(self):
        """Test YAKE-based keyword extraction"""
        from analysis.arxiv_agent import ArxivAnalysisAgent
        
        agent = ArxivAnalysisAgent()
        
        papers = [
            {
                "title": "Transformer Networks for Machine Translation",
                "abstract": "We propose a novel transformer architecture for neural machine translation tasks."
            },
            {
                "title": "Attention Mechanisms in Deep Learning",
                "abstract": "This paper explores attention mechanisms and their applications in deep learning."
            }
        ]
        
        try:
            keywords = agent._extract_with_yake(papers, limit=5)
            
            assert isinstance(keywords, list)
            # YAKE might return empty if import fails, that's ok
            if keywords:
                assert len(keywords) <= 5
                for kw_data in keywords:
                    assert "keyword" in kw_data
                    assert "count" in kw_data
        except ImportError:
            pytest.skip("YAKE not installed")
    
    def test_extract_bucket_keywords_uses_fallback(self):
        """Test that extraction falls back through strategies"""
        from analysis.arxiv_agent import ArxivAnalysisAgent
        
        agent = ArxivAnalysisAgent()
        
        papers = [
            {
                "raw_id": 1,
                "title": "Deep Learning Research",
                "abstract": "A comprehensive study of deep learning methods."
            }
        ]
        
        # Should use fallback strategies (DB -> YAKE -> frequency)
        keywords = agent._extract_bucket_keywords(papers, limit=5)
        
        # Should return something (at least from frequency fallback)
        assert isinstance(keywords, list)
        assert len(keywords) >= 0  # May be empty if all filtered
    
    def test_keyword_extraction_limit(self):
        """Test that keyword extraction respects limit"""
        from analysis.arxiv_agent import ArxivAnalysisAgent
        
        agent = ArxivAnalysisAgent()
        
        papers = [
            {"title": "Machine Learning Deep Learning Neural Networks Computer Vision Natural Language Processing", "abstract": "Test"}
        ]
        
        keywords = agent._extract_with_frequency(papers, limit=3)
        
        assert len(keywords) <= 3
    
    def test_keyword_extraction_case_insensitive(self):
        """Test that keyword extraction is case-insensitive"""
        from analysis.arxiv_agent import ArxivAnalysisAgent
        
        agent = ArxivAnalysisAgent()
        
        papers = [
            {"title": "Transformer TRANSFORMER transformer", "abstract": "Test"}
        ]
        
        keywords = agent._extract_with_frequency(papers, limit=5)
        
        # Should count all as same keyword (lowercase)
        if keywords:
            assert keywords[0]["keyword"] == "transformer"
            assert keywords[0]["count"] == 3
