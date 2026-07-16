# nashsu/llm_wiki 技术调研报告

> **GitHub:** [nashsu/llm_wiki](https://github.com/nashsu/llm_wiki) | **Stars:** 14,719⭐ | **License:** GPL v3.0 | **语言:** TypeScript + Rust (Tauri v2)

---

## 1. 系统架构与设计哲学

### 定位

nashsu/llm_wiki 是 Karpathy LLM Wiki 生态中 **Star 数最高、功能最完整**的实现——一个跨平台桌面应用，将 Karpathy 的抽象设计模式落地为 **Rust + React + Tauri v2** 的全栈产品。它在保留 Karpathy 三层架构（Raw Sources → Wiki → Schema）的基础上，进行了 19 项重大扩展。

**核心哲学：** "编译一次，持续使用"（Compile Once, Query Forever）。知识在 Ingest 时通过 LLM 编译为结构化的 Wiki 页面，后续查询直接使用已编译的知识图谱——而非每次都从零检索。

### 架构总览

```
┌──────────────────────────────────────────────────────┐
│               桌面应用 (Tauri v2)                      │
│                                                       │
│  ┌─────────────────────────────────────────────────┐ │
│  │  React 19 前端 (TypeScript + Vite)               │ │
│  │  ┌──────────┐ ┌───────────┐ ┌──────────────┐  │ │
│  │  │  Chat    │ │  Graph    │ │  Settings    │  │ │
│  │  │  Panel   │ │  Viewer   │ │  Panel        │  │ │
│  │  └──────────┘ └───────────┘ └──────────────┘  │ │
│  │  Zustand stores (chat/wiki/review/lint/...)     │ │
│  │  src/lib/ 核心算法 (~80+ 文件)                   │ │
│  └──────────────────┬──────────────────────────────┘ │
│                     │ Tauri IPC (invoke<>)            │
│  ┌──────────────────▼──────────────────────────────┐ │
│  │  Rust 后端 (src-tauri/src/)                      │ │
│  │  ┌────────────┐ ┌───────────┐ ┌─────────────┐  │ │
│  │  │ Agent RT   │ │ Search    │ │ API Server  │  │ │
│  │  │ (5550行)   │ │ Engine    │ │ (2720行)    │  │ │
│  │  └────────────┘ └───────────┘ └─────────────┘  │ │
│  │  pdf-extract | docx-rs | calamine | LanceDB    │ │
│  └──────────────────┬──────────────────────────────┘ │
└─────────────────────┼────────────────────────────────┘
                      │
         ┌────────────┼────────────┐
         ▼            ▼            ▼
    ┌─────────┐ ┌──────────┐ ┌──────────┐
    │ raw/    │ │  wiki/   │ │ .llm-wiki│
    │ sources │ │ entities │ │  configs │
    └─────────┘ └──────────┘ └──────────┘
```

**额外进程：**
- **MCP Server**（Node.js 独立进程）— 9 个 MCP Tools，通过 HTTP API 连接
- **Chrome Extension** — Web Clipper，通过 port 19827 通信

---

## 2. 数据流与管道步骤 (End-to-End Pipeline)

### Ingest 完整流程（两阶段 Chain-of-Thought）

基于 `src/lib/ingest.ts` (3376 行) 和 `src/lib/ingest-queue.ts` (821 行)：

```
Step 1: 文件上传/拖入
  └── GUI → enqueueTask() → 写入 .llm-wiki/ingest-queue.json

Step 2: 串行处理 (processNext)
  └── 每次只处理一个文件，防止并发 LLM 调用

Step 3: SHA256 增量缓存检查
  └── checkIngestCache(projectPath, sourceFileName, content)
       ├── SHA256(content) vs 缓存 → Hash 匹配 → 跳过 (零 token)
       └── 未匹配或文件丢失 → 继续

Step 4: 文档解析 (Rust 后端)
  └── pdf-extract (Rust) / docx-rs / calamine / MinerU 云解析
       支持: PDF, DOCX, PPTX, XLSX, MD, HTML, images

Step 5: 图片提取 (多模态)
  └── extractAndSaveSourceImages() → captionMarkdownImages()
       使用 Vision LLM 生成图片描述

Step 6: 🔬 阶段一 — ANALYSIS (结构化分析)
  └── LLM 调用 (Reasoning: off, Temperature: 0.1)
       Prompt 包含: purpose.md + schema.md + index.md + 源文档全文
       输出: {
         keyEntities: [{name, type, description}],
         keyConcepts: [{name, description, relatedEntities}],
         mainArguments: [string],
         contradictions: [{claim, conflictingWith}],
         recommendations: [{action, page, reason}],
         suggestedSearchQueries: [string]
       }

Step 7: ✍️ 阶段二 — GENERATION (Wiki 生成)
  └── LLM 调用 (Reasoning: off, Temperature: 0.1)
       Prompt 包含: 源文档 + 阶段一输出 + 语言指令 + 结构约束
       输出: 完整的 Markdown 文件集合:
         ├── wiki/sources/{slug}.md  (source summary)
         ├── wiki/entities/{Name}.md (entity pages)
         ├── wiki/concepts/{Name}.md (concept pages)
         ├── 更新的 wiki/index.md
         ├── 更新的 wiki/overview.md
         ├── wiki/log.md 条目
         └── Review items (含 pre-generated search queries)

Step 8: 文件写入
  └── executeIngestWrites():
       ├── 合并现有页面 (mergePageContent)
       ├── 路径安全检查 (拒绝 ../escape.md 等)
       └── Fallback: 确保 source summary 始终被创建

Step 9: 后处理
  └── saveIngestCache() → triggerAutoEmbedding() (如果启用)
       → updateIndexMd() → appendLogEntries()
       → invalidate graph cache → addReviewItems()

Step 10: 长文档分块处理
  └── 如果源文档 > 8,000 chars:
       ├── 分块 12K-60K chars each
       ├── 每个 chunk 单独 Analysis
       ├── 汇总 digest (< 15K chars)
       └── 用 digest 做 Generation
```

---

## 3. 实体与概念提取机制

### 提取技术

**两阶段 LLM CoT 提取**（非 NER 模型）。`src/lib/ingest.ts` 将提取过程分为：

- **阶段一 (Analysis)：** LLM 读取源文档全文 + 现有 Wiki 上下文（index.md, overview.md, purpose.md），输出结构化 JSON——包括 key entities、key concepts、矛盾、建议
- **阶段二 (Generation)：** LLM 基于阶段一的分析结果，生成完整的 entity/concept/source 页面，每个页面包含 YAML frontmatter（type, tags, sources[], created, updated）

### 实体与关系 Schema

从 `src/lib/wiki-page-types.ts` 和 `src/lib/wiki-schema.ts` 提取：

```
页面类型 (GENERATION_WIKI_TYPES):
  entity      → wiki/entities/{Name}.md     人员、组织、产品、数据集
  concept     → wiki/concepts/{Name}.md      理论、方法、框架
  source      → wiki/sources/{slug}.md       源文件摘要
  query       → wiki/queries/{slug}.md       保存的问答
  comparison  → wiki/comparisons/{slug}.md   并排对比
  synthesis   → wiki/synthesis/{slug}.md     综合分析

Frontmatter (必填):
  ---
  type: entity | concept | source | query | comparison | synthesis
  title: "Page Title"
  tags: [tag1, tag2]
  sources: [raw/sources/file.pdf]    ← 溯源链
  created: YYYY-MM-DD
  updated: YYYY-MM-DD
  ---

交叉引用: [[wikilink]] 语法
矛盾标记: contradictions: [other-page]  (frontmatter)
置信度: confidence: high | medium | low
```

### 源文件溯源

每个生成的 Wiki 页面通过 `sources: []` frontmatter 精确追溯到原始文件。`src/lib/source-identity.ts` 实现源文件身份标识，`src/lib/sources-merge.ts` 处理源文件数组的合并。

---

## 4. 知识图谱、向量嵌入与算法细节

### Embedding 策略

**可选，默认关闭。** 通过 `src/lib/embedding.ts` (691 行) 实现完整的 RAG 管线：

```
Pipeline:
  1. chunkMarkdown(content) → Chunk[]
     使用 src/lib/text-chunker.ts (603 行)
     策略: 段落对齐 + Markdown 标题感知
     参数: targetChars=1000, maxChars=1500, overlapChars=200
     安全规则: 不在代码块/表格内分割, YAML frontmatter 预剥离

  2. fetchEmbedding(title + headingPath + chunkText)
     支持任何 OpenAI-compatible /v1/embeddings 端点
     auto-halve retry: "input too long" 时自动减半重试

  3. vector_upsert_chunks(pageId, chunks)
     写入 LanceDB (Rust 后端, src-tauri/src/commands/vectorstore.rs)

搜索: fetchEmbedding(query) → LanceDB ANN → Cosine Similarity → top-K
  benchmark: Recall 58.2% (tokenized only) → 71.4% (tokenized + vector)
```

### 图技术实现

**图构建** (`src/lib/wiki-graph.ts` 305 行)：

```
buildRetrievalGraph(projectPath, dataVersion):
  
  Pass 1: 读取所有 wiki/*.md
    ├── extractFrontmatter(content) → title, type, sources[]
    └── extractWikilinks(content) → [[link1]], [[link2]], ...
  
  Pass 2: 解析链接 → 构建双向邻接矩阵
    ├── outLinksMap: A → {B, C, D}
    └── inLinksMap:  B ← {A, E}
  
  缓存: 模块级 cachedGraph，按 dataVersion 增量更新
```

**4-Signal Relevance Model** (`src/lib/graph-relevance.ts` 312 行)：

```
calculateRelevance(nodeA, nodeB, graph):
  
  Signal 1: Direct links (×3.0)
    (A→B 或 B→A) × 3.0
  
  Signal 2: Source overlap (×4.0) ← 最高权重
    |sources[A] ∩ sources[B]| × 4.0
  
  Signal 3: Adamic-Adar (×1.5)
    Σ (1 / log(degree(n))) for each common neighbor n
    惩罚通过高连接度节点产生的虚假关联
  
  Signal 4: Type affinity (×1.0)
    TYPE_AFFINITY[typeA][typeB]
    entity↔concept=1.2, entity↔entity=0.8, source↔source=0.5
```

**Louvain 社区发现** (`src/lib/wiki-graph.ts` LINES 32-105)：
- 使用 `graphology-communities-louvain` 库
- Resolution = 1（标准）
- Cohesion scoring：intraEdges / possibleEdges
- 低 cohesion (< 0.15) → 标记为 sparse（知识缺口信号）

**Graph Insights** (`src/lib/graph-insights.ts` 193 行)：
- **Surprising Connections：** 4 种信号评分（跨社区 +3, 跨类型 +2, 外设→Hub +2, 弱连接 +1）
- **Knowledge Gaps：** isolated nodes (度≤1), sparse communities (cohesion<0.15), bridge nodes (连接 3+ 社区)

### 可视化

- **sigma.js + graphology + ForceAtlas2** — WebGL 渲染，支持缩放/悬停交互
- 节点颜色：按页面类型或社区着色
- 边颜色：绿到灰 = 相关性强度

---

## 5. 查询与检索实现 (Query & Retrieval)

### 查询流步骤

**4 阶段混合检索管线：**

```
Phase 1: Tokenized Search (src/lib/search.ts 83 行)
  └── tokenizeQuery(query):
       ├── 英文: 停用词过滤 + 词干匹配
       ├── 中文: CJK bigram (汉字 → 相邻字对 + 单字 + 完整词)
       └── title match bonus: +10 score
       搜索范围: wiki/ + raw/sources/

Phase 1.5: Vector Semantic Search (可选, src/lib/embedding.ts)
  └── fetchEmbedding(query)
       → LanceDB ANN 检索 (Cosine Similarity)
       → 合并: boost 已有 match + 添加新 discovery

Phase 2: Graph Expansion (src/lib/graph-relevance.ts)
  └── Top 搜索结果为 seed nodes
       → 4-Signal Relevance Model 找相关页
       → 2-hop traversal with decay

Phase 3: Budget Control (src/lib/context-budget.ts 100 行)
  └── Configurable: 4K → 1M tokens
       分配: 60% wiki pages, 20% history, 5% index, 15% system
       按 relevance score 排序截断

Phase 4: Context Assembly
  └── 编号页面 (完整内容，非摘要)
       注入 system prompt (purpose.md + language + citation format)
       LLM 被指示引用: [1], [2]
```

### Rust Agent 运行时

`src-tauri/src/agent/runtime.rs` (5550 行) 实现工具调用 Agent：

```
Agent Chat 循环:
  1. routeQuery(message, mode) → RouterDecision
     意图分类: InternalSearch | ExternalSearch | RawSource | Graph | Write | Conversational
  
  2. buildSystemContext(project, router, skills)
     构建包含工具策略、权限模型的 system prompt
  
  3. 工具调用循环 (max 8 iterations):
     a. LLM 返回 {content, tool_calls[]}
     b. 执行工具: wiki.search | source.search | graph.search | web.search | shell.exec | workspace.*
     c. 权限检查: Read | Write | Network | Process 四种效应
     d. 如果 tool_calls 为空 → 返回最终回答
  
  4. 会话持久化: .llm-wiki/chats/{session_id}.json
     内存缓存: max 128 sessions, each max 40 messages
```

支持 5 种 Provider: OpenAI / Anthropic / Google / Ollama / Custom，每种有独立的 streaming 和 header 适配。

---

## 6. 特色系统

### 6.1 Review 异步审核系统
- LLM 在 Ingest 时标记需人工判断的条目
- Predefined actions: Create Page / Deep Research / Skip
- Pre-generated search queries（LLM 在 ingest 时生成优化搜索词）
- 不阻塞 ingest 管线

### 6.2 Deep Research 引擎
- Web Search: Tavily / SerpApi / SearXNG
- 最多 3 个并发研究任务
- LLM 优化研究主题（读取 overview.md + purpose.md）
- 研究结果自动 ingest 回 Wiki

### 6.3 MCP Server
- 9 个 MCP Tools: status, projects, files, read_file, reviews, search, chat, graph, rescan_sources
- 通过 `127.0.0.1:19828` HTTP API 通信
- Token 认证 + `127.0.0.1` 绑定安全
- 一键安装: `npx skills add https://github.com/nashsu/llm_wiki_skill.git`

### 6.4 Chrome Web Clipper
- Readability.js + Turndown.js (准确文章提取)
- HTTP API port 19827 (tiny_http)
- 自动触发 ingest 管线
- 多项目支持

### 6.5 Lint 系统
12 项自动化检查: orphan pages, broken wikilinks, no-outlinks, index completeness, frontmatter validation, stale content, contradictions, quality signals, source drift, page size, tag audit, log rotation

---

## 7. 总结

| 维度 | nashsu/llm_wiki |
|------|----------------|
| **部署复杂度** | 高 (Tauri v2 + Rust + Node.js) |
| **LLM 调用模式** | 两阶段 CoT Ingest + Agent 工具调用循环 |
| **实体提取** | 两阶段 LLM (Analysis → Generation) |
| **Embedding** | 可选 LanceDB (benchmark: +22.7% recall) |
| **向量搜索** | ✅ ANN + Cosine Similarity |
| **关键词搜索** | Tokenized + CJK bigram + title bonus |
| **图算法** | Louvain 社区发现 + 4-Signal Relevance + Graph Insights |
| **图可视化** | sigma.js + ForceAtlas2 (WebGL) |
| **Ingest 缓存** | SHA256 per-source + 文件存在验证 |
| **队列** | 持久化 JSON 队列 + 崩溃恢复 + 最多 3 次重试 |
| **部署模式** | 桌面应用 (macOS/Windows/Linux) |
| **MCP 支持** | ✅ 内置 Server (9 tools) |
| **Review 系统** | ✅ 异步队列 + pre-generated search queries |
| **适用规模** | 超大型 (>1000 源文件) |
| **核心优势** | 最完整实现、唯一带桌面 GUI、四阶段混合检索、Rust 性能 |
