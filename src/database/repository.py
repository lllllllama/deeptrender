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
            conn.execute("PRAGMA journal_mode = WAL")
            conn.execute("PRAGMA synchronous = NORMAL")
            conn.execute("PRAGMA cache_size = -64000")
            conn.execute("PRAGMA temp_store = MEMORY")
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
                (canonical_name, full_name, domain, tier, venue_type, 
                 openreview_ids, years_available, first_year, last_year, discovered_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                venue.canonical_name,
                venue.full_name,
                venue.domain,
                getattr(venue, 'tier', 'C'),
                venue.venue_type,
                json.dumps(getattr(venue, 'openreview_ids', [])),
                json.dumps(getattr(venue, 'years_available', [])),
                venue.first_year,
                venue.last_year,
                datetime.now().isoformat(),
            ))
            conn.commit()
            
            # 获取 venue_id
            cursor.execute(
                "SELECT venue_id FROM venues WHERE canonical_name = ?",
                (venue.canonical_name,)
            )
            return cursor.fetchone()["venue_id"]
    
    def save_discovered_venue(
        self,
        name: str,
        full_name: str,
        domain: str,
        tier: str,
        venue_type: str,
        openreview_ids: List[str],
        years: List[int]
    ) -> int:
        """保存动态发现的会议"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # 检查是否已存在
            cursor.execute(
                "SELECT venue_id, openreview_ids, years_available FROM venues WHERE canonical_name = ?",
                (name,)
            )
            existing = cursor.fetchone()
            
            if existing:
                # 更新现有记录 - 合并 openreview_ids 和 years
                existing_ids = json.loads(existing["openreview_ids"] or "[]")
                existing_years = json.loads(existing["years_available"] or "[]")
                
                merged_ids = list(set(existing_ids + openreview_ids))
                merged_years = sorted(set(existing_years + years), reverse=True)
                
                cursor.execute("""
                    UPDATE venues SET 
                        openreview_ids = ?,
                        years_available = ?,
                        first_year = ?,
                        last_year = ?
                    WHERE venue_id = ?
                """, (
                    json.dumps(merged_ids),
                    json.dumps(merged_years),
                    min(merged_years) if merged_years else None,
                    max(merged_years) if merged_years else None,
                    existing["venue_id"]
                ))
                conn.commit()
                return existing["venue_id"]
            else:
                # 插入新记录
                cursor.execute("""
                    INSERT INTO venues 
                    (canonical_name, full_name, domain, tier, venue_type,
                     openreview_ids, years_available, first_year, last_year, discovered_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    name,
                    full_name,
                    domain,
                    tier,
                    venue_type,
                    json.dumps(openreview_ids),
                    json.dumps(years),
                    min(years) if years else None,
                    max(years) if years else None,
                    datetime.now().isoformat()
                ))
                conn.commit()
                return cursor.lastrowid
    
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
            cursor.execute("SELECT * FROM venues ORDER BY tier, canonical_name")
            return [self._row_to_venue(row) for row in cursor.fetchall()]
    
    def get_venues_by_domain(self, domain: str) -> List[Venue]:
        """按领域获取会议"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM venues WHERE domain = ? ORDER BY tier, canonical_name",
                (domain,)
            )
            return [self._row_to_venue(row) for row in cursor.fetchall()]
    
    def get_venues_by_tier(self, tier: str) -> List[Venue]:
        """按等级获取会议"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM venues WHERE tier = ? ORDER BY canonical_name",
                (tier,)
            )
            return [self._row_to_venue(row) for row in cursor.fetchall()]
    
    def get_venue_stats(self) -> Dict:
        """获取会议统计"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # 按领域统计
            cursor.execute("""
                SELECT domain, COUNT(*) as count 
                FROM venues GROUP BY domain ORDER BY count DESC
            """)
            by_domain = {row["domain"]: row["count"] for row in cursor.fetchall()}
            
            # 按等级统计
            cursor.execute("""
                SELECT tier, COUNT(*) as count 
                FROM venues GROUP BY tier ORDER BY tier
            """)
            by_tier = {row["tier"]: row["count"] for row in cursor.fetchall()}
            
            # 总数
            cursor.execute("SELECT COUNT(*) as total FROM venues")
            total = cursor.fetchone()["total"]
            
            return {
                "total": total,
                "by_domain": by_domain,
                "by_tier": by_tier
            }
    
    def _row_to_venue(self, row: sqlite3.Row) -> Venue:
        """将数据库行转换为 Venue"""
        venue = Venue(
            venue_id=row["venue_id"],
            canonical_name=row["canonical_name"],
            full_name=row["full_name"],
            domain=row["domain"],
            venue_type=row["venue_type"],
            first_year=row["first_year"],
            last_year=row["last_year"],
        )
        # 添加新字段
        venue.tier = row.get("tier", "C")
        venue.openreview_ids = json.loads(row.get("openreview_ids") or "[]")
        venue.years_available = json.loads(row.get("years_available") or "[]")
        return venue
    
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
    
    def save_paper_keyword(self, pk: PaperKeyword):
        """保存单个 PaperKeyword 对象"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO paper_keywords (paper_id, keyword, method, score)
                VALUES (?, ?, ?, ?)
            """, (pk.paper_id, pk.keyword.lower().strip(), pk.method, pk.score))
            conn.commit()
    
    def get_papers_without_keywords(
        self,
        method: str = "yake",
        limit: int = 1000,
    ) -> List[Paper]:
        """
        获取没有提取关键词的论文（增量处理）
        
        Args:
            method: 提取方法
            limit: 最大数量
            
        Returns:
            需要处理的论文列表
        """
        import json
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT p.*
                FROM papers p
                LEFT JOIN paper_keywords pk ON p.paper_id = pk.paper_id AND pk.method = ?
                WHERE pk.id IS NULL
                  AND p.canonical_title IS NOT NULL
                  AND p.canonical_title != ''
                LIMIT ?
            """, (method, limit))
            
            papers = []
            for row in cursor.fetchall():
                authors = row["authors"]
                if isinstance(authors, str):
                    authors = json.loads(authors) if authors else []
                
                papers.append(Paper(
                    paper_id=row["paper_id"],
                    canonical_title=row["canonical_title"],
                    abstract=row["abstract"] or "",
                    authors=authors,
                    year=row["year"],
                    venue_id=row["venue_id"],
                    venue_type=row["venue_type"],
                    domain=row["domain"],
                    quality_flag=row["quality_flag"],
                ))
            
            return papers
    
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
    
    # ========== Analysis Meta 操作 ==========
    
    def get_meta(self, key: str) -> Optional[str]:
        """获取分析元信息"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM analysis_meta WHERE key = ?", (key,))
            row = cursor.fetchone()
            return row["value"] if row else None
    
    def set_meta(self, key: str, value: str):
        """设置分析元信息"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO analysis_meta (key, value, updated_at)
                VALUES (?, ?, ?)
            """, (key, value, datetime.now().isoformat()))
            conn.commit()
    
    def get_all_meta(self) -> Dict[str, str]:
        """获取所有元信息"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT key, value FROM analysis_meta")
            return {row["key"]: row["value"] for row in cursor.fetchall()}
    
    # ========== Analysis Venue Summary 操作 ==========
    
    def save_venue_summary(
        self,
        venue: str,
        year: Optional[int],
        paper_count: int,
        top_keywords: List[Dict],
        emerging_keywords: List[str] = None
    ):
        """保存会议总览缓存"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            year_val = year if year else 0  # 0 表示全量汇总
            cursor.execute("""
                INSERT OR REPLACE INTO analysis_venue_summary 
                (venue, year, paper_count, top_keywords_json, emerging_keywords_json, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                venue,
                year_val,
                paper_count,
                json.dumps(top_keywords, ensure_ascii=False),
                json.dumps(emerging_keywords or [], ensure_ascii=False),
                datetime.now().isoformat()
            ))
            conn.commit()
    
    def get_venue_summary(self, venue: str, year: int = None) -> Optional[Dict]:
        """获取会议总览缓存"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            year_val = year if year else 0
            cursor.execute(
                "SELECT * FROM analysis_venue_summary WHERE venue = ? AND year = ?",
                (venue, year_val)
            )
            row = cursor.fetchone()
            if not row:
                return None
            return {
                "venue": row["venue"],
                "year": row["year"],
                "paper_count": row["paper_count"],
                "top_keywords": json.loads(row["top_keywords_json"]) if row["top_keywords_json"] else [],
                "emerging_keywords": json.loads(row["emerging_keywords_json"]) if row["emerging_keywords_json"] else [],
                "updated_at": row["updated_at"]
            }
    
    def get_all_venue_summaries(self) -> List[Dict]:
        """获取所有会议总览"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM analysis_venue_summary ORDER BY venue, year")
            results = []
            for row in cursor.fetchall():
                year_val = row["year"]
                results.append({
                    "venue": row["venue"],
                    "year": year_val if year_val != 0 else None,  # 0 -> None for 'all years'
                    "paper_count": row["paper_count"],
                    "top_keywords": json.loads(row["top_keywords_json"]) if row["top_keywords_json"] else [],
                    "emerging_keywords": json.loads(row["emerging_keywords_json"]) if row["emerging_keywords_json"] else [],
                    "updated_at": row["updated_at"]
                })
            return results
    
    # ========== Analysis Keyword Trends 操作 ==========
    
    def save_keyword_trend_bucket(
        self,
        scope: str,
        venue: Optional[str],
        keyword: str,
        granularity: str,
        bucket: str,
        count: int
    ):
        """保存关键词趋势数据点"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO analysis_keyword_trends 
                (scope, venue, keyword, granularity, bucket, count, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                scope,
                venue or '',  # 空字符串代替 NULL
                keyword.lower(),
                granularity,
                bucket,
                count,
                datetime.now().isoformat()
            ))
            conn.commit()
    
    def save_keyword_trends_batch(self, trends: List[Dict]):
        """批量保存关键词趋势"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            for t in trends:
                cursor.execute("""
                    INSERT OR REPLACE INTO analysis_keyword_trends 
                    (scope, venue, keyword, granularity, bucket, count, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    t["scope"],
                    t.get("venue") or '',  # 空字符串代替 NULL
                    t["keyword"].lower(),
                    t["granularity"],
                    t["bucket"],
                    t["count"],
                    datetime.now().isoformat()
                ))
            conn.commit()
    
    def get_keyword_trends_cached(
        self,
        scope: str,
        keyword: str,
        granularity: str,
        venue: str = None
    ) -> List[Dict]:
        """获取缓存的关键词趋势"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            venue_val = venue or ''
            cursor.execute("""
                SELECT bucket, count FROM analysis_keyword_trends 
                WHERE scope = ? AND keyword = ? AND granularity = ? AND venue = ?
                ORDER BY bucket
            """, (scope, keyword.lower(), granularity, venue_val))
            return [{"bucket": row["bucket"], "count": row["count"]} for row in cursor.fetchall()]
    
    # ========== Analysis arXiv Timeseries 操作 ==========
    
    def save_arxiv_timeseries(
        self,
        category: str,
        granularity: str,
        bucket: str,
        paper_count: int,
        top_keywords: List[Dict] = None
    ):
        """保存 arXiv 时间序列数据"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO analysis_arxiv_timeseries 
                (category, granularity, bucket, paper_count, top_keywords_json, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                category,
                granularity,
                bucket,
                paper_count,
                json.dumps(top_keywords or [], ensure_ascii=False),
                datetime.now().isoformat()
            ))
            conn.commit()
    
    def save_arxiv_timeseries_batch(self, data: List[Dict]):
        """批量保存 arXiv 时间序列"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            for d in data:
                cursor.execute("""
                    INSERT OR REPLACE INTO analysis_arxiv_timeseries 
                    (category, granularity, bucket, paper_count, top_keywords_json, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    d["category"],
                    d["granularity"],
                    d["bucket"],
                    d["paper_count"],
                    json.dumps(d.get("top_keywords", []), ensure_ascii=False),
                    datetime.now().isoformat()
                ))
            conn.commit()
    
    def get_arxiv_timeseries(
        self,
        category: str,
        granularity: str
    ) -> List[Dict]:
        """获取 arXiv 时间序列"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT bucket, paper_count, top_keywords_json FROM analysis_arxiv_timeseries 
                WHERE category = ? AND granularity = ?
                ORDER BY bucket
            """, (category, granularity))
            return [
                {
                    "bucket": row["bucket"],
                    "paper_count": row["paper_count"],
                    "top_keywords": json.loads(row["top_keywords_json"]) if row["top_keywords_json"] else []
                }
                for row in cursor.fetchall()
            ]
    
    # ========== 辅助查询 ==========
    
    def get_max_retrieved_at(self) -> Optional[str]:
        """获取 raw_papers 中最大的 retrieved_at"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT MAX(retrieved_at) as max_retrieved FROM raw_papers")
            row = cursor.fetchone()
            return row["max_retrieved"] if row else None
    
    def get_total_paper_count(self) -> int:
        """获取论文总数"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM papers")
            return cursor.fetchone()["count"]

    # ========== Analysis arXiv Emerging 操作 ==========

    def save_emerging_topic(
        self,
        category: str,
        keyword: str,
        growth_rate: float,
        first_seen: str,
        recent_count: int,
        trend: str
    ):
        """保存新兴主题"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO analysis_arxiv_emerging
                (category, keyword, growth_rate, first_seen, recent_count, trend, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                category,
                keyword.lower(),
                growth_rate,
                first_seen,
                recent_count,
                trend,
                datetime.now().isoformat()
            ))
            conn.commit()

    def save_emerging_topics_batch(self, topics: List[Dict]):
        """批量保存新兴主题"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            for t in topics:
                cursor.execute("""
                    INSERT OR REPLACE INTO analysis_arxiv_emerging
                    (category, keyword, growth_rate, first_seen, recent_count, trend, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    t["category"],
                    t["keyword"].lower(),
                    t["growth_rate"],
                    t["first_seen"],
                    t["recent_count"],
                    t["trend"],
                    datetime.now().isoformat()
                ))
            conn.commit()

    def get_emerging_topics(
        self,
        category: str = "ALL",
        limit: int = 20,
        min_growth_rate: float = 1.5
    ) -> List[Dict]:
        """获取新兴主题"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM analysis_arxiv_emerging
                WHERE category = ? AND growth_rate >= ?
                ORDER BY growth_rate DESC
                LIMIT ?
            """, (category, min_growth_rate, limit))
            return [
                {
                    "category": row["category"],
                    "keyword": row["keyword"],
                    "growth_rate": row["growth_rate"],
                    "first_seen": row["first_seen"],
                    "recent_count": row["recent_count"],
                    "trend": row["trend"],
                    "updated_at": row["updated_at"]
                }
                for row in cursor.fetchall()
            ]


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
