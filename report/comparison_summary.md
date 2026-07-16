# Karpathy LLM Wiki 生态 — 横向对比与总结

> **调研日期：** 2026-07-16  
> **项目数量：** 9 个（全部 >1000 GitHub Stars）  
> **单份报告位置：** `D:/llm-wiki/report/{project}_technical_report.md`

---

## 一、生态全景图

```
              Karpathy LLM Wiki 生态光谱
              
  轻量 Agent Skill ←──────────────────────→ 重型全栈应用
  
  karpathy-llm-wiki   llm-wiki-agent   llmwiki   llm-wiki-compiler   obsidian-wiki   llm-wiki-skill   AutoSci   nashsu/llm_wiki   OpenKnowledge
  (1.5K⭐)             (3.2K⭐)         (1.4K⭐)   (1.8K⭐)            (2.9K⭐)        (2.2K⭐)         (1.5K⭐)   (14.7K⭐)         (2.9K⭐)
  
  纯 Prompt 指令      Python 脚本      MCP-first  TS 编译器          Python + CLI   Bash + TS         Python    Rust + React     TS monorepo
  零代码              + LLM 调用       + CRDT     + RPC               + GraphRAG     + 图谱引擎        + Skills   + Tauri           + CRDT
```

---

## 二、共同点 (Commonalities)

### 2.1 架构共识

所有 9 个项目无一例外地遵循 Karpathy 提出的**三层架构**：

```
Layer 1: Raw Sources (不可变原始资料)
Layer 2: Wiki Pages (LLM 生成的编译知识层)  
Layer 3: Schema / Skill (规则与工作流定义)
```

**每个项目都有自己的方式实现这三层：**

| 项目 | Layer 1 | Layer 2 | Layer 3 |
|------|---------|---------|---------|
| nashsu/llm_wiki | `raw/sources/` | `wiki/entities/`, `wiki/concepts/` | `schema.md` + `purpose.md` |
| llm-wiki-agent | `raw/` | `wiki/sources/`, `wiki/entities/`, `wiki/concepts/` | `CLAUDE.md` |
| open-knowledge | 工作区文件系统 | Markdown docs + Wiki links | `SKILL.md` (MCP ingest body) |
| obsidian-wiki | Obsidian vault `raw/` | `wiki/` (Markdown) | `.skills/llm-wiki/SKILL.md` |
| llm-wiki-skill | `raw/` | `wiki/` (Markdown) | `SKILL.md` (1133 行) |
| llm-wiki-compiler | `raw/` | `wiki/` (Markdown) | `profile.json` + `schema/` |
| AutoSci | `research/` 目录 | `entities/`, `concepts/`, `papers/` | `.claude/skills/*/SKILL.md` |
| karpathy-llm-wiki | `raw/` | `wiki/` | `SKILL.md` (187 行) |
| llmwiki | 用户文件夹 | `wiki/` (Markdown) | `guide.md` |

### 2.2 `[[wikilinks]]` 作为通用交叉引用语法

所有项目使用 Markdown 风格的 `[[wikilinks]]` 或等效的 `[text](path.md)` 作为页面间引用的标准语法。

### 2.3 LLM 作为核心"编译器"

每个项目都将 LLM 视为知识"编译器"而非检索器——知识在 Ingest 时编译，在 Query 时消费。区别仅在于谁调用 LLM、何时调用、如何调用。

### 2.4 人机协作分工

全部遵循"Human curates, LLM maintains"的角色划分：
- **人**负责选择源材料、审查质量、定义方向
- **LLM** 负责提取知识、生成页面、维护交叉引用

---

## 三、特色与差异 (Differences & Specialties)

### 3.1 多维度对比矩阵

| 维度 | nashsu/llm_wiki | llm-wiki-agent | open-knowledge | obsidian-wiki | llm-wiki-skill | llm-wiki-compiler | AutoSci | karpathy-llm-wiki | llmwiki |
|------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **实体抽取方式** | 两阶段 CoT LLM | 单次 LLM 调用 | 无内置（用户手写链接） | AST正则 + LLM | 两步式 CoT LLM | Anthropic tool_use | LLM Skill 编排 | 纯 LLM 自由发挥 | 纯外部Agent |
| **Embedding / 向量** | ✅ LanceDB | ❌ | ✅ text-embedding-3-small | ❌ | ❌ | ✅ 可选 | ❌ | ❌ | ❌ |
| **向量搜索** | ✅ | ❌ | ✅ RRF 融合 | ❌ | ❌ | ✅ 可选 | ❌ | ❌ | ❌ |
| **关键词搜索** | Tokenized + BM25-like | ❌ (Agent Read) | ✅ BM25 + 词汇分级 | ❌ (Agent Read) | Grep + 相关性排序 | ❌ | ❌ (Agent Read) | ❌ (Agent Read) | SQL LIKE |
| **图算法** | Louvain + 4-Signal | Louvain via NetworkX | 文档链接图 | LabelProp/Leiden + God Node | Louvain + 3-Signal 边权重 | ❌ | BFS 图遍历 | ❌ | ❌ |
| **图数据库** | sigma.js + graphology | vis.js | 内存 BacklinkIndex | GraphRAG 索引 | 自定义 JS 引擎 | ❌ | JSONL + Cytoscape | ❌ | SQLite/PostgreSQL |
| **Ingest 并发** | 串行队列 + 持久化 | 顺序 | 文件监控 | 并行批次 | 顺序 + 缓存 | 变更检测 + 增量 | Git worktree 并行 | 顺序 | 文件监控 |
| **部署复杂度** | 高 (Tauri + Rust) | 极低 (git clone) | 高 (TS monorepo) | 中 (Python venv) | 中 (Bash + Node) | 中 (Node.js) | 中 (Python + Claude) | 极低 (Skill 文件) | 中 (Python + Next.js) |
| **LLM Provider** | 7 种 | 1 种 (litellm) | 外部 MCP Agent | 外部 Agent Skill | 外部 Agent Skill | 6 种 (可切换) | Claude Skills | 外部 Agent Skill | 外部 MCP Agent |
| **增量缓存** | SHA256 per-source | SHA256 per-page (图) | 向量缓存 | SHA256 per-page | SHA256 自愈缓存 | SHA256 per-source | ❌ | ❌ | 文件 mtime |
| **适用规模** | 超大型 (>1000 文件) | 小型 (<200 页) | 中型团队协作 | 中型个人 Vault | 中型 | 小型-中型 | 大型学术研究 | 小型 | 小-中 + 定时维护 |
| **MCP 支持** | ✅ 内置 Server | ❌ | ✅ 内置 | ❌ (Agent Skill) | ❌ (Agent Skill) | ❌ | ❌ (Claude Skill) | ❌ (Agent Skill) | ✅ 内置 Server |
| **Review 系统** | ✅ 异步队列 | ❌ (Lint 报告) | ❌ | ✅ 信任账本 | ❌ (Lint 检查) | ❌ | ❌ | ❌ (Lint 报告) | ❌ |

### 3.2 各项目独门绝技

#### 🥇 nashsu/llm_wiki — 最完整的企业级实现
- **独一无二：** 完整的 Tauri 桌面应用 + Rust 后端 + React 前端
- **四阶段混合检索：** Tokenized + Vector (LanceDB) + Graph Expansion + Budget Control
- **4-Signal Relevance Model：** direct link ×3.0 + source overlap ×4.0 + Adamic-Adar ×1.5 + type affinity ×1.0
- **Rust Agent Runtime：** 5550 行，工具调用循环 + 权限模型 + Skill 系统
- **适用：** 需要全功能桌面 GUI、大规模知识库、向量搜索的用户

#### 🥈 obsidian-wiki — 最强大的图分析引擎
- **独一无二：** Label Propagation / Leiden 社区检测、God Node 排名、Surprising Connections
- **GraphRAG 索引：** BFS 多跳路径查找，6 层分层检索协议
- **双层实体提取：** 本地 AST 正则（12 种语言代码）+ LLM 语义提取
- **信任账本：** 人工审核信任度追踪系统
- **适用：** Obsidian 重度用户、需要图分析深度的场景

#### 🥉 llm-wiki-compiler — 最优雅的"编译器"设计
- **独一无二：** 使用 Anthropic 的 `tool_use` 功能进行结构化概念提取
- **两阶段编译器：** Extraction Phase（tool_use 强制调用）→ Generation Phase（纯文本生成）
- **增量编译：** 跨源依赖追踪 + 变更检测 + 受影响源重新编译
- **适用：** 需要确定性高、结构化输出强的批量编译场景

#### 🏅 AutoSci — 最大型的科研自动化系统
- **独一无二：** 30+ Claude Skills 编排，覆盖完整科研生命周期
- **9 种实体类型 + 14 种边类型：** 最丰富的知识 Schema
- **Git worktree 并行摄入：** 科研级大规模文献处理
- **5 阶段构思流程：** 从问题定义到实验设计的完整链路
- **适用：** 学术研究人员、需要自动化文献综述和知识发现的团队

#### 🏅 llmwiki (lucasastorian) — 最彻底的"Agent-First"设计
- **独一无二：** Claude Routines（定时自主维护），Wiki 可完全无人值守运行
- **MCP-first 架构：** 自身不做任何 LLM 调用，全部委托给外部 Agent
- **VaultFS 抽象层：** 同一套代码同时支持 SQLite 和 PostgreSQL
- **高亮笔记系统：** Chrome Extension 捕获的高亮和评论自动纳入 Wiki
- **适用：** 希望 Wiki "自己维护自己"的用户、定时更新的个人知识库

#### 🏅 OpenKnowledge — 最先进的实时协同
- **独一无二：** CRDT 实时协同编辑（非 Git-based）
- **RRF（Reciprocal Rank Fusion）：** BM25 + 语义嵌入的标准化融合
- **7 级词汇分级：** 精确匹配始终优于语义匹配
- **适用：** 团队实时协作、需要多人同时编辑 Wiki 的场景

---

## 四、技术路线分化

### 4.1 Ingest 策略分化

```
                     Ingest 策略光谱

  单次 LLM 调用 ←────────────────────────→ 多阶段 LLM 调用
  
  karpathy-llm-wiki   llm-wiki-agent   AutoSci   llm-wiki-skill   nashsu/llm_wiki   llm-wiki-compiler
  (自由发挥)          (JSON 结构化)    (9步Skill)  (2步CoT)        (2步CoT + 队列)   (tool_use + 纯文本)
  
  llmwiki: 完全无内置 Ingest — 100% 外部 Agent 完成
  obsidian-wiki: 8 步 Skill 管线 + 本地 AST 预提取
  OpenKnowledge: 无内置 Ingest — 依赖用户手写 Wiki
```

### 4.2 搜索/检索策略分化

```
                    搜索策略光谱

  纯 Agent Read ←─────────────────────────→ 全混合检索管线
  
  karpathy-llm-wiki   llm-wiki-agent   AutoSci   llmwiki   llm-wiki-skill   obsidian-wiki   OpenKnowledge   nashsu/llm_wiki
  (index.md 导航)     (Agent 判断)     (BFS遍历)  (SQL LIKE) (Grep+排序)    (6层协议)      (BM25+RRF)      (4阶段混合)
  
  llm-wiki-compiler: 无内置搜索
```

### 4.3 图分析深度分化

```
                    图分析深度光谱

  无图分析 ←──────────────────────────────────→ 最深度图分析
  
  karpathy-llm-wiki   llmwiki   OpenKnowledge   llm-wiki-compiler   llm-wiki-agent   llm-wiki-skill   nashsu/llm_wiki   obsidian-wiki   AutoSci
  (仅文件链接)        (引用图)   (文档链接图)    (无图分析)          (Louvain+NX)    (Louvain+3信号)  (4-Signal)       (Leiden+GodNode) (14种边)
```

---

## 五、推荐使用矩阵

| 使用场景 | 首选方案 | 备选方案 |
|---------|---------|---------|
| **个人研究知识库（GUI 优先）** | nashsu/llm_wiki | obsidian-wiki |
| **极简零配置启动** | karpathy-llm-wiki | llm-wiki-agent |
| **定时自主维护的 Wiki** | llmwiki | llm-wiki-agent |
| **学术文献管理** | AutoSci | obsidian-wiki |
| **批量文档编译** | llm-wiki-compiler | nashsu/llm_wiki |
| **团队实时协作** | OpenKnowledge | llmwiki (hosted) |
| **最大规模知识库** | nashsu/llm_wiki | AutoSci |
| **最深度图分析** | obsidian-wiki | nashsu/llm_wiki |
| **Claude Code 用户** | karpathy-llm-wiki | llm-wiki-agent |
| **不想写一行代码** | karpathy-llm-wiki | llmwiki |

---

## 六、技术债务与共同挑战

### 6.1 共同痛点

| 挑战 | 影响的项目数 | 说明 |
|------|:-----------:|------|
| **无法处理超大型文档** | 7/9 | 大多数项目依赖 LLM context window (8K-200K)，对 >200K token 的文档无法单次处理 |
| **多语言支持薄弱** | 8/9 | 除 nashsu/llm_wiki（中/英 i18n）外，其他项目几乎只考虑英文 |
| **缺乏版本控制** | 6/9 | 多数项目无内置版本管理；依赖外部 Git |
| **矛盾检测不成熟** | 7/9 | 多数仅标记矛盾，无自动解决机制 |
| **Graph 可扩展性** | 5/9 | 大型图 (>1000 节点) 的布局/分析存在性能瓶颈 |

### 6.2 演化趋势

```
v0: Karpathy Gist (Prompt 模式)
  ↓
v1: Agent Skill (karpathy-llm-wiki, llm-wiki-agent)
  ↓
v2: 编译型工具 (llm-wiki-compiler, llm-wiki-skill)
  ↓
v3: 全栈应用 (nashsu/llm_wiki, llmwiki, OpenKnowledge)
  ↓
v4: 生态系统集成 (MCP, Obsidian, Chrome Extension, Claude Routines)
  ↓
v5: 自主维护 (Routines, Cron, Auto-watch)
```

---

## 七、总结

Karpathy LLM Wiki 生态已经从一段抽象的 Prompt 设计模式，演化为一个多样化的工程实践光谱。9 个 >1000 Stars 的项目各自代表了不同的设计取舍：

- **最完整：** nashsu/llm_wiki — 一个真正的桌面应用产品
- **最纯粹：** karpathy-llm-wiki — 仅用 187 行 SKILL.md 实现了核心哲学
- **最深度图分析：** obsidian-wiki — Leiden + Label Propagation + God Node
- **最 Agent-Native：** llmwiki — 定时自主维护，人只需 curation
- **最学术：** AutoSci — 30+ Skills 覆盖完整科研生命周期
- **最团队：** OpenKnowledge — CRDT 实时协同

**共同的核心理念始终如一：** 知识应该被"编译"、沉淀和积累，而非每次都从零开始检索。这正是 Karpathy LLM Wiki 模式与传统 RAG 的根本区别——也是这个生态持续吸引开发者的原因。

---

*全部 9 份单项报告 + 1 份横向对比总结，位于 `D:/llm-wiki/report/`。*
