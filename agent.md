下面我按你“短期可落地成品”的目标（**arXiv 日/月/年趋势 + 会议关键词趋势排行 + 搜索/筛选关键词 + GitHub Actions 定时更新 + GitHub Pages 一键打开**）给出：

1. **大致规划（能完全实现）**
2. **任务划分（按依赖顺序）**
3. **每个任务可直接丢给 AI 的“详细提示词”（包含修改/实施/测试/验收）**
   并把**必须人工**的部分尽量放到最后。

---

## 一、MVP 大致规划（可完全实现）

### 目标产物（你说的“打开网页就能看”）

* 一个 GitHub Pages 网站（静态）：

  * **arXiv 趋势**：按 *year / month / day* 切换；支持 category（cs.LG/cs.CV/…）筛选；展示 Top keywords 排行与变化
  * **会议趋势**：选择会议（尽量覆盖 CCF 列表），展示 *year* 维度的关键词排行与趋势折线
  * **关键词搜索**：在 arXiv 与会议页面都能搜索关键词（在“可用关键词索引”范围内），查看数量曲线 + rank
* GitHub Actions 每天跑：

  * 拉取最近 N 天 arXiv（你 workflow 里已有 `--arxiv-days` 默认 7，见 `.github/workflows/update.yml` ）
  * 更新数据库（SQLite）与分析缓存
  * 导出静态 JSON 数据到 `docs/data/`，并把页面/资源拷贝到 `docs/`（供 Pages 直接托管）
  * 自动 commit 回仓库（你 workflow 已会 commit `data/ output/` ，我们扩展为也提交 `docs/`）

### 关键实现策略（为了“快落地、偏差不大、可长期维护”）

* **数据层**：真实、实时、可用即可（你要求），重点保证时间轴统计正确

  * arXiv 趋势用 **published**（论文真正发布时间）做 bucket，而不是 retrieved_at（你现在的 API 与分析缓存是有的，但要确认 arXiv 分析是否用对时间字段）
* **分析层**：不追求完美语义理解，追求“趋势偏差不大”

  * 关键词抽取用你项目已经集成的 **YAKE/KeyBERT/both**（`requirements.txt` 已包含 ，`config.py` 默认 extractor 可选 ）
* **可视化层**：静态 JSON + 前端渲染（避免后端部署复杂度）
* **会议覆盖**：用“会议注册表（registry）”管理（CCF 列表靠你提供/导入），爬取源可分层：

  * OpenReview（你 config 里已有 VENUES，且 web API 会从 config 读 ）
  * Semantic Scholar / OpenAlex 作为补充（你的 README 已声明支持 S2 会议如 CVPR/ACL/AAAI 等 ）
  * 短期先实现：**CCF 列表 → 注册表 → 作为“展示与筛选的会议全集”**；数据抓取先覆盖“能抓到的部分”，抓不到的标记为 pending（这样能尽快上线，后续再补齐映射与抓取策略）

---

## 二、任务划分（按依赖顺序）

> 你可以把每个任务交给 AI 独立执行（一次一个任务），做完你只需要做最后的“人工步骤”，项目就能跑起来并上线可用。

1. **T0 基线检查**：本地可跑、测试可跑、Actions 可跑（最小改动前的安全网）
2. **T1 arXiv 时间轴正确化 + 增加 month 粒度**（year/month/day 三档必须准）
3. **T2 arXiv 关键词抽取与清洗统一**（用现有 extractor 管线，保证一致、可控、可复现）
4. **T3 生成 “可静态化” 的 arXiv 缓存**（timeseries/top keywords/keyword index）
5. **T4 会议侧：引入 CCF 会议注册表（registry）**（先把“尽可能多会议”组织起来）
6. **T5 会议侧：生成可静态化缓存（按会议/年份的 top 与趋势）**
7. **T6 静态站点导出脚本**：把 API 输出“落盘”为 `docs/data/*.json` + 拷贝静态页面到 `docs/`
8. **T7 前端适配 GitHub Pages**：API 调用改为读本地 JSON；路径改相对；新增搜索/筛选交互
9. **T8 GitHub Actions 扩展**：workflow 跑完后导出 docs 并 commit；提供手动参数（tier/venues）
10. **T9 回归测试补齐**：新增单测（bucket/月粒度/导出 json 结构），保证长期可维护

---

## 三、每个任务的“详细 AI 提示词”（可直接复制给 AI）

> 下面每段都是你可以直接粘贴给 AI（比如开新对话/新 agent）的“任务卡”。
> 每张卡都要求：**先读代码 → 再改 → 再测试 → 给出验收方式**。

---

### ✅ T0 基线检查（先立规矩，后面才不会炸）

**AI 提示词：**

> 你现在在一个名为 deeptrender 的 Python 项目仓库里工作。目标：在不改变功能的前提下，建立“可重复”的本地运行与测试基线。
> **请你先完成：**
>
> 1. 阅读并总结目前的运行入口：`src/main.py`、`src/web/app.py`、`.github/workflows/update.yml`（workflow 里已经会运行 `python src/main.py` 并提交 `data/ output/`，见 update.yml）。
> 2. 给出本地一键运行命令（venv/依赖/初始化数据库/跑一次 pipeline/启动 web）。
> 3. 运行并通过 pytest（项目已经有 `tests/`、`pytest.ini`、依赖里有 pytest ）。
> 4. 输出一个“基线检查清单”：后续每个任务改动后都必须跑哪些命令验证。
>    **约束：**不引入新依赖；不改业务代码；只允许新增 docs/README 的说明或 Makefile（可选）。
>    **验收：**给出你实际跑过的命令列表、pytest 结果、以及发现的问题（如有）和建议（不改代码也可以先记录）。

---

### ✅ T1 arXiv 时间轴正确化 + month 粒度

**AI 提示词：**

> 目标：arXiv 趋势统计必须以论文的 **published 日期**做时间 bucket，并新增 `month` 粒度。
> 背景：当前 web API 已有 `/api/arxiv/timeseries`（从 `repo.analysis.get_arxiv_timeseries(category, granularity)` 取缓存 ），granularity 目前文档写 year/week/day。我们要补齐 month，并保证 bucket 的时间字段正确。
> **请你按步骤做：**
>
> 1. 定位 arXiv 分析 agent / 统计逻辑（例如 `src/analysis/...arxiv...py`），确认目前 bucket 用的是 `retrieved_at` 还是 `published`。
> 2. 修改：
>
>    * bucket 统一使用 `published_at`（如果 raw 数据里只有字符串，解析为 datetime；没有则降级为 retrieved_at，但要打日志并计数）。
>    * 增加 `_group_by_month()`（或等价实现），输出 bucket key：`YYYY-MM`。
>    * 更新 `repo.analysis.get_arxiv_timeseries(..., granularity)` 的可选值：`year|month|day`（如果保留 week 也行，但 MVP 必须 year/month/day）。
> 3. 同步 web：
>
>    * `/api/arxiv/timeseries` 文档注释更新 granularity 可选值（见 `src/web/app.py` 的注释块 ）。
> 4. 写测试：
>
>    * 新增 `tests/test_arxiv_timeseries.py`（或合适位置），构造几条带 published_at 的样本，断言 month/day/year bucket 计数正确。
> 5. 跑：`pytest -q`。
>    **约束：**不改数据库 schema（除非完全必要）；尽量只改分析与 API 层。
>    **验收：**pytest 通过；本地跑一次 pipeline 后，`/api/arxiv/timeseries?granularity=month&category=ALL` 返回非空且 bucket key 形如 `2025-12`。

---

### ✅ T2 arXiv 关键词抽取与清洗统一（复用现有 extractor）

**AI 提示词：**

> 目标：arXiv 关键词抽取必须复用项目现有 extractor（YAKE/KeyBERT/both），并复用统一的关键词清洗/去重规则，保证 arXiv 与会议关键词“可比”。
> 背景：项目已经有 extractor 体系（`requirements.txt` 包含 yake/keybert/sentence-transformers ，`config.py` 有 `EXTRACTOR_CONFIG.default_extractor` ，并且 tests 里已有 extractor 测试 ）。
> **请你按步骤做：**
>
> 1. 找到当前 arXiv 分析里关键词是怎么来的（title/abstract 提取？还是 categories？）
> 2. 改造为：
>
>    * 对每篇 arXiv paper：用 `KeywordProcessor(extractor_type=...)` 从 `title + ". " + abstract` 提取关键词
>    * 然后走同一套 normalize/filter（如果 KeywordProcessor 已有 `_normalize_keywords` 就复用；如果项目里还有 `AnalysisAgent.filter_keywords` 也可复用，但要避免重复过滤导致过度丢词）
> 3. 性能要求：
>
>    * GitHub Actions 每日跑，默认 `--arxiv-days 7`，不要让 KeyBERT 导致超时：
>
>      * 如果 extractor=both：允许 KeyBERT 只对“候选关键词集合”或“抽样论文”跑；或者在 Actions 默认改为 yake，手动再用 both（由你决定并说明）。
> 4. 写测试：
>
>    * arXiv 关键词抽取函数：空文本返回空；正常文本返回小写、长度合理的词。
> 5. 跑：`pytest -q`。
>    **验收：**arXiv 分析输出的 top_keywords 看起来合理（不会全是 stopword / 单字母 / 超长串），并且 tests 通过。

---

### ✅ T3 生成可静态化的 arXiv 缓存（timeseries + keyword index + top）

**AI 提示词：**

> 目标：为了 GitHub Pages 静态站点，arXiv 侧必须产出“可落盘”的 JSON 缓存：
>
> * timeseries：year/month/day 各一份
> * keyword index：用于前端搜索的关键词列表（建议只保留最近 90 天出现次数>=阈值的关键词）
> * top keywords：每个 bucket 的 top N
>   背景：web API 当前 `/api/arxiv/timeseries` 与 `/api/arxiv/keywords/trends` 都是从 analysis repo 的缓存取（`repo.analysis.get_arxiv_timeseries`、`repo.analysis.get_keyword_trends_cached(scope="arxiv", ...)` ）。但静态站点不能实时 query keyword，因此要把“可搜索范围”与趋势数据落盘。
>   **请你做：**
>
> 1. 在 analysis 层新增一个 arXiv 导出用的数据结构（或直接在 export 脚本里查询并生成）：
>
>    * `arxiv_timeseries_{granularity}_{category}.json`
>    * `arxiv_keywords_index.json`（list[str]）
>    * `arxiv_keyword_trends_day.json`（dict: keyword -> [[date, count], ...]），仅保留最近 90 天、总次数>=5 的关键词（阈值可配）
> 2. 你需要决定在哪里生成它：
>
>    * 方案 A：分析阶段写入 analysis_* 表，并由 export 脚本读出来落盘
>    * 方案 B：export 脚本直接扫 paper_keywords 聚合生成
>      请选择更快且 Actions 不容易超时的方式，并实现。
> 3. 写测试：
>
>    * 生成的 json 必须可被 `json.load` 读入
>    * 关键字段存在且格式正确
>      **验收：**本地跑一次 pipeline + 导出后，能在 `docs/data/`（或你选择的目录）看到上述 json，且体积可控（建议 < 20MB）。

---

### ✅ T4 引入 CCF 会议注册表（registry，尽可能多会议的“组织中枢”）

**AI 提示词：**

> 目标：实现一个“会议注册表 registry”，用于承载 **CCF 尽可能多会议** 的清单、分级(A/B/C)、领域、别名、抓取源映射（openreview/s2/openalex）。
> 要求：即使某些会议暂时抓不到数据，也要能在 UI 里展示为“待补齐/无数据”，不阻塞上线。
> **请你做：**
>
> 1. 新增 `data/registry/ccf_venues.csv` 模板（或 `venues/ccf_venues.csv`）：字段建议：
>
>    * `canonical_name, full_name, domain, tier, source_preference, openreview_id_pattern, s2_venue_key, openalex_venue_name, aliases`
> 2. 新增一个导入脚本：`src/tools/import_ccf_registry.py`
>
>    * 读 CSV，写入 structured 层（如果已有 structured 表/接口就复用；如果没有就新建 `structured_venues` 表，字段最少包含 canonical_name/full_name/domain/tier/aliases/mappings）
> 3. 在 web API 增加一个 registry 输出（如果已有 `/api/venues/explorer` 等 structured API 就扩展）：保证前端能拿到“会议全集 + tier/domain”。
>    **约束：**先不追求立刻全量抓取；先把“会议管理与展示”打通。
>    **测试：**给一个小 CSV fixture（3 条），导入后 API 能返回这 3 条。
>    **验收：**你给出 CSV 模板 + 导入脚本 + 能在本地跑通导入与查询。

---

### ✅ T5 会议侧静态缓存（按会议/年份 top 与趋势，支持搜索）

**AI 提示词：**

> 目标：会议页面需要“选择会议 → 看关键词排行/趋势 → 搜索关键词看曲线与 rank”。由于 GitHub Pages 静态化，必须导出会议侧 JSON：
>
> * `venues_index.json`：会议列表（含 tier/domain/paper_count/可用年份）
> * `venue_{name}_top_keywords.json`：每年 top N
> * `venue_{name}_keyword_trends.json`：仅保留 top M 可搜索关键词的 yearly trends（keyword->[[year,count],...]）
>   背景：`src/web/app.py` 当前有 registry 相关 API（如 `/api/registry/venues` 会从 config.VENUES 读取，并尝试从 `repo.analysis.get_all_venue_summaries()` 拿缓存 ）。我们要把“静态站点需要的数据”导出成文件。
>   **请你做：**
>
> 1. 选择聚合来源：优先从 analysis 缓存读（快），没有则从 DB 聚合（慢但可用）。
> 2. 限制规模：每个会议只导出 top M（如 300）关键词趋势，保证体积可控。
> 3. 给出 rank 计算方式：同一年里按 count 排名（并把 rank 也导出，前端就能直接画 rank）。
> 4. 写测试：生成的 json 结构正确，包含必要字段。
>    **验收：**导出后，任意会议都能在静态数据里找到：年份列表、top keywords、关键词趋势。

---

### ✅ T6 静态站点导出脚本（docs/ = GitHub Pages 根目录）

**AI 提示词：**

> 目标：新增一个命令 `python src/tools/export_static_site.py`，把项目的 web 静态资源与数据导出到 `docs/`，用于 GitHub Pages 部署。
> **你需要完成：**
>
> 1. 输出目录结构：
>
>    * `docs/index.html` 等页面（从 `src/web/static/` 拷贝）
>    * `docs/static/...`（CSS/JS/assets）
>    * `docs/data/...json`（T3/T5 的导出数据）
> 2. 处理路径问题：把 HTML/JS/CSS 中以 `/static/...`、`/api/...` 这种“绝对路径”改为相对路径或可配置 basePath（让 GitHub Pages 的 `/repo-name/` 子路径下也能工作）。
> 3. 增加一个“静态模式”开关：
>
>    * 例如前端 `API_BASE = "./data"`（静态） vs `API_BASE = "/api"`（本地 Flask）
> 4. 写测试：export 后检查关键文件存在（index.html、data json、static js/css）。
>    **验收：**本地跑 export 后，用任意静态服务器打开 `docs/`（如 `python -m http.server -d docs 8000`），页面能加载并渲染图表（不需要 Flask）。

---

### ✅ T7 前端适配与交互增强（趋势+搜索+筛选）

**AI 提示词：**

> 目标：实现你要的“打开网页立刻看到趋势 + 可点会议 + 可搜索/筛选关键词”。前端为原生 HTML/JS（项目当前也是原生前端，Flask 只是静态托管与 API，见 `src/web/app.py` 的静态路由与 API ）。
> **请你做：**
>
> 1. 梳理现有页面：`src/web/static/index.html`、可能的 `arxiv.html`、`venues.html`（按仓库实际为准）。
> 2. 把 API 调用改为读 `docs/data/*.json`：
>
>    * arXiv：默认展示 day（最近 90 天）+ top 新兴关键词（最近 7 天 vs 28 天增长率）
>    * 会议：左侧会议列表（支持 tier/domain 过滤），右侧显示 top 与趋势
> 3. 加入关键词搜索：
>
>    * 输入框联想（基于 `*_keywords_index.json`）
>    * 选中后画 count 曲线 + rank 曲线（如果你在导出里给了 rank）
> 4. 兼容本地 Flask：如果存在 `/api/health` 则走 API，否则走静态 json。
>    **验收：**
>
> * GitHub Pages 静态打开可用
> * 本地 `python src/web/app.py` 也可用（不强制，但尽量兼容）
> * 关键词搜索不卡顿（索引用 list + 前端前缀过滤即可）

---

### ✅ T8 GitHub Actions 扩展：跑完 pipeline 自动导出 docs 并提交

**AI 提示词：**

> 目标：扩展 `.github/workflows/update.yml`：在跑完 `python src/main.py` 后，自动执行 `python src/tools/export_static_site.py`，并把 `docs/` 一起 commit。
> 背景：当前 workflow 会在最后 `git add data/ output/ -f` 并 push 。
> **请你做：**
>
> 1. 在 workflow 增加一步：`python src/tools/export_static_site.py`
> 2. 修改 add：`git add data/ output/ docs/ -f`
> 3. 增加可选 inputs：
>
>    * `ccf_tier`（A/B/C/all）
>    * `export_only`（只导出 docs 不跑采集，便于调 UI）
> 4. 给出 Actions 运行时长控制建议：默认只跑 arXiv 7 天 + CCF-A 会议；手动可跑全量。
>    **验收：**workflow 运行结束后仓库出现 `docs/` 更新；Pages 可直接访问。

---

### ✅ T9 回归测试补齐（保证“以后好维护”）

**AI 提示词：**

> 目标：把本次改动的关键风险点加上单测，避免以后改崩：
>
> * arXiv bucket(year/month/day) 正确
> * export_static_site 导出文件齐全、json 格式正确
> * registry 导入正确
>   **请你做：**
>
> 1. 为 bucket 函数与导出 JSON 增加 tests
> 2. 如需要，为测试加 fixture（小型 sqlite 临时库，项目已有 `tests/conftest.py` 里提供 temp_db_path 与 repo fixture ）
> 3. 跑 `pytest -q` 并确保通过
>    **验收：**CI/本地都能稳定通过；测试运行时间可控（<30s）。

---

## 四、最后必须人工做的事情（尽量放后）

1. **准备 CCF 会议列表 CSV**（这是最关键的人为输入之一）

* 你把 CCF 会议清单整理进 `ccf_venues.csv`（AI 可给模板与导入脚本，但“权威清单内容”最好由你提供/粘贴）

2. **打开 GitHub Pages**

* Settings → Pages → Source 选 `docs/`（或 GitHub Pages 新版的 “Deploy from a branch”，选择 main / docs）

3. **（可选）配置 Secrets**

* 如果你需要 OpenReview 抓取更多：设置 `OPENREVIEW_USERNAME` / `OPENREVIEW_PASSWORD`（README 里也提到了 ）

---

如果你愿意，我下一步可以**先回答你“当前项目已经涉及哪些会议”**（从 `config.py` 的 OpenReview VENUES  + README 的 S2 列表  + 你 web 的 registry API  这三处合并），然后我们再按上面任务从 T1 开始逐个落地改代码。
