"""
数据库操作仓库

提供论文和关键词的 CRUD 操作。
"""

import sqlite3
import json
from pathlib import Path
from typing import List, Optional, Tuple, Dict
from contextlib import contextmanager
from datetime import datetime

from scraper.models import Paper
from config import DATABASE_PATH


class DatabaseRepository:
    """数据库操作仓库"""
    
    def __init__(self, db_path: Path = None):
        """
        初始化仓库
        
        Args:
            db_path: 数据库文件路径
        """
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
    
    # ==================== 论文操作 ====================
    
    def save_paper(self, paper: Paper) -> bool:
        """
        保存论文
        
        Args:
            paper: 论文对象
            
        Returns:
            是否成功
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # 插入或更新论文
            cursor.execute("""
                INSERT OR REPLACE INTO papers 
                (id, title, abstract, venue, year, url, pdf_url, authors, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                paper.id,
                paper.title,
                paper.abstract,
                paper.venue,
                paper.year,
                paper.url,
                paper.pdf_url,
                json.dumps(paper.authors),
                datetime.now().isoformat(),
            ))
            
            # 保存作者提交的关键词
            for kw in paper.keywords:
                self._save_keyword_association(cursor, paper.id, kw, "author")
            
            # 保存提取的关键词
            for kw in paper.extracted_keywords:
                self._save_keyword_association(cursor, paper.id, kw, "extracted")
            
            conn.commit()
            return True
    
    def _save_keyword_association(
        self, 
        cursor: sqlite3.Cursor, 
        paper_id: str, 
        keyword: str, 
        source: str,
        score: float = 1.0,
    ):
        """保存论文-关键词关联"""
        # 确保关键词存在
        cursor.execute(
            "INSERT OR IGNORE INTO keywords (keyword) VALUES (?)",
            (keyword.lower().strip(),)
        )
        
        # 获取关键词 ID
        cursor.execute(
            "SELECT id FROM keywords WHERE keyword = ?",
            (keyword.lower().strip(),)
        )
        row = cursor.fetchone()
        if row:
            keyword_id = row["id"]
            
            # 插入关联
            cursor.execute("""
                INSERT OR REPLACE INTO paper_keywords (paper_id, keyword_id, source, score)
                VALUES (?, ?, ?, ?)
            """, (paper_id, keyword_id, source, score))
    
    def save_papers(self, papers: List[Paper]) -> int:
        """
        批量保存论文
        
        Args:
            papers: 论文列表
            
        Returns:
            成功保存的数量
        """
        count = 0
        for paper in papers:
            if self.save_paper(paper):
                count += 1
        return count
    
    def get_paper(self, paper_id: str) -> Optional[Paper]:
        """获取单篇论文"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM papers WHERE id = ?", (paper_id,))
            row = cursor.fetchone()
            
            if row:
                return self._row_to_paper(conn, row)
            return None
    
    def _row_to_paper(self, conn: sqlite3.Connection, row: sqlite3.Row) -> Paper:
        """将数据库行转换为 Paper 对象"""
        cursor = conn.cursor()
        
        # 获取作者关键词
        cursor.execute("""
            SELECT k.keyword FROM paper_keywords pk
            JOIN keywords k ON pk.keyword_id = k.id
            WHERE pk.paper_id = ? AND pk.source = 'author'
        """, (row["id"],))
        author_keywords = [r["keyword"] for r in cursor.fetchall()]
        
        # 获取提取的关键词
        cursor.execute("""
            SELECT k.keyword FROM paper_keywords pk
            JOIN keywords k ON pk.keyword_id = k.id
            WHERE pk.paper_id = ? AND pk.source = 'extracted'
        """, (row["id"],))
        extracted_keywords = [r["keyword"] for r in cursor.fetchall()]
        
        return Paper(
            id=row["id"],
            title=row["title"],
            abstract=row["abstract"] or "",
            authors=json.loads(row["authors"]) if row["authors"] else [],
            venue=row["venue"],
            year=row["year"],
            url=row["url"] or "",
            keywords=author_keywords,
            extracted_keywords=extracted_keywords,
            pdf_url=row["pdf_url"],
        )
    
    def get_papers_by_venue_year(self, venue: str, year: int) -> List[Paper]:
        """获取指定会议和年份的论文"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM papers WHERE venue = ? AND year = ?",
                (venue, year)
            )
            return [self._row_to_paper(conn, row) for row in cursor.fetchall()]
    
    def get_paper_count(self, venue: str = None, year: int = None) -> int:
        """获取论文数量"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT COUNT(*) as count FROM papers WHERE 1=1"
            params = []
            
            if venue:
                query += " AND venue = ?"
                params.append(venue)
            if year:
                query += " AND year = ?"
                params.append(year)
            
            cursor.execute(query, params)
            return cursor.fetchone()["count"]
    
    # ==================== 关键词统计 ====================
    
    def get_top_keywords(
        self,
        venue: str = None,
        year: int = None,
        source: str = None,
        limit: int = 50,
    ) -> List[Tuple[str, int]]:
        """
        获取 Top-K 关键词
        
        Args:
            venue: 会议名称（可选）
            year: 年份（可选）
            source: 来源（"author" 或 "extracted"，可选）
            limit: 返回数量
            
        Returns:
            关键词和计数的列表
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            query = """
                SELECT k.keyword, COUNT(*) as count
                FROM paper_keywords pk
                JOIN keywords k ON pk.keyword_id = k.id
                JOIN papers p ON pk.paper_id = p.id
                WHERE 1=1
            """
            params = []
            
            if venue:
                query += " AND p.venue = ?"
                params.append(venue)
            if year:
                query += " AND p.year = ?"
                params.append(year)
            if source:
                query += " AND pk.source = ?"
                params.append(source)
            
            query += " GROUP BY k.keyword ORDER BY count DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            return [(row["keyword"], row["count"]) for row in cursor.fetchall()]
    
    def get_keyword_trend(
        self,
        keyword: str,
        venue: str = None,
    ) -> Dict[int, int]:
        """
        获取关键词的年度趋势
        
        Args:
            keyword: 关键词
            venue: 会议名称（可选）
            
        Returns:
            年份到数量的映射
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            query = """
                SELECT p.year, COUNT(*) as count
                FROM paper_keywords pk
                JOIN keywords k ON pk.keyword_id = k.id
                JOIN papers p ON pk.paper_id = p.id
                WHERE k.keyword = ?
            """
            params = [keyword.lower()]
            
            if venue:
                query += " AND p.venue = ?"
                params.append(venue)
            
            query += " GROUP BY p.year ORDER BY p.year"
            
            cursor.execute(query, params)
            return {row["year"]: row["count"] for row in cursor.fetchall()}
    
    def get_venue_comparison(
        self,
        year: int,
        limit: int = 10,
    ) -> Dict[str, List[Tuple[str, int]]]:
        """
        获取各会议的关键词对比
        
        Args:
            year: 年份
            limit: 每个会议的 Top-K
            
        Returns:
            会议名称到关键词列表的映射
        """
        result = {}
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # 获取所有会议
            cursor.execute(
                "SELECT DISTINCT venue FROM papers WHERE year = ?",
                (year,)
            )
            venues = [row["venue"] for row in cursor.fetchall()]
            
            for venue in venues:
                result[venue] = self.get_top_keywords(venue=venue, year=year, limit=limit)
        
        return result
    
    def get_all_venues(self) -> List[str]:
        """获取所有会议名称"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT venue FROM papers ORDER BY venue")
            return [row["venue"] for row in cursor.fetchall()]
    
    def get_all_years(self, venue: str = None) -> List[int]:
        """获取所有年份"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT DISTINCT year FROM papers"
            params = []
            
            if venue:
                query += " WHERE venue = ?"
                params.append(venue)
            
            query += " ORDER BY year DESC"
            cursor.execute(query, params)
            return [row["year"] for row in cursor.fetchall()]
    
    # ==================== 爬取日志 ====================
    
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


# 单例仓库
_repository: Optional[DatabaseRepository] = None


def get_repository(db_path: Path = None) -> DatabaseRepository:
    """获取数据库仓库（单例）"""
    global _repository
    if _repository is None:
        _repository = DatabaseRepository(db_path)
    return _repository
