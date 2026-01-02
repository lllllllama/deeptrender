"""
Web API 集成测试
"""

import pytest
import json


class TestHealthEndpoint:
    """健康检查端点测试"""
    
    def test_health_check(self, test_client):
        """测试健康检查 API"""
        response = test_client.get("/api/health")
        
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data["status"] == "healthy"
        assert data["service"] == "deeptrender"


class TestOverviewEndpoint:
    """总览统计端点测试"""
    
    def test_overview(self, test_client):
        """测试总览 API"""
        response = test_client.get("/api/stats/overview")
        
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert "total_papers" in data
        assert "total_keywords" in data
        assert "total_venues" in data
        assert "venues" in data
        assert "years" in data


class TestKeywordsEndpoints:
    """关键词端点测试"""
    
    def test_top_keywords(self, test_client):
        """测试 Top 关键词 API"""
        response = test_client.get("/api/keywords/top")
        
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert isinstance(data, list)
    
    def test_top_keywords_with_limit(self, test_client):
        """测试带限制的 Top 关键词 API"""
        response = test_client.get("/api/keywords/top?limit=10")
        
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert isinstance(data, list)
        assert len(data) <= 10
    
    def test_top_keywords_with_venue(self, test_client):
        """测试按会议筛选的 Top 关键词 API"""
        response = test_client.get("/api/keywords/top?venue=ICLR")
        
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert isinstance(data, list)
    
    def test_keyword_trends(self, test_client):
        """测试关键词趋势 API"""
        response = test_client.get("/api/keywords/trends")
        
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert isinstance(data, list)
    
    def test_keyword_trends_with_keywords(self, test_client):
        """测试指定关键词的趋势 API"""
        response = test_client.get(
            "/api/keywords/trends?keyword=transformer&keyword=bert"
        )
        
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert isinstance(data, list)
    
    def test_wordcloud(self, test_client):
        """测试词云数据 API"""
        response = test_client.get("/api/keywords/wordcloud")
        
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert isinstance(data, list)
        # 词云数据格式是 [{name, value}, ...]
        for item in data:
            if item:  # 非空项
                assert "name" in item
                assert "value" in item
    
    def test_emerging_keywords(self, test_client):
        """测试新兴关键词 API"""
        response = test_client.get("/api/keywords/emerging")
        
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert isinstance(data, list)


class TestVenuesEndpoints:
    """会议端点测试"""
    
    def test_venues_list(self, test_client):
        """测试会议列表 API"""
        response = test_client.get("/api/stats/venues")
        
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert isinstance(data, list)
    
    def test_venue_detail(self, test_client):
        """测试会议详情 API"""
        response = test_client.get("/api/stats/venue/ICLR")
        
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert "venue" in data
        assert data["venue"] == "ICLR"


class TestComparisonEndpoint:
    """会议对比端点测试"""
    
    def test_comparison(self, test_client):
        """测试会议对比 API"""
        response = test_client.get("/api/keywords/comparison")
        
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert "year" in data
        assert "venues" in data


class TestStatusEndpoint:
    """系统状态端点测试"""
    
    def test_status(self, test_client):
        """测试系统状态 API"""
        response = test_client.get("/api/status")
        
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert "database" in data
        assert "data" in data
        assert "server_time" in data


class TestStaticFiles:
    """静态文件服务测试"""
    
    def test_index_page(self, test_client):
        """测试首页"""
        response = test_client.get("/")
        
        # 首页应该返回 HTML
        assert response.status_code == 200
