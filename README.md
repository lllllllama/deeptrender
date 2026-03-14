# DeepTrender

[中文](#中文说明) | [English](#english)

---

## 中文说明

DeepTrender 是一个面向 AI 论文的关键词追踪与趋势分析项目，覆盖数据采集、结构化存储、关键词提取、趋势分析、Flask API，以及面向 GitHub Pages 的静态站点导出。

### 主要功能

- 多源采集：`arxiv`、`openreview`、`openalex`、`s2`
- 关键词提取：`YAKE`、`KeyBERT`
- 数据存储：SQLite
- Web 服务：Flask REST API + 静态前端
- 静态导出：输出到 `docs/`
- 测试覆盖：数据库、分析、API、静态导出

### 项目结构

```text
deeptrender/
|-- src/
|   |-- agents/
|   |-- analysis/
|   |-- database/
|   |-- extractor/
|   |-- scraper/
|   |-- tools/
|   |-- visualization/
|   |-- web/
|   `-- main.py
|-- tests/
|-- docs/
|-- data/
`-- output/
```

### 环境要求

- Python 3.11+
- 建议使用虚拟环境
- `KeyBERT` 首次运行会下载模型

### 安装

```bash
pip install -r requirements.txt
```

### 运行主流程

```bash
python src/main.py
```

默认行为：

- 采集 `arxiv` 和 `openalex`
- 执行结构化处理
- 执行关键词分析
- 生成图表和 Markdown 报告

### 常用命令

按数据源运行：

```bash
python src/main.py --source arxiv --arxiv-days 7
python src/main.py --source openreview --venue ICLR NeurIPS --year 2024
python src/main.py --source openalex --venue ICLR NeurIPS --year 2024
python src/main.py --source s2 --venue CVPR ACL --year 2024
```

控制提取器或阶段：

```bash
python src/main.py --extractor yake
python src/main.py --extractor keybert
python src/main.py --extractor both
python src/main.py --skip-ingestion
python src/main.py --skip-structuring
python src/main.py --limit 100
```

### Web 界面

启动服务：

```bash
python src/web/app.py
```

默认地址：

```text
http://localhost:5000
```

核心接口：

- `GET /api/health`
- `GET /api/status`
- `GET /api/stats/overview`
- `GET /api/stats/venues`
- `GET /api/stats/venue/<venue>`
- `GET /api/keywords/top`
- `GET /api/keywords/trends`
- `GET /api/keywords/comparison`
- `GET /api/arxiv/timeseries`
- `GET /api/arxiv/emerging`
- `POST /api/refresh`

更多说明见 [docs/API_CONTRACT.md](docs/API_CONTRACT.md) 和 [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)。

### 静态站点导出

```bash
python src/tools/export_static_site.py
```

可选参数：

```bash
python src/tools/export_static_site.py --output-dir dist --top-keywords 100
```

导出的静态站点默认适配 `docs/`，并已使用相对资源路径与 API 路径，以便在 GitHub Pages 子路径下正常工作。

### 测试

运行全部测试：

```bash
pytest -q
```

运行核心测试：

```bash
pytest tests/test_database.py tests/test_web_api.py tests/test_export_static_site.py
```

### 数据与输出

- 数据库：`data/keywords.db`
- 图表：`output/figures/`
- 报告：`output/reports/`
- 静态站点：`docs/`

### 当前说明

- 当前本地测试状态：`89 passed`
- 最近一次高价值修复包括文本编码问题和静态前端根路径依赖问题
- `src/database/repository.py` 仍然偏大，适合后续继续拆分
- 根目录历史总结文档较多，后续可继续收敛到 `README.md` 或 `docs/`

---

## English

DeepTrender is an AI paper keyword tracking and trend analysis project. It covers data ingestion, structured storage, keyword extraction, trend analytics, a Flask API, and static site export for GitHub Pages.

### Highlights

- Multi-source ingestion: `arxiv`, `openreview`, `openalex`, `s2`
- Keyword extraction: `YAKE`, `KeyBERT`
- Storage: SQLite
- Web service: Flask REST API plus static frontend
- Static export: outputs to `docs/`
- Test suite: database, analysis, API, and static export coverage

### Requirements

- Python 3.11+
- Virtual environment recommended
- `KeyBERT` downloads models on first run

### Install

```bash
pip install -r requirements.txt
```

### Run

```bash
python src/main.py
```

### Web UI

```bash
python src/web/app.py
```

Default address:

```text
http://localhost:5000
```

### Static Export

```bash
python src/tools/export_static_site.py
```

### Tests

```bash
pytest -q
```

For more details, see the Chinese section above or the docs in `docs/`.
