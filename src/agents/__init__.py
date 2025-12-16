"""
Agent 模块

提供三阶段工作流的 Agent 实现：
- IngestionAgent: 原始数据采集
- StructuringAgent: 数据结构化
- AnalysisAgent: 分析与关键词提取
"""

from .ingestion_agent import IngestionAgent, run_ingestion
from .structuring_agent import StructuringAgent, run_structuring

__all__ = [
    "IngestionAgent",
    "StructuringAgent",
    "run_ingestion",
    "run_structuring",
]
