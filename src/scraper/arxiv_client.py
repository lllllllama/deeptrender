"""
arXiv API 客户端

作为 Raw Layer 的主要数据源，用于大规模论文采集。
arXiv 提供最广泛的 AI 相关论文覆盖，更新最快。

使用说明:
- 按领域采集（cs.CV / cs.CL / cs.LG / cs.AI）
- 不做会议筛选（仅用于 Raw Layer）
- 完整保存所有元数据
"""

import time
import urllib.parse
import feedparser
import requests
from typing import List, Optional, Iterator, Dict, Any
from datetime import datetime, timedelta
from dataclasses import dataclass

from .models import RawPaper


# arXiv API 配置
ARXIV_API_URL = "http://export.arxiv.org/api/query"
ARXIV_BULK_URL = "https://arxiv.org/list"

# 默认 AI 相关类别
DEFAULT_CATEGORIES = ["cs.CV", "cs.CL", "cs.LG", "cs.AI", "cs.RO", "cs.NE", "stat.ML"]


@dataclass
class ArxivQuery:
    """arXiv 查询参数"""
    categories: List[str] = None  # cs.CV, cs.LG, etc.
    search_query: str = None  # 自定义搜索词
    start_date: datetime = None
    end_date: datetime = None
    max_results: int = 1000
    

class ArxivClient:
    """arXiv API 客户端"""
    
    def __init__(self, delay: float = 3.0):
        """
        初始化客户端
        
        Args:
            delay: 请求间隔（秒），arXiv 要求至少 3 秒
        """
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "DepthTrender/1.0 (https://github.com/depthtrender)"
        })
        self._last_request = 0
    
    def _wait_for_rate_limit(self):
        """遵守 arXiv 速率限制"""
        elapsed = time.time() - self._last_request
        if elapsed < self.delay:
            time.sleep(self.delay - elapsed)
        self._last_request = time.time()
    
    def search(
        self,
        categories: List[str] = None,
        search_query: str = None,
        start: int = 0,
        max_results: int = 100,
    ) -> List[RawPaper]:
        """
        搜索 arXiv 论文
        
        Args:
            categories: arXiv 类别列表（如 ["cs.CV", "cs.LG"]）
            search_query: 搜索词
            start: 起始位置
            max_results: 最大结果数（单次最多 2000）
            
        Returns:
            RawPaper 列表
        """
        self._wait_for_rate_limit()
        
        # 构建查询
        query_parts = []
        
        if categories:
            cat_query = " OR ".join([f"cat:{cat}" for cat in categories])
            query_parts.append(f"({cat_query})")
        
        if search_query:
            query_parts.append(f"({search_query})")
        
        query = " AND ".join(query_parts) if query_parts else "cat:cs.LG"
        
        params = {
            "search_query": query,
            "start": start,
            "max_results": min(max_results, 2000),
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }
        
        try:
            response = self.session.get(ARXIV_API_URL, params=params)
            response.raise_for_status()
            
            # 解析 Atom feed
            feed = feedparser.parse(response.text)
            papers = []
            
            for entry in feed.entries:
                paper = self._parse_entry(entry)
                if paper:
                    papers.append(paper)
            
            return papers
            
        except Exception as e:
            print(f"arXiv API 请求失败: {e}")
            return []
    
    def search_recent(
        self,
        categories: List[str] = None,
        days: int = 7,
        max_results: int = 1000,
    ) -> List[RawPaper]:
        """
        获取最近几天的论文
        
        Args:
            categories: arXiv 类别
            days: 天数
            max_results: 最大结果数
            
        Returns:
            RawPaper 列表
        """
        categories = categories or DEFAULT_CATEGORIES
        
        print(f"🔍 正在从 arXiv 获取最近 {days} 天的论文...")
        print(f"   类别: {', '.join(categories)}")
        
        all_papers = []
        start = 0
        batch_size = 500
        
        while len(all_papers) < max_results:
            papers = self.search(
                categories=categories,
                start=start,
                max_results=min(batch_size, max_results - len(all_papers)),
            )
            
            if not papers:
                break
            
            # 过滤日期
            cutoff_date = datetime.now() - timedelta(days=days)
            recent_papers = []
            
            for paper in papers:
                if paper.retrieved_at and paper.retrieved_at >= cutoff_date:
                    recent_papers.append(paper)
                elif paper.year and paper.year >= cutoff_date.year:
                    recent_papers.append(paper)
            
            all_papers.extend(recent_papers)
            
            # 如果这批次都太旧了，停止
            if len(recent_papers) < len(papers) * 0.5:
                break
            
            start += batch_size
            print(f"   已获取 {len(all_papers)} 篇论文...")
        
        print(f"✅ arXiv: 共获取 {len(all_papers)} 篇论文")
        return all_papers
    
    def search_by_category(
        self,
        category: str,
        max_results: int = 1000,
    ) -> List[RawPaper]:
        """
        按类别获取论文
        
        Args:
            category: arXiv 类别（如 "cs.CV"）
            max_results: 最大结果数
            
        Returns:
            RawPaper 列表
        """
        print(f"🔍 正在从 arXiv 获取 {category} 类别论文...")
        
        all_papers = []
        start = 0
        batch_size = 500
        
        while len(all_papers) < max_results:
            papers = self.search(
                categories=[category],
                start=start,
                max_results=min(batch_size, max_results - len(all_papers)),
            )
            
            if not papers:
                break
            
            all_papers.extend(papers)
            start += batch_size
            
            print(f"   已获取 {len(all_papers)} 篇论文...")
        
        print(f"✅ arXiv {category}: 共获取 {len(all_papers)} 篇论文")
        return all_papers
    
    def get_paper(self, arxiv_id: str) -> Optional[RawPaper]:
        """
        获取单篇论文
        
        Args:
            arxiv_id: arXiv ID（如 "2312.12345"）
            
        Returns:
            RawPaper
        """
        self._wait_for_rate_limit()
        
        params = {
            "id_list": arxiv_id,
            "max_results": 1,
        }
        
        try:
            response = self.session.get(ARXIV_API_URL, params=params)
            response.raise_for_status()
            
            feed = feedparser.parse(response.text)
            if feed.entries:
                return self._parse_entry(feed.entries[0])
            return None
            
        except Exception as e:
            print(f"获取 arXiv 论文失败: {e}")
            return None
    
    def _parse_entry(self, entry: Dict[str, Any]) -> Optional[RawPaper]:
        """解析 arXiv Atom entry 为 RawPaper"""
        try:
            # 提取 arXiv ID
            arxiv_id = entry.get("id", "").split("/abs/")[-1].split("v")[0]
            if not arxiv_id:
                return None
            
            # 标题（移除换行）
            title = entry.get("title", "").replace("\n", " ").strip()
            
            # 摘要
            abstract = entry.get("summary", "").replace("\n", " ").strip()
            
            # 作者
            authors = []
            for author in entry.get("authors", []):
                name = author.get("name", "")
                if name:
                    authors.append(name)
            
            # 发布日期
            published = entry.get("published", "")
            year = None
            if published:
                try:
                    year = int(published[:4])
                except:
                    pass
            
            # 类别
            categories = []
            for tag in entry.get("tags", []):
                term = tag.get("term", "")
                if term:
                    categories.append(term)
            
            # Comments（可能包含会议信息）
            comments = entry.get("arxiv_comment", "")
            
            # Journal reference
            journal_ref = entry.get("arxiv_journal_ref", "")
            
            # DOI
            doi = entry.get("arxiv_doi", "")
            
            # PDF 链接
            pdf_url = None
            for link in entry.get("links", []):
                if link.get("type") == "application/pdf":
                    pdf_url = link.get("href")
                    break
            
            return RawPaper(
                source="arxiv",
                source_paper_id=arxiv_id,
                title=title,
                abstract=abstract,
                authors=authors,
                year=year,
                venue_raw=None,  # arXiv 本身不是 venue
                journal_ref=journal_ref,
                comments=comments,
                categories=",".join(categories),
                doi=doi,
                raw_json={
                    "id": entry.get("id"),
                    "published": published,
                    "updated": entry.get("updated"),
                    "pdf_url": pdf_url,
                    "links": [l.get("href") for l in entry.get("links", [])],
                },
                retrieved_at=datetime.now(),
            )
            
        except Exception as e:
            print(f"解析 arXiv entry 失败: {e}")
            return None


def create_arxiv_client(delay: float = 3.0) -> ArxivClient:
    """创建 arXiv 客户端"""
    return ArxivClient(delay=delay)
