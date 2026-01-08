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

GranularityType = Literal["year", "month", "week", "day"]


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
        elif granularity == "month":
            buckets = self._group_by_month(papers)
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
        for granularity in ["year", "month", "week", "day"]:
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
                "published_at": getattr(paper, 'published_at', None),
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
    
    def _group_by_month(self, papers: List[Dict]) -> Dict[str, List[Dict]]:
        """按月份分组 (YYYY-MM)，优先使用 published_at"""
        buckets = defaultdict(list)
        missing_published_count = 0
        
        for paper in papers:
            # 优先使用 published_at
            date_field = paper.get("published_at")
            if not date_field:
                # 降级为 retrieved_at
                date_field = paper.get("retrieved_at")
                missing_published_count += 1
            
            if isinstance(date_field, str):
                try:
                    date_field = datetime.fromisoformat(date_field)
                except:
                    continue
            
            if date_field:
                bucket_key = date_field.strftime("%Y-%m")
                buckets[bucket_key].append(paper)
        
        if missing_published_count > 0:
            logger.warning(
                f"{missing_published_count}/{len(papers)} papers missing published_at, "
                f"used retrieved_at as fallback"
            )
        
        return dict(buckets)
    
    def _group_by_week(self, papers: List[Dict]) -> Dict[str, List[Dict]]:
        """按 ISO 周分组 (YYYY-Www)，优先使用 published_at"""
        buckets = defaultdict(list)
        missing_published_count = 0
        
        for paper in papers:
            # 优先使用 published_at
            date_field = paper.get("published_at")
            if not date_field:
                # 降级为 retrieved_at
                date_field = paper.get("retrieved_at")
                missing_published_count += 1
            
            if isinstance(date_field, str):
                try:
                    date_field = datetime.fromisoformat(date_field)
                except:
                    continue
            
            if date_field:
                # ISO week format: 2024-W05
                iso_cal = date_field.isocalendar()
                bucket_key = f"{iso_cal.year}-W{iso_cal.week:02d}"
                buckets[bucket_key].append(paper)
        
        if missing_published_count > 0:
            logger.warning(
                f"{missing_published_count}/{len(papers)} papers missing published_at, "
                f"used retrieved_at as fallback"
            )
        
        return dict(buckets)
    
    def _group_by_day(self, papers: List[Dict]) -> Dict[str, List[Dict]]:
        """按日期分组 (YYYY-MM-DD)，优先使用 published_at"""
        buckets = defaultdict(list)
        missing_published_count = 0
        
        for paper in papers:
            # 优先使用 published_at
            date_field = paper.get("published_at")
            if not date_field:
                # 降级为 retrieved_at
                date_field = paper.get("retrieved_at")
                missing_published_count += 1
            
            if isinstance(date_field, str):
                try:
                    date_field = datetime.fromisoformat(date_field)
                except:
                    continue
            
            if date_field:
                bucket_key = date_field.strftime("%Y-%m-%d")
                buckets[bucket_key].append(paper)
        
        if missing_published_count > 0:
            logger.warning(
                f"{missing_published_count}/{len(papers)} papers missing published_at, "
                f"used retrieved_at as fallback"
            )
        
        return dict(buckets)
    
    def _extract_bucket_keywords(
        self,
        papers: List[Dict],
        limit: int = 10
    ) -> List[Dict]:
        """
        增强版关键词提取

        三级策略：
        1. 优先使用 paper_keywords 表中已提取的关键词（最优）
        2. 使用 YAKE 从 title + abstract 提取（次优）
        3. 使用词频统计（兜底）
        """
        # 策略1：尝试从 paper_keywords 表获取
        keywords_from_db = self._get_keywords_from_db(papers)
        if keywords_from_db:
            return keywords_from_db[:limit]

        # 策略2：尝试使用 YAKE 提取
        keywords_from_yake = self._extract_with_yake(papers, limit)
        if keywords_from_yake:
            return keywords_from_yake

        # 策略3：使用词频统计（兜底）
        return self._extract_with_frequency(papers, limit)

    def _get_keywords_from_db(self, papers: List[Dict]) -> List[Dict]:
        """从 paper_keywords 表获取关键词"""
        try:
            from database.repository import get_structured_repository, get_analysis_repository

            structured_repo = get_structured_repository()
            analysis_repo = get_analysis_repository()

            # 获取这些论文对应的 paper_id
            keyword_counts = defaultdict(int)

            for paper in papers:
                title = paper.get("title", "")
                if not title:
                    continue

                # 尝试通过标题查找 paper_id
                paper_id = structured_repo.find_paper_by_title(title)
                if paper_id:
                    # 获取该论文的关键词
                    keywords = analysis_repo.get_paper_keywords(paper_id)
                    for kw in keywords:
                        if self._is_valid_keyword(kw.keyword):
                            keyword_counts[kw.keyword] += 1

            if keyword_counts:
                # 返回 top keywords
                top = sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True)
                return [{"keyword": kw, "count": count} for kw, count in top]

            return []
        except Exception as e:
            logger.debug(f"Failed to get keywords from DB: {e}")
            return []

    def _extract_with_yake(self, papers: List[Dict], limit: int) -> List[Dict]:
        """使用 YAKE 提取关键词"""
        try:
            import yake

            # 合并所有论文的标题和摘要
            texts = []
            for paper in papers:
                title = paper.get("title", "")
                abstract = paper.get("abstract", "")
                if title or abstract:
                    texts.append(f"{title}. {abstract}")

            if not texts:
                return []

            combined_text = " ".join(texts)

            # 使用 YAKE 提取关键词
            kw_extractor = yake.KeywordExtractor(
                lan="en",
                n=3,  # n-gram size
                dedupLim=0.9,
                top=limit * 2,  # 提取更多，然后过滤
                features=None
            )

            keywords = kw_extractor.extract_keywords(combined_text)

            # 过滤和统计
            keyword_counts = defaultdict(int)
            for kw, score in keywords:
                if self._is_valid_keyword(kw):
                    # YAKE 的 score 越小越好，转换为 count
                    keyword_counts[kw] += 1

            if keyword_counts:
                top = sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True)[:limit]
                return [{"keyword": kw, "count": count} for kw, count in top]

            return []
        except Exception as e:
            logger.debug(f"Failed to extract with YAKE: {e}")
            return []

    def _extract_with_frequency(self, papers: List[Dict], limit: int) -> List[Dict]:
        """使用词频统计提取关键词（兜底方案）"""
        from collections import Counter
        import re

        # 扩展的停用词列表
        stopwords = {
            # 基础停用词
            'a', 'an', 'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'is', 'are', 'was', 'were', 'be', 'been',
            'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
            'could', 'should', 'may', 'must', 'can', 'this', 'that',
            'these', 'those', 'it', 'its', 'as', 'we', 'our', 'their', 'your',

            # 学术常用词
            'paper', 'study', 'analysis', 'approach', 'method', 'methods',
            'model', 'models', 'learning', 'network', 'networks', 'neural',
            'deep', 'data', 'using', 'via', 'based', 'novel', 'new', 'towards',
            'propose', 'proposed', 'present', 'show', 'demonstrate', 'introduce',
            'framework', 'system', 'algorithm', 'technique', 'techniques',
        }

        word_counts = Counter()

        for paper in papers:
            title = paper.get("title", "")
            # 提取词语（3个字符以上）
            words = re.findall(r'\b[a-zA-Z]{3,}\b', title.lower())
            for word in words:
                if self._is_valid_keyword(word) and word not in stopwords:
                    word_counts[word] += 1

        # 返回 top keywords
        top = word_counts.most_common(limit)
        return [{"keyword": kw, "count": count} for kw, count in top]

    def _is_valid_keyword(self, keyword: str) -> bool:
        """
        验证关键词是否有效

        过滤规则：
        - 过滤纯数字
        - 过滤单字符和双字符
        - 过滤特殊字符
        """
        import re

        if not keyword:
            return False

        keyword = keyword.strip().lower()

        # 过滤纯数字
        if re.match(r'^\d+$', keyword):
            return False

        # 过滤太短的词
        if len(keyword) <= 2:
            return False

        # 过滤包含特殊字符的词（允许字母、空格、连字符）
        if not re.match(r'^[a-z][a-z\s-]*$', keyword):
            return False

        return True

    def detect_emerging_topics(
        self,
        category: str = "ALL",
        threshold: float = 1.5,
        recent_window: int = 4
    ) -> List[Dict]:
        """
        识别新兴研究主题

        算法：
        1. 计算关键词的环比增长率（最近 N 个时间窗口 vs 之前 N 个时间窗口）
        2. 识别突然出现的新关键词
        3. 标记趋势（rising/stable/declining）

        Args:
            category: arXiv 分类
            threshold: 增长率阈值（默认 1.5 = 50% 增长）
            recent_window: 最近时间窗口数量（默认 4 周）

        Returns:
            新兴主题列表
        """
        logger.info(f"Detecting emerging topics for category={category}")

        # 获取周粒度的时间序列数据
        timeseries = self.analysis_repo.get_arxiv_timeseries(category, "week")

        if len(timeseries) < recent_window * 2:
            logger.warning(f"Not enough data for emerging topic detection (need {recent_window * 2} weeks)")
            return []

        # 按时间排序
        timeseries = sorted(timeseries, key=lambda x: x["bucket"])

        # 收集所有关键词及其时间序列
        keyword_timeseries = defaultdict(list)
        for ts in timeseries:
            bucket = ts["bucket"]
            for kw_data in ts.get("top_keywords", []):
                keyword = kw_data.get("keyword")
                count = kw_data.get("count", 0)
                if keyword:
                    keyword_timeseries[keyword].append((bucket, count))

        # 分析每个关键词的趋势
        emerging_topics = []

        for keyword, data_points in keyword_timeseries.items():
            if len(data_points) < recent_window:
                continue

            # 按时间排序
            data_points = sorted(data_points, key=lambda x: x[0])

            # 计算最近窗口和历史窗口的平均值
            recent_counts = [count for _, count in data_points[-recent_window:]]
            recent_avg = sum(recent_counts) / len(recent_counts)

            if len(data_points) >= recent_window * 2:
                historical_counts = [count for _, count in data_points[-recent_window*2:-recent_window]]
                historical_avg = sum(historical_counts) / len(historical_counts) if historical_counts else 0.1
            else:
                historical_avg = 0.1  # 避免除零

            # 计算增长率
            if historical_avg > 0:
                growth_rate = recent_avg / historical_avg
            else:
                growth_rate = recent_avg * 10  # 新出现的关键词

            # 判断趋势
            if growth_rate >= threshold:
                trend = "rising"
            elif growth_rate <= 0.7:
                trend = "declining"
            else:
                trend = "stable"

            # 只保留上升趋势的关键词
            if trend == "rising" and growth_rate >= threshold:
                first_seen = data_points[0][0]
                recent_count = int(recent_avg)

                emerging_topics.append({
                    "category": category,
                    "keyword": keyword,
                    "growth_rate": round(growth_rate, 2),
                    "first_seen": first_seen,
                    "recent_count": recent_count,
                    "trend": trend
                })

        # 按增长率排序
        emerging_topics = sorted(emerging_topics, key=lambda x: x["growth_rate"], reverse=True)

        # 保存到数据库
        if emerging_topics:
            self.analysis_repo.save_emerging_topics_batch(emerging_topics)
            logger.info(f"Detected {len(emerging_topics)} emerging topics")

        return emerging_topics

    def compare_categories(
        self,
        categories: List[str],
        granularity: str = "year"
    ) -> Dict:
        """
        对比多个分类的趋势

        Args:
            categories: 分类列表（如 ["cs.LG", "cs.CV"]）
            granularity: 时间粒度

        Returns:
            对比结果，包含时间序列、重叠关键词、独特关键词
        """
        logger.info(f"Comparing categories: {categories}")

        result = {
            "categories": categories,
            "timeseries": {},
            "overlap": {
                "keywords": [],
                "overlap_rate": 0.0
            },
            "unique": {}
        }

        # 获取每个分类的时间序列
        all_keywords = defaultdict(set)

        for category in categories:
            timeseries = self.analysis_repo.get_arxiv_timeseries(category, granularity)
            result["timeseries"][category] = timeseries

            # 收集该分类的所有关键词
            for ts in timeseries:
                for kw_data in ts.get("top_keywords", []):
                    keyword = kw_data.get("keyword")
                    if keyword:
                        all_keywords[category].add(keyword)

        # 计算重叠关键词
        if len(categories) >= 2:
            overlap_keywords = set.intersection(*[all_keywords[cat] for cat in categories])
            result["overlap"]["keywords"] = sorted(list(overlap_keywords))

            # 计算重叠率
            total_unique = len(set.union(*[all_keywords[cat] for cat in categories]))
            if total_unique > 0:
                result["overlap"]["overlap_rate"] = round(len(overlap_keywords) / total_unique, 2)

        # 计算每个分类的独特关键词
        for category in categories:
            other_keywords = set.union(*[all_keywords[cat] for cat in categories if cat != category])
            unique_keywords = all_keywords[category] - other_keywords
            result["unique"][category] = sorted(list(unique_keywords))[:10]  # 只保留前 10 个

        logger.info(f"Comparison completed: {len(result['overlap']['keywords'])} overlapping keywords")

        return result


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
