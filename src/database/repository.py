"""
数据库操作仓库

三层架构的数据库操作：
- RawRepository: 原始数据层 CRUD
- StructuredRepository: 结构化数据层 CRUD  
- AnalysisRepository: 分析层 CRUD
- DatabaseRepository: 统一接口（向后兼容）
"""

import sqlite3
import json
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any
from contextlib import contextmanager
from datetime import datetime

from scraper.models import (
    RawPaper, Paper, Venue, PaperSource, PaperKeyword, TrendData
)
from config import DATABASE_PATH


# ============================================================
# BASE REPOSITORY
# ============================================================

class BaseRepository:
    """数据库基础仓库"""
    
    def __init__(self, db_path: Path = None):
        self.db_path = db_path or DATABASE_PATH
        self._init_database()
    
    def _init_database(self):
        """初始化数据库表"""
        schema_path = Path(__file__).parent / "schema.sql"
        with open(schema_path, "r", encoding="utf-8") as f:
            schema = f.read()
        
        with self._get_connection() as conn:
            conn.executescript(schema)
            conn.commit()
    
    @contextmanager
    def _get_connection(self):
        """获取数据库连接（上下文管理器）"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
        finally:
            conn.close()


# ============================================================
# RAW LAYER REPOSITORY
# ============================================================

class RawRepository(BaseRepository):
    """原始数据层仓库"""
    
    def save_raw_paper(self, paper: RawPaper) -> int:
        """
        保存原始论文
        
        Returns:
            raw_id
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO raw_papers 
                (source, source_paper_id, title, abstract, authors, year,
                 venue_raw, journal_ref, comments, categories, doi, raw_json, retrieved_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                paper.source,
                paper.source_paper_id,
                paper.title,
                paper.abstract,
                json.dumps(paper.authors) if paper.authors else None,
                paper.year,
                paper.venue_raw,
                paper.journal_ref,
                paper.comments,
                paper.categories,
                paper.doi,
                json.dumps(paper.raw_json) if paper.raw_json else None,
                datetime.now().isoformat(),
            ))
            conn.commit()
            return cursor.lastrowid
    
    def save_raw_papers(self, papers: List[RawPaper]) -> List[int]:
        """批量保存原始论文"""
        return [self.save_raw_paper(p) for p in papers]
    
    def get_raw_paper(self, raw_id: int) -> Optional[RawPaper]:
        """获取原始论文"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM raw_papers WHERE raw_id = ?", (raw_id,))
            row = cursor.fetchone()
            return self._row_to_raw_paper(row) if row else None
    
    def get_raw_paper_by_source(self, source: str, source_paper_id: str) -> Optional[RawPaper]:
        """按来源获取原始论文"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM raw_papers WHERE source = ? AND source_paper_id = ?",
                (source, source_paper_id)
            )
            row = cursor.fetchone()
            return self._row_to_raw_paper(row) if row else None
    
    def get_unprocessed_raw_papers(self, source: str = None, limit: int = 1000) -> List[RawPaper]:
        """获取未处理的原始论文（不在 paper_sources 中）"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            query = """
                SELECT r.* FROM raw_papers r
                LEFT JOIN paper_sources ps ON r.raw_id = ps.raw_id
                WHERE ps.id IS NULL
            """
            params = []
            if source:
                query += " AND r.source = ?"
                params.append(source)
            query += " LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            return [self._row_to_raw_paper(row) for row in cursor.fetchall()]
    
    def get_raw_papers_by_source(self, source: str, limit: int = None) -> List[RawPaper]:
        """按来源获取原始论文"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT * FROM raw_papers WHERE source = ?"
            params = [source]
            if limit:
                query += " LIMIT ?"
                params.append(limit)
            cursor.execute(query, params)
            return [self._row_to_raw_paper(row) for row in cursor.fetchall()]
    
    def get_raw_paper_count(self, source: str = None) -> int:
        """获取原始论文数量"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if source:
                cursor.execute("SELECT COUNT(*) as count FROM raw_papers WHERE source = ?", (source,))
            else:
                cursor.execute("SELECT COUNT(*) as count FROM raw_papers")
            return cursor.fetchone()["count"]
    
    def _row_to_raw_paper(self, row: sqlite3.Row) -> RawPaper:
        """将数据库行转换为 RawPaper"""
        authors = row["authors"]
        if isinstance(authors, str):
            authors = json.loads(authors)
        
        raw_json = row["raw_json"]
        if isinstance(raw_json, str):
            raw_json = json.loads(raw_json)
        
        retrieved_at = row["retrieved_at"]
        if isinstance(retrieved_at, str):
            retrieved_at = datetime.fromisoformat(retrieved_at)
        
        return RawPaper(
            raw_id=row["raw_id"],
            source=row["source"],
            source_paper_id=row["source_paper_id"],
            title=row["title"] or "",
            abstract=row["abstract"] or "",
            authors=authors or [],
            year=row["year"],
            venue_raw=row["venue_raw"],
            journal_ref=row["journal_ref"],
            comments=row["comments"],
            categories=row["categories"],
            doi=row["doi"],
            raw_json=raw_json,
            retrieved_at=retrieved_at or datetime.now(),
        )


# ============================================================
# STRUCTURED LAYER REPOSITORY
# ============================================================

class StructuredRepository(BaseRepository):
    """结构化数据层仓库"""
    
    # ========== Venue 操作 ==========
    
    def save_venue(self, venue: Venue) -> int:
        """保存会议/期刊"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO venues 
                (canonical_name, full_name, domain, venue_type, first_year, last_year)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                venue.canonical_name,
                venue.full_name,
                venue.domain,
                venue.venue_type,
                venue.first_year,
                venue.last_year,
            ))
            conn.commit()
            
            # 获取 venue_id
            cursor.execute(
                "SELECT venue_id FROM venues WHERE canonical_name = ?",
                (venue.canonical_name,)
            )
            return cursor.fetchone()["venue_id"]
    
    def get_venue(self, venue_id: int) -> Optional[Venue]:
        """获取会议"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM venues WHERE venue_id = ?", (venue_id,))
            row = cursor.fetchone()
            return self._row_to_venue(row) if row else None
    
    def get_venue_by_name(self, canonical_name: str) -> Optional[Venue]:
        """按名称获取会议"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM venues WHERE canonical_name = ?",
                (canonical_name,)
            )
            row = cursor.fetchone()
            return self._row_to_venue(row) if row else None
    
    def get_all_venues(self) -> List[Venue]:
        """获取所有会议"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM venues ORDER BY canonical_name")
            return [self._row_to_venue(row) for row in cursor.fetchall()]
    
    def _row_to_venue(self, row: sqlite3.Row) -> Venue:
        """将数据库行转换为 Venue"""
        return Venue(
            venue_id=row["venue_id"],
            canonical_name=row["canonical_name"],
            full_name=row["full_name"],
            domain=row["domain"],
            venue_type=row["venue_type"],
            first_year=row["first_year"],
            last_year=row["last_year"],
        )
    
    # ========== Paper 操作 ==========
    
    def save_paper(self, paper: Paper) -> int:
        """保存论文"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO papers 
                (canonical_title, abstract, authors, year, venue_id, venue_type,
                 domain, quality_flag, doi, url, pdf_url, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                paper.canonical_title,
                paper.abstract,
                json.dumps(paper.authors) if paper.authors else None,
                paper.year,
                paper.venue_id,
                paper.venue_type,
                paper.domain,
                paper.quality_flag,
                paper.doi,
                paper.url,
                paper.pdf_url,
                datetime.now().isoformat(),
            ))
            conn.commit()
            return cursor.lastrowid
    
    def get_paper(self, paper_id: int) -> Optional[Paper]:
        """获取论文"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM papers WHERE paper_id = ?", (paper_id,))
            row = cursor.fetchone()
            return self._row_to_paper(conn, row) if row else None
    
    def get_papers_by_venue_year(self, venue_id: int, year: int) -> List[Paper]:
        """获取指定会议和年份的论文"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM papers WHERE venue_id = ? AND year = ?",
                (venue_id, year)
            )
            return [self._row_to_paper(conn, row) for row in cursor.fetchall()]
    
    def get_paper_count(self, venue_id: int = None, year: int = None) -> int:
        """获取论文数量"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT COUNT(*) as count FROM papers WHERE 1=1"
            params = []
            
            if venue_id:
                query += " AND venue_id = ?"
                params.append(venue_id)
            if year:
                query += " AND year = ?"
                params.append(year)
            
            cursor.execute(query, params)
            return cursor.fetchone()["count"]
    
    def find_paper_by_title(self, title: str, year: int = None) -> Optional[int]:
        """
        根据标题查找论文（用于去重）
        
        Args:
            title: 标准化后的标题（小写）
            year: 年份（可选）
            
        Returns:
            paper_id 如果找到，否则 None
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # 使用 LOWER 进行不区分大小写匹配
            if year:
                cursor.execute(
                    "SELECT paper_id FROM papers WHERE LOWER(canonical_title) = ? AND year = ? LIMIT 1",
                    (title.lower(), year)
                )
            else:
                cursor.execute(
                    "SELECT paper_id FROM papers WHERE LOWER(canonical_title) = ? LIMIT 1",
                    (title.lower(),)
                )
            
            row = cursor.fetchone()
            return row["paper_id"] if row else None
    
    def _row_to_paper(self, conn: sqlite3.Connection, row: sqlite3.Row) -> Paper:
        """将数据库行转换为 Paper"""
        authors = row["authors"]
        if isinstance(authors, str):
            authors = json.loads(authors)
        
        # 获取 venue 名称
        venue_name = None
        if row["venue_id"]:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT canonical_name FROM venues WHERE venue_id = ?",
                (row["venue_id"],)
            )
            venue_row = cursor.fetchone()
            if venue_row:
                venue_name = venue_row["canonical_name"]
        
        return Paper(
            paper_id=row["paper_id"],
            canonical_title=row["canonical_title"],
            abstract=row["abstract"] or "",
            authors=authors or [],
            year=row["year"],
            venue_id=row["venue_id"],
            venue_type=row["venue_type"] or "unknown",
            domain=row["domain"],
            quality_flag=row["quality_flag"] or "unknown",
            doi=row["doi"],
            url=row["url"],
            pdf_url=row["pdf_url"],
            venue_name=venue_name,
        )
    
    # ========== PaperSource 操作 ==========
    
    def link_paper_source(self, paper_id: int, raw_id: int, source: str, confidence: float = 1.0):
        """关联论文和原始数据"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO paper_sources (paper_id, raw_id, source, confidence)
                VALUES (?, ?, ?, ?)
            """, (paper_id, raw_id, source, confidence))
            conn.commit()
    
    def get_paper_sources(self, paper_id: int) -> List[PaperSource]:
        """获取论文的所有数据源"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM paper_sources WHERE paper_id = ?",
                (paper_id,)
            )
            return [
                PaperSource(
                    id=row["id"],
                    paper_id=row["paper_id"],
                    raw_id=row["raw_id"],
                    source=row["source"],
                    confidence=row["confidence"],
                )
                for row in cursor.fetchall()
            ]


# ============================================================
# ANALYSIS LAYER REPOSITORY
# ============================================================

class AnalysisRepository(BaseRepository):
    """分析层仓库"""
    
    # ========== Keyword 操作 ==========
    
    def save_keyword(self, paper_id: int, keyword: str, method: str, score: float = 1.0):
        """保存关键词"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO paper_keywords (paper_id, keyword, method, score)
                VALUES (?, ?, ?, ?)
            """, (paper_id, keyword.lower().strip(), method, score))
            conn.commit()
    
    def save_keywords(self, paper_id: int, keywords: List[Tuple[str, str, float]]):
        """批量保存关键词 [(keyword, method, score), ...]"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            for keyword, method, score in keywords:
                cursor.execute("""
                    INSERT OR REPLACE INTO paper_keywords (paper_id, keyword, method, score)
                    VALUES (?, ?, ?, ?)
                """, (paper_id, keyword.lower().strip(), method, score))
            conn.commit()
    
    def get_paper_keywords(self, paper_id: int, method: str = None) -> List[PaperKeyword]:
        """获取论文的关键词"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if method:
                cursor.execute(
                    "SELECT * FROM paper_keywords WHERE paper_id = ? AND method = ?",
                    (paper_id, method)
                )
            else:
                cursor.execute(
                    "SELECT * FROM paper_keywords WHERE paper_id = ?",
                    (paper_id,)
                )
            return [
                PaperKeyword(
                    id=row["id"],
                    paper_id=row["paper_id"],
                    keyword=row["keyword"],
                    method=row["method"],
                    score=row["score"],
                )
                for row in cursor.fetchall()
            ]
    
    def get_top_keywords(
        self,
        venue_id: int = None,
        year: int = None,
        method: str = None,
        limit: int = 50,
    ) -> List[Tuple[str, int]]:
        """获取 Top-K 关键词"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            query = """
                SELECT pk.keyword, COUNT(*) as count
                FROM paper_keywords pk
                JOIN papers p ON pk.paper_id = p.paper_id
                WHERE 1=1
            """
            params = []
            
            if venue_id:
                query += " AND p.venue_id = ?"
                params.append(venue_id)
            if year:
                query += " AND p.year = ?"
                params.append(year)
            if method:
                query += " AND pk.method = ?"
                params.append(method)
            
            query += " GROUP BY pk.keyword ORDER BY count DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            return [(row["keyword"], row["count"]) for row in cursor.fetchall()]
    
    def get_keyword_trend(self, keyword: str, venue_id: int = None) -> Dict[int, int]:
        """获取关键词的年度趋势"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            query = """
                SELECT p.year, COUNT(*) as count
                FROM paper_keywords pk
                JOIN papers p ON pk.paper_id = p.paper_id
                WHERE pk.keyword = ?
            """
            params = [keyword.lower()]
            
            if venue_id:
                query += " AND p.venue_id = ?"
                params.append(venue_id)
            
            query += " GROUP BY p.year ORDER BY p.year"
            
            cursor.execute(query, params)
            return {row["year"]: row["count"] for row in cursor.fetchall()}
    
    # ========== Trend Cache 操作 ==========
    
    def update_trend_cache(self, keyword: str, venue_id: int, year: int, count: int):
        """更新趋势缓存"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO trend_cache (keyword, venue_id, year, count, updated_at)
                VALUES (?, ?, ?, ?, ?)
            """, (keyword.lower(), venue_id, year, count, datetime.now().isoformat()))
            conn.commit()
    
    def get_cached_trends(self, keyword: str) -> List[Tuple[int, int, int]]:
        """获取缓存的趋势数据 [(venue_id, year, count), ...]"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT venue_id, year, count FROM trend_cache WHERE keyword = ?",
                (keyword.lower(),)
            )
            return [(row["venue_id"], row["year"], row["count"]) for row in cursor.fetchall()]


# ============================================================
# UNIFIED REPOSITORY (向后兼容)
# ============================================================

class DatabaseRepository(BaseRepository):
    """
    统一数据库仓库
    
    整合三层仓库的功能，并提供向后兼容的接口。
    """
    
    def __init__(self, db_path: Path = None):
        super().__init__(db_path)
        self.raw = RawRepository(self.db_path)
        self.structured = StructuredRepository(self.db_path)
        self.analysis = AnalysisRepository(self.db_path)
    
    # ========== 向后兼容接口 ==========
    
    def save_paper(self, paper: Paper) -> bool:
        """保存论文（兼容旧接口）"""
        try:
            # 处理 venue
            venue_id = None
            if paper.venue_name:
                venue = self.structured.get_venue_by_name(paper.venue_name)
                if not venue:
                    venue_id = self.structured.save_venue(Venue(
                        canonical_name=paper.venue_name,
                        domain=paper.domain,
                    ))
                else:
                    venue_id = venue.venue_id
                paper.venue_id = venue_id
            
            # 保存论文
            paper_id = self.structured.save_paper(paper)
            paper.paper_id = paper_id
            
            # 保存关键词
            for kw in paper.keywords:
                self.analysis.save_keyword(paper_id, kw, "author")
            for kw in paper.extracted_keywords:
                self.analysis.save_keyword(paper_id, kw, "extracted")
            
            return True
        except Exception as e:
            print(f"保存论文失败: {e}")
            return False
    
    def save_papers(self, papers: List[Paper]) -> int:
        """批量保存论文（兼容旧接口）"""
        count = 0
        for paper in papers:
            if self.save_paper(paper):
                count += 1
        return count
    
    def get_paper(self, paper_id: int) -> Optional[Paper]:
        """获取论文"""
        paper = self.structured.get_paper(paper_id)
        if paper:
            # 加载关键词
            keywords = self.analysis.get_paper_keywords(paper_id)
            paper.keywords = [k.keyword for k in keywords if k.method == "author"]
            paper.extracted_keywords = [k.keyword for k in keywords if k.method != "author"]
        return paper
    
    def get_paper_count(self, venue: str = None, year: int = None) -> int:
        """获取论文数量（兼容旧接口）"""
        venue_id = None
        if venue:
            v = self.structured.get_venue_by_name(venue)
            if v:
                venue_id = v.venue_id
        return self.structured.get_paper_count(venue_id=venue_id, year=year)
    
    def get_top_keywords(
        self,
        venue: str = None,
        year: int = None,
        source: str = None,
        limit: int = 50,
    ) -> List[Tuple[str, int]]:
        """获取 Top-K 关键词（兼容旧接口）"""
        venue_id = None
        if venue:
            v = self.structured.get_venue_by_name(venue)
            if v:
                venue_id = v.venue_id
        
        # source 映射到 method
        method = None
        if source == "author":
            method = "author"
        elif source == "extracted":
            method = "extracted"  # 包含 yake, keybert 等
        
        return self.analysis.get_top_keywords(
            venue_id=venue_id,
            year=year,
            method=method,
            limit=limit,
        )
    
    def get_keyword_trend(self, keyword: str, venue: str = None) -> Dict[int, int]:
        """获取关键词趋势（兼容旧接口）"""
        venue_id = None
        if venue:
            v = self.structured.get_venue_by_name(venue)
            if v:
                venue_id = v.venue_id
        return self.analysis.get_keyword_trend(keyword, venue_id)
    
    def get_all_venues(self) -> List[str]:
        """获取所有会议名称（兼容旧接口）"""
        venues = self.structured.get_all_venues()
        return [v.canonical_name for v in venues]
    
    def get_all_years(self, venue: str = None) -> List[int]:
        """获取所有年份（兼容旧接口）"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if venue:
                v = self.structured.get_venue_by_name(venue)
                if v:
                    cursor.execute(
                        "SELECT DISTINCT year FROM papers WHERE venue_id = ? ORDER BY year DESC",
                        (v.venue_id,)
                    )
                else:
                    return []
            else:
                cursor.execute("SELECT DISTINCT year FROM papers ORDER BY year DESC")
            return [row["year"] for row in cursor.fetchall()]
    
    def get_venue_comparison(self, year: int, limit: int = 10) -> Dict[str, List[Tuple[str, int]]]:
        """获取会议对比（兼容旧接口）"""
        result = {}
        venues = self.structured.get_all_venues()
        
        for venue in venues:
            keywords = self.analysis.get_top_keywords(
                venue_id=venue.venue_id,
                year=year,
                limit=limit,
            )
            if keywords:
                result[venue.canonical_name] = keywords
        
        return result
    
    # ========== 爬取日志（向后兼容）==========
    
    def log_scrape(self, venue: str, year: int, paper_count: int):
        """记录爬取日志"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO scrape_logs (venue, year, paper_count)
                VALUES (?, ?, ?)
            """, (venue, year, paper_count))
            conn.commit()
    
    def get_last_scrape(self, venue: str, year: int) -> Optional[datetime]:
        """获取上次爬取时间"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT scraped_at FROM scrape_logs
                WHERE venue = ? AND year = ?
                ORDER BY scraped_at DESC LIMIT 1
            """, (venue, year))
            row = cursor.fetchone()
            if row:
                return datetime.fromisoformat(row["scraped_at"])
            return None
    
    def should_scrape(self, venue: str, year: int, max_age_days: int = 7) -> bool:
        """检查是否需要爬取"""
        from datetime import timedelta
        
        last_scrape = self.get_last_scrape(venue, year)
        if last_scrape is None:
            return True
        
        age = datetime.now() - last_scrape
        return age > timedelta(days=max_age_days)


# ============================================================
# 单例与工厂函数
# ============================================================

_repository: Optional[DatabaseRepository] = None
_raw_repository: Optional[RawRepository] = None
_structured_repository: Optional[StructuredRepository] = None
_analysis_repository: Optional[AnalysisRepository] = None


def get_repository(db_path: Path = None) -> DatabaseRepository:
    """获取统一数据库仓库（单例）"""
    global _repository
    if _repository is None:
        _repository = DatabaseRepository(db_path)
    return _repository


def get_raw_repository(db_path: Path = None) -> RawRepository:
    """获取原始数据层仓库"""
    global _raw_repository
    if _raw_repository is None:
        _raw_repository = RawRepository(db_path)
    return _raw_repository


def get_structured_repository(db_path: Path = None) -> StructuredRepository:
    """获取结构化数据层仓库"""
    global _structured_repository
    if _structured_repository is None:
        _structured_repository = StructuredRepository(db_path)
    return _structured_repository


def get_analysis_repository(db_path: Path = None) -> AnalysisRepository:
    """获取分析层仓库"""
    global _analysis_repository
    if _analysis_repository is None:
        _analysis_repository = AnalysisRepository(db_path)
    return _analysis_repository
