# llm-wiki-compiler 技术调研报告

> 调研对象: [atomicstrata/llm-wiki-compiler](https://github.com/atomicstrata/llm-wiki-compiler) v1.1.0  
> 调研方法: 深入研读源码（`src/` 目录下约 200+ TypeScript 源文件）、README、与核心编译管线  
> 调研日期: 2026-07-16

---

## 1. 系统架构与设计哲学

### 1.1 项目定位

`llm-wiki-compiler`（npm 包名 `llm-wiki-compiler`，CLI 命令 `llmwiki`）是一个 **Node.js 知识编译器 CLI**，由 Ethan Joffe（atomicstrata）开发，截止调研时在 GitHub 上已获得约 1,773 颗星。它实现了 Andrej Karpathy 提出的 [LLM Wiki 模式](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)：将原始资料（论文、笔记、README、转录稿、PDF、图片、网页等）**编译**为可持久化的、相互链接的、引用可追溯的 Markdown Wiki，而不是在每次查询时重新从原始文件中检索。

### 1.2 “编译器”隐喻的核心

llmwiki 使用编译器隐喻来组织其架构：

| 编译器概念 | llmwiki 对应 | 源码实现 |
|-----------|-------------|----------|
| **词法分析/解析** | Ingest 阶段：抓取 URL、复制文件、解析 PDF/图片/YouTube 转录 | `src/ingest/web.ts`, `src/ingest/file.ts`, `src/ingest/pdf.ts`, `src/ingest/image.ts` |
| **语法分析** | Extraction Phase（提取阶段/Phase 1）：LLM 从每个源文件中提取结构化概念 | `src/compiler/extraction-phase.ts` |
| **语义分析** | 跨源概念合并、去重、冻结机制 | `src/compiler/extraction-merge.ts`, `src/compiler/deps.ts` |
| **代码生成** | Generation Phase（生成阶段/Phase 2）：LLM 为每个合并概念生成完整 wiki 页面 | `src/compiler/review-pipeline.ts`, `src/compiler/page-renderer.ts` |
| **链接器** | 双向 [[wikilink]] 解析、种子页面生成、索引/目录构建 | `src/compiler/resolver.ts`, `src/compiler/indexgen.ts`, `src/compiler/obsidian.ts` |
| **优化通道** | Incremental compilation（增量编译）、谱系追踪、引用规范化、新鲜度检测、嵌入向量刷新 | `src/compiler/hasher.ts`, `src/compiler/citation-normalize.ts`, `src/freshness/index.ts` |

### 1.3 整体项目结构

项目使用 TypeScript 编写，引擎要求 Node.js ≥ 24，使用 ESM 模块系统（`"type": "module"`）。关键依赖包括：

- `@anthropic-ai/sdk`: Anthropic Claude SDK（主要 LLM 后端，含 tool_use）
- `@anthropic-ai/claude-agent-sdk`: Claude Agent SDK 本地登录支持
- `openai`: OpenAI 兼容后端
- `@modelcontextprotocol/sdk`: MCP 服务器支持
- `commander`: CLI 命令框架
- `p-limit`: 并行 LLM 调用并发控制
- `zod` / `ajv`: Schema 验证
- `turndown`: HTML→Markdown 转换
- `pdf-parse`: PDF 解析
- `jsdom` / `@mozilla/readability`: 网页正文提取

### 1.4 核心架构分层

```
src/
├── commands/         # CLI 命令实现（compile, query, ingest, etc.）
├── compiler/         # ★ 核心编译管线
│   ├── index.ts              # 编译编排器（compileAndReport）
│   ├── extraction-phase.ts   # Phase 1: 概念提取
│   ├── prompts.ts            # LLM prompt 模板与 Anthropic tool schema
│   ├── page-renderer.ts      # 单页 LLM 生成
│   ├── review-pipeline.ts    # 审查管线（candidate 决策）
│   ├── extraction-merge.ts   # 跨源概念合并
│   ├── seed-pages.ts         # Schema 驱动的种子页面生成
│   ├── prompt-budget.ts      # 上下文窗口预算控制
│   ├── deps.ts               # 跨源语义依赖追踪
│   ├── hasher.ts             # SHA-256 变更检测
│   ├── resolver.ts           # [[wikilink]] 纯规则解析
│   ├── indexgen.ts           # wiki/index.md 构建
│   ├── provenance.ts         # 模型出处元数据
│   └── ...
├── providers/        # LLM 后端实现
│   ├── anthropic.ts          # Anthropic Claude（tool_use 支持）
│   ├── claude-agent.ts       # Claude Agent SDK
│   ├── openai.ts             # OpenAI / OpenAI 兼容
│   ├── ollama.ts             # 本地 Ollama
│   ├── copilot.ts            # GitHub Copilot
│   ├── minimax.ts            # MiniMax
│   └── voyage-embed.ts       # Voyage 嵌入向量
├── utils/            # 通用工具
│   ├── llm.ts                # callClaude() 通用 LLM 调用 + 重试
│   ├── provider.ts           # LLMProvider 工厂
│   ├── retrieval.ts          # 分块切割 + BM25 重排
│   ├── embeddings-chunks.ts  # Chunk 级嵌入向量
│   ├── embeddings-store.ts   # 嵌入向量存储 (V3)
│   └── constants.ts          # 全局常量
├── context/          # 上下文证据包构建
├── search/           # 检索管线
├── schema/           # Schema 层（页面类型、种子页面）
├── review/           # 审查策略评估
├── linter/           # Lint 规则（引用、交叉链接等）
├── eval/             # 质量评估
├── export/           # 导出格式（OKF, JSON, JSON-LD, GraphML 等）
├── import/           # 导入（OKF）
├── mcp/              # MCP 服务器
├── freshness/        # 页面新鲜度
├── profile/          # 可配置生命周期配置（CLP）
├── connectors/       # 外部数据连接器
└── ...
```

---

## 2. 数据流与管道步骤

### 2.1 编译管线全景

完整的增量编译管线由 `src/compiler/index.ts` 中的 `compileAndReport()` 函数编排，执行流程如下：

```
compileAndReport(root, options)
│
├── 1. acquireLock(root)                     # 获取 .llmwiki/lock 文件锁
│
├── 2. recoverJournalBeforeCompile(root)     # 重放崩溃日志（journal recovery）
│
├── 3. runCompilePipeline(root, options)     # 主流水线入口
│   │
│   ├── 3.1 loadSchema(root)                # 加载 .llmwiki/schema.json
│   ├── 3.2 loadReviewPolicy(root)          # 加载审查策略
│   ├── 3.3 CompileStateDraft.load(root)    # 加载 .llmwiki/state.json（增量状态）
│   ├── 3.4 detectChanges(root, state)      # SHA-256 哈希变更检测
│   │       └─ src/compiler/hasher.ts::hashFile() / detectChanges()
│   │
│   ├── 3.5 findAffectedSources()           # 跨源语义依赖追踪
│   │       └─ src/compiler/deps.ts::findAffectedSources()
│   │
│   ├── 3.6 bucketChanges()                 # 将变化分类为 toCompile/deleted/unchanged
│   │
│   ├── ★ Phase 1: runExtractionPhases()   # 概念提取
│   │   │  src/compiler/extraction-phase.ts
│   │   ├── extractSourcesLimited()         # p-limit 并发提取
│   │   │   └── extractForSource()          # 单个源文件提取
│   │   │       ├── readFile(sourcePath)
│   │   │       ├── readConfinedExtractionIndex()  # 读取 wiki/index.md 去重
│   │   │       └── extractConcepts()
│   │   │           ├── buildExtractionPrompt()    # 构建 prompt
│   │   │           └── callClaude({ tools: [CONCEPT_EXTRACTION_TOOL] })
│   │   │               └── src/utils/llm.ts::callClaude()
│   │   └── findLateAffectedSources()       # 晚期影响源检测
│   │
│   ├── 3.7 findFrozenSlugs() / freezeFailedExtractions()
│   │       └─ src/compiler/deps.ts
│   │
│   ├── ★ Phase 2: generatePagesPhase()     # 页面生成
│   │   │  src/compiler/index.ts::generatePagesPhase()
│   │   ├── mergeExtractions()             # 跨源概念合并
│   │   │   └─ src/compiler/extraction-merge.ts
│   │   ├── generateMergedPage() × N (p-limit 并发)
│   │   │   └─ src/compiler/review-pipeline.ts
│   │   │       ├── renderMergedPageContent()
│   │   │       │   └─ src/compiler/page-renderer.ts::renderMergedPageContent()
│   │   │       │       ├── loadRelatedPages()       # 加载 ≤5 个相关页面作为上下文
│   │   │       │       ├── buildPagePrompt()
│   │   │       │       ├── callClaude({ system, messages })  # 非 tool_use，直接文本
│   │   │       │       ├── normalizeCitationsInBody()
│   │   │       │       └── buildMergedFrontmatter()
│   │   │       ├── collectReviewDiagnostics()
│   │   │       │   ├── checkPageCrossLinks()        # Schema lint
│   │   │       │   └── collectCandidateProvenanceViolations()
│   │   │       ├── evaluatePolicy()                 # 审查策略评估
│   │   │       └── writeCandidate() OR return liveWrite
│   │   └── commitLivePageWrites()         # 事务性整批写入
│   │       └─ src/compiler/compile-write.ts::applyCompilePageWritesLocked()
│   │
│   ├── 3.8 persistExtractionStates()       # 持久化源文件状态
│   ├── 3.9 persistFrozenSlugs()            # 持久化冻结 slug
│   ├── 3.10 generateSeedPages()            # Schema 种子页面
│   │       └─ src/compiler/seed-pages.ts
│   │
│   ├── 3.11 finalizeWiki()                  # 最终化
│   │   ├── resolveAndApplyLinks()          # [[wikilink]] 解析
│   │   │   └─ src/compiler/resolver.ts
│   │   ├── draft.flush(root)               # 原子化写入 .llmwiki/state.json
│   │   ├── generateIndex()                 # 重建 wiki/index.md
│   │   │   └─ src/compiler/indexgen.ts
│   │   ├── generateMOC()                  # 构建 MOC（Obsidian 兼容）
│   │   │   └─ src/compiler/obsidian.ts
│   │   └── safelyUpdateEmbeddings()       # 刷新嵌入向量（非关键）
│   │       └─ src/utils/embeddings-refresh.ts
│   │
│   └── 3.12 logCompile()                   # 写入 log.md
│       └─ src/compiler/compile-report.ts
│
└── 4. releaseLock(root)                    # 释放锁
```

### 2.2 增量编译机制

增量编译是核心设计决策。变更检测由 `src/compiler/hasher.ts` 实现：

- **`hashFile(filePath)`**：读取文件内容，计算 SHA-256 哈希值
- **`detectChanges(root, prevState)`**：扫描 `sources/` 目录下的 `.md` 文件，与 `state.sources[file].hash` 对比，将每个文件标记为 `"new"`, `"changed"`, `"unchanged"`, 或 `"deleted"`
- 只有 `new` 和 `changed` 的文件才会通过 LLM 管线重新处理

### 2.3 审查模式（Review Mode）

当用户使用 `--review` 标志或审查策略触发时：
- 生成的页面不会直接写入 `wiki/concepts/`，而是作为 **candidate**（审查候选）持久化到 `.llmwiki/candidates/`
- Candidate 包含完整的页面正文、源文件状态快照、schema 违规和来源违规的 lint 结果
- 之后可通过 `llmwiki review approve` 或 `llmwiki review reject` 处理

### 2.4 源文件切片与上下文预算（Prompt Budget）

`src/compiler/prompt-budget.ts` 实现了 per-concept 的 prompt 预算控制：

- **常量**：`DEFAULT_PROMPT_BUDGET_CHARS = 200_000`（约 50k tokens）
- **环境变量覆盖**：`LLMWIKI_PROMPT_BUDGET_CHARS`
- **`buildBudgetedCombinedContent(concept, slices)`**：当多个源文件贡献同一概念，总字符数超过预算时，按比例均等截断每个源的贡献，追加 `[…truncated for prompt budget — see #39…]` 标记
- **`budgetAndNumberSource(file, content)`**：为规则提取器提供类似功能，包含行号添加
- **`numberLines()`**：给每行源码添加右对齐的 1-indexed 行号，让 LLM 能在 `^[filename.md:N-M]` 引用中精确引用行范围

---

## 3. 实体与概念提取机制

### 3.1 概念提取 Phase（Phase 1）

入口函数：`src/compiler/extraction-phase.ts::extractForSource()`

#### 3.1.1 Anthropic tool_use 结构化提取

与传统的自由文本 prompt 不同，llmwiki 使用 **Anthropic 的 tool_use 功能**来实现结构化概念提取。

Tool Schema 定义在 `src/compiler/prompts.ts::CONCEPT_EXTRACTION_TOOL`：

```typescript
export const CONCEPT_EXTRACTION_TOOL = {
  name: "extract_concepts",
  description: "Extract knowledge concepts from a source document",
  input_schema: {
    type: "object",
    properties: {
      concepts: {
        type: "array",
        items: {
          type: "object",
          properties: {
            concept:       { type: "string", description: "Human-readable concept title" },
            summary:       { type: "string", description: "One-line description" },
            is_new:        { type: "boolean", description: "True if not in existing wiki" },
            tags:          { type: "array", items: { type: "string" }, description: "2-4 categorical tags" },
            confidence:    { type: "number", description: "0..1 confidence scale" },
            provenance_state: {
              type: "string",
              enum: ["extracted", "merged", "inferred", "ambiguous"],
              description: "How this concept was produced"
            },
            contradicted_by: { type: "array", items: { slug, reason } }
          },
          required: ["concept", "summary", "is_new"]
        }
      }
    },
    required: ["concepts"]
  }
};
```

#### 3.1.2 tool_use 调用方式

`src/providers/anthropic.ts::AnthropicProvider.toolCall()`：

```typescript
async toolCall(system, messages, tools, maxTokens): Promise<string> {
  const anthropicTools = tools.map(t => ({
    name: t.name, description: t.description, input_schema: t.input_schema
  }));
  const response = await this.client.messages.create({
    model: this.model, max_tokens: maxTokens,
    system, messages,
    tools: anthropicTools,
    tool_choice: { type: "any" },  // ★ 强制 Claude 必须调用 tool
  });
  const toolBlock = response.content.find(block => block.type === "tool_use");
  if (toolBlock?.type === "tool_use") {
    return JSON.stringify(toolBlock.input);  // 返回 JSON 化的 tool input
  }
  // 回退到纯文本解析
}
```

关键点：
- `tool_choice: { type: "any" }` 强制 Claude 必须使用该 tool，确保结构化输出
- 返回的是 JSON 字符串，由 `parseConcepts()` 解析
- 如果 tool 调用失败，回退到纯文本块

#### 3.1.3 提取 Prompt 构建

`src/compiler/prompts.ts::buildExtractionPrompt(sourceContent, existingIndex)`：

```
You are a knowledge extraction engine. Analyze the following source document
and identify 3-8 distinct, meaningful concepts worth documenting as wiki pages.

For every concept, emit provenance metadata:
  - confidence: 0..1
  - provenance_state: 'extracted' | 'merged' | 'inferred' | 'ambiguous'
  - contradicted_by: slugs of conflicting concepts

{existing wiki index for dedup — 当 wiki/index.md 已存在时}

--- SOURCE DOCUMENT ---
{sourceContent with numbered lines}
```

#### 3.1.4 去重机制

提取阶段通过读取 `wiki/index.md` 作为去重上下文传给 LLM。`extractForSource()` 调用 `readConfinedExtractionIndex(root)` 读取索引内容，如果索引文件不存在或为越界符号链接（symlink escape），则返回空字符串继续提取而不中断管线。

### 3.2 跨源概念合并

`src/compiler/extraction-merge.ts::mergeExtractions()` 将多个源文件提取出来的相同概念合并为单个 `MergedConcept`：

```typescript
interface MergedConcept {
  slug: string;              // slugify(concept.concept)
  concept: ExtractedConcept; // 合并后的元数据
  sourceFiles: string[];     // 所有贡献源文件名
  combinedContent: string;   // 预算控制的合并内容
}
```

合并规则（`reconcileConceptMetadata()`）：
- **confidence**：取所有源的最小值（悲观聚合）
- **provenanceState**：强制设为 `"merged"`（一旦涉及多源）
- **contradictedBy**：按 slug 去重取并集
- **combinedContent**：通过 `buildBudgetedCombinedContent()` 构建，各源内容包裹在 `--- SOURCE: filename.md ---` 标记中

### 3.3 谱系元数据（Provenance）

`src/compiler/provenance.ts` 负责将以下元数据写入每个 wiki 页面的 YAML frontmatter：

- **`confidence`**：从提取的 concept 中复制
- **`provenanceState`**：`extracted | merged | inferred | ambiguous`
- **`contradictedBy`**：矛盾引用列表
- **`modelId`**：生成该页面的实际模型 ID（如 `claude-sonnet-4-6`）
- **`promptVersion`**：`v1`（prompt 合同版本，从 `src/compiler/prompts.ts::PROMPT_VERSION` 导出）

### 3.4 依赖追踪与冻结机制

`src/compiler/deps.ts` 实现了复杂的跨源依赖管理：

- **`findAffectedSources(state, directChanges)`**：构建 "概念→源文件" 反向索引，当源 A 变化时，所有与 A 共享概念的未变化源也被标记为 affected 并重新编译
- **`findLateAffectedSources(extractions, state, allChanges)`**：提取后检查——新源或提取出新概念的源可能导致额外的未变化源受影响
- **`findFrozenSlugs(state, changes)`**：当一个源被删除但其概念与其他源共享时，概念被"冻结"——保留已有内容不重新生成
- **`freezeFailedExtractions(draft, results, frozenSlugs)`**：提取失败的源保留旧概念列表并标记为需重试

---

## 4. 知识图谱、向量嵌入与算法细节

### 4.1 Schema 层与页面类型

`src/schema/types.ts` 定义了四种页面类型（PageKind）：

| Kind | 说明 | 默认最小 wikilink 数 |
|------|------|---------------------|
| `concept` | 独立概念/技术/模式 | 0 |
| `entity` | 具体实体（人、产品、组织） | 1 |
| `comparison` | 多概念对比分析 | 2 |
| `overview` | 领域顶层总览图 | 3 |

默认 schema (`src/schema/defaults.ts::buildDefaultSchema()`)：
- `version: 1`, `defaultKind: "concept"`, 无种子页面
- 当项目没有 `.llmwiki/schema.json` 时使用

**种子页面** (`SeedPage`) 是 schema 声明的非概念页面（overview/comparison/entity），由 `src/compiler/seed-pages.ts::generateSeedPages()` 在每次编译时生成：
- 接收 `relatedSlugs` 列表作为编织素材
- 通过 `buildSeedPagePrompt()` 的专用 prompt 生成
- 写入 `wiki/concepts/`，与概念页面统一管理

### 4.2 可配置生命周期配置（CLP）

CLP 是 v1.0 引入的核心扩展机制，将 llmwiki 从固定格式的知识编译器转变为可重用的领域知识基板。`.llmwiki/profile.json` 是唯一的配置文件，声明：

- 类型化实体（typed entities）、字段和定向关系
- 生命周期状态、转换证据和信任门（trust gates）
- 多阶段工作流和声明式动作
- 内容分层和检索行为

内置模板包括 `autosci`（研究系统：papers, ideas, experiments, manuscripts）和 `newsroom`（编辑系统：articles, desks, bylines）。

### 4.3 分块（Chunking）算法

`src/utils/retrieval.ts::splitIntoChunks()` 实现了段落对齐的分块策略：

**关键常量**（`src/utils/constants.ts`）：
- `CHUNK_TARGET_CHARS = 800` — 目标分块大小
- `CHUNK_MAX_CHARS = 1,400` — 硬上限
- `CHUNK_MIN_CHARS = 200` — 最小独立分块

**算法流程**：
1. **`extractParagraphs(body)`**：按 `\n{2,}` 分割段落，过滤空白
2. **`splitOversizedParagraph(paragraph)`**：超长段落（>1400 字符）→ 按句子分割（`/(?<=[.!?])\s+/`），超过上限则硬切
3. **`appendParagraph(buffer, piece, chunks)`**：累积段落直到超过 800 字符目标 → 刷新 buffer
4. **`mergeTrailingFragment(chunks)`**：末尾片段 < 200 字符则合并回前一个 chunk（受限于 1400 字符上限）

### 4.4 内容哈希与分块嵌入复用

`src/utils/embeddings-chunks.ts::refreshChunkEmbeddings()` 实现了智能的增量嵌入更新：

```typescript
async refreshChunkEmbeddings(records, existing, forceAll, batchSize, expectedDim) {
  // 1. 按 (slug, chunkIndex) 索引已有 chunk
  // 2. 为每个 page record 分块
  // 3. 对每个 chunk 计算 SHA-256 内容哈希 (前16字节hex)
  // 4. 如果已有 chunk 的 contentHash 匹配 → reuse（跳过嵌入）
  // 5. 否则加入 work list → batch embed
  // 6. slots 按页面顺序 + chunkIndex 重建，确保确定性输出
}
```

- **`hashChunkText(text)`**：`sha256(text).slice(0, 16)` — 16 字符十六进制摘要
- **`indexChunksByKey(chunks)`**：使用嵌套 `Map<slug, Map<chunkIndex, entry>>` 而非字符串拼接 key，防止 `#` 碰撞

### 4.5 嵌入向量存储（V3）

项目使用 V3 嵌入向量存储，支持：
- **Per-page 嵌入**：整个页面的向量（用于页面级语义检索）
- **Per-chunk 嵌入**：页面分块后的向量（用于 chunk 级检索，更高精度）
- **Content-hash-aware 更新**：通过内容哈希跳过未变化 chunk
- **批量嵌入**：`EMBED_BATCH_SIZES` 按 provider 配置（Anthropic: 128, OpenAI: 256, Ollama: 64）
- **Pending embeddings** 机制：`.llmwiki/pending-embeddings.json` 写前标记（write-ahead marker），确保即使刷新中途失败也在下次编译重试；最多重试 `MAX_PENDING_EMBEDDING_ATTEMPTS = 5` 次后隔离（quarantine）

### 4.6 BM25 重排序

`src/utils/retrieval.ts::rerankWithBm25()` 实现了标准的 BM25 算法作为语义相似度的补充：

```typescript
function rerankWithBm25<T extends RankableCandidate>(query, candidates) {
  const queryTerms = tokenize(query);              // 小写字母数字 token
  const docs = candidates.map(c => tokenize(c.text));
  const stats = buildCorpusStats(docs);
  // 最终得分 = BM25(query, doc) + baseScore * BASE_SCORE_WEIGHT(0.5)
  return rankByBm25Score(candidates, docs, queryTerms, stats);
}
```

BM25 参数：
- `BM25_K1 = 1.5`（词频饱和）
- `BM25_B = 0.75`（文档长度归一化）
- `BASE_SCORE_WEIGHT = 0.5`（语义相似度权重）

分词采用小写字母数字正则 (`/[a-z0-9]+/g`)，IDF 使用 Robertson-Spärck Jones 公式。

### 4.7 检索管线

`src/search/retrieval.ts::pickSearchRefs()` 实现了三级检索策略：

1. **Chunk 级语义检索**（最高精度）：使用嵌入向量找到最相关 chunk（`CHUNK_TOP_K = 30`，经 BM25 重排后保留 `CHUNK_RERANK_KEEP = 12`）
2. **Page 级语义检索**（备选）：当没有 chunk 命中时回退到页面级嵌入（`EMBEDDING_TOP_K = 15`）
3. **LLM 驱动索引选择**（终极兜底）：当没有可用的嵌入向量存储时，通过 `selectFallbackRefs()` 让 LLM 从页面列表中选择最相关的页面

每个命中记录携带 **qualified pageId**（如 `concepts/ml-papers`），确保概念页和查询页的同名 slug 不会混淆。

### 4.8 关系图与事件存储

项目支持类型化关系（typed relations）和事件审计：
- **关系存储**：`wiki/graph/relations.jsonl` — append-only JSONL，单条上限 `MAX_RELATION_RECORD_BYTES = 100_000`
- **事件存储**：`wiki/graph/events.jsonl` — append-only，hash-chained，封存锚点 `.llmwiki/events.head`
- 两个存储都使用 `wiki/graph/` 目录（默认 profile 不创建此目录）

---

## 5. 查询与检索实现

### 5.1 查询命令

`src/commands/query.ts` 和 `src/commands/query-save.ts` 实现了 `llmwiki query` 命令：

```
llmwiki query "your question here"
llmwiki query "your question here" --save   # 将答案保存回 wiki/queries/
```

### 5.2 上下文证据包（Context Pack）

`src/context/build.ts::buildContextPack()` 构建结构化的证据包，供 agent 消费：

```typescript
interface ContextPack {
  version: 1;
  prompt: string;           // 截断到 PROMPT_ECHO_MAX_LENGTH
  budget: ContextBudget;    // token 预算信息
  project: ContextProject;  // { root, pages, pendingCandidates, lint }
  primary: PrimaryEntry[];  // 排序后的主要页面
  neighbors: NeighborEntry[];  // 图谱邻居
  warnings: ContextWarning[];  // 警告（截断、嵌入降级等）
  gaps: GapEntry[];         // 图谱间隙
  suggestedActions: RecommendedAction[];  // 推荐下一步操作
}
```

Context Pack 的构建流程：
1. 加载 viewer snapshot（页面元数据、引用、图谱等）
2. 如果使用非默认 profile，补充类型化实体页面
3. **语义检索**：`retrieveSemanticChunks()` 从 V3 嵌入存储获取相关 chunk
4. **词法排序**：`rankPages()` 结合语义 hits + 词法匹配 + 前缀/精确匹配
5. **图谱扩展**：`expandGraphNeighborhood()` 遍历 [[wikilink]] 边
6. **内容分层投影**：CLP 6.2 — 根据 profile 声明的内容层级裁剪页面内容
7. **源窗口附接**：`attachSourceWindows()` 从引用 claim 提取源文件窗口
8. **预算裁剪**：`trimToBudget()` 确保包不超出 token 预算

### 5.3 混合检索策略总结

| 阶段 | 算法 | 说明 |
|------|------|------|
| 语义预筛选 | Cosine similarity | 对嵌入向量做余弦相似度计算，返回 top-k 页面/chunk |
| BM25 重排 | BM25 (K1=1.5, B=0.75) | 结合关键词精确匹配与语义得分 |
| 图谱扩展 | [[wikilink]] BFS | 沿 wikilink 边扩展至 depth 层 |
| 内容分层 | CLP content tiers | 根据 profile 声明控制每个页面暴露的内容深度 |
| LLM 兜底 | LLM 页面选择 | 无嵌入存储时，让 LLM 从候选列表中选择 |

### 5.4 图谱健康与评估

评估系统 (`src/eval/`) 提供多维度的质量度量：
- **Health Score**：整体 wiki 健康分
- **Page Health Distribution**：每个页面的健康分分布
- **Graph Health**：wikilink 图连通性
- **Citation Coverage/Precision**：引用覆盖率与精度
- **Citation Support**（full suite）：LLM 评判引用是否正确支持其 claim
- **Corpus Stats**：源文件统计数据
- **Regression Deltas**：与历史评估的差异

### 5.5 导出格式

llmwiki 支持多种导出格式，定义在 `src/export/`：

| 格式 | CLI Target | 说明 |
|------|-----------|------|
| **OKF** | `--target okf` | Open Knowledge Format（Google Cloud 项目），可移植 Markdown + frontmatter |
| **JSON** | `--target json` | 结构化 JSON 导出 |
| **JSON-LD** | `--target jsonld` | 链接数据格式 |
| **GraphML** | `--target graphml` | 图可视化格式 |
| **Marp** | `--target marp` | 演示文稿导出 |
| **llms.txt** | `--target llmstxt` | 单文件 LLM 上下文格式 |

---

## 6. 安全与信任模型

### 6.1 路径限制（Path Confinement）

整个代码库大量使用 `readConfinedWikiFile()` / `readWikiPageInDirOrWarn()` （`src/compiler/confined-wiki-read.ts`）来防止符号链接逃逸攻击：

- 所有 `wiki/concepts/` 和 `sources/` 下的文件读取都经过路径限制
- 符号链接目标超出项目根目录 → 丢弃并警告，使用空内容继续
- 确保恶意符号链接无法将外部文件内容注入 LLM prompt 或 wiki 输出

### 6.2 资源上限（Resource Caps）

`src/utils/constants.ts` 定义了全面的资源限制：

| 限制 | 值 | 说明 |
|------|-----|------|
| `MAX_SOURCE_CHARS` | 100,000 | 单个源文件最大字符数 |
| `GENERATED_PAGE_MAX_CHARS` | 500,000 | 编译生成页面最大字符数（5× 源上限） |
| `DEFAULT_PROMPT_BUDGET_CHARS` | 200,000 | LLM prompt 字符预算 |
| `MAX_LOCK_FILE_BYTES` | 256 | 锁文件大小上限 |
| `JOURNAL_PRESTATE_MAX_BYTES` | 16 MiB | Journal 预状态记录上限 |
| `MAX_PROFILE_BYTES` | 1 MiB | Profile 文件大小上限 |
| `MAX_WORKFLOW_SUBMIT_FILE_BYTES` | 1 MiB | 工作流上传文件上限 |
| `MAX_RELATION_STORE_BYTES` | 64 MiB | 关系存储文件上限 |

### 6.3 审查策略与信任门

- **Fail-closed config**：无效的审查策略配置会中止编译而非静默禁用审查
- **Profile floors**：字段契约、生命周期转换、关系计数、证据和 artifact 要求在页面/生命周期/工作流/导入/审批写入表面强制执行
- **外部数据不受信**：连接器数据通过受限 fetch 获取并暂存为审查候选
- **Imported knowledge is staged**：外部 OKF bundles 默认进入审查队列

---

## 7. 技术亮点总结

1. **两阶段编译器设计**：Phase 1（Anthropic tool_use 结构化提取概念）+ Phase 2（纯文本 LLM 生成完整页面），是编译范式在知识工程中的创新应用
2. **增量编译**：SHA-256 哈希驱动的变更检测 + 跨源依赖追踪 + 冻结/解冻机制，确保只重编译变化的部分
3. **结构化 tool_use 提取**：利用 Anthropic tool_use 而非自由文本 prompt 来确保概念提取的 schema 合规性和可解析性
4. **混合检索管道**：语义嵌入（余弦相似度）→ BM25 重排 → wikilink 图谱扩展 → LLM 兜底选择 → 内容分层投影，形成了多层精炼的检索漏斗
5. **Prompt 预算控制**：防止多源合并时超出 LLM 上下文窗口，按比例截断而非直接丢弃
6. **审查与安全模型**：路径限制、资源上限、审查候选队列、fail-closed 设计贯穿全线
7. **Obsidian 兼容**：`[[slug|Title]]` wikilink 格式 + MOC 页面 + YAML frontmatter 元数据，可直接在 Obsidian 中打开浏览
8. **Provider 可移植**：支持 Anthropic、Claude Agent SDK、OpenAI、Ollama、Copilot、MiniMax 六种后端
