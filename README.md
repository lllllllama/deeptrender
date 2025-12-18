# 🔬 DepthTrender

**AI 顶会论文关键词追踪系统** | 实时掌握研究热点与发展趋势

[![Update Keywords](https://github.com/YOUR_USERNAME/depthtrender/actions/workflows/update.yml/badge.svg)](https://github.com/YOUR_USERNAME/depthtrender/actions/workflows/update.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## ✨ 核心特性

| 功能 | 描述 |
|------|------|
| 🌐 **三层架构** | Raw (原始保存) → Structured (结构化) → Analysis (分析层) |
| 🔍 **全网覆盖** | 以 arXiv 为主数据源，OpenAlex 为结构化锚点 |
| 🔑 **智能提取** | YAKE（快速）+ KeyBERT（精准）双引擎 |
| 📊 **深度分析** | 频率统计、趋势追踪、新兴关键词识别 |
| 🎨 **可视化** | 词云、柱状图、趋势折线图、会议对比 |
| 📄 **自动报告** | 生成 Markdown 格式的分析报告 |
| 🤖 **Agent工作流** | Ingestion → Structuring → Analysis 独立智能体协作 |

---

## 📈 支持的会议

<table>
<tr>
<td width="50%">

### 🟢 OpenReview 数据源
| 会议 | 领域 | 年份 |
|------|------|------|
| **ICLR** | 机器学习 | 2021-2025 |
| **NeurIPS** | 机器学习 | 2021-2024 |
| **ICML** | 机器学习 | 2021-2024 |
| **EMNLP** | NLP | 2023-2024 |
| **COLM** | 语言模型 | 2024 |
| **CoRL** | 机器人 | 2022-2024 |
| **LOG** | 图学习 | 2022-2024 |
| **AISTATS** | 统计学习 | 2022-2024 |

</td>
<td width="50%">

### 🔵 Semantic Scholar 数据源
| 会议 | 领域 | 年份 |
|------|------|------|
| **CVPR** | 计算机视觉 | 2021-2024 |
| **ICCV** | 计算机视觉 | 2021, 2023 |
| **ECCV** | 计算机视觉 | 2022, 2024 |
| **ACL** | NLP | 2022-2024 |
| **NAACL** | NLP | 2022, 2024 |
| **AAAI** | 人工智能 | 2022-2024 |
| **IJCAI** | 人工智能 | 2022-2024 |

</td>
</tr>
</table>

---

## 🚀 快速开始

### 安装

```bash
git clone https://github.com/YOUR_USERNAME/depthtrender.git
cd depthtrender
pip install -r requirements.txt
```

### 基础用法

```bash
# 运行完整三阶段工作流（采集 → 结构化 → 分析）
python src/main.py

# 指定会议和年份
python src/main.py --venue ICLR NeurIPS --year 2024

# 限制每阶段处理数量（测试用）
python src/main.py --limit 100
```

### 数据源选择

```bash
# arXiv（最近 7 天的 ML 论文）
python src/main.py --source arxiv --arxiv-days 7

# OpenAlex（结构化元数据）
python src/main.py --source openalex

# OpenReview（ICLR, NeurIPS 等）
python src/main.py --source openreview

# Semantic Scholar（CVPR, ACL 等）
python src/main.py --source s2

# 所有数据源（默认）
python src/main.py --source all
```

### 提取器选择

```bash
# YAKE - 快速，无需模型（默认）
python src/main.py --extractor yake

# KeyBERT - 基于 BERT，更精准
python src/main.py --extractor keybert

# 两者结合
python src/main.py --extractor both
```

### 其他选项

```bash
# 跳过采集阶段，仅运行结构化和分析
python src/main.py --skip-ingestion

# 跳过结构化阶段
python src/main.py --skip-structuring

# 查看帮助
python src/main.py --help
```


---

## 🌐 Web 可视化仪表盘

### 启动服务器

```bash
python src/web/app.py
```

访问 **http://localhost:5000** 查看仪表盘。

### 页面功能

| 页面 | 功能 |
|------|------|
| **首页** | 总览统计、词云、Top 关键词、趋势图 |
| **会议分析** | 单会议词云、年度统计、关键词演变 |
| **趋势追踪** | 多关键词对比、新兴关键词发现 |
| **会议对比** | 雷达图对比、并排 Top-K 排名 |

### 技术栈

- 后端: Flask + REST API
- 前端: 原生 HTML/CSS/JS
- 图表: ECharts 5.x
- 主题: 深色专业风格

---

## 📊 输出示例

运行后将在 `output/` 目录生成：

| 文件 | 说明 |
|------|------|
| `figures/wordcloud_overall.png` | 整体关键词词云 |
| `figures/wordcloud_*.png` | 各会议词云 |
| `figures/top_keywords.png` | Top-K 关键词柱状图 |
| `figures/keyword_trends.png` | 关键词趋势图 |
| `figures/comparison_*.png` | 会议对比图 |
| `reports/report.md` | Markdown 分析报告 |

---

## ⚙️ GitHub Actions 自动化

### 自动触发
- **时间**：每周日 UTC 0:00（北京时间 8:00）
- **内容**：自动爬取、分析、生成报告并提交

### 手动触发
1. 进入 GitHub 仓库 → **Actions** 标签页
2. 选择 **Update Keywords** 工作流
3. 点击 **Run workflow**
4. 可选参数：`venues`、`years`、`limit`

### 配置 Secrets（可选）

在 **Settings → Secrets → Actions** 添加：
- `OPENREVIEW_USERNAME` - OpenReview 账号
- `OPENREVIEW_PASSWORD` - OpenReview 密码

---

## 📁 项目结构

```
depthtrender/
├── .github/workflows/update.yml    # 自动化工作流
├── src/
│   ├── scraper/                   # 多源爬取（OpenReview + S2）
│   ├── extractor/                 # 关键词提取（YAKE + KeyBERT）
│   ├── database/                  # SQLite 存储
│   ├── analysis/                  # 统计分析
│   ├── visualization/             # 图表生成
│   ├── report/                    # 报告生成
│   ├── config.py                  # 配置管理
│   └── main.py                    # 主入口
├── data/keywords.db               # SQLite 数据库
├── output/                        # 生成的图表和报告
├── requirements.txt
└── README.md
```

---

## 🛠️ 技术栈

| 类别 | 技术 |
|------|------|
| **数据源** | OpenReview API, Semantic Scholar API |
| **关键词提取** | YAKE, KeyBERT (Sentence-Transformers) |
| **数据存储** | SQLite |
| **可视化** | Matplotlib, WordCloud |
| **自动化** | GitHub Actions |
| **语言** | Python 3.11+ |

---

## 📝 开发计划

- [x] OpenReview 数据源支持
- [x] Semantic Scholar 数据源支持
- [x] YAKE + KeyBERT 双提取器
- [x] GitHub Actions 自动化
- [ ] 集成 AI 趋势总结（Gemini/OpenAI）
- [ ] Web 仪表盘界面
- [ ] 论文推荐系统
- [ ] 中文关键词支持

---

## 📄 许可证

[MIT License](LICENSE)

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/amazing`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送分支 (`git push origin feature/amazing`)
5. 提交 Pull Request
