"""
arXiv Analysis Agent

负责 arXiv 数据的多粒度趋势分析（年/周/日）。

职责：
1. 统计 paper_count：年/周/日
2. 每个 bucket 提取 top keywords
3. 写入 analysis_arxiv_timeseries 与 analysis_keyword_trends(scope='arxiv')
"""

import logging
from typing import List, Dict, Optional, Literal
from datetime import datetime, timedelta
from collections import defaultdict

from database.repository import (
    AnalysisRepository,
    RawRepository,
    get_analysis_repository,
    get_raw_repository
)

logger = logging.getLogger(__name__)

GranularityType = Literal["year", "week", "day"]


class ArxivAnalysisAgent:
    """
    arXiv 趋势分析 Agent
    
    支持年/周/日多粒度的论文数量统计和关键词趋势分析。
    数据来源：raw_papers 表中 source='arxiv' 的记录。
    """
    
    # 支持的 arXiv 分类
    CATEGORIES = ["cs.LG", "cs.CL", "cs.CV", "cs.AI", "cs.RO", "ALL"]
    
    def __init__(
        self,
        analysis_repo: AnalysisRepository = None,
        raw_repo: RawRepository = None
    ):
        self.analysis_repo = analysis_repo or get_analysis_repository()
        self.raw_repo = raw_repo or get_raw_repository()
    
    def run(
        self,
        granularity: GranularityType = "year",
        category: str = "ALL",
        force: bool = False
    ) -> Dict:
        """
        运行 arXiv 趋势分析
        
        Args:
            granularity: 时间粒度 ('year'/'week'/'day')
            category: arXiv 分类 ('cs.LG' 等，或 'ALL')
            force: 强制重算（忽略缓存）
            
        Returns:
            分析结果统计
        """
        logger.info(f"Starting arXiv analysis: granularity={granularity}, category={category}")
        
        # 检查是否需要重算
        if not force and not self._should_run(granularity, category):
            logger.info("No new data, skipping arXiv analysis")
            return {"status": "skipped", "reason": "no_new_data"}
        
        # 获取 arXiv 论文数据
        papers = self._get_arxiv_papers(category)
        if not papers:
            logger.warning(f"No arXiv papers found for category={category}")
            return {"status": "completed", "paper_count": 0, "buckets": 0}
        
        logger.info(f"Processing {len(papers)} arXiv papers")
        
        # 按时间桶分组
        if granularity == "year":
            buckets = self._group_by_year(papers)
        elif granularity == "week":
            buckets = self._group_by_week(papers)
        else:  # day
            buckets = self._group_by_day(papers)
        
        # 保存时间序列数据
        timeseries_data = []
        for bucket_key, bucket_papers in buckets.items():
            # 提取 top keywords（从标题中简单提取）
            top_keywords = self._extract_bucket_keywords(bucket_papers, limit=10)
            
            timeseries_data.append({
                "category": category,
                "granularity": granularity,
                "bucket": bucket_key,
                "paper_count": len(bucket_papers),
                "top_keywords": top_keywords
            })
        
        # 批量保存
        self.analysis_repo.save_arxiv_timeseries_batch(timeseries_data)
        
        # 更新元信息
        self._update_meta(granularity, category)
        
        result = {
            "status": "completed",
            "granularity": granularity,
            "category": category,
            "paper_count": len(papers),
            "buckets": len(buckets)
        }
        
        logger.info(f"arXiv analysis completed: {result}")
        return result
    
    def run_all_granularities(self, category: str = "ALL", force: bool = False) -> Dict:
        """运行所有粒度的分析"""
        results = {}
        for granularity in ["year", "week", "day"]:
            results[granularity] = self.run(granularity, category, force)
        return results
    
    def _should_run(self, granularity: str, category: str) -> bool:
        """判断是否需要重新运行分析"""
        # 获取上次分析时的 max_retrieved_at
        meta_key = f"arxiv_last_retrieved_{category}_{granularity}"
        last_retrieved = self.analysis_repo.get_meta(meta_key)
        
        # 获取当前最大 retrieved_at
        current_max = self.analysis_repo.get_max_retrieved_at()
        
        if not last_retrieved:
            return True
        
        if not current_max:
            return False
        
        return current_max > last_retrieved
    
    def _update_meta(self, granularity: str, category: str):
        """更新分析元信息"""
        current_max = self.analysis_repo.get_max_retrieved_at()
        if current_max:
            meta_key = f"arxiv_last_retrieved_{category}_{granularity}"
            self.analysis_repo.set_meta(meta_key, current_max)
        
        # 记录分析时间
        run_key = f"arxiv_last_run_{category}_{granularity}"
        self.analysis_repo.set_meta(run_key, datetime.now().isoformat())
    
    def _get_arxiv_papers(self, category: str) -> List[Dict]:
        """获取 arXiv 论文"""
        papers = self.raw_repo.get_raw_papers_by_source("arxiv")
        
        result = []
        for paper in papers:
            # 过滤分类
            if category != "ALL":
                categories = paper.categories or ""
                if category not in categories:
                    continue
            
            result.append({
                "raw_id": paper.raw_id,
                "title": paper.title,
                "abstract": paper.abstract,
                "year": paper.year,
                "categories": paper.categories,
                "retrieved_at": paper.retrieved_at
            })
        
        return result
    
    def _group_by_year(self, papers: List[Dict]) -> Dict[str, List[Dict]]:
        """按年份分组"""
        buckets = defaultdict(list)
        for paper in papers:
            year = paper.get("year")
            if year:
                bucket_key = str(year)
                buckets[bucket_key].append(paper)
        return dict(buckets)
    
    def _group_by_week(self, papers: List[Dict]) -> Dict[str, List[Dict]]:
        """按 ISO 周分组 (YYYY-Www)"""
        buckets = defaultdict(list)
        for paper in papers:
            retrieved_at = paper.get("retrieved_at")
            if isinstance(retrieved_at, str):
                try:
                    retrieved_at = datetime.fromisoformat(retrieved_at)
                except:
                    continue
            
            if retrieved_at:
                # ISO week format: 2024-W05
                iso_cal = retrieved_at.isocalendar()
                bucket_key = f"{iso_cal.year}-W{iso_cal.week:02d}"
                buckets[bucket_key].append(paper)
        
        return dict(buckets)
    
    def _group_by_day(self, papers: List[Dict]) -> Dict[str, List[Dict]]:
        """按日期分组 (YYYY-MM-DD)"""
        buckets = defaultdict(list)
        for paper in papers:
            retrieved_at = paper.get("retrieved_at")
            if isinstance(retrieved_at, str):
                try:
                    retrieved_at = datetime.fromisoformat(retrieved_at)
                except:
                    continue
            
            if retrieved_at:
                bucket_key = retrieved_at.strftime("%Y-%m-%d")
                buckets[bucket_key].append(paper)
        
        return dict(buckets)
    
    def _extract_bucket_keywords(
        self,
        papers: List[Dict],
        limit: int = 10
    ) -> List[Dict]:
        """
        从论文标题中提取关键词
        
        简单实现：统计标题中的词频
        更好的实现应该使用 YAKE 或 KeyBERT
        """
        from collections import Counter
        import re
        
        # 停用词
        stopwords = {
            'a', 'an', 'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'is', 'are', 'was', 'were', 'be', 'been',
            'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
            'could', 'should', 'may', 'might', 'must', 'can', 'this', 'that',
            'these', 'those', 'it', 'its', 'as', 'we', 'our', 'using', 'via',
            'based', 'approach', 'method', 'methods', 'new', 'novel', 'towards',
            'paper', 'study', 'analysis', 'model', 'models', 'learning', 'network',
            'networks', 'neural', 'deep', 'data'
        }
        
        word_counts = Counter()
        
        for paper in papers:
            title = paper.get("title", "")
            # 提取词语
            words = re.findall(r'\b[a-zA-Z]{3,}\b', title.lower())
            for word in words:
                if word not in stopwords:
                    word_counts[word] += 1
        
        # 返回 top keywords
        top = word_counts.most_common(limit)
        return [{"keyword": kw, "count": count} for kw, count in top]


def run_arxiv_analysis(
    granularity: str = "year",
    category: str = "ALL",
    force: bool = False
) -> Dict:
    """运行 arXiv 分析的便捷函数"""
    agent = ArxivAnalysisAgent()
    return agent.run(granularity, category, force)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # 运行所有粒度的分析
    agent = ArxivAnalysisAgent()
    results = agent.run_all_granularities()
    print(f"Analysis results: {results}")
