# [OpenKnowledge] 技术调研报告

> 项目地址: https://github.com/inkeep/open-knowledge (~2,934 stars)
> 调研版本: v0.32.0
> 技术栈: TypeScript (Bun@1.3.13 / Node.js ≥24), Hocuspocus (CRDT), Tiptap/ProseMirror (编辑器), Orama (全文检索), unified/remark (Markdown 解析)

---

## 1. 系统架构与设计哲学

### 定位

OpenKnowledge 是一个 **Markdown-CRDT 知识协作平台**，定位为 "Notion 与 VS Code 的融合"——提供所见即所得的 Markdown 编辑体验，同时通过 MCP (Model Context Protocol) 将知识库暴露给 AI Agent（Claude、Codex、Cursor 等）。它不是一个传统的"文档上传 → 向量化 → 知识图谱"的 RAG 系统，而是一个**本地优先、Git 同步、Agent 可操作的知识写作环境**。

### 核心痛点

- **AI Agent 无法感知和操作本地知识库**：Claude/Codex 等 Agent 通常只能通过 MCP 工具操作文件，但对 Markdown 内部的前置元数据（frontmatter）、反向链接、文档图谱等信息缺乏感知。
- **碎片化的 AI 写作体验**：开发者需要在编辑器、AI Chat、知识库之间来回切换。
- **知识图谱的可移植性**：基于 Git 的内容同步，而非专有数据库。

### 设计哲学

1. **本地优先 (Local-first)**：所有内容以 Markdown 文件形式存储在磁盘上，通过 Git 同步和版本控制。
2. **CRDT 协同编辑**：基于 Hocuspocus（Yjs 的 WebSocket 服务端）实现实时协作。
3. **Agent 原生**：通过 MCP 协议提供 20 个工具（`exec`, `search`, `write`, `edit`, `links` 等），Agent 可直接读写知识库。
4. **闭合知识循环 (Closed-loop)**：外部资源通过 `ingest` 拉入知识库，内部引用始终指向本地路径，不依赖外部 URL。
5. **分层知识架构**：external-sources → research → articles（Karpathy 式三层 wiki 架构）。

---

## 2. 数据流与管道步骤 (End-to-End Pipeline)

OpenKnowledge 的"管道"与传统 RAG 系统截然不同——它以**文件系统为真相源**，通过文件监控器和 CRDT 协同层实现实时索引，而非离线批处理管道。

### 步骤一：项目初始化 (`ok init` / Server Boot)

**关键文件**: `packages/server/src/server-factory.ts` (函数 `createServer`)

1. `ok init` 或 `ok start` 启动 Hocuspocus WebSocket 服务器
2. 读取 `contentDir`（来自 `.ok/config.yml` 中 `content.dir` 配置）
3. 构建 `contentFilter`：解析 `.gitignore` + `.okignore`，决定哪些文件进入索引
4. 初始化三大索引引擎（同步构建）：
   - `BacklinkIndex`：解析所有 Markdown 文件中的 Wiki 链接
   - `TagIndex`：提取所有 frontmatter 中的 tags
   - `Orama` 搜索语料库（全量构建 workspace search corpus）

### 步骤二：文件监控与增量索引

**关键文件**: `packages/server/src/file-watcher.ts`

1. Chokidar 监控 `contentDir` 下所有文件变化
2. **文件新增 (add)**：
   - 注册到 `fileIndex`（内存 Map，key 为 docName）
   - BacklinkIndex 增量更新：解析新文件的 Wiki 链接，更新反向链接图
   - 触发搜索语料库重建（通过 `generation counter` 单调递增触发）
3. **文件修改 (change)**：
   - BacklinkIndex 重新解析：`updateDocumentFromMarkdown()`
   - Wiki 链接变化时，增量更新所有受影响文档的入链/出链
   - 搜索语料库按需重建（fingerprint 变化检测）
4. **文件删除 (unlink)**：
   - 从索引中移除；清理反向链接残留

### 步骤三：搜索语料库构建 (Workspace Search Corpus)

**关键文件**: `packages/server/src/api-extension.ts` (函数 `buildWorkspaceSearchDocumentsFromIndex`)

```
buildWorkspaceSearchDocumentsFromIndex():
  ├── 遍历 getAllFilesIndex() (所有文件索引)
  ├── 分类文档为 pages (Markdown) / files (非 Markdown)
  ├── 对每个 Markdown page:
  │     ├── 读取文件内容 (readFile)
  │     ├── 提取标题 (extractPageTitle - 从 frontmatter 或首行 # 标题)
  │     ├── 缓存未变化的文档 (pageDocCache, key = mtime+size+path+inode+aliases)
  │     └── 创建 WorkspaceSearchDocument { kind:'page', path, title, content, modifiedTs }
  ├── 对每个非 Markdown file:
  │     └── 创建 WorkspaceSearchDocument { kind:'file', ... } (仅名称/路径可搜索)
  ├── 构建 Skills 搜索文档 (buildSkillSearchDocuments)
  ├── 推导文件夹搜索文档 (deriveFolderSearchDocuments)
  └── 创建 Orama 全文检索索引 (createWorkspaceSearchCorpus)
```

### 步骤四：文档"嵌入"（可选，API Key 驱动）

**关键文件**: `packages/server/src/embeddings/semantic-search-service.ts`

语义搜索是**延迟激活**的：
1. 语义搜索功能由 `search.semantic.enabled` 配置控制（项目本地层）
2. 仅在用户配置了 API Key（`~/.ok/secrets.yml` 或 `OK_EMBEDDINGS_API_KEY` 环境变量）时激活
3. **首次语义搜索触发** corpus embed（而非服务启动时）
4. 嵌入管道：`embedCorpus(docs) → ensureWarm() → runEmbedPass(docs)`

### 步骤五：向量缓存持久化

**关键文件**: `packages/server/src/embeddings/vector-cache.ts`

```
布局: <projectDir>/.ok/local/embeddings/
  ├── manifest.json     { schemaVersion, providerId, modelId, dims, chunkConfigId, entries }
  └── vec/<sha256>.bin  Float32 blob (chunkCount × dims)
```

- 内容寻址 (Content-addressed)：blob 按 SHA-256 命名
- mtime 预过滤：mtime 未变 → 跳过；mtime 变但 SHA-256 同 → 更新时间戳；SHA-256 变 → 重新嵌入
- 跨 provider/model/dims/chunk-config 隔离：任一参数变化 → 整个缓存失效重建

---

## 3. 实体与概念提取机制

### 重要发现：OpenKnowledge **没有**独立的实体/概念提取层

与传统的 LLM Wiki / RAG 系统（如使用 LLM 提取实体、构建知识图谱）不同，OpenKnowledge 的知识结构完全由**用户写作的 Wiki 链接**驱动。

### 提取技术

**基于语法解析的 Wiki 链接提取**（非 LLM 驱动），在 `BacklinkIndex` 中实现：

**关键文件**: `packages/server/src/backlink-index.ts`

```typescript
// Wiki-link 格式: [[Page Name]] 或 [[Page#anchor]] 或 [[Page|Display Text]]
const WIKI_LINK_RE = /\[\[([^\n#\[\]|]+)(?:#([^\n\[\]|]+))?(?:\|([^\n\[\]]+))?\]\]/y;

// Markdown link 格式: [text](./path.md) 或 [text](path.md)
const MD_LINK_RE = /\[([^\]\n]*)\]\((<[^>\n]+>|[^)\s\n]+)(?:\s+(?:"[^"\n]*"|'[^'\n]*'|\([^)\n]*\)))?\)/y;
```

在解析时使用 `classifyMarkdownHref` 和 `classifyWikiLinkTarget` 对链接目标进行分类：
- **内部文档链接**：指向其他 Markdown 文件的链接
- **外部链接**：`https://...` URL
- **断链 (Dead links)**：指向不存在的文档
- **孤儿文档 (Orphans)**：没有被任何文档引用的文档

### "实体"定义

OpenKnowledge 中的"实体"即**文档本身**，类型包括：

| 类型 | 说明 | 来源 |
|------|------|------|
| **Page** | Markdown (.md/.mdx) 文档 | 文件系统中的 Markdown 文件 |
| **Folder** | 文件夹（作为搜索结果的聚合体） | 从文档路径推导 |
| **File** | 非 Markdown 文件（按名称/路径搜索） | 文件索引中 kind='file' 的条目 |

**关系类型**（通过 Wiki 链接定义）：

| 关系 | 方向 | 存储 |
|------|------|------|
| **forward** (正向链接) | Doc A → Doc B | `BacklinkIndex.forward` Map |
| **backward** (反向链接) | Doc B ← Doc A | `BacklinkIndex.backward` Map (带 anchor + snippet) |
| **external** (外部链接) | Doc → URL | `BacklinkIndex.externalForward` Map |

> **注意**：OpenKnowledge 没有从文档内容中自动提取实体（人名、组织、概念等）的机制。知识的"结构化"完全依赖人工在写作时使用 Wiki 链接语法。
> 唯一的例外是测试工具 `ConceptEmbedder`（见第 4 节），它使用手动声明的概念列表进行确定性测试，而不是生产环境的自动提取。

### Graph Role 分类

**关键文件**: `packages/server/src/content/enrichment.ts` (函数 `computeGraphRole`)

基于入链/出链计数将文档分类为：
- **orphan**: 入链=0 且 出链=0
- **hub**: 入链 ≥ 5
- **connector**: 入链>0 且 出链>0
- **leaf**: 其他情况

---

## 4. 知识图谱、向量嵌入与算法细节

### Embedding 策略

#### 生产环境：OpenAI Embeddings

**关键文件**: `packages/server/src/embeddings/embedder.ts`

- **模型**: `text-embedding-3-small`（通过配置 `search.semantic.model` 可更改）
- **默认维度**: 1536（可通过 `search.semantic.dimensions` 配置）
- **Base URL**: `https://api.openai.com/v1`（可通过 `search.semantic.baseUrl` 指向其他兼容服务）
- **API Key 存储**: `~/.ok/secrets.yml`（0600 权限）或 `OK_EMBEDDINGS_API_KEY` 环境变量
- **安全策略**: 仅允许 HTTPS（localhost 除外），防止 API Key 明文泄露
- **请求方式**: HTTP POST 到 `/embeddings` 端点（无 SDK 依赖）

**批处理参数**:
```
maxBatchSize: 96 (每请求最多 96 个文本)
maxBatchChars: 96,000 (每请求字符预算)
docTimeoutMs: 30,000 (文档嵌入超时)
queryTimeoutMs: 8,000 (查询嵌入超时)
maxRetries: 4 (指数退避重试)
```

#### 文档分块策略 (Chunking)

**关键文件**: `packages/server/src/embeddings/chunking.ts`

```typescript
CHUNK_TARGET_CHARS = 8000   // ~2-4k tokens，远低于 8191 token 限制
CHUNK_OVERLAP_CHARS = 400   // ~5% 重叠，确保跨边界匹配不丢失
MAX_CHUNKS_PER_DOC = 80     // 单文档最大块数
```

- **纯字符预算**：不依赖 tokenizer，确定性分块
- **智能边界**：chunk 边界回退到最近的空格/换行（仅在 chunk 后半部分时）
- **上界保护**：超大文档（≈600KB+）截断，防止嵌入队列被阻塞
- **分块配置 ID**：`CHUNK_CONFIG_ID = "c8000-o400-m80"` 被纳入向量缓存键，配置变更自动失效旧缓存

#### 测试环境：确定性概念嵌入器

**关键文件**: `packages/server/src/embeddings/concept-embedder.ts`

- **用途**: 仅用于无网络测试环境
- **原理**: 每个手动声明的概念拥有一个"准正交基方向"；文本触发概念即累加基向量，加上 token-hash 底线
- **特点**: 纯确定性、无网络依赖、无 API Key 要求

#### 向量存储与缓存

**关键文件**: `packages/server/src/embeddings/vector-cache.ts`

```
缓存 Key 组成: providerId + modelId + dims + chunkConfigId
文档 Key: SHA-256(content)  → 内容寻址，相同内容共享向量
增量检查: mtime 过滤 → SHA-256 确认 → 嵌入新 chunks
GC 策略: retain(activeIds) → 清理已删除文档的向量
```

### 图技术实现

#### 链接图 (Link Graph)

**关键文件**: `packages/server/src/backlink-index.ts`

- **存储**: 内存中的双向图（`Map` + `Set`）
- **持久化**: 启动时从磁盘序列化加载，运行时 debounced 保存
- **数据结构**:
  ```typescript
  backward: Map<targetDocName, Map<sourceDocName, {anchor, snippet}>>  // 反向链接
  forward:  Map<sourceDocName, Set<targetDocName>>                      // 正向链接
  externalForward: Map<sourceDocName, Map<url, {label, snippet}>>       // 外部链接
  externalBackward: Map<url, Map<sourceDocName, {label, snippet}>>      // 外部反向链接
  ```
- **解析**: 逐行扫描 Markdown，使用 sticky regex（`/y` 标志）进行位置匹配，跳过代码块
- **Skill 链接**: 项目级和全局级 skill 的引用也纳入图结构（通过 `structuralBundleNeighbors` 建立 bundle 内链接）

> **注意**：这不是传统意义上的"知识图谱"（无 RDF 三元组、无 SPARQL、无实体类型）。它更像是 Wikipedia 的 Wiki 链接图——节点是文档，边是用户写作的超链接。

### 底层算法

#### 1. 全文检索：Orama BM25

**关键文件**: `packages/core/src/search/workspace-search.ts`

- **搜索引擎**: Orama v3（纯 JavaScript 全文搜索引擎）
- **算法**: BM25 变体（Orama 内部实现）
- **索引字段**: `title`, `name`, `path`, `pathSegments`, `content`
- **Boosting 权重**:
  ```
  full_text  intent:  title:8, name:7, path:5, pathSegments:4, content:1
  autocomplete:        title:10, name:9, path:5, pathSegments:4
  omnibar:             title:8, name:7, path:5, pathSegments:4
  ```
- **模糊匹配**: `full_text` 意图时 `tolerance=1`（允许 1 个编辑距离），其他意图 `tolerance=0`

#### 2. 词汇分级排序 (Lexical Bracket)

```
精确匹配 title/name:  bracket=700
精确匹配 path:         bracket=650
前缀匹配 title/name:   bracket=600
前缀匹配 pathSegments: bracket=550
包含匹配 title/name:   bracket=500
包含匹配 path:         bracket=450 (仅当作 pathOnly)
无词汇匹配:            bracket=-1
```

隐藏路径 (`.changeset/`, `.github/` 等) 乘以 0.5 惩罚因子。

#### 3. 分层主导排序 (Tier-Dominant Ranking)

```typescript
// Navigation score (omnibar/autocomplete)
score = lexical * TIER_DOMINANT_GAP(1000) + bodyNorm + recencyNorm + kindNudge

// Relevance score (full_text)
score = lexical + fullText * 20 + recency + canonicalKindAdjustment(kind)
```

关键设计：`TIER_DOMINANT_GAP=1000` 远大于二级信号范围，确保词汇匹配层级严格主导，高 bracket 的结果永远排在低 bracket 之前。

#### 4. 语义融合：RRF (Reciprocal Rank Fusion)

**关键文件**: `packages/core/src/search/workspace-search.ts` (函数 `rankWithVector`)

在语义搜索模式下，结果分为两层：

- **词汇层 (Lexical Tier)**: bracket > 0 的文档，沿用非语义模式的 combined score 排序
- **内容层 (Body Tier)**: bracket = 0 的文档，使用 RRF 融合：
  ```
  RRF(doc) = 1/(K + BM25_rank) + 1/(K + Vector_rank)  (K=60)
  ```
- **候选池扩展**: top-K 向量结果（默认 K=64）被并入候选池，使"概念相似但无词汇重叠"的文档也能被检索
- **Cosine Floor**: 默认为 0（仅过滤负余弦值），可通过 `search.semantic.similarityFloor` 配置硬阈值

#### 5. 结果类别限制 (Category Caps)

导航排名下，为防止某一匹配类别（如大量 pathOnly 结果）淹没其他：
- `lexical` 类别: 上限 = MAX_WORKSPACE_SEARCH_LIMIT(100)
- `body` 类别: 上限 = 6
- `pathOnly` 类别: 上限 = 4

---

## 5. 查询与检索实现 (Query & Retrieval)

### 查询流步骤

**端点**: `GET/POST /api/search`

**关键文件**: `packages/server/src/api-extension.ts` (函数 `buildSearchResponse`)

```
Step 1: 冷启动检查
  ├── isSearchCorpusWarming() ?
  │     └── Yes → 返回 { ready: false, results: [] }，通知调用方重试
  └── No → 继续

Step 2: 获取/构建搜索语料库
  ├── getWorkspaceSearchCorpus()
  │     ├── 计算 fingerprint (generation counter + skill stats)
  │     ├── 缓存命中 → 直接返回
  │     └── 缓存未命中 → buildWorkspaceSearchDocumentsFromIndex()
  │           ├── 遍历文件索引，读取所有 Markdown 文件
  │           ├── 构建 Orama 全文索引
  │           └── 缓存结果
  └── 返回 { corpus: WorkspaceSearchCorpus, truncated: boolean }

Step 3: 语义信号解析 (resolveSemantic)
  ├── 语义未启用 / 未 opt-in → 纯词汇路径
  ├── 语义启用 + opt-in →
  │     ├── 后台触发 embedCorpus()（延迟、增量、非阻塞）
  │     ├── intent === 'full_text' && queryLen >= 3 →
  │     │     ├── embedder.embed([query], {role:'query'})
  │     │     └── semanticSearch.queryScores(query, embeddableDocs)
  │     │           └── 对每个已嵌入文档：MAX(chunk cosine with query)
  │     └── 构建 WorkspaceSemanticInput { scores, ... }
  └── 返回 { input?, status, ... }

Step 4: 排名 (searchWorkspaceCorpus)
  ├── Orama full-text search (BM25) → fullTextScores
  ├── recencyScores (归一化到 [0,50])
  ├── lexicalScore (词汇 bracket 计算)
  ├── 候选池 Union (词汇匹配 ∪ BM25 命中 ∪ 语义 top-K)
  ├── 排名:
  │     ├── 无语义 → combinedScore + 排序
  │     └── 有语义 → rankWithVector
  │           ├── 词汇层: combinedScore 排序
  │           └── 内容层: RRF(BM25 rank, Vector rank) 排序
  └── finalizeResults (类别上限 + 种类配额)

Step 5: 结果构建
  ├── toSearchResultEntry → 计算 snippet (查询词周围 ±80/+120 字符)
  ├── 统计 semantic status (capable, applied, coverage)
  └── 返回 SearchSuccess { query, intent, results[], elapsedMs, ready, semantic? }
```

### 召回算法

| 召回层 | 算法 | 范围 | 信号 |
|--------|------|------|------|
| **词汇匹配** | 精确/前缀/包含 7-level bracket | 所有文档的 title/name/path | lexical bracket (0-700) |
| **全文检索** | Orama BM25 + boost | Markdown body + title/path | fullText score |
| **时间衰减** | Min-Max 归一化 (0-50) | 所有文档的 modifiedTs | recency score |
| **语义检索** | OpenAI embedding + Cosine + RRF | 已嵌入的 Markdown pages (非隐藏) | vector cosine |
| **文件夹匹配** | Path segment 推导 | 从文档路径推导的文件夹 | pathSegments field |

### Prompt 整合

OpenKnowledge **不直接拼接 Context 喂给 LLM**。相反，它的交互模式是：

1. **Agent 主动调用 MCP 工具**：
   - `exec("cat <path>")` — 读取完整文档（含 frontmatter + backlinks + 历史）
   - `search({ query })` — 排名检索
   - `links({ kind: "backlinks" | "forward" | "hubs" | "suggest" })` — 链接图遍历
   - `exec("grep -rn <term> <dir>")` — 字面量全文搜索

2. **Workflow 引导式 Agent**：
   通过 `workflow({ kind: "research" | "discover" | "ingest" | "consolidate" })` 返回详细的操作指令（见 `research-body.ts`, `discover-body.ts` 等），这些文件实际上是**Agent 的行为规范**而非数据管道。

3. **Research Workflow 的 Prompt 结构**（示例）：
   ```
   ## Proposed research rubric
   **Question:** [具体问题]
   **Dimensions to investigate:** [3-7 个维度]
   **Candidate sources:** [3-8 个候选来源]
   **Success criteria:** [2-3 个成功标准]
   **Output format:** Path A (article) | Path B (direct answer) | Path C (update)
   ```

   Agent 按照 8 步流程执行：Scan → Scope → Ingest → Analyze → Write → Link → Validate → Recap

4. **写作时的 Context 注入**：
   `exec("cat <path>")` 返回的内容**已包含丰富的上下文**：
   ```yaml
   # 响应结构
   path: "specs/2026-04-23-foo/SPEC.md"
   content: "完整的 Markdown 正文"
   frontmatter: { title, description, tags, status, ... }
   backlinks: [{ source, title, snippet }]   # 哪些文档链接到本文
   forwardLinks: [{ kind:'doc'|'external', ... }]  # 本文链接到哪里
   history: [{ commit, author, date }]        # 最近的编辑历史
   projectHistory: [{ commit, author, date }] # Git 项目历史
   graphRole: "connector"                     # 图结构角色
   ```

这种设计使得 Agent 可以在单次 `exec("cat")` 调用中获得文档的**写作内容 + 结构上下文 + 图谱位置 + 历史轨迹**，由 Agent 自行决定如何组合这些信息作为 LLM prompt。

---

## 附录：关键技术指标总结

| 维度 | 实现 |
|------|------|
| **Markdown 解析** | unified + remark-parse + remark-gfm + remark-frontmatter |
| **WYSIWYG 编辑器** | Tiptap (ProseMirror) 通过 @handlewithcare/remark-prosemirror 与 Markdown 互转 |
| **实时协同** | Hocuspocus (Yjs WebSocket) |
| **全文检索引擎** | Orama v3 (BM25) |
| **链接图** | BacklinkIndex (内存双向图 + 磁盘序列化) |
| **语义嵌入模型** | text-embedding-3-small (1536-dim, OpenAI-compatible API) |
| **分块策略** | 8000 字符目标，400 字符重叠 |
| **融合算法** | Reciprocal Rank Fusion (K=60) |
| **向量缓存** | SHA-256 内容寻址 + Float32 二进制存储 |
| **MCP 工具数** | 20 个 (exec, search, write, edit, delete, move, links, workflow, skills, lint, config, palette, preview_url, share_link, history, checkpoint, restore_version, conflicts, resolve_conflict, install) |
| **Workflow 类型** | 4 个 (ingest, research, consolidate, discover) |
| **图分析视图** | 6 种 (backlinks, forward, dead, orphans, hubs, suggest) |

---

> **结论**: OpenKnowledge 是一个以 **Markdown 文件系统 + CRDT 协同 + Wiki 链接图 + MCP Agent 接口** 为核心的本地知识协作平台。其"知识图谱"本质上是一个文档链接图（类似 Obsidian 的反向链接），而非带有实体类型和关系类型的语义图。其检索系统采用"BM25 + 词汇分级 + 可选语义 RRF 融合"的混合架构，语义嵌入通过 OpenAI API 实现且完全可选。整体设计哲学强调**用户的主动写作与链接**而非机器的自动理解与提取。
