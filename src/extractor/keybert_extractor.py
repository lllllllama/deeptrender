"""
KeyBERT 关键词提取器

KeyBERT 使用 BERT embeddings 进行关键词提取，
能够捕获文本的语义信息，提取更准确的关键词。
"""

from typing import List, Tuple, Optional
from keybert import KeyBERT

from config import EXTRACTOR_CONFIG


class KeyBertExtractor:
    """KeyBERT 关键词提取器"""
    
    _instance: Optional["KeyBertExtractor"] = None
    _model: Optional[KeyBERT] = None
    
    def __init__(
        self,
        model_name: str = None,
        top_n: int = None,
        keyphrase_ngram_range: tuple = None,
    ):
        """
        初始化 KeyBERT 提取器
        
        Args:
            model_name: 模型名称（默认 "all-MiniLM-L6-v2"）
            top_n: 返回关键词数量（默认 20）
            keyphrase_ngram_range: n-gram 范围（默认 (1, 3)）
        """
        self.model_name = model_name or EXTRACTOR_CONFIG.keybert_model
        self.top_n = top_n or EXTRACTOR_CONFIG.keybert_top_n
        self.keyphrase_ngram_range = (
            keyphrase_ngram_range or EXTRACTOR_CONFIG.keybert_keyphrase_ngram_range
        )
        
        # 延迟加载模型
        self._keybert = None
    
    @property
    def keybert(self) -> KeyBERT:
        """延迟加载 KeyBERT 模型"""
        if self._keybert is None:
            print(f"⏳ 加载 KeyBERT 模型: {self.model_name}...")
            self._keybert = KeyBERT(self.model_name)
            print("✅ KeyBERT 模型加载完成")
        return self._keybert
    
    def extract(self, text: str) -> List[Tuple[str, float]]:
        """
        从文本中提取关键词
        
        Args:
            text: 输入文本
            
        Returns:
            关键词列表，每个元素为 (关键词, 分数) 元组
        """
        if not text or not text.strip():
            return []
        
        try:
            keywords = self.keybert.extract_keywords(
                text,
                keyphrase_ngram_range=self.keyphrase_ngram_range,
                stop_words="english",
                top_n=self.top_n,
                use_maxsum=True,  # 使用 Max Sum 多样化
                nr_candidates=20,
            )
            return keywords
        except Exception as e:
            print(f"KeyBERT 提取失败: {e}")
            return []
    
    def extract_keywords(self, text: str) -> List[str]:
        """
        从文本中提取关键词（仅返回关键词，不含分数）
        
        Args:
            text: 输入文本
            
        Returns:
            关键词列表
        """
        return [kw for kw, _ in self.extract(text)]


# 单例模式，避免重复加载模型
_keybert_instance: Optional[KeyBertExtractor] = None


def get_keybert_extractor(**kwargs) -> KeyBertExtractor:
    """获取 KeyBERT 提取器（单例）"""
    global _keybert_instance
    if _keybert_instance is None:
        _keybert_instance = KeyBertExtractor(**kwargs)
    return _keybert_instance


def create_keybert_extractor(**kwargs) -> KeyBertExtractor:
    """创建新的 KeyBERT 提取器"""
    return KeyBertExtractor(**kwargs)
