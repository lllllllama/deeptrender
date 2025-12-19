# agent.md 执行文档（Playbook）

## 0. 总目标与原则

**目标**：构建长期可信、可扩展的“论文数据基础设施”，而不是一次性分析脚本。
**硬原则**：

1. **Coverage First**：最大化覆盖
2. **Raw Preservation**：Raw 数据永不覆盖、永不删除
3. **结构化 ≠ 分析**：采集/结构化阶段不做趋势判断
4. 处理流：Ingestion → Structuring → Analysis → Visualization，各阶段可独立重复执行

---

## 1. 分层与职责边界

### 1.1 Raw Layer（原始数据层）

**职责**：把每个数据源返回的元数据**尽量完整**落库，保留追溯性。
核心表 `raw_papers`（你现有 agent.md 已定义）

> 关键字段提示：`venue_raw/comments/categories` 在 Raw 层**不解释**（仅保存）

### 1.2 Structured Layer（结构化论文层）

**职责**：把 raw 对齐成“统一的 paper 事实表”，建立 venue/year/domain 等可分析字段。
核心表 `papers` / `paper_sources` / `venues`（你现有 agent.md 已定义）

### 1.3 Analysis Layer（分析特征层）

**职责**：关键词提取、趋势统计、新兴词识别；分析结果必须可缓存（落库），避免重复算。
你已有 `paper_keywords` 与可选 `trend_cache` ，本执行文档会把它升级成更系统的 `analysis_*` 中间态表。

---

# 2. Raw Layer 维护与质量检验（QA）与优化

## 2.1 Raw 写入策略（必须满足“可重跑、可增量”）

**强制：Append-only**

* raw 数据写入只允许 INSERT（或 INSERT OR IGNORE）
* 不允许 UPDATE 覆盖历史 raw

**建议加唯一键（避免重复）**

* `(source, source_paper_id)` 唯一
* 或加 `content_hash = sha1(lower(title)+abstract)` 作为辅助去重

## 2.2 Raw QA 检查清单（每次 Action/本地运行都跑）

### 基础完整性

* title 非空率 ≥ 99%
* abstract 非空率 ≥ 95%（arXiv/S2 应更高）
* year 可解析率 ≥ 99%
* retrieved_at 必填（你 schema 已有）

### 重复与异常

* `(source, source_paper_id)` 重复数 = 0
* title+abstract 哈希重复率可接受（通常 < 3%）；若 > 阈值，提示“跨源重复激增”

### 变化检测（为“避免重复分析”做前置）

* 记录本次 ingestion 的：

  * raw 新增条数
  * raw 最大 retrieved_at
  * per-source 新增条数
    这些将写入 `analysis_meta`（后文定义）用于判断是否需要重跑分析。

## 2.3 Raw 优化建议（资源与稳定性）

* **分源限速/重试**：OpenReview 客户端已具备失败容错与 invitation 兼容逻辑，建议统一封装到 `scraper/*` 的基类里，标准化 retry/backoff。
* **分页与批处理**：一次抓取不要在内存累积过大，边拉边落库。
* **字段原样落库**：例如 comments/categories 在 Raw 仅保存，用于后续结构化识别。

---

# 3. Structured Layer 维护与质量检验（QA）与优化

## 3.1 结构化策略（从 Raw 到 Papers）

Structured 层要解决 3 件事：

1. **去重与归一（canonical_title）**
2. **会议识别（canonical_venue / venue_type）**
3. **多源对齐可追溯（paper_sources）** 

### 建议的“结构化对齐优先级”

* OpenReview（会议权威） > OpenAlex（结构化锚点） > S2（补全） > arXiv（preprint）
  这与 agent.md 的数据源角色定义一致。

## 3.2 Structured QA 检查清单

### 会议识别质量

* `canonical_venue != 'UNKNOWN'` 的比例（分来源统计）
* 对 OpenReview 来源：UNKNOWN 应接近 0（否则 venue_id_pattern/抓取范围可能错）

### 可追溯性

* `papers` 中每条必须至少关联 1 条 `paper_sources`
* `paper_sources.confidence_score` 分布检查（过多 0/1 可能意味着对齐策略过粗）

### 结构化字段一致性

* 同一 `paper_id` 不应出现多版本 abstract（若出现，按优先级来源覆盖，但**Raw 不覆盖**）

## 3.3 Structured 优化建议

* **Title 归一化**：lower、去标点、去多空格；生成 `title_norm` 与 `title_hash`，用来快速对齐
* **可解释置信度**：confidence_score 不要只是一个数字，建议追加 `match_reason`（exact_title / doi / openalex_id / arxiv_id）
* **增量结构化**：只处理新增 raw（通过 raw_id 或 retrieved_at 增量），避免全表重扫

---

# 4. ✅ Analysis 中间态（analysis_*）—最重要

你现在已有 `paper_keywords` 与 `trend_cache`（可选），但它不足以：

* 支撑前端“会议矩阵卡片”快速加载
* 支撑 arXiv 年/周/日多粒度趋势
* 支撑“判断是否需要重算”的元信息闭环

## 4.1 新增分析缓存表（建议 DDL）

### A) 分析元信息（全局）

`analysis_meta`

* key TEXT PRIMARY KEY  （例如: last_raw_max_retrieved_at、last_structured_run_at）
* value TEXT
* updated_at DATETIME

用途：判断是否需要跑 analysis（**避免重复分析的闸门**）

### B) 会议卡片/总览缓存（前端直读）

`analysis_venue_summary`

* venue TEXT
* year INTEGER (可为 NULL 表示全量)
* paper_count INTEGER
* top_keywords_json TEXT  (JSON: [{keyword,count},...])
* emerging_keywords_json TEXT (JSON)
* updated_at DATETIME
* PRIMARY KEY (venue, year)

### C) 关键词趋势缓存（通用）

`analysis_keyword_trends`

* scope TEXT  ('venue' / 'overall' / 'arxiv')
* venue TEXT NULL
* keyword TEXT
* granularity TEXT ('year'/'week'/'day')
* bucket TEXT (year=“2024”, week=“2024-W05”, day=“2024-02-03”)
* count INTEGER
* updated_at DATETIME
* PRIMARY KEY(scope, venue, keyword, granularity, bucket)

### D) arXiv 时间序列缓存（专用，快）

`analysis_arxiv_timeseries`

* category TEXT  (cs.LG/cs.CL/cs.CV/cs.AI/ALL)
* granularity TEXT ('year'/'week'/'day')
* bucket TEXT
* paper_count INTEGER
* top_keywords_json TEXT
* updated_at DATETIME
* PRIMARY KEY(category, granularity, bucket)

> 注：arXiv 的“周趋势”建议使用 ISO week（`YYYY-Www`），避免跨年混乱。

## 4.2 分析执行规则（是否重算）

每次运行 Analysis Agent，先判断：

* `raw_max_retrieved_at` 是否 > `analysis_meta.last_raw_max_retrieved_at`
* 或结构化层新增 `papers` 数是否变化

**无变化**：直接跳过重算（只提供 Web 服务）
**有变化**：按 granularity 增量写入/更新 `analysis_*`

---

# 5. ✅ 拆 arXiv 分析 Agent（年/周/日趋势）

`agent.md` 里明确 arXiv 主要服务 Raw Layer；但你现在的产品需求是把 arXiv 做成“独立趋势基准”。

## 5.1 新增 Agent：ArxivAnalysisAgent

建议模块：

* `src/analysis/arxiv_agent.py`

职责：

1. 统计 paper_count：年/周/日
2. 每个 bucket 下提取 top keywords（可复用 `paper_keywords` 或直接从 raw/structured 过滤抽取）
3. 写入 `analysis_arxiv_timeseries` 与 `analysis_keyword_trends(scope='arxiv')`

### 推荐的输入数据

* 来自 Raw：source='arxiv'（覆盖最快）
* 也可用 Structured：venue_type='preprint'（更统一，但会慢一点）

## 5.2 arXiv API 设计（给前端）

新增 endpoints：

* `GET /api/arxiv/timeseries?granularity=year|week|day&category=cs.LG`
* `GET /api/arxiv/keywords/trends?granularity=week&keyword=diffusion&category=ALL`

---

# 6. ✅ 会议矩阵式前端展示（几乎覆盖会议表）

你 README 中已经列了 OpenReview + Semantic Scholar 覆盖的会议清单；前端应做到：

* **会议“注册表驱动”展示**：即使某会议当前 DB 数据为 0，也能显示卡片（灰态/无数据提示）
* 每个会议卡片有**图标 + 简要统计 + 点击进入详情页**

## 6.1 会议注册表（Registry）统一来源

把“可展示的会议列表”统一为一个 Registry：

* 来自 `src/config.py` 的 VENUES（OpenReview 侧）
* 以及 README 表中的 S2 会议（CVPR/ICCV/ECCV/ACL/NAACL/AAAI/IJCAI）

建议新增：

* `src/config_venues_extra.py`（或合并进 config.py）维护 S2 venues

## 6.2 前端资源与命名约定

目录：

* `src/web/static/assets/venues/ICLR.svg`
* `.../NeurIPS.svg` 等

前端规则：

* icon 路径 = `/static/assets/venues/${venue}.svg`
* 找不到则用默认 `/static/assets/venues/default.svg`

## 6.3 新 API：前端一次拿齐会议矩阵数据

`GET /api/registry/venues`

返回：

* venues: [{name, full_name, domain, years_supported, icon_url, paper_count, latest_year, top_keywords[] }]

其中统计数据来自 `analysis_venue_summary`（快），没有则返回空数组/0。

---

# 7. GitHub Actions：统一爬取→存储→分析→提交（本地 clone 可直接用）

README 已描述 Action 会定时运行并提交结果；你要把它升级为“数据闭环”：

## 7.1 Action 标准流水线

1. Ingestion Agent：抓取增量 raw（arXiv/OpenReview/S2/OpenAlex）
2. Structuring Agent：只处理新增 raw
3. Analysis Agent：

   * 写入 `paper_keywords`
   * 写入 `analysis_*` 缓存表
   * 跑 arXiv 年/周/日并写缓存
4. 输出物：

   * `data/keywords.db`（或拆分为 `data/raw.db + data/analysis.db`）
   * `output/reports/report.md`（可选）
5. Git commit & push（让用户 clone 直接可用）

> 如果 DB 增长很快：建议每周发布一个 `data/snapshot.zip` 到 Release，同时仓库只保留“最近 N 期快照 + 最新 db”，避免仓库膨胀。

## 7.2 本地使用体验（你要求的关键结果）

用户 clone 后：

* `python src/web/app.py`
  前端直接读 `analysis_*`（无需重算）
  若用户想重算：
* `python src/main.py --skip-ingestion --extractor both`（只重算结构化/分析）

---

# 8. 运行与验收（Definition of Done）

你这次升级完成的验收标准建议是：

1. **前端首页出现会议矩阵**：覆盖 README 表会议
2. 点击任一会议卡片：秒开（由 `analysis_venue_summary` 提供）
3. arXiv 页面：

   * 年/周/日三条趋势都能切换
   * 切换 granularity 不触发后端重算（读缓存）
4. Action 连续跑两次：

   * 第二次如果 raw 无新增，analysis 阶段应跳过或极快（由 `analysis_meta` 决策）

---
