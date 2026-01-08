"""
关键词处理器

批量处理论文，提取关键词并进行标准化。
"""

from typing import List, Literal, Optional, Union
from tqdm import tqdm

from .yake_extractor import YakeExtractor, create_yake_extractor
from .keybert_extractor import KeyBertExtractor, get_keybert_extractor
from scraper.models import Paper
from config import EXTRACTOR_CONFIG


ExtractorType = Literal["yake", "keybert", "both"]


class KeywordProcessor:
    """关键词处理器"""
    
    def __init__(
        self,
        extractor_type: ExtractorType = None,
        yake_extractor: Optional[YakeExtractor] = None,
        keybert_extractor: Optional[KeyBertExtractor] = None,
    ):
        """
        初始化处理器
        
        Args:
            extractor_type: 提取器类型（"yake", "keybert", "both"）
            yake_extractor: YAKE 提取器实例
            keybert_extractor: KeyBERT 提取器实例
        """
        self.extractor_type = extractor_type or EXTRACTOR_CONFIG.default_extractor
        
        # 初始化提取器
        if self.extractor_type in ("yake", "both"):
            self.yake = yake_extractor or create_yake_extractor()
        else:
            self.yake = None
        
        if self.extractor_type in ("keybert", "both"):
            self.keybert = keybert_extractor or get_keybert_extractor()
        else:
            self.keybert = None
    
    def extract_from_text(self, text: str) -> List[str]:
        """
        从文本中提取关键词
        
        Args:
            text: 输入文本
            
        Returns:
            关键词列表
        """
        keywords = set()
        
        if self.yake:
            yake_keywords = self.yake.extract_keywords(text)
            keywords.update(yake_keywords)
        
        if self.keybert:
            keybert_keywords = self.keybert.extract_keywords(text)
            keywords.update(keybert_keywords)
        
        return list(keywords)
    
    def process_paper(self, paper: Paper) -> Paper:
        """
        处理单篇论文，提取关键词
        
        Args:
            paper: 论文对象
            
        Returns:
            更新了 extracted_keywords 的论文对象
        """
        text = paper.text_for_extraction
        extracted = self.extract_from_text(text)
        
        # 标准化关键词
        normalized = self._normalize_keywords(extracted)
        
        paper.extracted_keywords = normalized
        return paper
    
    def process_papers(
        self,
        papers: List[Paper],
        show_progress: bool = True,
    ) -> List[Paper]:
        """
        批量处理论文
        
        Args:
            papers: 论文列表
            show_progress: 是否显示进度条
            
        Returns:
            处理后的论文列表
        """
        print(f"\n🔑 正在提取关键词（使用 {self.extractor_type}）...")
        
        if show_progress:
            papers = tqdm(papers, desc="提取关键词")
        
        processed = []
        for paper in papers:
            processed.append(self.process_paper(paper))
        
        total_keywords = sum(len(p.extracted_keywords) for p in processed)
        print(f"✅ 提取完成，共 {total_keywords} 个关键词")
        
        return processed
    
    def _normalize_keywords(self, keywords: List[str]) -> List[str]:
        """
        标准化关键词
        
        - 转换为小写
        - 去除首尾空格
        - 去重
        - 过滤过短的关键词
        
        Args:
            keywords: 原始关键词列表
            
        Returns:
            标准化后的关键词列表
        """
        normalized = set()
        for kw in keywords:
            kw = kw.strip().lower()
            # 过滤过短或过长的关键词
            if 2 <= len(kw) <= 100:
                normalized.add(kw)
        return list(normalized)


def extract_keywords_batch(
    papers: List[Paper],
    extractor_type: ExtractorType = None,
    show_progress: bool = True,
) -> List[Paper]:
    """
    批量提取论文关键词的便捷函数
    
    Args:
        papers: 论文列表
        extractor_type: 提取器类型
        show_progress: 是否显示进度条
        
    Returns:
        处理后的论文列表
    """
    processor = KeywordProcessor(extractor_type=extractor_type)
    return processor.process_papers(papers, show_progress=show_progress)
