"""
图表生成器

生成词云、柱状图、趋势图等可视化图表。
"""

from pathlib import Path
from typing import List, Tuple, Dict, Optional
import matplotlib.pyplot as plt
import matplotlib
from wordcloud import WordCloud
import numpy as np

from .theme import ChartTheme, CHART_THEME
from analysis.statistics import AnalysisResult, TrendData
from config import FIGURES_DIR

# 设置 matplotlib 后端
matplotlib.use('Agg')

# 设置中文字体支持
plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False


class ChartGenerator:
    """图表生成器"""
    
    def __init__(
        self,
        output_dir: Path = None,
        theme: ChartTheme = None,
    ):
        """
        初始化生成器
        
        Args:
            output_dir: 输出目录
            theme: 图表主题
        """
        self.output_dir = output_dir or FIGURES_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.theme = theme or CHART_THEME
    
    def generate_wordcloud(
        self,
        keywords: List[Tuple[str, int]],
        filename: str = "wordcloud.png",
        title: str = None,
    ) -> Path:
        """
        生成词云图
        
        Args:
            keywords: 关键词和计数的列表
            filename: 输出文件名
            title: 图表标题
            
        Returns:
            输出文件路径
        """
        # 转换为频率字典
        freq_dict = {kw: count for kw, count in keywords}
        
        # 创建词云
        wc = WordCloud(
            width=self.theme.wordcloud_width,
            height=self.theme.wordcloud_height,
            background_color=self.theme.wordcloud_background,
            colormap=self.theme.wordcloud_colormap,
            max_words=self.theme.wordcloud_max_words,
            prefer_horizontal=0.7,
            min_font_size=10,
            max_font_size=150,
        )
        
        wc.generate_from_frequencies(freq_dict)
        
        # 创建图表
        fig, ax = plt.subplots(figsize=(
            self.theme.figure_width,
            self.theme.figure_height
        ))
        
        ax.imshow(wc, interpolation='bilinear')
        ax.axis('off')
        
        if title:
            ax.set_title(
                title,
                fontsize=self.theme.title_fontsize,
                color=self.theme.text_color,
                pad=20,
            )
        
        # 保存
        output_path = self.output_dir / filename
        plt.tight_layout()
        plt.savefig(output_path, dpi=self.theme.dpi, bbox_inches='tight')
        plt.close()
        
        return output_path
    
    def generate_bar_chart(
        self,
        keywords: List[Tuple[str, int]],
        filename: str = "top_keywords.png",
        title: str = "Top Keywords",
        xlabel: str = "Count",
        ylabel: str = "Keyword",
        top_k: int = 20,
    ) -> Path:
        """
        生成水平柱状图
        
        Args:
            keywords: 关键词和计数的列表
            filename: 输出文件名
            title: 图表标题
            top_k: 显示前 K 个
            
        Returns:
            输出文件路径
        """
        # 取 Top-K
        data = keywords[:top_k]
        
        # 反转顺序（最高的在上面）
        keywords_list = [kw for kw, _ in reversed(data)]
        counts = [count for _, count in reversed(data)]
        
        # 创建图表
        fig, ax = plt.subplots(figsize=(
            self.theme.figure_width,
            max(self.theme.figure_height, len(data) * 0.4)
        ))
        
        # 绘制柱状图
        y_pos = np.arange(len(keywords_list))
        bars = ax.barh(y_pos, counts, color=self.theme.primary_color, alpha=0.8)
        
        # 在柱状图上显示数值
        for bar, count in zip(bars, counts):
            ax.text(
                bar.get_width() + max(counts) * 0.01,
                bar.get_y() + bar.get_height() / 2,
                str(count),
                va='center',
                fontsize=self.theme.tick_fontsize,
                color=self.theme.text_color,
            )
        
        # 设置标签
        ax.set_yticks(y_pos)
        ax.set_yticklabels(keywords_list, fontsize=self.theme.tick_fontsize)
        ax.set_xlabel(xlabel, fontsize=self.theme.label_fontsize)
        ax.set_title(title, fontsize=self.theme.title_fontsize, pad=15)
        
        # 设置样式
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.set_facecolor(self.theme.background_color)
        
        # 保存
        output_path = self.output_dir / filename
        plt.tight_layout()
        plt.savefig(output_path, dpi=self.theme.dpi, bbox_inches='tight')
        plt.close()
        
        return output_path
    
    def generate_trend_chart(
        self,
        trends: List[TrendData],
        filename: str = "trends.png",
        title: str = "Keyword Trends",
        xlabel: str = "Year",
        ylabel: str = "Count",
    ) -> Path:
        """
        生成趋势折线图
        
        Args:
            trends: 趋势数据列表
            filename: 输出文件名
            title: 图表标题
            
        Returns:
            输出文件路径
        """
        fig, ax = plt.subplots(figsize=(
            self.theme.figure_width,
            self.theme.figure_height
        ))
        
        # 绘制每条趋势线
        for i, trend in enumerate(trends):
            color = self.theme.color_palette[i % len(self.theme.color_palette)]
            ax.plot(
                trend.years,
                trend.counts,
                marker='o',
                linewidth=2,
                markersize=6,
                label=trend.keyword,
                color=color,
            )
        
        # 设置标签
        ax.set_xlabel(xlabel, fontsize=self.theme.label_fontsize)
        ax.set_ylabel(ylabel, fontsize=self.theme.label_fontsize)
        ax.set_title(title, fontsize=self.theme.title_fontsize, pad=15)
        
        # 设置 x 轴为整数
        ax.xaxis.set_major_locator(plt.MaxNLocator(integer=True))
        
        # 网格和图例
        ax.grid(True, linestyle='--', alpha=0.5, color=self.theme.grid_color)
        ax.legend(
            loc='upper left',
            bbox_to_anchor=(1.02, 1),
            fontsize=self.theme.tick_fontsize,
        )
        
        # 设置样式
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.set_facecolor(self.theme.background_color)
        
        # 保存
        output_path = self.output_dir / filename
        plt.tight_layout()
        plt.savefig(output_path, dpi=self.theme.dpi, bbox_inches='tight')
        plt.close()
        
        return output_path
    
    def generate_venue_comparison(
        self,
        comparison: Dict[str, List[Tuple[str, int]]],
        filename: str = "venue_comparison.png",
        title: str = "Venue Comparison",
        top_k: int = 10,
    ) -> Path:
        """
        生成会议对比图
        
        Args:
            comparison: 会议到关键词的映射
            filename: 输出文件名
            title: 图表标题
            top_k: 每个会议显示前 K 个
            
        Returns:
            输出文件路径
        """
        venues = list(comparison.keys())
        num_venues = len(venues)
        
        if num_venues == 0:
            return None
        
        # 创建子图
        fig, axes = plt.subplots(
            1, num_venues,
            figsize=(self.theme.figure_width, self.theme.figure_height),
            sharey=False,
        )
        
        if num_venues == 1:
            axes = [axes]
        
        for ax, (venue, keywords) in zip(axes, comparison.items()):
            data = keywords[:top_k]
            kw_list = [kw for kw, _ in reversed(data)]
            counts = [count for _, count in reversed(data)]
            
            y_pos = np.arange(len(kw_list))
            color_idx = venues.index(venue) % len(self.theme.color_palette)
            ax.barh(y_pos, counts, color=self.theme.color_palette[color_idx], alpha=0.8)
            
            ax.set_yticks(y_pos)
            ax.set_yticklabels(kw_list, fontsize=self.theme.tick_fontsize - 2)
            ax.set_title(venue, fontsize=self.theme.label_fontsize)
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
        
        fig.suptitle(title, fontsize=self.theme.title_fontsize)
        
        # 保存
        output_path = self.output_dir / filename
        plt.tight_layout()
        plt.savefig(output_path, dpi=self.theme.dpi, bbox_inches='tight')
        plt.close()
        
        return output_path


def generate_all_charts(
    result: AnalysisResult,
    output_dir: Path = None,
) -> Dict[str, Path]:
    """
    生成所有图表
    
    Args:
        result: 分析结果
        output_dir: 输出目录
        
    Returns:
        图表名称到路径的映射
    """
    generator = ChartGenerator(output_dir=output_dir)
    charts = {}
    
    print("\n📊 正在生成图表...")
    
    # 1. 整体词云
    if result.overall_top_keywords:
        path = generator.generate_wordcloud(
            result.overall_top_keywords,
            filename="wordcloud_overall.png",
            title="Overall Keyword Cloud",
        )
        charts["wordcloud_overall"] = path
        print(f"  ✅ 词云图: {path}")
    
    # 2. Top-K 柱状图
    if result.overall_top_keywords:
        path = generator.generate_bar_chart(
            result.overall_top_keywords,
            filename="top_keywords.png",
            title="Top 20 Keywords",
            top_k=20,
        )
        charts["top_keywords"] = path
        print(f"  ✅ Top-K 图: {path}")
    
    # 3. 趋势图
    if result.keyword_trends:
        # 只显示前 8 个关键词的趋势
        path = generator.generate_trend_chart(
            result.keyword_trends[:8],
            filename="keyword_trends.png",
            title="Top Keyword Trends",
        )
        charts["keyword_trends"] = path
        print(f"  ✅ 趋势图: {path}")
    
    # 4. 各会议词云
    for venue in result.venues:
        if venue in result.venue_stats:
            # 合并该会议所有年份的关键词
            all_keywords = {}
            for year, stats in result.venue_stats[venue].items():
                for kw, count in stats.top_keywords:
                    all_keywords[kw] = all_keywords.get(kw, 0) + count
            
            if all_keywords:
                sorted_keywords = sorted(
                    all_keywords.items(),
                    key=lambda x: -x[1]
                )[:100]
                
                path = generator.generate_wordcloud(
                    sorted_keywords,
                    filename=f"wordcloud_{venue.lower()}.png",
                    title=f"{venue} Keyword Cloud",
                )
                charts[f"wordcloud_{venue.lower()}"] = path
                print(f"  ✅ {venue} 词云: {path}")
    
    # 5. 最新年份的会议对比
    if result.years:
        latest_year = result.years[0]
        comparison = {}
        for venue in result.venues:
            if venue in result.venue_stats and latest_year in result.venue_stats[venue]:
                comparison[venue] = result.venue_stats[venue][latest_year].top_keywords
        
        if comparison:
            path = generator.generate_venue_comparison(
                comparison,
                filename=f"comparison_{latest_year}.png",
                title=f"Venue Comparison ({latest_year})",
            )
            charts[f"comparison_{latest_year}"] = path
            print(f"  ✅ 会议对比图: {path}")
    
    print(f"\n✅ 共生成 {len(charts)} 张图表")
    return charts
