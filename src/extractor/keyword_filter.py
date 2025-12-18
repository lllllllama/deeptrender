"""
关键词过滤与规范化模块

提供多层过滤：
- 2.2.A 低信息词过滤（banned / generic）
- 2.2.B stopwords 过滤
- 2.2.C 形态过滤（数字、URL、长度）
- 2.2.D 领域噪声过滤
- 2.3 去重与合并（严格/近似）
- 2.4 同义归并
"""

import re
from typing import List, Tuple, Optional, Set, Dict
from difflib import SequenceMatcher


# ============================================================
# 2.2.A 低信息词（banned / generic words）
# ============================================================

BANNED_WORDS = {
    # 论文写作通用词
    "method", "methods", "approach", "approaches", "technique", "techniques",
    "result", "results", "performance", "paper", "papers", "study", "studies",
    "novel", "new", "proposed", "propose", "present", "presents", "introduction",
    "conclusion", "abstract", "work", "works", "research", "analysis",
    "experiment", "experiments", "evaluation", "evaluations",
    
    # 过于泛化的技术词
    "model", "models", "network", "networks", "system", "systems",
    "algorithm", "algorithms", "framework", "frameworks",
    "data", "dataset", "datasets", "benchmark", "benchmarks",
    "training", "testing", "learning", "task", "tasks",
    
    # 形容词/副词
    "based", "using", "via", "improved", "better", "best", "efficient",
    "effective", "simple", "complex", "large", "small", "high", "low",
    "state", "art", "end", "end to end",
    
    # 动词/短语
    "show", "shows", "demonstrate", "demonstrates", "achieve", "achieves",
    "outperform", "outperforms", "improve", "improves",
}

# ============================================================
# 2.2.B English Stopwords
# ============================================================

ENGLISH_STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "if", "then", "else", "when",
    "at", "by", "for", "with", "about", "against", "between", "into",
    "through", "during", "before", "after", "above", "below", "to", "from",
    "up", "down", "in", "out", "on", "off", "over", "under", "again",
    "further", "once", "here", "there", "all", "each", "few", "more",
    "most", "other", "some", "such", "no", "nor", "not", "only", "own",
    "same", "so", "than", "too", "very", "can", "will", "just", "should",
    "now", "also", "however", "thus", "therefore", "hence", "although",
    "whereas", "while", "since", "because", "as", "is", "are", "was",
    "were", "be", "been", "being", "have", "has", "had", "having", "do",
    "does", "did", "doing", "would", "could", "might", "may", "must",
    "shall", "i", "you", "he", "she", "it", "we", "they", "what", "which",
    "who", "whom", "this", "that", "these", "those", "am",
}

# ============================================================
# 2.2.D 领域噪声词
# ============================================================

DOMAIN_NOISE_WORDS = {
    # 实验相关
    "experiments", "experimental", "ablation", "ablations",
    "comparison", "comparisons", "baseline", "baselines",
    
    # 数据相关
    "dataset", "datasets", "benchmark", "benchmarks",
    "samples", "sample", "examples", "example",
    
    # 结果相关
    "accuracy", "loss", "metrics", "metric", "score", "scores",
    "table", "figure", "figures", "tables",
    
    # 其他泛词
    "problem", "problems", "solution", "solutions",
    "challenge", "challenges", "issue", "issues",
    "application", "applications",
}

# ============================================================
# 2.4 同义归并词典
# ============================================================

SYNONYM_MAPPING = {
    # LLM 相关
    "llm": "large language model",
    "llms": "large language model",
    "large language models": "large language model",
    
    # Diffusion 相关
    "diffusion models": "diffusion model",
    "diffusion based": "diffusion model",
    
    # Transformer 相关
    "transformers": "transformer",
    "vision transformer": "vision transformer",
    "vision transformers": "vision transformer",
    "vit": "vision transformer",
    "vits": "vision transformer",
    
    # GAN 相关
    "gans": "generative adversarial network",
    "gan": "generative adversarial network",
    "generative adversarial networks": "generative adversarial network",
    
    # CNN 相关
    "cnn": "convolutional neural network",
    "cnns": "convolutional neural network",
    "convolutional neural networks": "convolutional neural network",
    
    # RNN 相关
    "rnn": "recurrent neural network",
    "rnns": "recurrent neural network",
    "recurrent neural networks": "recurrent neural network",
    "lstm": "long short term memory",
    "lstms": "long short term memory",
    
    # 强化学习
    "rl": "reinforcement learning",
    "drl": "deep reinforcement learning",
    
    # 自监督
    "self supervised": "self supervised learning",
    "self supervision": "self supervised learning",
    
    # 对比学习
    "contrastive": "contrastive learning",
    
    # 其他
    "nlp": "natural language processing",
    "cv": "computer vision",
    "ml": "machine learning",
    "dl": "deep learning",
    "ai": "artificial intelligence",
}


class KeywordFilter:
    """关键词过滤器"""
    
    def __init__(
        self,
        banned_words: Set[str] = None,
        stopwords: Set[str] = None,
        domain_noise: Set[str] = None,
        synonym_map: Dict[str, str] = None,
        min_length: int = 3,
        max_length: int = 60,
    ):
        self.banned_words = banned_words or BANNED_WORDS
        self.stopwords = stopwords or ENGLISH_STOPWORDS
        self.domain_noise = domain_noise or DOMAIN_NOISE_WORDS
        self.synonym_map = synonym_map or SYNONYM_MAPPING
        self.min_length = min_length
        self.max_length = max_length
        
        # 合并所有需要过滤的词
        self._all_filtered = self.banned_words | self.stopwords | self.domain_noise
    
    # ========== 2.1 规范化层 ==========
    
    def normalize(self, keyword: str) -> Optional[str]:
        """
        规范化关键词
        
        1. lower() + strip()
        2. 标点统一：- / _ → 空格
        3. 去掉尾部标点
        4. 空白折叠
        """
        if not keyword:
            return None
        
        kw = keyword.lower().strip()
        
        # 标点统一
        kw = re.sub(r'[-_/]', ' ', kw)
        
        # 去掉尾部标点
        kw = re.sub(r'[,;:.!?\'")\]]+$', '', kw)
        kw = re.sub(r'^[(\[\'\"]+', '', kw)
        
        # 空白折叠
        kw = re.sub(r'\s+', ' ', kw).strip()
        
        return kw if kw else None
    
    # ========== 2.2 过滤层 ==========
    
    def is_banned(self, keyword: str) -> bool:
        """检查是否是低信息词"""
        return keyword in self.banned_words
    
    def is_stopword(self, keyword: str) -> bool:
        """检查是否是停用词"""
        # 检查整体
        if keyword in self.stopwords:
            return True
        # 检查单词组成
        words = keyword.split()
        if len(words) == 1:
            return keyword in self.stopwords
        return False
    
    def is_domain_noise(self, keyword: str) -> bool:
        """检查是否是领域噪声词"""
        return keyword in self.domain_noise
    
    def is_noise_pattern(self, keyword: str) -> bool:
        """
        检查是否匹配噪声模式
        
        - 纯数字
        - 含大量数字（如 "2024 2025"）
        - 含 URL/email
        - 过短/过长
        """
        # 长度检查
        if len(keyword) < self.min_length or len(keyword) > self.max_length:
            return True
        
        # 纯数字
        if re.match(r'^[\d\s.,-]+$', keyword):
            return True
        
        # 数字占比过高（>50%）
        digits = sum(1 for c in keyword if c.isdigit())
        if digits > len(keyword) * 0.5:
            return True
        
        # URL/email 模式
        if re.search(r'(http|www|\.com|\.org|@)', keyword):
            return True
        
        # 单个字符
        if len(keyword.split()) == 1 and len(keyword) < 3:
            return True
        
        return False
    
    def should_filter(self, keyword: str) -> bool:
        """综合判断是否应该过滤"""
        return (
            self.is_banned(keyword) or
            self.is_stopword(keyword) or
            self.is_domain_noise(keyword) or
            self.is_noise_pattern(keyword)
        )
    
    # ========== 2.3 去重与合并 ==========
    
    def deduplicate_exact(
        self,
        keywords: List[Tuple[str, float]],
    ) -> List[Tuple[str, float]]:
        """严格去重：完全相同的只留最高分"""
        seen = {}
        for kw, score in keywords:
            if kw not in seen or score > seen[kw]:
                seen[kw] = score
        return [(kw, score) for kw, score in seen.items()]
    
    def similarity(self, a: str, b: str) -> float:
        """计算两个字符串的相似度"""
        return SequenceMatcher(None, a, b).ratio()
    
    def deduplicate_fuzzy(
        self,
        keywords: List[Tuple[str, float]],
        threshold: float = 0.85,
    ) -> List[Tuple[str, float]]:
        """
        近似去重：相似度高的只留得分更高的
        
        处理 "diffusion model" vs "diffusion models" 这类情况
        """
        if not keywords:
            return []
        
        # 按分数降序排序
        sorted_kws = sorted(keywords, key=lambda x: x[1], reverse=True)
        result = []
        
        for kw, score in sorted_kws:
            # 检查是否与已有关键词相似
            is_similar = False
            for existing_kw, _ in result:
                if self.similarity(kw, existing_kw) >= threshold:
                    is_similar = True
                    break
                # 特殊处理单复数：最后一个字符差异
                if kw.rstrip('s') == existing_kw or existing_kw.rstrip('s') == kw:
                    is_similar = True
                    break
            
            if not is_similar:
                result.append((kw, score))
        
        return result
    
    # ========== 2.4 同义归并 ==========
    
    def apply_synonym(self, keyword: str) -> str:
        """应用同义归并"""
        return self.synonym_map.get(keyword, keyword)
    
    # ========== 完整处理流程 ==========
    
    def process(
        self,
        keywords: List[Tuple[str, float]],
        fuzzy_dedup: bool = True,
        fuzzy_threshold: float = 0.85,
    ) -> List[Tuple[str, float]]:
        """
        完整的关键词处理流程
        
        1. 规范化
        2. 过滤
        3. 同义归并
        4. 去重
        """
        result = []
        
        for kw, score in keywords:
            # 1. 规范化
            normalized = self.normalize(kw)
            if not normalized:
                continue
            
            # 2. 过滤
            if self.should_filter(normalized):
                continue
            
            # 3. 同义归并
            canonical = self.apply_synonym(normalized)
            
            result.append((canonical, score))
        
        # 4. 严格去重
        result = self.deduplicate_exact(result)
        
        # 5. 近似去重（可选）
        if fuzzy_dedup:
            result = self.deduplicate_fuzzy(result, threshold=fuzzy_threshold)
        
        return result


# 全局过滤器实例
_default_filter = None

def get_keyword_filter() -> KeywordFilter:
    """获取默认过滤器"""
    global _default_filter
    if _default_filter is None:
        _default_filter = KeywordFilter()
    return _default_filter


def filter_keywords(
    keywords: List[Tuple[str, float]],
    fuzzy_dedup: bool = True,
) -> List[Tuple[str, float]]:
    """过滤关键词的便捷函数"""
    return get_keyword_filter().process(keywords, fuzzy_dedup=fuzzy_dedup)
