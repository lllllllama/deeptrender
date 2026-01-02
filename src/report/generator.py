"""
Markdown 报告生成器

生成包含图表和统计信息的 Markdown 报告。
"""

from pathlib import Path
from typing import Dict, Optional
from datetime import datetime

from analysis.statistics import AnalysisResult
from config import REPORTS_DIR, FIGURES_DIR


class ReportGenerator:
    """报告生成器"""
    
    def __init__(
        self,
        output_dir: Path = None,
        figures_dir: Path = None,
    ):
        """
        初始化生成器
        
        Args:
            output_dir: 报告输出目录
            figures_dir: 图表目录
        """
        self.output_dir = output_dir or REPORTS_DIR
        self.figures_dir = figures_dir or FIGURES_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate(
        self,
        result: AnalysisResult,
        charts: Dict[str, Path],
        filename: str = "report.md",
    ) -> Path:
        """
        生成 Markdown 报告
        
        Args:
            result: 分析结果
            charts: 图表路径映射
            filename: 输出文件名
            
        Returns:
            报告文件路径
        """
        lines = []
        
        # 标题
        lines.append("# 🔬 顶会论文关键词趋势报告")
        lines.append("")
        lines.append(f"> 自动生成于 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        
        # 概览
        lines.append("## 📊 数据概览")
        lines.append("")
        lines.append(f"| 指标 | 数值 |")
        lines.append("|------|------|")
        lines.append(f"| 论文总数 | {result.total_papers:,} |")
        lines.append(f"| 关键词总数 | {result.total_keywords:,} |")
        lines.append(f"| 覆盖会议 | {', '.join(result.venues)} |")
        lines.append(f"| 年份范围 | {min(result.years)} - {max(result.years)} |")
        lines.append("")
        
        # 整体词云
        if "wordcloud_overall" in charts:
            lines.append("## ☁️ 关键词云")
            lines.append("")
            rel_path = self._get_relative_path(charts["wordcloud_overall"])
            lines.append(f"![关键词云]({rel_path})")
            lines.append("")
        
        # Top-K 关键词
        if result.overall_top_keywords:
            lines.append("## 🏆 Top 20 热门关键词")
            lines.append("")
            
            if "top_keywords" in charts:
                rel_path = self._get_relative_path(charts["top_keywords"])
                lines.append(f"![Top 关键词]({rel_path})")
                lines.append("")
            
            # 表格形式
            lines.append("<details>")
            lines.append("<summary>📋 完整列表（Top 50）</summary>")
            lines.append("")
            lines.append("| 排名 | 关键词 | 出现次数 |")
            lines.append("|------|--------|----------|")
            for i, (kw, count) in enumerate(result.overall_top_keywords[:50], 1):
                lines.append(f"| {i} | {kw} | {count} |")
            lines.append("")
            lines.append("</details>")
            lines.append("")
        
        # 趋势分析
        if result.keyword_trends:
            lines.append("## 📈 关键词趋势")
            lines.append("")
            
            if "keyword_trends" in charts:
                rel_path = self._get_relative_path(charts["keyword_trends"])
                lines.append(f"![关键词趋势]({rel_path})")
                lines.append("")
        
        # 新兴关键词
        if result.emerging_keywords:
            lines.append("## 🚀 新兴关键词")
            lines.append("")
            lines.append("以下关键词在最近一年增长显著：")
            lines.append("")
            for i, kw in enumerate(result.emerging_keywords[:10], 1):
                lines.append(f"{i}. **{kw}**")
            lines.append("")
        
        # 各会议详情
        lines.append("## 📚 会议详情")
        lines.append("")
        
        for venue in result.venues:
            if venue not in result.venue_stats:
                continue
                
            lines.append(f"### {venue}")
            lines.append("")
            
            # 会议词云
            chart_key = f"wordcloud_{venue.lower()}"
            if chart_key in charts:
                rel_path = self._get_relative_path(charts[chart_key])
                lines.append(f"![{venue} 词云]({rel_path})")
                lines.append("")
            
            # 各年份统计
            lines.append("| 年份 | 论文数 | Top 5 关键词 |")
            lines.append("|------|--------|--------------|")
            
            for year in sorted(result.venue_stats[venue].keys(), reverse=True):
                stats = result.venue_stats[venue][year]
                top5 = ", ".join([kw for kw, _ in stats.top_keywords[:5]])
                lines.append(f"| {year} | {stats.paper_count} | {top5} |")
            
            lines.append("")
        
        # 会议对比
        if result.years:
            latest_year = result.years[0]
            chart_key = f"comparison_{latest_year}"
            if chart_key in charts:
                lines.append(f"## ⚖️ 会议对比 ({latest_year})")
                lines.append("")
                rel_path = self._get_relative_path(charts[chart_key])
                lines.append(f"![会议对比]({rel_path})")
                lines.append("")
        
        # 页脚
        lines.append("---")
        lines.append("")
        lines.append("*本报告由 [DeepTrender](https://github.com/your-repo/deeptrender) 自动生成*")
        
        # 写入文件
        output_path = self.output_dir / filename
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        
        return output_path
    
    def _get_relative_path(self, path: Path) -> str:
        """获取相对于报告目录的路径"""
        try:
            return "../figures/" + path.name
        except ValueError:
            return str(path)


def generate_report(
    result: AnalysisResult,
    charts: Dict[str, Path],
    output_dir: Path = None,
    filename: str = "report.md",
) -> Path:
    """
    生成报告的便捷函数
    
    Args:
        result: 分析结果
        charts: 图表路径映射
        output_dir: 输出目录
        filename: 文件名
        
    Returns:
        报告文件路径
    """
    generator = ReportGenerator(output_dir=output_dir)
    return generator.generate(result, charts, filename)
