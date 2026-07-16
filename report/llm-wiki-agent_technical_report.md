# llm-wiki-agent (SamurAIGPT) 技术调研报告

> **GitHub:** [SamurAIGPT/llm-wiki-agent](https://github.com/SamurAIGPT/llm-wiki-agent) | **Stars:** 3,216⭐ | **License:** MIT | **语言:** Python 3.10+

---

## 1. 系统架构与设计哲学

### 定位

llm-wiki-agent 是一个**纯 Agent Skill**——它不是一个独立的服务器或数据库应用，而是一套"指令文件 + Python 辅助工具"，需要运行在 Claude Code、Codex、Gemini CLI 等 AI Coding Agent 内部。

**核心创新：** 将 Karpathy LLM Wiki 模式实现为可复用的 Agent Skill 包（而非桌面应用），最大程度降低了部署门槛——无需 API key 配置、无需数据库、无需向量存储。Agent 本身就是整个"后端"。

### 架构总览

```
┌──────────────────────────────────────────┐
│        AI Coding Agent                    │
│  (Claude Code / Codex / Gemini CLI)      │
│                                           │
│  ┌────────────────────────────────────┐  │
│  │  CLAUDE.md / AGENTS.md / GEMINI.md │  │
│  │  (5000+ 字的工作流指令)             │  │
│  └──────────────┬─────────────────────┘  │
│                 │ 指导行为                 │
│  ┌──────────────▼─────────────────────┐  │
│  │  Agent 直接执行:                    │  │
│  │  - Read/Write/Grep 文件             │  │
│  │  - 调用 LLM API (via litellm)       │  │
│  │  - 运行 Python 工具脚本              │  │
│  └──────────────┬─────────────────────┘  │
└─────────────────┼────────────────────────┘
                  │
     ┌────────────┼────────────┐
     ▼            ▼            ▼
┌─────────┐ ┌─────────┐ ┌──────────┐
│  raw/   │ │  wiki/  │ │  graph/  │
│ (不可变) │ │ (Agent  │ │ (vis.js) │
│         │ │  维护)   │ │          │
└─────────┘ └─────────┘ └──────────┘
```

**零依赖哲学：** 不需要安装数据库、向量存储、或 Web 服务器。Agent 直接读写 Markdown 文件，Python 脚本仅做确定性计算（图构建、哈希校验）。

---

## 2. 数据流与管道步骤 (End-to-End Pipeline)

### Ingest 完整流程

从 `CLAUDE.md` (L64-81) 和 `tools/ingest.py` 提取的精确步骤：

```
Step 1: 格式转换 (auto-convert)
  └── detect_format(source_path)
       ├── .md → 直接读取
       └── .pdf/.docx/.pptx/... → markitdown.convert() → .md
           支持: PDF, DOCX, PPTX, XLSX, HTML, CSV, JSON, XML,
                 EPUB, RST, IPYNB, WAV, MP3

Step 2: 构建 Wiki 上下文
  └── build_wiki_context()
       ├── read wiki/index.md (目录)
       ├── read wiki/overview.md (全局摘要)
       └── read 最近 5 个 source pages (矛盾检测)

Step 3: 读取 Schema 指令
  └── read CLAUDE.md (SCHEMA_FILE = CLAUDE.md)
       包含: 页面格式、命名规范、Ingest/Query/Lint 工作流

Step 4: ⚡ 单次 LLM 调用 (结构化的 Ingest Prompt)
  └── call_llm(prompt, max_tokens=8192)
       通过 litellm 调用 (provider-agnostic):
         LLM_MODEL 环境变量指定模型
         默认: claude-3-5-sonnet-latest
       
       Prompt 结构:
         "Schema and conventions: {CLAUDE.md}"
         "Current wiki state: {index.md + overview.md + recent sources}"
         "New source: {full_content}"
         → 要求返回单一 JSON 对象:
           {
             "title": "...",
             "slug": "...",
             "source_page": "full markdown with [[wikilinks]]",
             "index_entry": "- [Title](sources/slug.md) — summary",
             "overview_update": "updated overview.md or null",
             "entity_pages": [{path, content}, ...],
             "concept_pages": [{path, content}, ...],
             "contradictions": [...],
             "log_entry": "..."
           }

Step 5: 写入文件
  └── 解析 JSON → 写入:
       ├── wiki/sources/{slug}.md
       ├── wiki/entities/{Name}.md (每个 entity)
       ├── wiki/concepts/{Name}.md (每个 concept)
       ├── wiki/overview.md (如果更新)
       └── wiki/index.md (追加条目)

Step 6: Post-Ingest 验证 (validate_ingest)
  └── 检查 newly created pages:
       ├── broken [[wikilinks]] in new pages
       └── unindexed pages (不在 index.md 中)

Step 7: 汇报
  └── 打印: created/updated pages, contradictions, validation results
```

**关键差异 vs nashsu/llm_wiki:**
- **单次 LLM 调用** (而非两阶段 CoT)：所有生成在一个 Prompt 中完成
- **无增量缓存**：没有 SHA256 去重（依赖 Agent 记忆上下文避免重复）
- **无持久化队列**：Agent 会话即队列
- **无 Embedding / 向量搜索**：完全依赖 `[[wikilinks]]` 图结构检索

---

## 3. 实体与概念提取机制

### 提取技术

**纯 Prompt 驱动，非 NER 模型：** llm-wiki-agent 完全依赖 LLM 的语义理解能力在一次 API 调用中完成所有实体和概念提取。`ingest.py` 的 Prompt (L207-237) 要求 LLM 返回结构化的 `entity_pages[]` 和 `concept_pages[]` 数组。

### 实体与概念 Schema

```
Entity (实体):
  - 类型: people, companies, projects, products, datasets
  - 页面路径: wiki/entities/{Name}.md
  - 命名: TitleCase (OpenAI.md, SamAltman.md)
  - Frontmatter: title, type: entity, tags, sources, last_updated

Concept (概念):
  - 类型: ideas, frameworks, methods, theories, techniques
  - 页面路径: wiki/concepts/{Name}.md
  - 命名: TitleCase (ReinforcementLearning.md, RAG.md)
  - Frontmatter: title, type: concept, tags, sources, last_updated

Source (源文件):
  - 页面路径: wiki/sources/{slug}.md
  - 命名: kebab-case (attention-is-all-you-need.md)
  - 内容模板: Summary / Key Claims / Key Quotes / Connections / Contradictions

Synthesis (综合):
  - 页面路径: wiki/syntheses/{slug}.md
  - 来源: query 结果手动保存
```

### 关键 Prompt 设计

从 `ingest.py` L224-237 的 JSON schema 可以看出，LLM 被要求一次性输出：
- `source_page`: 完整的源文件摘要页（含内联 `[[wikilinks]]`）
- `entity_pages[]`: 每个实体的完整 Markdown 页面
- `concept_pages[]`: 每个概念的完整 Markdown 页面
- `contradictions[]`: 与现有 Wiki 的矛盾

**指令强调：** `"Aggressively convert key people, products, concepts and projects into [[Wikilinks]] inline in the text. Omitting [[ ]] for known terms is a failure."`

---

## 4. 知识图谱、向量嵌入与算法细节

### Embedding 策略

**无向量嵌入。** llm-wiki-agent 不生成 embeddings，不使用向量数据库。查询完全依赖 Agent 直接 Read 文件 + LLM 上下文理解。

### 图技术实现

图构建由 `tools/build_graph.py` (1240 行) 独立完成，分为两遍扫描：

**Pass 1: 确定性 `[[wikilink]]` 边 (EXTRACTED)**
```python
# build_extracted_edges() — build_graph.py L116-139
for p in pages:
    for link in extract_wikilinks(content, unique=True):
        target = stem_map.get(link.lower())
        if target and target != src:
            edges.append({type: "EXTRACTED", confidence: 1.0})
```

**Pass 2: LLM 推断语义边 (INFERRED / AMBIGUOUS)**
```python
# build_inferred_edges() — build_graph.py L180-325
# 对每个页面，调用 LLM 推断未通过 [[wikilink]] 连接的隐式关系
prompt = """Analyze this wiki page and identify implicit semantic relationships...
Return ONLY a JSON object containing an "edges" array...
Rules:
- Confidence >= 0.7 → INFERRED, < 0.7 → AMBIGUOUS
- Do not repeat edges already in the extracted list"""
# 使用 claude-3-5-haiku-latest (快速模型)
```

**边类型与可视化：**
| Edge Type | Color | Confidence | Source |
|-----------|-------|------------|--------|
| EXTRACTED | #555555 (灰) | 1.0 | 显式 `[[wikilinks]]` |
| INFERRED | #FF5722 (红) | ≥ 0.7 | LLM 高置信推断 |
| AMBIGUOUS | #BDBDBD (浅灰) | < 0.7 | LLM 低置信推断 |

### 底层算法

**Louvain 社区发现** (via NetworkX)：
```python
# detect_communities() — build_graph.py L349-371
G = nx.Graph()
for n in nodes: G.add_node(n["id"])
for e in edges: G.add_edge(e["from"], e["to"])
communities = nx_community.louvain_communities(G, seed=42)
```

**图健康分析** (via NetworkX)：
- **God Nodes** (Hub 检测): `degree > μ + 2σ` → 标志为超连接节点
- **Orphan Pages**: `degree == 0` → 孤立页面
- **Fragile Bridges**: 社区间仅有 1 条边的脆弱连接
- **Phantom Hubs**: 被 3+ 页面引用但未创建的缺失实体页
- **Isolated Communities**: 零外部连接的"知识孤岛"

**增量缓存与断点续传：**
- `graph/.cache.json`: SHA256 页面哈希，仅变更页面重新推断
- `graph/.inferred_edges.jsonl`: JSONL 断点文件，支持中断后恢复

```python
# build_graph.py L142-169
def load_checkpoint():
    """从 JSONL 恢复已完成的推断"""
    for line in INFERRED_EDGES_FILE:
        record = json.loads(line)
        completed.add(record["page_id"])
        for edge in record.get("edges", []):
            # 恢复边...
```

---

## 5. 查询与检索实现 (Query & Retrieval)

### 查询流步骤

**无检索管线，完全依赖 Agent 能力** (`CLAUDE.md` L155-163)：

```
Step 1: Agent 读取 wiki/index.md 识别相关页面
Step 2: Agent 用 Read 工具读取目标页面
Step 3: Agent 综合所有页面内容，以内联 [[PageName]] 格式引用
Step 4: 询问用户是否保存到 wiki/syntheses/{slug}.md
```

**关键限制：**
- 无语义搜索——Agent 必须读 `index.md` 手动匹配
- 无 rerank——依赖 LLM 自身的判断力
- 对大 Wiki (>200 页) 可能因上下文限制而遗漏相关页面

### 召回算法

**无混合检索。** 检索过程为：
1. `index.md` 线性扫描（Agent 阅读）
2. Agent 自主决定哪些页面相关
3. Agent 逐个 Read 目标页面
4. LLM 合成答案

**对比 nashsu/llm_wiki 的 4 阶段检索管线**（Tokenized → Vector → Graph → Budget），llm-wiki-agent 的查询是最简化的——适合小型 Wiki（<100 页），但不适合大规模知识库。

### Prompt 整合

查询时没有专门的 Prompt 模板；Agent 根据 `CLAUDE.md` 中的 Query Workflow 指导自主构建上下文。唯一的"Prompt 工程"体现在：
- `[[PageName]]` 内联引用格式
- 询问用户是否保存结果（将有用答案沉淀为永久页面）

---

## 6. 特色能力

### 6.1 Health vs Lint 双层检查

| 层次 | 工具 | LLM 调用 | 成本 | 频率 |
|------|------|---------|------|------|
| **Health** | `tools/health.py` | 零 | 免费 | 每次会话 |
| **Lint** | `tools/lint.py` | 是 (语义分析) | Tokens | 每 10-15 次 ingest |

**Health 检查 (确定性):** Empty files, index sync, log coverage
**Lint 检查:** Orphans, broken links, contradictions, missing entities, graph-aware (hub stubs, fragile bridges, isolated communities)

### 6.2 Heal 自愈能力

`tools/heal.py` — 自动修复检测到的问题：
- 为缺失的实体页自动创建 stub 页面
- 修复断裂的 `[[wikilinks]]`

### 6.3 多 Agent 兼容

同一套指令文件适配 4 种 Agent 运行时：
- `CLAUDE.md` → Claude Code
- `AGENTS.md` → Codex / OpenCode
- `GEMINI.md` → Gemini CLI

---

## 7. 总结

| 维度 | llm-wiki-agent |
|------|---------------|
| **部署复杂度** | 极低 (git clone 即可) |
| **LLM 调用模式** | 单次调用 (Ingest 全生成) |
| **Embedding** | 无 |
| **向量搜索** | 无 |
| **图算法** | Louvain + NetworkX 中心度/桥接分析 |
| **查询检索** | Agent 自行 Read 文件，无检索管线 |
| **增量缓存** | 图构建有 SHA256 缓存；Ingest 无 |
| **队列** | 无（Agent 会话即队列） |
| **适用规模** | 小型 Wiki (<200 页) |
| **核心优势** | 零配置、多 Agent 兼容、图健康分析 |
