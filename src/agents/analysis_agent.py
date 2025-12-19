"""
Analysis Agent

负责从 Structured Layer 提取关键词到 Analysis Layer。

职责：
- 增量处理：仅处理未提取关键词的论文
- 关键词提取：YAKE（快速）+ KeyBERT（精准）
- 关键词规范化：统一格式、去重
- 保存到 paper_keywords 表
"""

import sys
import re
from pathlib import Path
from typing import List, Optional, Dict, Tuple, Literal
from datetime import datetime

# 确保 src 目录在路径中
_src_dir = Path(__file__).parent.parent
if str(_src_dir) not in sys.path:
    sys.path.insert(0, str(_src_dir))

from database import get_structured_repository, get_analysis_repository
from database.repository import StructuredRepository, AnalysisRepository
from scraper.models import Paper, PaperKeyword
from extractor.yake_extractor import YakeExtractor, create_yake_extractor
from extractor.keybert_extractor import KeyBertExtractor, get_keybert_extractor


ExtractorType = Literal["yake", "keybert", "both"]


class AnalysisAgent:
    """
    分析 Agent
    
    负责从 papers 表提取关键词到 paper_keywords 表。
    """
    
    def __init__(
        self,
        structured_repo: StructuredRepository = None,
        analysis_repo: AnalysisRepository = None,
        yake_extractor: YakeExtractor = None,
        keybert_extractor: KeyBertExtractor = None,
    ):
        self.structured_repo = structured_repo or get_structured_repository()
        self.analysis_repo = analysis_repo or get_analysis_repository()
        self._yake = yake_extractor
        self._keybert = keybert_extractor
    
    def _get_yake(self) -> YakeExtractor:
        """懒加载 YAKE 提取器"""
        if self._yake is None:
            self._yake = create_yake_extractor()
        return self._yake
    
    def _get_keybert(self) -> KeyBertExtractor:
        """懒加载 KeyBERT 提取器"""
        if self._keybert is None:
            self._keybert = get_keybert_extractor()
        return self._keybert
    
    # ========== Step 1: 增量选择 ==========
    
    def get_papers_without_keywords(
        self,
        method: str = "yake",
        limit: int = 1000,
    ) -> List[Paper]:
        """
        获取还没有提取关键词的论文（增量）
        
        Args:
            method: 提取方法（yake/keybert）
            limit: 最大数量
            
        Returns:
            需要处理的论文列表
        """
        return self.analysis_repo.get_papers_without_keywords(method=method, limit=limit)
    
    # ========== Step 2: 构建提取文本 ==========
    
    def get_text_for_extraction(self, paper: Paper) -> str:
        """
        获取用于关键词提取的文本
        
        使用 Paper.text_for_extraction: "{canonical_title}. {abstract}"
        """
        return paper.text_for_extraction
    
    # ========== Step 3: 关键词提取 ==========
    
    def extract_keywords_yake(
        self,
        text: str,
        top_n: int = 10,
    ) -> List[Tuple[str, float]]:
        """
        使用 YAKE 提取关键词
        
        Returns:
            [(keyword, score), ...] score 越高越好
        """
        extractor = self._get_yake()
        # YAKE 的 num_keywords 在初始化时设置，这里直接调用
        results = extractor.extract(text)
        return results[:top_n]  # 截取 top_n
    
    def extract_keywords_keybert(
        self,
        text: str,
        top_n: int = 10,
    ) -> List[Tuple[str, float]]:
        """
        使用 KeyBERT 提取关键词
        
        Returns:
            [(keyword, score), ...]
        """
        extractor = self._get_keybert()
        # KeyBERT 的接口可能也类似
        results = extractor.extract(text)
        return results[:top_n]
    
    # ========== 规范化与过滤 ==========
    
    def _get_filter(self):
        """获取关键词过滤器"""
        if not hasattr(self, '_filter'):
            from extractor.keyword_filter import get_keyword_filter
            self._filter = get_keyword_filter()
        return self._filter
    
    def filter_keywords(
        self,
        keywords: List[Tuple[str, float]],
        fuzzy_dedup: bool = True,
    ) -> List[Tuple[str, float]]:
        """
        过滤并规范化关键词
        
        包含：
        - 规范化（lower, 标点, 空白）
        - 过滤（banned, stopwords, noise）
        - 同义归并
        - 去重（严格 + 近似）
        """
        return self._get_filter().process(keywords, fuzzy_dedup=fuzzy_dedup)
    
    # ========== 处理流程 ==========
    
    def process_paper(
        self,
        paper: Paper,
        method: str = "yake",
        top_n: int = 15,  # 提取更多，过滤后保留 ~10
    ) -> List[PaperKeyword]:
        """
        处理单篇论文，提取并过滤关键词
        
        Returns:
            PaperKeyword 列表
        """
        text = self.get_text_for_extraction(paper)
        if not text or len(text) < 10:
            return []
        
        # 提取关键词（多提取一些，后续过滤）
        if method == "yake":
            raw_keywords = self.extract_keywords_yake(text, top_n=top_n)
        elif method == "keybert":
            raw_keywords = self.extract_keywords_keybert(text, top_n=top_n)
        else:
            raise ValueError(f"未知的提取方法: {method}")
        
        # 过滤、规范化、去重、同义归并
        filtered = self.filter_keywords(raw_keywords, fuzzy_dedup=True)
        
        # 截取最终保留数量
        filtered = filtered[:10]
        
        # 构建 PaperKeyword 对象
        results = []
        for kw, score in filtered:
            results.append(PaperKeyword(
                paper_id=paper.paper_id,
                keyword=kw,
                method=method,
                score=score,
            ))
        
        return results
    
    def run(
        self,
        method: str = "yake",
        limit: int = 1000,
        top_n: int = 10,
        force: bool = False,
    ) -> Dict[str, int]:
        """
        运行增量分析流程
        
        Args:
            method: 提取方法
            limit: 单次处理上限
            top_n: 每篇论文提取的关键词数
            force: 强制运行（忽略缓存）
            
        Returns:
            处理统计
        """
        print("\n" + "=" * 60)
        print(f"🔑 [Analysis Agent] 开始关键词提取 (method={method})")
        print("=" * 60)
        
        # 检查是否需要运行分析
        if not force and not self.should_run_analysis():
            print("   ⏭️ 无新数据，跳过分析")
            return {"status": "skipped", "reason": "no_new_data", "processed": 0, "keywords": 0}
        
        # Step 1: 获取待处理论文
        papers = self.get_papers_without_keywords(method=method, limit=limit)
        
        if not papers:
            print("   ✅ 没有需要处理的论文（已全部提取）")
            # 仍然更新元信息，表示已检查
            self._update_analysis_meta()
            return {"processed": 0, "keywords": 0}
        
        print(f"\n📝 待处理论文: {len(papers)} 篇")
        
        # Step 2-3: 处理每篇论文
        total_keywords = 0
        processed = 0
        
        for i, paper in enumerate(papers):
            try:
                keywords = self.process_paper(paper, method=method, top_n=top_n)
                
                # 保存到数据库
                for pk in keywords:
                    self.analysis_repo.save_paper_keyword(pk)
                
                total_keywords += len(keywords)
                processed += 1
                
                if (i + 1) % 100 == 0:
                    print(f"   已处理 {i + 1}/{len(papers)}...")
                    
            except Exception as e:
                print(f"   ❌ 处理失败 (paper_id={paper.paper_id}): {e}")
        
        # 更新元信息
        self._update_analysis_meta()
        
        # 更新会议缓存
        self._update_venue_caches()
        
        print(f"\n✅ [Analysis] 处理完成")
        print(f"   - 论文数: {processed}")
        print(f"   - 关键词数: {total_keywords}")
        print(f"   - 平均每篇: {total_keywords / processed:.1f}" if processed else "")
        
        return {
            "processed": processed,
            "keywords": total_keywords,
        }
    
    def should_run_analysis(self) -> bool:
        """
        判断是否需要运行分析
        
        检查：
        - raw_max_retrieved_at > analysis_meta.last_raw_max_retrieved_at
        - papers 数量是否变化
        """
        # 获取上次分析的元信息
        last_retrieved = self.analysis_repo.get_meta("last_raw_max_retrieved_at")
        last_paper_count = self.analysis_repo.get_meta("last_paper_count")
        
        # 获取当前状态
        current_retrieved = self.analysis_repo.get_max_retrieved_at()
        current_paper_count = self.analysis_repo.get_total_paper_count()
        
        # 首次运行
        if last_retrieved is None:
            return True
        
        # 检查是否有新数据
        if current_retrieved and current_retrieved > last_retrieved:
            return True
        
        # 检查论文数是否变化
        if last_paper_count and str(current_paper_count) != last_paper_count:
            return True
        
        return False
    
    def _update_analysis_meta(self):
        """更新分析元信息"""
        current_retrieved = self.analysis_repo.get_max_retrieved_at()
        current_paper_count = self.analysis_repo.get_total_paper_count()
        
        if current_retrieved:
            self.analysis_repo.set_meta("last_raw_max_retrieved_at", current_retrieved)
        
        self.analysis_repo.set_meta("last_paper_count", str(current_paper_count))
        self.analysis_repo.set_meta("last_analysis_run", datetime.now().isoformat())
    
    def _update_venue_caches(self):
        """更新会议总览缓存"""
        print("\n📊 更新会议缓存...")
        
        venues = self.structured_repo.get_all_venues()
        
        for venue in venues:
            venue_name = venue.canonical_name
            
            # 获取该会议的统计信息
            paper_count = self.structured_repo.get_paper_count(venue_id=venue.venue_id)
            top_keywords = self.analysis_repo.get_top_keywords(
                venue_id=venue.venue_id, 
                limit=20
            )
            
            # 转换为 JSON 格式
            top_kw_list = [{"keyword": kw, "count": count} for kw, count in top_keywords]
            
            # 保存到缓存
            self.analysis_repo.save_venue_summary(
                venue=venue_name,
                year=None,  # 全量统计
                paper_count=paper_count,
                top_keywords=top_kw_list
            )
        
        print(f"   ✅ 已更新 {len(venues)} 个会议的缓存")


def run_analysis(
    method: str = "yake",
    limit: int = 1000,
) -> Dict[str, int]:
    """运行分析的便捷函数"""
    agent = AnalysisAgent()
    return agent.run(method=method, limit=limit)
