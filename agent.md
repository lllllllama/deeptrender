# agent.md

## Research Data Agent Design for Large-Scale Paper Ingestion & Trend Analysis

---

## 1. Agent 角色定义（Role Definition）

本项目中的 **Data Agent** 负责以下核心职责：

1. **最大化获取学术论文数据（Coverage First）**
2. **完整保存原始数据，确保可追溯性（Raw Preservation）**
3. **对原始数据进行结构化处理，而非在采集阶段做分析判断**
4. **为后续分析、趋势建模和可视化提供稳定的数据基础**

> Agent 的目标不是“立即分析”，
> 而是 **构建一个长期可信、可扩展的学术数据基础设施**。

---

## 2. 设计原则（Design Principles）

### 2.1 数据优先（Data-First）

* 所有分析都应建立在**已结构化的数据之上**
* 不在采集阶段进行会议、质量、趋势判断

### 2.2 原始数据不可丢失（Raw Data Is Sacred）

* 所有从数据源获得的字段必须完整保存
* 原始数据 **永不覆盖、永不删除**

### 2.3 分层解耦（Layered Architecture）

```
Raw Ingestion Layer
→ Structured Paper Layer
→ Analysis Feature Layer
→ Visualization Layer
```

---

## 3. 数据源选择方案（Data Source Selection）

### 3.1 数据源选择目标

| 目标  | 说明                    |
| --- | --------------------- |
| 覆盖面 | 尽量多的 AI 相关论文          |
| 可持续 | API 稳定、长期可用           |
| 自动化 | 支持程序化拉取               |
| 合规  | 不使用违规爬虫               |
| 元数据 | 至少包含 title + abstract |

---

### 3.2 核心数据源（Primary Sources）

#### 3.2.1 arXiv

**角色：原始论文数据池（Raw Paper Reservoir）**

* 覆盖最广
* 更新最快
* 提供高质量摘要
* 不区分会议（这是设计特性，而非缺点）

**使用策略**：

* 按领域采集（cs.CV / cs.CL / cs.LG / cs.AI）
* 不做会议筛选
* 仅用于 Raw Layer

---

#### 3.2.2 OpenAlex

**角色：结构化锚点（Structured Anchor Source）**

* 提供论文与会议（venue）的结构化关系
* 免费、开放
* 支持大规模批量访问

**使用策略**：

* 用于会议识别与校验
* 用于补充 DOI、venue_id 等字段

---

### 3.3 增强数据源（Secondary Sources）

#### 3.3.1 Semantic Scholar

**角色：补充与对齐源（Metadata Enrichment & Alignment）**

* 用于补全摘要、引用信息
* 用于跨源对齐（arXiv ↔ DOI ↔ OpenAlex）

---

#### 3.3.2 OpenReview

**角色：顶会权威确认源（Conference Ground Truth）**

* 仅用于 ICLR / NeurIPS / ICML 等 ML 顶会
* 用于确认会议与年份的准确性

---

### 3.4 辅助数据源（Support Sources）

#### 3.4.1 DBLP

**角色：会议结构字典（Conference Dictionary）**

* 不用于 NLP
* 用于维护会议标准名称、年份范围

---

### 3.5 明确不采用的数据源

* Google Scholar（无官方 API，不可持续）
* 会议官网爬虫（高维护成本）
* 出版商 API（摘要缺失、授权复杂）

---

## 4. 存储结构设计（Storage Architecture）

### 4.1 总体结构

```
┌──────────────────┐
│  Raw Layer       │
│  raw_papers      │
└──────────────────┘
          ↓
┌──────────────────┐
│ Structured Layer │
│ papers           │
│ paper_sources    │
│ venues           │
└──────────────────┘
          ↓
┌──────────────────┐
│ Analysis Layer   │
│ paper_keywords   │
│ trend_cache      │
└──────────────────┘
```

---

## 5. Raw Layer（原始数据层）

### 5.1 表：`raw_papers`

```sql
raw_papers
----------
raw_id              INTEGER PRIMARY KEY
source              TEXT        -- arxiv / openalex / s2 / openreview
source_paper_id     TEXT
title               TEXT
abstract            TEXT
authors             TEXT        -- JSON / raw string
year                INTEGER
venue_raw           TEXT
journal_ref         TEXT
comments            TEXT
categories           TEXT
doi                 TEXT
retrieved_at        DATETIME
```

**说明**：

* 不解释 venue_raw
* comments 用于后续会议识别（如 “Accepted at CVPR”）
* categories 用于领域粗筛

---

## 6. Structured Layer（结构化论文层）

### 6.1 表：`papers`

```sql
papers
------
paper_id            INTEGER PRIMARY KEY
canonical_title     TEXT
abstract            TEXT
year                INTEGER
canonical_venue     TEXT        -- CVPR / ICML / UNKNOWN
venue_type          TEXT        -- conference / journal / preprint
domain              TEXT        -- CV / NLP / ML / RL
quality_flag        TEXT        -- accepted / unknown / filtered
created_at          DATETIME
```

---

### 6.2 表：`paper_sources`

```sql
paper_sources
-------------
paper_id
raw_id
source
confidence_score
```

**作用**：

* 支持多源对齐
* 可回溯每篇论文的来源
* 支持调试与审计

---

### 6.3 表：`venues`

```sql
venues
------
venue_id
canonical_name      -- CVPR
full_name
domain
first_year
last_year
```

---

## 7. Analysis Layer（分析特征层）

### 7.1 表：`paper_keywords`

```sql
paper_keywords
--------------
paper_id
keyword
method              -- yake / keybert / llm
score
```

> 关键词是 **分析产物**，不是原始属性。

---

### 7.2 表（可选）：`trend_cache`

```sql
trend_cache
-----------
keyword
venue
year
count
```

用于加速 Web 可视化。

---

## 8. 数据处理流程（Agent Workflow）

```
[Ingestion Agent]
    ↓
raw_papers
    ↓
[Structuring Agent]
    ↓
papers + paper_sources
    ↓
[Analysis Agent]
    ↓
paper_keywords / trends
```

每一阶段 **可独立重复执行**。

---

## 9. 升级与扩展路径（Evolution Plan）

### 阶段 1

* arXiv + OpenAlex
* raw_papers 表
* 不做分析

### 阶段 2

* 加入会议识别逻辑
* 填充 papers 表

### 阶段 3

* 接入关键词提取
* 趋势分析与可视化

### 阶段 4（可选）

* LLM 辅助会议/领域分类
* 引文网络分析

---

## 10. 关键设计总结（Key Takeaways）

* **Raw Layer 是系统最重要的资产**
* 数据源各司其职，没有“万能源”
* 结构化 ≠ 分析
* 趋势可信度来自数据治理，而非模型复杂度

---

## 11. 一句话总结（Agent Philosophy）

> **A reliable research trend system is not built on clever models,
> but on disciplined data ingestion, preservation, and structuring.**
