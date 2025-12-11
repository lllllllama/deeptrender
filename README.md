# DepthTrender - 顶会论文关键词追踪系统

[![Update Keywords](https://github.com/YOUR_USERNAME/depthtrender/actions/workflows/update.yml/badge.svg)](https://github.com/YOUR_USERNAME/depthtrender/actions/workflows/update.yml)

自动追踪深度学习顶级会议（ICLR、NeurIPS、ICML）的论文关键词，提供统计分析、可视化和趋势报告，助力研究人员实时掌握最新的研究热点与发展趋势。

## ✨ 特性

- 🔍 **自动爬取** - 通过 OpenReview API 自动获取顶会论文
- 🔑 **智能提取** - 支持 YAKE 和 KeyBERT 两种关键词提取方法
- 📊 **统计分析** - 提供关键词频率、趋势、会议对比等统计
- 🎨 **可视化** - 生成词云图、柱状图、趋势折线图
- 📄 **报告生成** - 自动生成包含图表的 Markdown 报告
- ⏰ **定时更新** - 通过 GitHub Actions 每周自动更新

## 📁 项目结构

```
depthtrender/
├── .github/workflows/     # GitHub Actions 工作流
├── src/
│   ├── scraper/          # 论文爬取模块
│   ├── extractor/        # 关键词提取模块
│   ├── database/         # 数据库模块
│   ├── analysis/         # 统计分析模块
│   ├── visualization/    # 可视化模块
│   ├── report/           # 报告生成模块
│   ├── config.py         # 配置管理
│   └── main.py           # 主程序入口
├── data/                 # 数据库文件
├── output/
│   ├── figures/          # 生成的图表
│   └── reports/          # 生成的报告
├── requirements.txt
└── README.md
```

## 🚀 快速开始

### 1. 克隆仓库

```bash
git clone https://github.com/YOUR_USERNAME/depthtrender.git
cd depthtrender
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 运行

```bash
# 运行完整流程（所有会议，所有年份）
python -m src.main

# 只处理特定会议和年份
python -m src.main --venue ICLR --year 2024

# 限制论文数量（测试用）
python -m src.main --limit 10

# 使用 KeyBERT 提取器（更准确但较慢）
python -m src.main --extractor keybert

# 跳过爬取，只重新生成报告
python -m src.main --skip-scrape
```

## 📊 输出示例

### 词云图

![词云示例](output/figures/wordcloud_overall.png)

### Top 关键词

![Top 关键词](output/figures/top_keywords.png)

### 趋势图

![趋势图](output/figures/keyword_trends.png)

## ⚙️ 配置

### 会议配置

编辑 `src/config.py` 中的 `VENUES` 字典来添加或修改会议：

```python
VENUES = {
    "ICLR": VenueConfig(
        name="ICLR",
        full_name="International Conference on Learning Representations",
        venue_id_pattern="ICLR.cc/{year}/Conference",
        years=[2024, 2023, 2022, 2021]
    ),
    # 添加更多会议...
}
```

### 提取器配置

```python
EXTRACTOR_CONFIG = ExtractorConfig(
    yake_num_keywords=20,          # YAKE 提取关键词数量
    keybert_top_n=20,             # KeyBERT 提取关键词数量
    default_extractor="yake",     # 默认提取器
)
```

## 🔄 自动更新

项目使用 GitHub Actions 实现自动更新：

- **定时触发**：每周日 UTC 0:00（北京时间周日 8:00）
- **手动触发**：可在 GitHub Actions 页面手动运行

### 配置 Secrets（可选）

如需访问非公开数据，在仓库设置中添加：

- `OPENREVIEW_USERNAME` - OpenReview 账号
- `OPENREVIEW_PASSWORD` - OpenReview 密码

## 📈 支持的会议

| 会议 | 全称 | 年份范围 |
|------|------|----------|
| ICLR | International Conference on Learning Representations | 2021-2024 |
| NeurIPS | Conference on Neural Information Processing Systems | 2021-2024 |
| ICML | International Conference on Machine Learning | 2021-2024 |

## 🛠️ 技术栈

- **数据源**: OpenReview API (`openreview-py`)
- **关键词提取**: YAKE, KeyBERT
- **数据库**: SQLite
- **可视化**: matplotlib, wordcloud
- **自动化**: GitHub Actions

## 📝 开发计划

- [ ] 支持更多会议（CVPR、ACL、AAAI 等）
- [ ] 集成 AI 趋势总结（OpenAI/Gemini API）
- [ ] 添加论文推荐功能
- [ ] 构建 Web 界面
- [ ] 支持中文关键词

## 📄 许可证

MIT License

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！
