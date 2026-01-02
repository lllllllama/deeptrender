# DeepTrender Agent 执行文档（Playbook）

**版本**: v2.0 - arXiv 优化版
**更新时间**: 2025-01-02
**状态**: ✅ 生产就绪

---

## 0. 总目标与原则

**目标**：构建长期可信、可扩展的"论文数据基础设施"，而不是一次性分析脚本。

**硬原则**：

1. **Coverage First**：最大化覆盖
2. **Raw Preservation**：Raw 数据永不覆盖、永不删除
3. **结构化 ≠ 分析**：采集/结构化阶段不做趋势判断
4. **处理流**：Ingestion → Structuring → Analysis → Visualization，各阶段可独立重复执行

---

## 1. 分层与职责边界

### 1.1 Raw Layer（原始数据层）

**职责**：把每个数据源返回的元数据**尽量完整**落库，保留追溯性。

**核心表**：`raw_papers`

**字段说明**：
- `source`: 数据源标识（arxiv/openreview/s2/openalex）
- `source_paper_id`: 源系统的论文ID
- `title`: 论文标题
- `abstract`: 摘要
- `authors`: 作者列表（JSON）
- `year`: 发表年份
- `venue_raw`: 原始会议/期刊名称（不解释）
- `journal_ref`: 期刊引用
- `comments`: 备注信息（可能包含会议信息）
- `categories`: arXiv 分类（如 cs.LG, cs.CV）
- `doi`: DOI
- `raw_json`: 完整原始数据（JSON）
- `retrieved_at`: 采集时间

**关键原则**：
- ✅ Append-only：只允许 INSERT 或 INSERT OR IGNORE
- ✅ 唯一键：`(source, source_paper_id)` 唯一
- ✅ 不解释：`venue_raw/comments/categories` 仅保存，不做解析

---

### 1.2 Structured Layer（结构化论文层）

**职责**：把 raw 对齐成"统一的 paper 事实表"，建立 venue/year/domain 等可分析字段。

**核心表**：
- `papers`: 结构化论文表
- `venues`: 会议/期刊表
- `paper_sources`: 多源对齐表

**结构化策略**：
1. **去重与归一**：生成 `canonical_title`（标准化标题）
2. **会议识别**：识别 `canonical_venue` 和 `venue_type`
3. **多源对齐**：通过 `paper_sources` 表追溯原始数据

**对齐优先级**：
```
OpenReview（会议权威） > OpenAlex（结构化锚点） > S2（补全） > arXiv（preprint）
```

---

### 1.3 Analysis Layer（分析特征层）

**职责**：关键词提取、趋势统计、新兴词识别；分析结果必须可缓存（落库），避免重复算。

**核心表**：
- `paper_keywords`: 论文关键词表
- `analysis_meta`: 分析元信息（用于判断是否需要重算）
- `analysis_venue_summary`: 会议总览缓存
- `analysis_keyword_trends`: 关键词趋势缓存
- `analysis_arxiv_timeseries`: arXiv 时间序列缓存
- `analysis_arxiv_emerging`: arXiv 新兴主题缓存（新增）

**分析执行规则**：
```python
# 判断是否需要重算
if raw_max_retrieved_at > analysis_meta.last_raw_max_retrieved_at:
    # 有新数据，需要重算
    run_analysis()
else:
    # 无新数据，跳过
    skip_analysis()
```

---

## 2. Raw Layer 维护与质量检验（QA）

### 2.1 Raw 写入策略

**强制规则**：
- ✅ Append-only：只允许 INSERT（或 INSERT OR IGNORE）
- ❌ 禁止 UPDATE：不允许覆盖历史 raw 数据

**唯一键约束**：
```sql
UNIQUE(source, source_paper_id)
```

**辅助去重**（可选）：
```python
content_hash = sha1(lower(title) + abstract)
```

### 2.2 Raw QA 检查清单

**基础完整性**：
- ✅ title 非空率 ≥ 99%
- ✅ abstract 非空率 ≥ 95%（arXiv/S2 应更高）
- ✅ year 可解析率 ≥ 99%
- ✅ retrieved_at 必填

**重复与异常**：
- ✅ `(source, source_paper_id)` 重复数 = 0
- ✅ title+abstract 哈希重复率 < 3%

**变化检测**：
- 记录本次 ingestion 的：
  - raw 新增条数
  - raw 最大 retrieved_at
  - per-source 新增条数

### 2.3 Raw 优化建议

**资源与稳定性**：
- 分源限速/重试
- 分页与批处理（边拉边落库）
- 字段原样落库

**arXiv 特殊处理**：
- 遵守 3 秒速率限制
- 保存完整的 categories 字段
- 从 comments 提取会议信息

---

## 3. Structured Layer 维护与质量检验（QA）

### 3.1 结构化策略

**三大任务**：
1. **去重与归一**：生成 `canonical_title`
2. **会议识别**：识别 `canonical_venue` / `venue_type`
3. **多源对齐**：建立 `paper_sources` 关联

**Title 归一化**：
```python
canonical_title = title.lower().strip()
canonical_title = re.sub(r'[^\w\s]', '', canonical_title)
canonical_title = re.sub(r'\s+', ' ', canonical_title)
```

### 3.2 Structured QA 检查清单

**会议识别质量**：
- ✅ `canonical_venue != 'UNKNOWN'` 的比例
- ✅ OpenReview 来源：UNKNOWN 应接近 0

**可追溯性**：
- ✅ `papers` 中每条必须至少关联 1 条 `paper_sources`
- ✅ `paper_sources.confidence_score` 分布合理

**字段一致性**：
- ✅ 同一 `paper_id` 不应出现多版本 abstract

### 3.3 Structured 优化建议

**增量处理**：
- 只处理新增 raw（通过 raw_id 或 retrieved_at 增量）
- 避免全表重扫

**可解释置信度**：
- 追加 `match_reason`（exact_title / doi / openalex_id / arxiv_id）

---

## 4. Analysis Layer - 核心优化 ⭐⭐⭐⭐⭐

### 4.1 分析缓存表设计

#### A) 分析元信息（全局）

**表名**：`analysis_meta`

```sql
CREATE TABLE analysis_meta (
    key TEXT PRIMARY KEY,
    value TEXT,
    updated_at DATETIME
);
```

**用途**：判断是否需要跑 analysis（避免重复分析的闸门）

**关键 keys**：
- `last_raw_max_retrieved_at`: 上次间
- `last_structured_run_at`: 上次结构化运行时间
- `last_analysis_run`: 上次分析运行时间
- `last_paper_count`: 上次统计的论文数
- `arxiv_last_run_{category}_{granularity}`: arXiv 分析运行时间
- `arxiv_last_retrieved_{category}_{granularity}`: arXiv 数据最大时间

#### B) 会议卡片/总览缓存

**表名**：`analysis_venue_summary`

```sql
CREATE TABLE analysis_venue_summary (
    venue TEXT,
    year INTEGER,  -- NULL 表示全量
    paper_count INTEGER,
    top_keywords_json TEXT,  -- JSON: [{keyword, count}, ...]
    emerging_keywords_json TEXT,  -- JSON: [keyword, ...]
    updated_at DATETIME,
    PRIMARY KEY (venue, year)
);
```

**用途**：前端直读，秒开会议卡片

#### C) 关键词趋势缓存

**表名**：`analysis_keyword_trends`

```sql
CREATE TABLE analysis_keyword_trends (
    scope TEXT,  -- 'venue' / 'overall' / 'arxiv'
    venue TEXT,  -- NULL for overall/arxiv
    keyword TEXT,
    granularity TEXT,  -- 'year' / 'week' / 'day'
    bucket TEXT,  -- '2024' / '2024-W05' / '2024-02-03'
    count INTEGER,
    updated_at DATETIME,
    PRIMARY KEY(scope, venue, keyword, granularity, bucket)
);
```

**用途**：支持多粒度关键词趋势查询

#### D) arXiv 时间序列缓存

**表名**：`analysis_arxiv_timeseries`

```sql
CREATE TABLE analysis_arxiv_timeseries (
    category TEXT,  -- 'cs.LG' / 'cs.CL' / 'cs.CV' / 'cs.AI' / 'ALL'
 arity TEXT,  -- 'year' / 'week' / 'day'
    bucket TEXT,  -- '2024' / '2024-W05' / '2024-02-03'
    paper_count INTEGER,
    top_keywords_json TEXT,  -- JSON: [{keyword, count}, ...]
    updated_at DATETIME,
    PRIMARY KEY(category, granularity, bucket)
);
```

**用途**：arXiv 专用，快速加载时间序列

**注意**：周趋势使用 ISO week（`YYYY-Www`），避免跨年混乱

#### E) arXiv 新兴主题缓存（新增）

**表名**：`analysis_arxiv_emerging`

```sql
CREATE TABLE analysis_arxiv_emerging (
    category TEXT,
    keyword TEXT,
    growth_rate REAL,  -- 增长率（环比/同比）
    first_seen TEXT,  -- 首次出现时间
    recent_count INTEGER,  -- 最近出现次数
    trend TEXT,  -- 'rising' / 'stable' / 'declining'
    updated_at DATETIME,
    PRIMARY KEY(category, keyword)
);
```

**用途**：识别快速增长的研究主题

### 4.2 分析执行规则

**判断逻辑**：
```python
def should_run_analysis():
    # 获取当前 raw 最大时间
    current_max = get_max_retrieved_at()

    # 获取上次分析时的 raw 最大时间
    last_max = analysis_meta.get('last_raw_max_retrieved_at')

    # 判断是否有新数据
    if current_max > last_max:
        return True  # 有新数据，需要重算

    # 检查结构化层是否有变化
    current_paper_count = count_papers()
    last_paper_count = analysis_meta.get('last_paper_count')

    if current_paper_count != last_paper_count:
        return True  # 论文数变化，需要重算

    return False  # 无变化，跳过
```

**执行流程**：
```
1. 检查是否需要重算 (should_run_analysis)
2. 如果需要：
   a. 提取关键词 (paper_keywords)
   b. 生成会议总览 (analysis_venue_summary)
   c. 生成关键词趋势 (analysis_keyword_trends)
   d. 生成 arXiv 时间序列 (analysis_arxiv_timeseries)
   e. 识别新兴主题 (analysis_arxiv_emerging)
   f. 更新元信息 (analysis_meta)
3. 如果不需要：
   - 直接返回，提供 Web 服务
```

---

## 5. arXiv 分析 Agent - 重点优化 ⭐⭐⭐⭐⭐

### 5.1 ArxivAnalysisAgent 职责

**模块**：`src/analysis/arxiv_agent.py`

**核心职责**：
1. 统计 paper_count：年/周/日
2. 每个 bucket 提取 top keywords
3. 写入 `analysis_arxiv_timeseries`
4. 写入 `analysis_keyword_trends(scope='arxiv')`
5. 识别新兴主题 → `analysis_arxiv_emerging`

### 5.2 关键词提取优化

**当前问题**：
- ❌ 仅基于标题词频，质量较低
- ❌ 停用词过滤不够完善
- ❌ 未利用 abstract 和已有的 paper_keywords

**优化方案**：
```python
def _extract_bucket_keywords(self, papers, limit=10):
    """
    增强版关键词提取

    优先级：
    1. 使用 paper_keywords 表中已提取的关键词（最优）
    2. 使用 YAKE 从 title + abstract 提取（次优）
    3. 使用词频统计（兜底）
    """

    # 方案1：从 paper_keywords 表获取
    keywords_from_db = self._get_keywords_from_db(papers)
    if keywords_from_db:
        return keywords_from_db

    # 方案2：使用 YAKE 提取
    keywords_from_yake = self._extract_with_yake(papers)
    if keywords_from_yake:
        return keywords_from_yake

    # 方案3：词频统计（兜底）
    return self._extract_with_frequency(papers)
```

**改进的停用词列表**：
```python
STOPWORDS = {
    # 基础停用词
    'a', 'an', 'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
    'of', 'with', 'by', 'from', 'is', 'are', 'was', 'were', 'be', 'been',

    # 学术常用词
    'paper', 'study', 'analysis', 'approach', 'method', 'methods',
    'model', 'models', 'learning', 'network', 'networks', 'neural',
    'deep', 'data', 'using', 'via', 'based', 'novel', 'new', 'towards',

    # 数字和单字符
    # 通过正则过滤：r'^\d+$' 和 }
```

**过滤规则**：
```python
def is_valid_keyword(keyword):
    # 过滤纯数字
    if re.match(r'^\d+$', keyword):
        return False

    # 过滤单字符
    if len(keyword) <= 2:
        return False

    # 过滤停用词
    if keyword.lower() in STOPWORDS:
        return False

    # 过滤特殊字符
    if not re.match(r'^[a-zA-Z][a-zA-Z\s-]*$', keyword):
        return False

    return True
```

### 5.3 新增功能

#### A) 跨分类对比

```python
def compare_categories(
    self,
    categories: List[str],
    granularity: str = "year"
) -> Dict:
    """
    对比多个分类的趋势

    Returns:
             "categories": ["cs.LG", "cs.CV"],
            "timeseries": {
                "cs.LG": [...],
                "cs.CV": [...]
            },
            "overlap": {
                "keywords": ["transformer", "attention"],
                "overlap_rate": 0.35
            },
            "unique": {
                "cs.LG": ["reinforcement", "policy"],
                "cs.CV": ["segmentation", "detection"]
            }
        }
    """
```

###兴主题识别

```python
def detect_emerging_topics(
    self,
    category: str = "ALL",
    threshold: float = 1.5  # 增长率阈值
) -> List[Dict]:
    """
    识别新兴研究主题

    算法：
    1. 计算关键词的环比增长率
    2. 识别突然出现的新关键词
    3. 分析关键词组合（co-occurrence）

    Returns:
        [
            {
                "keyword": "multimodal learning",
                "growth_rate": 2.5,
                "first_seen": "2024-W10",
                "recent_count": 15,
                "trend": "rising"
            },
            ...
        ]
    """
```

### 5.4 API 设计

**新增 endpoints**：

```python
# 1. 时间序列（已有）
GET /api/arxiv/timeseries?granularity=year|week|day&category=cs.LG

# 2. 关键词趋势（已有）
GET /api/arxiv/keywords/trends?granularity=week&keyword=diffusion&category=ALL

# 3. 统计概览（新增）
GET /api/arxiv/stats
Response: {
    "total_papers": 84,
    "categories": {
        "cs.LG": 46,
        "cs.CV": 29,
        ...
    },
    "date_range": {
        "min": "2023-01-01",
        "max": "2025-12-16"
    },
    "latest_update": "2025-12-19T10:24:55"
}

# 4. 分类对比（新增）
GET /api/arxiv/compare?categories=cs.LG,cs.CV&granularity=year
Response: {
    "categories": ["cs.LG", "cs.CV"],
    "timeseries": {...},
    "overlap": {...},
    "unique": {...}
}

# 5. 新兴主题（新增）
GET /api/arxiv/emerging?category=ALL&limit=20
Response: [
    {
        "keyword": "multimodal learning",
        "growth_rat,
        "trend": "rising",
        ...
    },
    ...
]

# 6. 论文列表（新增）
GET /api/arxiv/papers?category=cs.LG&limit=20&offset=0
Response: {
    "total": 46,
    "papers": [
        {
            "arxiv_id": "2312.12345",
            "title": "...",
            "abstract": "...",
            "categories": ["cs.LG", "cs.AI"],
            "year": 2025,
            "retrieved_at": "2025-12-16",
            "keywords": ["transformer", "attention"]
        },
        ...
    ]
}

# 7. 论文详情（新增）
GET /api/arxiv/paper/<arxiv_id>
Response: {
    "arxiv_id": "2312.12345",
    "title": "...",
    "abstract": "...",
    "authors": [...],
    "categories": [...],
    "year": 2025,
    "pdf_url": "...",
    "keywords": [...],
    "related_papers": [...]
}
```

---

## 6. 会议矩阵式前端展示

### 6.1 会议注册表（Registry）

**来源**：
- `src/config.py` 的 VENUES（OpenReview 侧）
- README 表中的 S2 会议（CVPR/ICCV/ECCV/ACL/NAACL/AAAI/IJCAI）

**前端资源**：
```
src/web/static/assets/venues/
├── ICLR.svg
├── NeurIPS.svg
├── CVPR.svg
├── default.svg
└── ...
```

**API**：
```
GET /api/registry/venues
Response: {
    "venues": [
        {
            "name": "ICLR",
            "full_name": "International Conference on Learning Representations",
            "domain": "ML",
            "years_supported": [2021, 2022, 2023, 2024, 2025],
            "icon_url": "/static/assets/venues/ICLR.svg",
            "paper_count": 30,
            "latest_year": 2024,
            "top_keywords": [...]
        },
        ...
    ]
}
```

---

## 7. GitHub Actions 自动化

### 7.1 标准流水线

```yaml
name: Update Keywords

on:
  schedule:
    - cron: '0 0 * * 0'  # 每周日 UTC 0:00
  workflow_dispatch:

jobs:
  update:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v3

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run Ingestion
        run: python src/main.py --source all --limit 1000

      - name: Run Analysis
        run: python src/main.py --skiion --extractor both

      - name: Run arXiv Analysis
        run: python -c "from analysis import ArxivAnalysisAgent; ArxivAnalysisAgent().run_all_granularities(force=True)"

      - name: Commit and Push
        run: |
          git config user.name "GitHub Actions"
          git config user.email "actions@github.com"
          git add data/ output/
          git commit -m "chore: auto-update keywords [$(date +%Y-%m-%d)]" || exit 0
          git push
```

### 7.2 本地使用体验

**用户 clone 后**：
```bash
# 1. 直接启动 Web 服务（无需重算）
python src/web/app.py

# 2. 如果想重算分析
python src/main.py --skip-ingestion --extracn
# 3. 如果想重新采集数据
python src/main.py --source arxiv --arxiv-days 30
```

---

## 8. 运行与验收（Definition of Done）

### 8.1 功能验收

**前端**：
- ✅ 首页出现会议矩阵
- ✅ 点击会议卡片秒开
- ✅ arXiv 页面支持年/周/日切换
- ✅ 切换 granularity 不触发后端重算

**后端**：
- ✅ 所有 API 正常响应
- ✅ 缓存机制正常工作
- ✅ QA 检查通过率 > 95%

**性能**：
- ✅ 页面加载时间 < 2s
- ✅ API 响应时间 < 500ms
- ✅ 分析任务执行时间 < 30s

### 8.2 数据质量验收

**Raw Layer**：
- ✅ title 非空率 ≥ 99%
- ✅ abstract 非空率 ≥ 95%
- ✅ 无重复数据

**Analysis Layer**：
- ✅ 关键词质量提升（无纯数字）
- ✅ 缓存数据完整
- ✅ 元信息正确更新

### 8.3 用户体验验收

- ✅ UI 交互流畅
- ✅ 数据可视化清晰
- ✅ 错误提示友好
- ✅ 支持移动n
## 9. 维护与监控

### 9.1 日常维护

**每周**：
- 检查 GitHub Actions 运行状态
- 查看数据增长情况
- 检查 QA 报告

**每月**：
- 清理过期缓存
- 优化数据库索引
- 更新会议列表

### 9.2 监控指标

**数据指标**：
- Raw 层数据量
- Structured 层数据量
- Analysis 层缓存命中率

**性能指标**：
- API 响应时间
- 页面加载时间
- 分析任务执行时间

**质量指标**：
- QA 检查通过率
- 数据完整性
- 用户反馈

---

## 10. 附录

### 10.1 常用命令

```bash
# 运行完整流水线
python src/main.py

# 只运行 arXiv 采集
python src/main.py --source arxiv --arxiv-days 7

# 只运行分析
python src/main.py --skip-ingestion --extractor both

# 运行 arXiv 分析
python -c "from analysis import ArxivAnalysisAgent; ArxivAnalysisAgent().run_all_granularities(force=True)"

# 运行 QA 检查
python src/dq_arxiv.py

# 启动 Web 服务
python src/web/app.py
```

### 10.2 故障排查

**问题1：缓存未更新**
```bash
# 强制刷新缓存
python -c "from analysis import ArxivAnalysisAgent; ArxivAnalysisAgent().run_all_granularities(force=True)"
```

**问题2：API 返回空数据**
```bash
# 检查数据库
sqlite3 data/keywords.db "SELECT COUNT(*) FROM analysis_arxiv_timeseries;"

# 重新运行分析
python src/main.py --skip-ingestion
```

**问题3：关键词质量差**
```bash
# 检查 paper_keywords 表
sqlite3 data/keywords.db "SELECT COUNT(*) FROM paper_keywords;"

# 重新提取关键词
python src/main.py --skip-ingestion --extractor both
```

---

**文档版本**: v2.0
**最后更新**: 2025-01-02
**维护者**: DeepTrender Team
**状态**: ✅ 生产就绪
