"""
图表主题配置
"""

from dataclasses import dataclass
from typing import List


@dataclass
class ChartTheme:
    """图表主题"""
    
    # 图表尺寸
    figure_width: int = 12
    figure_height: int = 8
    dpi: int = 150
    
    # 颜色
    primary_color: str = "#4C72B0"
    secondary_color: str = "#55A868"
    accent_color: str = "#C44E52"
    background_color: str = "#FFFFFF"
    text_color: str = "#333333"
    grid_color: str = "#E5E5E5"
    
    # 调色板（用于多系列图表）
    color_palette: List[str] = None
    
    # 词云配置
    wordcloud_width: int = 1600
    wordcloud_height: int = 800
    wordcloud_background: str = "white"
    wordcloud_colormap: str = "viridis"
    wordcloud_max_words: int = 100
    
    # 字体
    font_family: str = "DejaVu Sans"
    title_fontsize: int = 16
    label_fontsize: int = 12
    tick_fontsize: int = 10
    
    def __post_init__(self):
        if self.color_palette is None:
            self.color_palette = [
                "#4C72B0",  # 蓝色
                "#55A868",  # 绿色
                "#C44E52",  # 红色
                "#8172B3",  # 紫色
                "#CCB974",  # 黄色
                "#64B5CD",  # 青色
                "#E377C2",  # 粉色
                "#7F7F7F",  # 灰色
            ]


# 默认主题
CHART_THEME = ChartTheme()

# 深色主题
DARK_THEME = ChartTheme(
    background_color="#1E1E1E",
    text_color="#E0E0E0",
    grid_color="#333333",
    wordcloud_background="#1E1E1E",
    wordcloud_colormap="plasma",
)
