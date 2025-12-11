"""
YAKE 关键词提取器

YAKE (Yet Another Keyword Extractor) 是一个无监督的关键词提取方法，
基于统计特征，不需要训练数据或外部资源。
"""

from typing import List, Tuple
import yake

from config import EXTRACTOR_CONFIG


class YakeExtractor:
    """YAKE 关键词提取器"""
    
    def __init__(
        self,
        language: str = None,
        max_ngram_size: int = None,
        deduplication_threshold: float = None,
        num_keywords: int = None,
    ):
        """
        初始化 YAKE 提取器
        
        Args:
            language: 语言代码（默认 "en"）
            max_ngram_size: 最大 n-gram 大小（默认 3）
            deduplication_threshold: 去重阈值（默认 0.9）
            num_keywords: 返回关键词数量（默认 20）
        """
        self.language = language or EXTRACTOR_CONFIG.yake_language
        self.max_ngram_size = max_ngram_size or EXTRACTOR_CONFIG.yake_max_ngram_size
        self.deduplication_threshold = (
            deduplication_threshold or EXTRACTOR_CONFIG.yake_deduplication_threshold
        )
        self.num_keywords = num_keywords or EXTRACTOR_CONFIG.yake_num_keywords
        
        self._extractor = yake.KeywordExtractor(
            lan=self.language,
            n=self.max_ngram_size,
            dedupLim=self.deduplication_threshold,
            top=self.num_keywords,
            features=None,
        )
    
    def extract(self, text: str) -> List[Tuple[str, float]]:
        """
        从文本中提取关键词
        
        Args:
            text: 输入文本
            
        Returns:
            关键词列表，每个元素为 (关键词, 分数) 元组
            注意：YAKE 的分数越低表示越重要
        """
        if not text or not text.strip():
            return []
        
        keywords = self._extractor.extract_keywords(text)
        
        # 转换分数（YAKE 分数越低越好，我们转换为越高越好）
        if keywords:
            max_score = max(score for _, score in keywords) if keywords else 1.0
            keywords = [
                (kw, 1 - (score / (max_score + 1e-10)))
                for kw, score in keywords
            ]
        
        return keywords
    
    def extract_keywords(self, text: str) -> List[str]:
        """
        从文本中提取关键词（仅返回关键词，不含分数）
        
        Args:
            text: 输入文本
            
        Returns:
            关键词列表
        """
        return [kw for kw, _ in self.extract(text)]


def create_yake_extractor(**kwargs) -> YakeExtractor:
    """创建 YAKE 提取器"""
    return YakeExtractor(**kwargs)
