# 🔬 DeepTrender

**AI 顶会论文关键词追踪系统** | 实时掌握研究热点与发展趋势

[![Update Keywords](https://github.com/YOUR_USERNAME/deeptrender/actions/workflows/update.yml/badge.svg)](https://github.com/YOUR_USERNAME/deeptrender/actions/workflows/update.yml)
[![Test Pipeline](https://github.com/YOUR_USERNAME/deeptrender/actions/workflows/test.yml/badge.svg)](https://github.com/YOUR_USERNAME/deeptrender/actions/workflows/test.yml)
[![Codecov](https://img.shields.io/codecov/c/github/YOUR_USERNAME/deeptrender)](https://codecov.io/gh/YOUR_USERNAME/deeptrender)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](https://www.docker.com/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 📖 目录
- [✨ 核心特性](#-核心特性)
- [🏗️ 系统架构](#️-系统架构)
- [📈 支持的会议](#-支持的会议)
- [🚀 快速开始](#-快速开始)
- [🌐 Web 可视化仪表盘](#-web-可视化仪表盘)
- [📊 输出示例](#-输出示例)
- [⚙️ GitHub Actions 自动化](#-github-actions-自动化)
- [📁 项目结构](#-项目结构)
- [🛠️ 技术栈](#️-技术栈)
- [⚡ 性能指标](#-性能指标)
- [🔧 常见问题](#-常见问题)
- [📝 开发计划](#-开发计划)
- [📄 许可证](#-许可证)
- [🤝 贡献](#-贡献)

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

## 🏗️ 系统架构

DeepTrender 采用解耦的三层架构，通过独立的 Agent 协作完成从数据采集到洞察生成的全过程。

```mermaid
graph TD
    subgraph Data_Sources [数据源]
        A1[arXiv]
        A2[OpenReview]
        A3[OpenAlex]
        A4[Semantic Scholar]
    end

    subgraph Core_Engine [核心引擎]
        B1[Ingestion Agent<br/>(原始层)]
        B2[Structuring Agent<br/>(结构化层)]
        B3[Analysis Agent<br/>(分析层)]
    end

    subgraph Outputs [输出形式]
        C1[Web Dashboard]
        C2[Static Reports]
        C3[Visualizations]
        C4[REST API]
    end

    A1 & A2 & A3 & A4 --> B1
    B1 --> B2
    B2 --> B3
    B3 --> C1 & C2 & C3 & C4
```

- **原始层 (Raw Layer)**: 负责多源异步爬取，保持原始数据完整性。
- **结构化层 (Structured Layer)**: 利用 OpenAlex 锚点进行元数据清洗与关键词智能提取。
- **分析层 (Analysis Layer)**: 执行频率统计、趋势挖掘与新兴热点识别。

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

### Docker 安装 (推荐)

如果您安装了 Docker，可以使用以下命令快速启动：

```bash
# 构建并启动所有服务（包括 Web 仪表盘）
docker-compose up -d
```

访问 `http://localhost:5000` 即可查看运行中的系统。

### 本地安装

```bash
git clone https://github.com/YOUR_USERNAME/deeptrender.git
cd deeptrender
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

---

## 🌐 Web 可视化仪表盘

### 启动服务器

```bash
python src/web/app.py
```

访问 **http://localhost:5000** 查看仪表盘。

### 静态站点导出

DeepTrender 支持将仪表盘导出为完全静态的 HTML 站点，非常适合部署到 GitHub Pages。

```bash
python src/tools/export_static_site.py
```

导出的文件将保存在 `dist/` 目录下。

### 界面预览

<table>
<tr>
<td width="50%" align="center">
<img src="https://via.placeholder.com/600x400/1a1a2e/eee?text=Dashboard+Home" alt="Dashboard Home" width="100%"/>
<br/>
<b>仪表盘主页</b>
</td>
<td width="50%" align="center">
<img src="https://via.placeholder.com/600x400/1a1a2e/eee?text=Conference+Comparison" alt="Conference Comparison" width="100%"/>
<br/>
<b>会议对比视图</b>
</td>
</tr>
<tr>
<td width="50%" align="center">
<img src="https://via.placeholder.com/600x400/1a1a2e/eee?text=Trend+Tracking" alt="Trend Tracking" width="100%"/>
<br/>
<b>趋势追踪</b>
</td>
<td width="50%" align="center">
<img src="https://via.placeholder.com/600x400/1a1a2e/eee?text=Keyword+Analysis" alt="Keyword Analysis" width="100%"/>
<br/>
<b>关键词分析</b>
</td>
</tr>
</table>

> 💡 **提示**: 实际部署后，可将上述占位图替换为真实截图。建议截图尺寸为 1200x800 像素。

### REST API

系统提供完整的 REST API 接口，方便集成到其他系统。详细的 API 文档可通过访问本地服务器的 `/api/status` 或相关路由获取。

| 类别 | 路由 | 描述 |
|------|------|------|
| **统计** | `/api/stats/overview` | 总览统计数据 |
| **会议** | `/api/stats/venues` | 各会议概览 |
| **关键词** | `/api/keywords/top` | Top-K 关键词排名 |
| **趋势** | `/api/keywords/trends` | 关键词历史趋势 |
| **新兴** | `/api/arxiv/emerging` | arXiv 新兴主题发现 |

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

### 🤖 自动触发
- **时间**：每周日 UTC 0:00（北京时间 8:00）
- **内容**：自动爬取、分析、生成报告并提交
- **超时**：60分钟
- **缓存**：Python依赖 + Sentence-Transformers模型

---

## 📁 项目结构

```
deeptrender/
├── .github/workflows/update.yml    # 自动化工作流
├── src/
│   ├── scraper/                   # 多源爬取（OpenReview + S2 + arXiv）
│   ├── extractor/                 # 关键词提取（YAKE + KeyBERT）
│   ├── database/                  # SQLite 存储
│   ├── analysis/                  # 统计分析 (Ingestion/Structuring/Analysis Agent)
│   ├── visualization/             # 图表生成
│   ├── report/                    # 报告生成
│   ├── web/                       # Flask Web 仪表盘
│   ├── tools/                     # 工具脚本 (静态导出等)
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
| **数据源** | OpenReview, Semantic Scholar, OpenAlex, arXiv |
| **关键词提取** | YAKE, KeyBERT (Sentence-Transformers) |
| **后端** | Flask (Python 3.11+), REST API |
| **前端** | HTML5, Vanilla CSS, ECharts 5.x |
| **存储** | SQLite |
| **自动化** | GitHub Actions |

---

## ⚡ 性能指标

- **处理速度**: 约 100 篇论文/分钟 (YAKE) / 15 篇论文/分钟 (KeyBERT)
- **数据库容量**: 支持百万级论文元数据存储
- **系统要求**:
    - CPU: 2核+ (推荐 4核)
    - 内存: 4GB+ (KeyBERT 推荐 8GB+)
    - 存储: 1GB+ 可用空间

---

## 🔧 常见问题

| 问题 | 解决方案 |
|------|------|
| **OpenReview API 超时** | 尝试减小 `--limit` 参数，或检查网络连接。 |
| **数据库锁定 (Database Locked)** | 确保没有多个进程同时写入 `keywords.db`，或者重启服务。 |
| **图表中文字符显示异常** | 系统需要安装 `SimHei` 或 `Arial` 字体。在 Linux 上可安装 `fonts-wqy-microhei`。 |
| **KeyBERT 安装/运行缓慢** | KeyBERT 依赖预训练模型，首次运行需下载约 400MB 模型，处理耗时 5-10 分钟属正常现象。 |

---

## 📝 开发计划

- [x] OpenReview 数据源支持
- [x] Semantic Scholar 数据源支持
- [x] YAKE + KeyBERT 双提取器
- [x] GitHub Actions 自动化
- [x] Web 仪表盘界面
- [x] CCF Registry 集成
- [x] 静态站点生成 (Static Site Generation)
- [ ] 集成 AI 趋势总结 (Gemini/OpenAI)
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
