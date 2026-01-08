"""
OpenAlex API 客户端

作为 Structured Layer 的锚点数据源：
- 提供论文与会议（venue）的结构化关系
- 用于会议识别与校验
- 补充 DOI、venue_id 等字段

OpenAlex 是免费、开放的学术数据库，支持大规模批量访问。
https://docs.openalex.org/
"""

import time
import requests
from typing import List, Optional, Dict, Any, Iterator
from datetime import datetime
from dataclasses import dataclass

from .models import RawPaper, Venue


# OpenAlex API 配置
OPENALEX_API_URL = "https://api.openalex.org"

# 默认字段
WORK_FIELDS = [
    "id", "doi", "title", "display_name", "publication_year",
    "abstract_inverted_index", "authorships", "primary_location",
    "type", "language", "open_access", "cited_by_count",
    "concepts", "topics"
]


@dataclass  
class OpenAlexVenue:
    """OpenAlex 来源（期刊/会议）"""
    openalex_id: str
    display_name: str
    issn: List[str] = None
    type: str = None  # journal, repository, conference


class OpenAlexClient:
    """OpenAlex API 客户端"""
    
    def __init__(self, email: str = None, delay: float = 0.1):
        """
        初始化客户端
        
        Args:
            email: 用于 polite pool（可获得更高速率限制）
            delay: 请求间隔（秒）
        """
        self.email = email
        self.delay = delay
        self.session = requests.Session()
        
        # 设置 User-Agent（OpenAlex 推荐）
        headers = {"User-Agent": "DeepTrender/1.0"}
        if email:
            headers["User-Agent"] = f"DeepTrender/1.0 (mailto:{email})"
        self.session.headers.update(headers)
        
        self._last_request = 0
    
    def _wait_for_rate_limit(self):
        """遵守速率限制"""
        elapsed = time.time() - self._last_request
        if elapsed < self.delay:
            time.sleep(self.delay - elapsed)
        self._last_request = time.time()
    
    def _make_request(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        """发送 API 请求"""
        self._wait_for_rate_limit()
        
        url = f"{OPENALEX_API_URL}/{endpoint}"
        params = params or {}
        
        # 添加 email 用于 polite pool
        if self.email:
            params["mailto"] = self.email
        
        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"OpenAlex API 请求失败: {e}")
            return None
    
    def search_works(
        self,
        venue: str = None,
        year: int = None,
        concept: str = None,
        topic: str = None,
        per_page: int = 100,
        max_results: int = 1000,
    ) -> List[RawPaper]:
        """
        搜索论文
        
        Args:
            venue: 会议/期刊名称（模糊匹配）
            year: 发表年份
            concept: 概念 ID（如 computer vision）
            topic: 主题 ID
            per_page: 每页数量
            max_results: 最大结果数
            
        Returns:
            RawPaper 列表
        """
        filters = []
        
        if venue:
            filters.append(f"primary_location.source.display_name.search:{venue}")
        if year:
            filters.append(f"publication_year:{year}")
        if concept:
            filters.append(f"concepts.id:{concept}")
        if topic:
            filters.append(f"topics.id:{topic}")
        
        filter_str = ",".join(filters) if filters else None
        
        all_papers = []
        cursor = "*"
        
        while len(all_papers) < max_results:
            params = {
                "per_page": min(per_page, max_results - len(all_papers)),
                "cursor": cursor,
            }
            if filter_str:
                params["filter"] = filter_str
            
            data = self._make_request("works", params)
            if not data or "results" not in data:
                break
            
            results = data["results"]
            if not results:
                break
            
            for work in results:
                paper = self._parse_work(work)
                if paper:
                    all_papers.append(paper)
            
            # 获取下一页游标
            cursor = data.get("meta", {}).get("next_cursor")
            if not cursor:
                break
            
            print(f"   已获取 {len(all_papers)} 篇论文...")
        
        return all_papers
    
    def search_by_venue_year(
        self,
        venue_name: str,
        year: int,
        max_results: int = 2000,
    ) -> List[RawPaper]:
        """
        按会议和年份搜索论文
        
        Args:
            venue_name: 会议名称（如 "CVPR", "NeurIPS"）
            year: 年份
            max_results: 最大结果数
            
        Returns:
            RawPaper 列表
        """
        print(f"🔍 正在从 OpenAlex 获取 {venue_name} {year}...")
        
        papers = self.search_works(
            venue=venue_name,
            year=year,
            max_results=max_results,
        )
        
        print(f"✅ OpenAlex {venue_name} {year}: 获取 {len(papers)} 篇论文")
        return papers
    
    def get_work(self, work_id: str) -> Optional[RawPaper]:
        """
        获取单篇论文
        
        Args:
            work_id: OpenAlex Work ID（如 "W2741809807"）或 DOI
            
        Returns:
            RawPaper
        """
        # 处理不同 ID 格式
        if work_id.startswith("10."):
            endpoint = f"works/doi:{work_id}"
        elif work_id.startswith("W"):
            endpoint = f"works/{work_id}"
        else:
            endpoint = f"works/{work_id}"
        
        data = self._make_request(endpoint)
        if data:
            return self._parse_work(data)
        return None
    
    def get_venue(self, venue_id: str) -> Optional[OpenAlexVenue]:
        """
        获取会议/期刊信息
        
        Args:
            venue_id: OpenAlex Source ID
            
        Returns:
            OpenAlexVenue
        """
        data = self._make_request(f"sources/{venue_id}")
        if data:
            return OpenAlexVenue(
                openalex_id=data.get("id", ""),
                display_name=data.get("display_name", ""),
                issn=data.get("issn", []),
                type=data.get("type"),
            )
        return None
    
    def search_venues(self, query: str, limit: int = 10) -> List[OpenAlexVenue]:
        """
        搜索会议/期刊
        
        Args:
            query: 搜索词
            limit: 返回数量
            
        Returns:
            OpenAlexVenue 列表
        """
        params = {
            "search": query,
            "per_page": limit,
        }
        
        data = self._make_request("sources", params)
        if not data or "results" not in data:
            return []
        
        return [
            OpenAlexVenue(
                openalex_id=source.get("id", ""),
                display_name=source.get("display_name", ""),
                issn=source.get("issn", []),
                type=source.get("type"),
            )
            for source in data["results"]
        ]
    
    def _parse_work(self, work: Dict[str, Any]) -> Optional[RawPaper]:
        """解析 OpenAlex Work 为 RawPaper"""
        try:
            # OpenAlex ID
            openalex_id = work.get("id", "").split("/")[-1]
            if not openalex_id:
                return None
            
            # 标题
            title = work.get("display_name") or work.get("title", "")
            
            # 摘要（需要从 inverted index 重建）
            abstract = self._rebuild_abstract(work.get("abstract_inverted_index"))
            
            # 作者
            authors = []
            for authorship in work.get("authorships", []):
                author = authorship.get("author", {})
                name = author.get("display_name", "")
                if name:
                    authors.append(name)
            
            # 年份
            year = work.get("publication_year")
            
            # 来源/会议
            venue_raw = None
            primary_location = work.get("primary_location") or {}
            source = primary_location.get("source") or {}
            if source:
                venue_raw = source.get("display_name")
            
            # DOI
            doi = work.get("doi", "")
            if doi and doi.startswith("https://doi.org/"):
                doi = doi.replace("https://doi.org/", "")
            
            # 类型
            work_type = work.get("type", "")
            
            return RawPaper(
                source="openalex",
                source_paper_id=openalex_id,
                title=title,
                abstract=abstract,
                authors=authors,
                year=year,
                venue_raw=venue_raw,
                journal_ref=None,
                comments=None,
                categories=work_type,
                doi=doi,
                raw_json={
                    "id": work.get("id"),
                    "type": work_type,
                    "open_access": work.get("open_access"),
                    "cited_by_count": work.get("cited_by_count"),
                    "concepts": [c.get("display_name") for c in work.get("concepts", [])[:5]],
                    "primary_location": primary_location,
                },
                retrieved_at=datetime.now(),
            )
            
        except Exception as e:
            print(f"解析 OpenAlex work 失败: {e}")
            return None
    
    def _rebuild_abstract(self, inverted_index: Dict[str, List[int]]) -> str:
        """从 inverted index 重建摘要"""
        if not inverted_index:
            return ""
        
        try:
            # 找出最大位置
            max_pos = 0
            for positions in inverted_index.values():
                if positions:
                    max_pos = max(max_pos, max(positions))
            
            # 重建
            words = [""] * (max_pos + 1)
            for word, positions in inverted_index.items():
                for pos in positions:
                    words[pos] = word
            
            return " ".join(words)
        except:
            return ""


def create_openalex_client(email: str = None) -> OpenAlexClient:
    """创建 OpenAlex 客户端"""
    return OpenAlexClient(email=email)
