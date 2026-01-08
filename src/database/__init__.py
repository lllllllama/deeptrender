"""
数据库模块

提供三层架构的数据库操作：
- RawRepository: 原始数据层
- StructuredRepository: 结构化数据层
- AnalysisRepository: 分析层
- DatabaseRepository: 统一接口（向后兼容）
"""

from .repository import (
    DatabaseRepository,
    RawRepository,
    StructuredRepository,
    AnalysisRepository,
    get_repository,
    get_raw_repository,
    get_structured_repository,
    get_analysis_repository,
)

__all__ = [
    "DatabaseRepository",
    "RawRepository",
    "StructuredRepository",
    "AnalysisRepository",
    "get_repository",
    "get_raw_repository",
    "get_structured_repository",
    "get_analysis_repository",
]
