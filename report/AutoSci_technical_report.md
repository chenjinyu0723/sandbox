# AutoSci 深度技术分析报告

> **项目**: [skyllwt/AutoSci](https://github.com/skyllwt/AutoSci) — 面向全科研生命周期的记忆中心化智能体系统
> **论文**: [AutoSci: A Memory-Centric Agentic System for the Full Scientific Research Lifecycle](https://arxiv.org/abs/2605.31468)
> **团队**: 北京大学 DAIR Lab (崔斌教授课题组)
> **Stars**: ~1,546 | **当前状态**: internal beta

---

## 目录

1. [系统总览](#1-系统总览)
2. [论文处理流水线](#2-论文处理流水线-ingest-system)
3. [知识抽取与实体模型](#3-知识抽取与实体模型)
4. [图结构与嵌入机制](#4-图结构与嵌入机制)
5. [知识查询与检索机制](#5-知识查询与检索机制)
6. [核心工具与基础设施](#6-核心工具与基础设施)
7. [技能体系全览](#7-技能体系全览)
8. [前端可视化与交互](#8-前端可视化与交互)
9. [架构总结与设计洞察](#9-架构总结与设计洞察)

---

## 1. 系统总览

### 1.1 设计理念

AutoSci 是一个**以持久化记忆为核心**的智能体系统，目标是自动化科学研究的完整生命周期——从文献摄入到审稿 rebuttal。其核心理念是：

1. **记忆累积 (Memory Compounding)**：每摄入一篇论文、每产生一个想法、每完成一次实验，都持久化为 wiki 页面和图谱边。知识不会在会话结束后消失，而是跨项目持续增长。
2. **LLM 驱动的工作流 (LLM-Driven Workflow)**：所有操作通过 LLM Agent（Claude Code / Codex / OpenCode）以"技能 (Skill)"的形式执行，每个技能是一个结构化的 prompt 流程。
3. **数据驱动模式 (Schema-Driven)**：所有实体和关系通过 `runtime/schema/*.yaml` 定义，Python 工具层提供确定性底层操作，LLM 负责语义判断和内容生成。

### 1.2 核心组件四层架构

```
┌─────────────────────────────────────────────────────┐
│  Agent Runtime (Claude Code / Codex / OpenCode)     │
│  30+ Skills (init/ingest/ideate/exp-run/...)        │
├─────────────────────────────────────────────────────┤
│  Python Tool Layer (tools/research_wiki.py 等)      │
│  ┌──────────┬──────────┬──────────┬──────────┐     │
│  │ Wiki     │ Graph    │ Discover │ Visualize│     │
│  │ Engine   │ Engine   │ Engine   │ Engine   │     │
│  └──────────┴──────────┴──────────┴──────────┘     │
├─────────────────────────────────────────────────────┤
│  External APIs                                       │
│  ┌──────────┬──────────┬──────────┬──────────┐     │
│  │Semantic  │ DeepXiv  │  arXiv   │ Paper    │     │
│  │ Scholar  │          │          │ Copilot  │     │
│  └──────────┴──────────┴──────────┴──────────┘     │
├─────────────────────────────────────────────────────┤
│  Persistent Store (文件系统)                         │
│  wiki/{entity}/*.md  +  wiki/graph/{edges,citations}.jsonl │
└─────────────────────────────────────────────────────┘
```

### 1.3 关键文件清单

| 层次 | 关键文件 | 功能 |
|------|---------|------|
| **Schema** | `runtime/schema/entities.yaml` | 9 种实体类型的字段定义 |
| | `runtime/schema/edges.yaml` | 14 种边类型的端点/属性规范 |
| | `runtime/schema/xref.yaml` | 双向链接契约（13条规则） |
| | `runtime/schema/conventions.yaml` | 系统约定 (slug模式/文件归属/日期格式) |
| **Schema加载** | `runtime/loader.py` | 数据驱动式 schema 加载器 (237行)，在导入时从YAML派生所有常量 |
| **Wiki引擎** | `tools/research_wiki.py` | 核心 wiki 操作引擎 (2861行)：init/slug/add-edge/dedup/compile-context/neighbors/stats 等30+命令 |
| **可视化** | `tools/serve.py` | 本地HTTP服务器 + SSE实时推送 (1075行) |
| | `tools/visualize.py` | Obsidian图配置 + Canvas生成器 (726行) |
| **发现** | `tools/discover.py` | 论文发现与推荐排序引擎 (1255行) |
| | `tools/init_discovery.py` | /init 的论文发现规划器 |
| **每日arXiv** | `tools/daily_arxiv.py` | 日常 arXiv 论文推荐 (1534行) |
| **API封装** | `tools/fetch_s2.py` | Semantic Scholar API 封装 |
| | `tools/fetch_deepxiv.py` | DeepXiv API 封装 |
| | `tools/fetch_arxiv.py` | arXiv RSS 获取 |
| **前端SPA** | `app/index.html` + `app/modules/*.js` | 单页应用：Reader/Graph/Dashboard 三视图 |
| **技能定义** | `.claude/skills/*/SKILL.md` | 30+ 个 LLM 技能定义文件 |

---

## 2. 论文处理流水线 (Ingest System)

### 2.1 入口点与模式

论文摄入有两大入口：

**A. 直接摄入 (`/ingest`)**
- 用户手动触发，支持 arXiv URL、本地 `.tex`、本地 `.pdf`
- 立即执行完整的单篇论文摄入流程

**B. 批量初始化 (`/init`)**
- 扫描 `raw/papers/` (用户论文)、`raw/notes/`、`raw/web/`
- 通过规划器 (`tools/init_discovery.py`) 进行外部发现
- 并行摄入：使用 git worktree 隔离，每篇论文在独立子进程中并发执行
- 最终 fan-in 合并、去重、回填引用

### 2.2 `/ingest` 完整流程 (9 步骤)

**文件**: `.claude/skills/ingest/SKILL.md` (299行)

#### Step 1: 源解析 (Source Resolution)

```
arXiv URL → extract arXiv ID → fetch_s2.py paper → init_discovery.py download
Local .tex → 直接使用
Local .pdf → PDF预处理管道:
  1. 恢复 arXiv ID (文件名/路径解析)
  2. Semantic Scholar 标题恢复
  3. 获取 arXiv 源码 (.tex)
  4. 合成 .tex 兜底
→ 最终输出 canonical_ingest_path
```

**关键文件**: `tools/prepare_paper_source.py`, `references/pdf-preprocessing.md`

恢复优先级严格为：**handed-off arXiv ID > filename/path arXiv ID > agent-recovered title via S2 > synthetic .tex**

#### Step 2: 论文身份与富化

```bash
# Slug 生成 (基于关键词提取 + 去停用词 + 前6词截断)
research_wiki.py slug "<paper-title>"

# 已存在检查: wiki/papers/{slug}.md 存在且 arXiv ID 或标题匹配 → 终止

# Semantic Scholar 富化
fetch_s2.py paper <arxiv-id>  # venue, year, s2_id, citation_count, authors

# DeepXiv 富化 (可选，静默降级)
fetch_deepxiv.py brief <arxiv-id>   # TLDR + Key-idea
fetch_deepxiv.py head <arxiv-id>    # 章节结构
fetch_deepxiv.py social <arxiv-id>  # 社交影响力信号
```

#### Step 3: 论文页面创建

根据 `runtime/templates/papers.md.tmpl` 模板，创建 `wiki/papers/{slug}.md`：

**Frontmatter 字段** (来自 `entities.yaml`):
- `title`, `slug`, `arxiv`, `venue`, `year`, `tags`, `importance` (1-5)
- `contribution_type` (method/theory/benchmark/analysis/application/system/position/survey)
- `datasets`, `tldr`, `code_url`, `cited_by`, `date_added`

**Body 章节顺序**:
1. Problem & Context — 问题与领域背景
2. Key idea — 核心思想
3. Method — 方法细节
4. Experiment & Results — 实验与结果（含具体数据）
5. Limitations — 局限性
6. Open questions — 开放问题
7. My take — 个人评述
8. Related — 关联实体

#### Step 4: 概念、方法、人物提取

**概念 (Concepts)**: 
- 通过 `find-similar-concept` 进行 token 级相似度匹配（Jaccard + 短语匹配），防止重复创建
- 同时扫描 `wiki/concepts/` 和 `wiki/foundations/`（foundation 命中 → 引用而非创建）
- 匹配阈值：exact=1.0, phrase containment=0.85, Jaccard: 0.4-0.84，低于0.4过滤

**方法 (Methods)**:
- 仅在技术**命名、可复用、可引用**时创建
- 通过目录扫描 + 手动 title/alias 比较进行去重

**人物 (People)**:
- 论文 importance ≥ 4 → 创建 `wiki/people/{slug}.md`
- importance < 4 → 仅在已有作者页面追加 `## Recent work`

**数量限制** (`references/dedup-policy.md`):
- importance < 4: 最多 1 个新 concept + 1 个新 method
- importance ≥ 4: 最多 3 个新 concept + 2 个新 method

#### Step 5: 论文间引用与边

```bash
fetch_s2.py references <arxiv-id>  # 获取参考文献列表
fetch_s2.py citations <arxiv-id>   # 获取施引文献列表
```

- 对每篇已存在于 wiki 的参考文献，追加 `cites` 条目到 `graph/citations.jsonl`
- 语义关系边（builds_on/same_problem_as 等）仅在源文本有明确线索时添加
- 回填施引文献到 `cited_by` 字段
- 在 INIT MODE 中跳过此步骤，由 `/init` 完成后统一执行

#### Step 6: 主题归属

将论文 tags 与 `wiki/topics/*.md` 匹配：
- importance ≥ 4 → 追加到 topic 的 `## Seminal works` + frontmatter `key_papers`
- importance < 4 → 追加到 `## SOTA tracker` / `## Recent work`
- 论文直接解决已知 open problem → 在 topic 页面标注

#### Step 7: 日志与重建

```bash
research_wiki.py log wiki/ "ingest | added papers/<slug> | updated: <list>"
research_wiki.py rebuild-context-brief wiki/     # 重建压缩上下文
research_wiki.py rebuild-open-questions wiki/    # 重建知识缺口图
```

#### Step 8: 报告

输出紧凑摘要：创建/更新页面数量、图谱边数量、冲突发现、建议后续摄入。

#### Step 9: 可选发现 (`--discover`)

```bash
discover.py from-anchors --id <arxiv-id> --wiki-root wiki --limit 10
```

将关联论文短名单追加到报告，**不自动摄入**。

### 2.3 Slug 生成算法

**文件**: `tools/research_wiki.py` 第 105-129 行 (`slugify` 函数)

```
输入: "LoRA: Low-Rank Adaptation of Large Language Models"
→ 小写化 + 去标点 + 分词
→ 过滤停用词 (92个英文停用词集合)
→ 保留长度>1的词
→ 截取前6个关键词
→ 连字符连接
输出: "lora-low-rank-adaptation-large-language-models"
```

### 2.4 INIT MODE 并行摄入

**文件**: `.claude/skills/init/SKILL.md`, `references/parallel-ingest.md`

`/init` 使用 git worktree 实现论文并行处理：

1. **检查点 (Checkpoint)**: 在 `.checkpoints/init-sources.json` 中记录所有待摄入论文
2. **Git Worktree 隔离**: 每篇论文在自己的 worktree 中独立执行 `/ingest`
3. **合并策略**: `merge=union` 用于 `edges.jsonl`, `citations.jsonl`, `index.md`, `log.md`
4. **Fan-in**: 顺序合并所有 worktree 分支，然后执行全局去重、回填、重建
5. **INIT MODE 限制**: 子代理跳过 citations/references 回填、index/context-brief/open-questions 重建、冲突性 topic 写入

---

## 3. 知识抽取与实体模型

### 3.1 实体类型全景

**文件**: `runtime/schema/entities.yaml` (183行)

| 实体类型 | 目录 | 用途 | 关键字段 |
|---------|------|------|---------|
| **papers** | `wiki/papers/` | 论文页面 | title, arxiv, importance(1-5), contribution_type, tldr |
| **concepts** | `wiki/concepts/` | 技术概念 | maturity(stable/active/emerging/deprecated), aliases, key_papers |
| **topics** | `wiki/topics/` | 研究领域/主题 | key_venues, key_people, key_papers, linked_ideas |
| **methods** | `wiki/methods/` | 可复用方法/技术 | type(11种), source_papers, realizes_concepts |
| **people** | `wiki/people/` | 研究者 | type.kind(researcher/team/organization), research_areas |
| **ideas** | `wiki/ideas/` | 研究想法 | status 生命周期, novelty_score, priority, origin_gaps |
| **experiments** | `wiki/experiments/` | 实验记录 | linked_idea, setup(硬件/框架), outcome, metrics |
| **foundations** | `wiki/foundations/` | 领域基础知识 | terminal=true, domain, status(mainstream/historical) |
| **Summary** | `wiki/Summary/` | 领域概览 | scope, key_topics, paper_count |

### 3.2 生命周期管理

**Ideas** 状态转换 (`entities.yaml` 第 97-101 行):
```
proposed → in_progress → tested → validated | failed
                                (failed时必须填failure_reason)
```

**Experiments** 状态转换 (`entities.yaml` 第 157-160 行):
```
planned → running → completed | abandoned
```

生命周期转换由 `runtime/loader.py` 中的 `validate_lifecycle_transition()` 函数验证（第 225-237 行）。

### 3.3 双向链接契约 (Cross-Reference)

**文件**: `runtime/schema/xref.yaml` (78行)

定义了 13 条正向链接→反向更新的规则。核心原则：**每次创建正向链接，必须在同一轮对话中写入反向链接**。

关键规则示例：
```
papers.Related → concepts.key_papers                (论文引用概念→概念记录被引用)
ideas.origin_gaps → concepts.linked_ideas           (想法解决缺口→概念关联想法)
experiments.linked_idea → ideas.linked_experiments  (实验链接想法→想法关联实验)
methods.realizes_concepts → concepts."Realized by"  (方法实现概念→概念记录实现方法)
concepts.parent_topic → topics."Concepts"            (概念归属主题→主题记录概念)
```

**特殊规则**: `foundations` 是终端实体 (`terminal: true`)，所有指向它的链接**不写反向链接**。

### 3.4 去重机制

**`find-similar-concept`** (`research_wiki.py` 第 985-1118 行):

基于 token 级文本匹配的确定性去重（不依赖 LLM）：

```
评分标准:
  exact normalized match (忽略大小写+停用词)         → 1.00
  短语包含 (一个完全包含另一个，且较短的≥2词)        → 0.85
  Jaccard 相似度 (content tokens) ≥ 0.7              → 直接返回Jaccard值
  Jaccard 相似度 ≥ 0.4                               → 0.4 + (j-0.4)*0.5
  < 0.4                                               → 过滤

扫描目录: wiki/concepts/ + wiki/foundations/
排序策略: foundation高匹配优先 → 按score降序
```

---

## 4. 图结构与嵌入机制

### 4.1 边类型体系

**文件**: `runtime/schema/edges.yaml` (157行)

#### 4.1.1 论文间语义边 (workflow: ingest)

| 边类型 | 方向 | 属性 | 语义 |
|--------|------|------|------|
| `same_problem_as` | symmetric | confidence(high/medium/low) + evidence | 解决相同问题 |
| `similar_method_to` | symmetric | confidence + evidence | 方法相似 |
| `builds_on` | directed | confidence + evidence | 基于前作构建 |
| `challenges` | directed | confidence + evidence | 挑战前作结论 |

#### 4.1.2 论文-概念语义边 (workflow: ingest)

| 边类型 | 方向 | 属性 | 语义 |
|--------|------|------|------|
| `introduces_concept` | directed | confidence + evidence | 引入新概念 |
| `uses_concept` | directed | confidence + evidence | 使用已有概念 |
| `extends_concept` | directed | confidence + evidence | 扩展已有概念 |
| `critiques_concept` | directed | confidence + evidence | 批评已有概念 |

#### 4.1.3 工作流边 (跨实体)

| 边类型 | 方向 | workflow | 语义 |
|--------|------|---------|------|
| `supports` | directed | evidence | 证据支持 |
| `contradicts` | directed | evidence | 证据矛盾 |
| `tested_by` | directed | experiment | 被实验测试 |
| `invalidates` | directed | experiment | 实验结果证伪 |
| `addresses_gap` | directed | idea | 解决知识缺口 |
| `derived_from` | directed | provenance | 来源追溯 |
| `inspired_by` | directed | idea | 灵感来源 |

#### 4.1.4 书目引用

| 边类型 | 存储位置 | 属性 |
|--------|---------|------|
| `cites` | `graph/citations.jsonl` | source(semantic_scholar/parsed_bib/manual) + date |

### 4.2 图存储格式

**edges.jsonl** — 每行一个 JSON 对象:
```json
{"from": "papers/lora", "to": "papers/qlora", "type": "builds_on",
 "confidence": "high", "evidence": "QLoRA extends LoRA with 4-bit quantization",
 "date": "2026-07-16"}
```

**citations.jsonl** — 每行一个 JSON 对象:
```json
{"from": "papers/qlora", "to": "papers/lora", "type": "cites",
 "source": "semantic_scholar", "date": "2026-07-16"}
```

**对称边处理**: 对称边类型 (`same_problem_as`, `similar_method_to`) 在存储时排序 `from`/`to`，添加 `symmetric: true` 标记。

### 4.3 图操作

**文件**: `tools/research_wiki.py`, 核心操作在 `loader.py` 和 `research_wiki.py`

#### add-edge (第 275-357 行)
```python
add_edge(wiki_root, from_id, to_id, edge_type, evidence, confidence, symmetric)
```
- 验证边类型合法性
- 验证 confidence 枚举值
- 规范端点顺序（对称边）
- 拓扑检查（端点匹配、自环检测）
- 去重检查
- 追加写入 edges.jsonl

#### dedup-edges (第 711-751 行)
并行摄入后使用，按 `(from, to, type)` 三元组去重，保留首次出现。

#### neighbors (第 1184-1237 行) — BFS 图遍历
```python
neighbors(wiki_root, node_id, depth=1, edge_types=None, direction="both")
```
- 构建双向邻接表 (in/out + symmetric)
- BFS 遍历至指定深度
- 返回 {center, depth, nodes: [{id, edge, direction, evidence}]}

#### project_frontmatter_edges (第 586-678 行)
将实体 frontmatter 中的 `link`/`list_link` 字段**投影为图边**：
```python
# concepts.key_papers 投影为:
{"from": "concepts/lora", "to": "papers/lora", "type": "fm_concepts_key_papers",
 "source": "frontmatter"}
```

这在可视化时让 Obsidian Canvas 和 Web Graph 能看到 frontmatter 链接。

### 4.4 图加载器 (`runtime/loader.py`)

**文件**: `runtime/loader.py` (237行)

数据驱动的 schema 加载器，在**导入时**自动从 YAML 派生所有常量：

```
从 entities.yaml 派生:  ENTITY_DIRS, REQUIRED_FIELDS, VALID_VALUES, FIELD_DEFAULTS
从 edges.yaml 派生:     EDGE_TYPE_SPECS, PAPER_PAPER_EDGE_TYPES, PAPER_CONCEPT_EDGE_TYPES,
                         SYMMETRIC_EDGE_TYPES, CONFIDENCE_REQUIRED_EDGE_TYPES, VALID_EDGE_TYPES

导出的辅助函数:
  edge_types_matching(from_kind, to_kind, direction, confidence, workflow)
  edge_is_symmetric(edge_type)
  edge_requires_confidence(edge_type)
  edge_endpoint_matches(edge_type, from_kind, to_kind)
  validate_edge_attributes(edge_type, attrs)
  validate_lifecycle_transition(kind, from_state, to_state)
```

### 4.5 压缩上下文 (Context Brief / Query Pack)

**文件**: `research_wiki.py` 第 1244-1417 行 (`compile_context` 函数)

根据**目的**生成不同预算的压缩上下文：

```
CONTEXT_BUDGETS = {
              Methods  Gaps  Failed  Papers  Experiments  Edges  Stale
"ideation":   (1500,  2000, 2000,   1000,    500,         500,   500),
"experiment": (2500,   500,  500,   1000,   2500,         500,     0),
"writing":    (2000,   500,  200,   2500,    500,         800,     0),
"review":     (2500,  1000,  500,   1000,   1500,         500,   500),
"general":    (2000,  1500, 1500,   2000,      0,        1000,     0),
}
```

每个预算块包含 7 个维度的字符配额：
1. **Methods**: 按图连通度排序的可复用方法摘要
2. **Gaps**: 从 `open_questions.md` 提取的知识缺口
3. **Failed Ideas**: 状态为 failed 的想法及其失败原因（防止重复犯错）
4. **Papers**: 按重要性+连通度排序的论文 TLDR 摘要（最多15篇）
5. **Experiments**: 实验状态与结果一览
6. **Edges**: 最近的图关系（最后25条）
7. **Stale Entities**: 超过30天未更新的实体

最终控制在 `max_chars`（默认8000字符）内，超出部分截断标注。

---

## 5. 知识查询与检索机制

### 5.1 `/ask` — Wiki RAG 问答

**文件**: `.claude/skills/ask/SKILL.md` (210行)

完整的检索增强生成 (RAG) 流程：

**Step 1: 加载全局上下文**
- 读取 `wiki/graph/context_brief.md` (压缩知识快照)
- 读取 `wiki/graph/open_questions.md` (已知知识缺口)

**Step 2: 检索相关页面**
- 读取 `wiki/index.md`，匹配问题关键词与 slug
- 从 context_brief.md 中提取语义相关的 ideas/methods/papers
- 按相关性排序，选择 top-K (K ≤ 15，避免超 context window)
- 读取全部选中页面内容
- 如需关系查询（如 "X 和 Y 有什么区别"），额外读取 `edges.jsonl` 中相关边

**Step 3: LLM 综合生成答案**
- 必须引用 `[[slug]]` 来源
- 支持多种格式：`--format markdown/table/timeline/bullets`
- 明确标注"wiki 证据不足"的部分
- 引用 idea 时必须标注 `status` 和 `novelty_score`

**Step 4-6: Crystallize (结晶化)**
- 评估答案是否值得写回 wiki
- 三种写回模式：
  - Case A: 写入 `wiki/outputs/{query-slug}.md`
  - Case B: 创建新 concept 页面
  - Case C: 追加到已有 idea/method/output 页面
- 自动添加 `derived_from` 边链接源论文

### 5.2 `find` — 实体字段搜索

**文件**: `research_wiki.py` 第 919-953 行

```bash
research_wiki.py find wiki/ papers --field importance --field ">=4"
```

支持的过滤操作：`=` (精确匹配), `<`, `>`, `<=`, `>=`, `!=`

对 list 类型字段检查 `pattern in list`。

### 5.3 `neighbors` — BFS 图邻域查询

```bash
research_wiki.py neighbors wiki/ papers/lora --depth 2 --edge-type builds_on --outgoing
```

返回以指定节点为中心的 BFS 遍历结果，包含边类型和方向信息。

### 5.4 具名查询 (Named Queries)

**`query ready-to-test`** (第 1125-1152 行):
找出状态为 `proposed` 且没有关联实验的想法，按 priority 降序排列。

**`query orphans`** (第 1155-1177 行):
找出图中没有任何边的孤立节点。

### 5.5 `/discover` — 论文发现与推荐

**文件**: `.claude/skills/discover/SKILL.md` (179行), `tools/discover.py` (1255行)

四种种子模式：

| 模式 | 触发方式 | 数据源 |
|------|---------|--------|
| **Anchor** | `--anchor <id>` 或 `/ingest --discover` | S2 recommend + references + citations (三通道) |
| **Topic** | `--topic "<query>"` | S2 search + DeepXiv semantic search |
| **Wiki** | `--from-wiki` | 自动从 wiki 最活跃论文派生 anchors |
| **Venue** | `--venue iclr --year 2024` | Paper Copilot 数据集 + wiki 相关性排序 |

**排序信号** (Anchor 模式):
- Anchor 相似度 (来自 S2 recommendations)
- 有影响力引用 (is_influential_edge 标记)
- 作者 h-index (max_h_index)
- 引用次数 (citation_count, influential_citation_count)
- 新颖度 (year)

**硬约束**: 绝不自动摄入；始终去重 wiki 已有论文；模式输出仅做推荐。

---

## 6. 核心工具与基础设施

### 6.1 `tools/research_wiki.py` — Wiki 知识引擎 (2861行)

作为整个系统的**确定性底层操作核心**，提供 30+ 命令：

```
Infrastructure:   init, slug, log
Frontmatter:      read-meta, set-meta
Graph:            add-edge, add-citation, batch-edges, dedup-edges, dedup-citations
Query:            find, query (ready-to-test, orphans), neighbors
Context:          compile-context, rebuild-context-brief, rebuild-open-questions, rebuild-index
Lifecycle:        transition (状态转换验证)
Stats:            stats, maturity
Checkpoint:       checkpoint-save/load/clear/set-meta/get-meta
Frontmatter Proj: rebuild-projected-edges, project_frontmatter_edges
```

### 6.2 `tools/serve.py` — Web 服务器与 SSE 实时推送 (1075行)

纯标准库 `ThreadingHTTPServer`，绑定 `127.0.0.1:8765`：

**REST API**:
```
GET  /api/health, /api/stats, /api/maturity, /api/graph
GET  /api/entities/{type}, /api/entities/{type}/{slug}[/raw]
GET  /api/open-questions, /api/log?tail=N
GET  /api/events                          ← SSE 实时推送
POST /api/edges, /api/citations, /api/log
POST /api/regenerate/{index|context-brief|open-questions}
POST /api/intent/{ingest|ask|edit|check|ideate|discover|exp-design}
PATCH /api/entities/{type}/{slug}
```

**SSE 实时推送**: 后台线程每 1.5 秒轮询 `wiki/` 文件的 mtime，检测到变更时向所有 `/api/events` 客户端广播 `event: change`，SPA 自动重新渲染。SPA 写入后有 2.5 秒 grace window 抑制自触发的重复渲染。

**Skill Intent 边界**: SPA 不直接执行 `/skill` 命令。UI 按钮通过 `/api/intent/{skill}` 后端组装正确的命令字符串，前端弹出复制到剪贴板的模态框，用户粘贴到 Claude Code 中执行。

### 6.3 `tools/discover.py` — 论文发现引擎 (1255行)

四种模式的评分与聚合管道：
- **Anchor**: 三通道并发获取 (S2 recommend + references + citations)，合并去重后按 anchor count、影响力、引用量、h-index、年份排序
- **Topic**: S2 关键词搜索 + DeepXiv 语义搜索 (BM25+向量混合) 合并
- **Venue**: 从 Paper Copilot GitHub 仓库读取会议论文列表，提取 wiki 中已有的 title/abstract 文本作为词袋 TF 相关性打分

### 6.4 外部 API 封装

| 工具 | 功能 | API |
|------|------|-----|
| `fetch_s2.py` | 论文检索/引用/推荐/参考文献 | Semantic Scholar Graph API |
| `fetch_deepxiv.py` | 语义搜索/TLDR/趋势/影响力 | DeepXiv API |
| `fetch_arxiv.py` | arXiv RSS 新论文获取 | arXiv RSS Feed |
| `fetch_wikipedia.py` | Wikipedia 内容获取 | Wikipedia API |

### 6.5 环境配置

**文件**: `.env.example` (98行)

```
SEMANTIC_SCHOLAR_API_KEY=    # S2 API Key (可选，有key=1req/s，无key=1req/3s)
DEEPXIV_TOKEN=               # DeepXiv Token (可选，自动注册，1000次/天)
LLM_API_KEY=                 # Review LLM (OpenAI-compatible，可选)
LLM_BASE_URL=                # 支持 DeepSeek/OpenAI/Qwen/SiliconFlow
LLM_MODEL=
```

**Python 依赖** (`requirements.txt`):
```
PyMuPDF (PDF解析), feedparser (RSS), requests, markdownify, chardet,
deepxiv-sdk, PyYAML, playwright (poster渲染)
```

---

## 7. 技能体系全览

AutoSci 提供 30+ 个 LLM Agent 技能，覆盖科研全生命周期：

### Phase 0: 设置
| 技能 | 功能 |
|------|------|
| `/setup` | 交互式 API key 配置 |
| `/reset` | 销毁性清理 (wiki/raw/log/checkpoints/all 范围) |
| `/prefill` | 预填充 `wiki/foundations/` 领域背景知识 |

### Phase 1: 知识库
| 技能 | 功能 |
|------|------|
| `/init` | 从 raw/ 引导 wiki + 规划器发现 + 并行摄入 |
| `/ingest` | 单篇论文全链路摄入（9步） |
| `/discover` | 4 种模式的论文推荐排行榜 |
| `/edit` | 添加/移除 raw 源或更新 wiki 内容 |
| `/ask` | Wiki RAG 问答 + 结晶化写回 |
| `/check` | 全 wiki 健康扫描 + 分级修复建议 |
| `/daily-arxiv` | 日常 arXiv 推荐 (inform/auto-ingest) |
| `/visualize` | Obsidian 图谱配置 + Canvas 生成 |

### Phase 2: 构思与实验
| 技能 | 功能 |
|------|------|
| `/ideate` | 5阶段研究构思：景观扫描→双模型头脑风暴→过滤验证→写wiki→先导实验 |
| `/novelty` | 多渠道新颖性验证 (WebSearch + S2 + wiki + Review LLM) |
| `/review` | 跨模型评审（第二LLM独立打分+改进建议） |
| `/exp-design` | 实验设计：方法候选→基准选择→敏感性分析→主实验 |
| `/exp-run` | 实验全流程：准备代码→部署→监控→收集结果 |
| `/exp-status` | 实验状态监控+自动收集 |
| `/exp-eval` | 实验裁决门：Review LLM 独立判断结果 |
| `/exp-pilot-run` | 先导实验执行（内置于 `/ideate` Phase 5） |
| `/exp-pilot-eval` | 先导实验评估 |
| `/refine` | 多轮迭代改进至目标分数 |

### Phase 3: 写作与传播
| 技能 | 功能 |
|------|------|
| `/survey` | 从 wiki 知识生成 Related Work |
| `/paper-plan` | 从 idea 图编译论文大纲 |
| `/paper-draft` | 从 PAPER_PLAN 起草 LaTeX 论文 |
| `/paper-compile` | LaTeX 编译→PDF (latexmk + 自动修复) |
| `/research` | 端到端研究编排器 |
| `/rebuttal` | 解析审稿意见→原子化→生成 rebuttal |
| `/poster` | 从草稿生成学术海报 |

### `/ideate` 五阶段详细架构

**文件**: `.claude/skills/ideate/SKILL.md` (556行)

```
Phase 1: Landscape Scan (景观扫描)
  ├── wiki 内部上下文加载 (context_brief, open_questions, banlist, active list)
  ├── WebSearch (近期6个月的论文与进展)
  ├── Semantic Scholar 搜索 (top-20, fetch top-5 details)
  ├── DeepXiv 语义搜索 (hybrid模式) + Trending papers
  └── 生成内部 landscape report

Phase 2: Dual-Model Brainstorm (双模型头脑风暴)
  ├── Claude 独立生成 6-10 个想法 (5条结构化路径A-E)
  │    A: Landscape-driven  C: Combination
  │    B: Incremental       D: Innovation
  │                        E: Cross-domain transfer
  └── Review LLM 独立生成 4-6 个想法 (并行的 MCP llm-review 调用)

Phase 3: Filter & Validation
  ├── 第一遍过滤: 综合去重 + 可行性 + 新颖性初筛
  └── 深度验证 (/novelty + /review)

Phase 4: Write to Wiki
  ├── 创建 wiki/ideas/{slug}.md (status=proposed)
  ├── 淘汰想法也记录 (status=failed + failure_reason)
  └── 添加 addresses_gap + inspired_by 边

Phase 5: Pilot Experiments
  ├── /exp-pilot-run → 编写代码→部署→监控→收集原始结果
  └── /exp-pilot-eval → 读取结果→宽松裁决→更新 idea 页面
```

---

## 8. 前端可视化与交互

### 8.1 单页应用 (SPA)

**文件**: `app/index.html` + `app/modules/*.js` (11个 ES modules)

三视图导航：
- **Reader** (`#/reader/{type}/{slug}`): 实体页面渲染 + 编辑
- **Graph** (`#/graph`): 交互式 Cytoscape.js 知识图谱
- **Dashboard** (`#/dashboard`): 统计面板 + 健康报告

核心模块：
- `api.js` — REST API 客户端
- `graph.js` — Cytoscape 图谱视图 (1034行)
- `reader.js` — Markdown 渲染 + 编辑
- `router.js` — Hash 路由
- `state.js` — 客户端状态管理
- `intent.js` — Skill 命令生成
- `wikilink.js` — `[[slug]]` 链接解析

### 8.2 Graph View 功能

**文件**: `app/modules/graph.js` (1034行)

- **渲染引擎**: Cytoscape.js 3.28.1，力导向布局
- **实体颜色**: 9种类型各有独立颜色 (蓝/品红/橙/绿/琥珀/红/石灰绿/青/灰)
- **边颜色**: 按 workflow 区分 (ingest/evidence/experiment/idea/provenance/citation)
- **过滤器**: 按实体类型 / 边类型 / 低置信度隐藏
- **BFS 高亮**: 点击节点高亮 k-跳邻域 (可调深度 1-5)
- **路径查询**: 右键设置起点/终点，查找最短路径
- **双击导航**: 双击节点跳转到 Reader 页面
- **预设视图**: 预定义的子图视图
- **搜索**: 节点名搜索 + 高亮定位

### 8.3 Obsidian 集成

**`/visualize --obsidian`**: 生成 `wiki/.obsidian/graph.json`，配置按实体类型的颜色组。

**`/visualize --canvas`**: 生成 `wiki/canvases/*.canvas`，包含力导向布局的节点（带标签的语义边）。

---

## 9. 架构总结与设计洞察

### 9.1 核心设计原则

1. **确定性底层 + LLM 语义上层**：图操作、slug 生成、字段验证、去重匹配全部由确定性 Python 代码执行，LLM 仅在需要语义理解和内容生成时介入。这种分层确保了可靠性。

2. **Schema-Driven Architecture**：所有实体类型、字段约束、边类型、生命周期转换都定义在 YAML 中，`runtime/loader.py` 在导入时自动派生所有常量。新增实体/边类型只需修改 YAML，无需改动任何业务逻辑代码。

3. **持久化记忆而非嵌入向量**：AutoSci 不使用向量数据库或 embedding。知识以 Markdown 文件 + JSONL 图谱的形式存储。检索通过 frontmatter 字段过滤、token 级文本匹配、图遍历和 LLM 理解实现。这种设计保证了可读性、可调试性和版本控制友好性。

4. **双向链接不变性** (`xref.yaml`)：所有正向链接必须在同一轮对话中写入反向链接，确保知识图谱的一致性。`foundations` 作为终端实体豁免此规则。

5. **并行安全设计**：INIT MODE 使用 git worktree 隔离并行子代理，`merge=union` 策略处理共享文件合并，去重命令在 fan-in 后统一执行。

6. **抗重复记忆 (Anti-Repetition Memory)**：失败的 ideas 记录 `failure_reason` 并在 context_brief 中显式列出，防止 LLM 重复提出已被验证失败的方向。

### 9.2 技术栈总结

| 层次 | 技术 |
|------|------|
| Agent Runtime | Claude Code / OpenAI Codex / OpenCode |
| LLM 编排 | Skill-based (Markdown prompt with workflow steps) |
| 确定性引擎 | Python 3.9+ (stdlib http.server, threading, subprocess) |
| 图谱存储 | JSONL (edges.jsonl + citations.jsonl) |
| 知识存储 | Markdown (YAML frontmatter + body sections) |
| 图可视化 | Cytoscape.js (Web) + Obsidian Canvas (本地) |
| 实时推送 | Server-Sent Events (stdlib, no deps) |
| 外部 API | Semantic Scholar, DeepXiv, arXiv |
| Schema | YAML (entities, edges, xref, conventions) |
| 包管理 | requirements.txt (PyMuPDF, feedparser, requests, etc.) |

### 9.3 与论文中描述的关系

README 明确指出，论文中描述的四组件的完整实现 (`SciMem · SciFlow · SciDAG · SciEvolve`) 在 `paper` 分支（tag `arxiv-v1`）。`main` 分支是稳定的 Claude Code 版本，`autosci-codex` 和 `autosci-opencode` 分别是 Codex 和 OpenCode 的适配分支。

当前 `main` 分支实现的 OmegaWiki 系统包含了 SciMem（记忆系统）的核心功能，通过 30+ 个 LLM 技能将 SciFlow（科研流程）和 SciDAG（知识图谱）的概念以文件系统 + JSONL 的形式落地。

---

> **报告生成日期**: 2026年7月16日  
> **分析对象**: AutoSci main branch (Claude Code stable release)  
> **分析方法**: 完整阅读 README.md (640行)、runtime/loader.py (237行)、tools/research_wiki.py (2861行)、tools/serve.py (1075行)、tools/discover.py (1255行)、tools/visualize.py (726行)、tools/daily_arxiv.py (1534行)、runtime/schema/*.yaml (4个文件)、.claude/skills/ingest/init/ask/discover/ideate/daily-arxiv 等技能定义文件、app/ 前端代码等
