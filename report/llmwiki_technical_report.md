# llmwiki (lucasastorian) 技术调研报告

> **GitHub:** [lucasastorian/llmwiki](https://github.com/lucasastorian/llmwiki) | **Stars:** 1,374⭐ | **License:** Apache 2.0 | **语言:** Python 3.11+ / Next.js

---

## 1. 系统架构与设计哲学

### 定位

llmwiki 是一个 **"自主维护的 AI 驱动的个人 Wikipedia"**（`README.md` L3），核心设计理念是**完全将 Wiki 的编写工作委托给 AI Agent（Claude），通过 MCP 协议完成读写**。它自身**不嵌入任何 LLM 调用逻辑**——LLM 的所有操作通过外部 MCP Client 完成。

核心差异化定位（README L9）：
> "Because the clipper captures your highlights and margin notes alongside the source, the wiki becomes a record of not just what you read but what you *thought* about it."

### 三种使用尺度

```
For You        → 个人 Wikipedia（信息来源会自动更新）
For Your AI    → AI 工作的上下文层（Claude 可读取你的心智模型）
For Your Org   → 企业机构知识层
```

### 架构总览

```
┌──────────────────────────────────────────────────┐
│              用户操作层                            │
│  ┌─────────┐  ┌──────────┐  ┌───────────────┐   │
│  │ Browser │  │  Claude  │  │ Chrome        │   │
│  │ :3000   │  │  (MCP)   │  │ Extension     │   │
│  └────┬────┘  └────┬─────┘  └───────┬───────┘   │
└───────┼────────────┼────────────────┼────────────┘
        │            │                │
   ┌────▼────────────▼────────────────▼────────┐
   │            API Server (FastAPI)            │
   │            api/main.py                     │
   │                                            │
   │  ┌──────────┐ ┌──────────┐ ┌──────────┐  │
   │  │ Chunker  │ │ References│ │ Watcher  │  │
   │  │ 512-tok  │ │ Parser   │ │ (文件变更)│  │
   │  └──────────┘ └──────────┘ └──────────┘  │
   │                                            │
   │  ┌──────────────────────────────────────┐ │
   │  │         Database Layer                │ │
   │  │  Hosted: PostgreSQL (asyncpg)         │ │
   │  │  Local:  SQLite (aiosqlite)           │ │
   │  └──────────────────────────────────────┘ │
   └────────────────────────────────────────────┘
                         │
              ┌──────────▼──────────┐
              │    Filesystem       │
              │  wiki/ + .llmwiki/  │
              └─────────────────────┘

   外部 AI Agent (MCP Client) 通过 MCP Server 进程
   (mcp/local_server.py) 进行所有 Wiki 读写操作
```

**双模式设计：**
- **Hosted（云端）**：PostgreSQL + 用户认证 + 多知识库
- **Local（本地）**：SQLite + 文件系统即真相源 + `./llmwiki open ~/research`

---

## 2. 数据流与管道步骤 (End-to-End Pipeline)

### 文档索引流程

```
Step 1: 文档添加入库
  └── 途径:
       ├── Drag & Drop (Web UI → local_upload.py)
       ├── 文件放到 workspace 文件夹 (Watcher 自动感知)
       └── Chrome Extension (HTTP POST → local_upload.py)

Step 2: 文件解析 (local_processor.py)
  └── PDF     → 本地提取文本 + 图片
        └── 可选: MISTRAL_API_KEY 用于高质量 OCR
       DOCX/PPT → LibreOffice 转换 → 提取
       HTML     → 清洗为可读 Markdown
       MD/TXT   → 直接索引

Step 3: 分块 (services/chunker.py)
  └── chunk_text(content, chunk_size=512, overlap=128)
       ├── 按段落分割 (双换行)
       ├── 每个 chunk: 512 tokens, 128 token overlap
       ├── header_breadcrumb: 跟踪 Markdown 标题层级
       │     e.g. "## Introduction > ### Background"
       └── 限制: MAX_CHUNK_CHARS = 10,000

Step 4: 存储到数据库
  └── store_chunks() → INSERT INTO document_chunks
       字段: document_id, content, source_content,
             page, start_char, token_count, header_breadcrumb

Step 5: MCP Agent 读取文档并构建 Wiki
  └── Claude (via MCP) 被指示:
       "Read the guide, then ingest my sources and start
        building the wiki."
       → Claude 使用 MCP tools 读取源文件
       → Claude 自主生成 wiki/ 下的 Markdown 页面

Step 6: Reference Graph 重建
  └── rebuild_hosted/rebuild_local (services/graph.py)
       ├── 扫描 wiki/ 下所有 .md 文件
       ├── 解析:
       │    ├── footnote citations: [^N]: filename.pdf, p.3 → "cites" edges
       │    └── internal links: [text](path.md) → "links_to" edges
       └── 写入 document_references 表

Step 7: Claude Routine 定时维护
  └── 每夜运行的定时 Prompt:
       "Read the guide. Find everything added since your
        last run. For each one, read it and update the wiki..."
```

### LLM Wiki 构建方式

**关键差异：** llmwiki **自己不做任何 LLM 调用**——所有 Wiki 生成都由 Claude（通过 MCP）完成。`CLAUDE.md` 或 `guide.md` 文件指导 Claude 如何操作：

```
Claude 被指示的工作流:
1. Read guide (guide.md)
2. Search for new sources via MCP search tool
3. Read each new source via MCP read_file tool
4. Generate wiki pages via MCP write_file tool
5. Add cross-references and citations
```

---

## 3. 实体与概念提取机制

### 提取技术

**无内置实体提取。** llmwiki 自身不实现任何实体识别算法。实体提取完全委托给外部 AI Agent（Claude）。Claude 在生成 Wiki 页面时自主决定创建哪些 entity/concept 页面。

### 引用与关系 Schema

Wiki 页面通过两种方式引用源文件：

**1. Footnote Citations（脚注引用）**
```markdown
The transformer architecture improved translation quality significantly[^1].

[^1]: attention-is-all-you-need.pdf, p.3
```
正则解析（`references.py` L12）：`_CITATION_RE = r"\[\^\d+\]:\s*(.+)$"`

**2. Internal Links（内部链接）**
```markdown
See [Attention Mechanism](concepts/attention.md) for details.
```
正则解析（`references.py` L13）：`_WIKI_LINK_RE = r"(?<!!)\[(?:[^\]]*)\]\(([^)]+)\)"`

### 图边类型

| Edge Type | 来源 | 含义 |
|-----------|------|------|
| `cites` | `[^N]: file.pdf, p.3` | Wiki 页面引用源文件 |
| `links_to` | `[text](path.md)` | Wiki 页面间交叉引用 |

---

## 4. 知识图谱、向量嵌入与算法细节

### Embedding 策略

**无向量嵌入。** llmwiki 不生成任何 embeddings，不使用向量数据库。搜索完全依赖 SQLite/PostgreSQL 的文本匹配。

### 分块策略

`api/services/chunker.py`（236 行）实现了段落级别的 Markdown 分块：

```
chunk_text(content, chunk_size=512, overlap=128):
  
  1. _split_paragraphs(content):
     按双换行 (\n\s*\n) 分割
  
  2. 逐段落累积:
     ├── 检测 Markdown 标题 (HEADER_RE)
     │   └── 维护 header_stack: 记录标题层级
     ├── 当累积 tokens > 512:
     │   ├── 作为 chunk 输出
     │   │   包含: content, header_breadcrumb, start_char, page
     │   └── 保留最后约 128 tokens 作为 overlap
     └── 继续累积
  
  3. enforce_max_chars:
     任何超过 10,000 字符的 chunk 在句子边界拆分
  
  4. 返回 Chunk[]:
     每个 chunk: {index, content, page, start_char,
                  token_count, header_breadcrumb}
```

**Token 估算：** `len(text) // 4`（简化估算，非精确分词器）

### 图技术实现

`api/services/graph.py` 实现了一个**解析驱动的引用图**（非传统图数据库）：

```
节点 (Nodes):
  documents 表中的每一行 → 一个图节点
  属性: id, title, path, file_type, source_kind (wiki/source), tags

边 (Edges):
  document_references 表
  类型: cites (引用源文件) / links_to (页面间链接)
  属性: source_document_id, target_document_id, reference_type, page

构建过程 (rebuild_hosted/rebuild_local):
  1. 加载所有文档元数据
  2. 构建三个查找表:
     filename_to_doc: 文件名 → 文档
     base_to_doc: 去除扩展名 → 文档
     wiki_path_to_doc: wiki 路径 → 文档
  3. 扫描每个 wiki 页面:
     ├── extract footnotes → cites edges
     └── extract internal links → links_to edges
  4. 原子写入: DELETE all + INSERT all (savepoint)
```

**图算法：无。** llmwiki 的图仅用于可视化引用关系，不运行任何图算法（无社区发现、无 PageRank）。

### 数据库 Schema

```
documents:
  - id, user_id, knowledge_base_id, filename, title, path
  - file_type, content, source_kind (wiki/source)
  - metadata (JSON), tags (JSON), status
  
document_chunks:
  - document_id, chunk_index, content, source_content
  - page, start_char, token_count, header_breadcrumb
  
document_references:
  - source_document_id, target_document_id
  - reference_type (cites/links_to), page
```

---

## 5. 查询与检索实现 (Query & Retrieval)

### 查询流步骤

**搜索：SQL 文本匹配（无语义搜索）**

```
1. MCP search tool (mcp/tools/search.py)
   → 执行 SQL LIKE 查询:
     SELECT ... FROM documents
     WHERE content LIKE '%keyword%'
        OR filename LIKE '%keyword%'
        OR title LIKE '%keyword%'
     ORDER BY created_at DESC
     LIMIT configurable

2. 返回匹配的文档列表 (title, path, snippet)
```

**AI 生成回答：**

```
1. Claude 通过 MCP 读取 search results
2. Claude 自主决定读取哪些文档的完整内容
   (mcp/tools/read.py → read_file)
3. Claude 基于内容合成答案
4. Claude 通过 MCP write_file 将回答写入 wiki/
```

### 召回算法

**无混合检索。** 使用单一 SQL LIKE 查询的全文匹配：
- 无 BM25 或 TF-IDF 加权
- 无向量相似度搜索
- 无 graph traversal 搜索
- 无 rerank

**分块检索：** 搜索匹配在 `documents.content` 层面进行，chunks 主要用于引用定位（高亮标注等），不参与搜索排序。

### Prompt 整合

llmwiki 自身不构建 Prompt。AI Agent（Claude）在 MCP 另一侧自主构建上下文。llmwiki 提供的是：
- **guide.md**：Wiki 构建和维护的工作流指令
- **MCP tools**：search, read_file, write_file, list_files, ingest, lint

---

## 6. 特色能力

### 6.1 Claude Routines（定时自主维护）

llmwiki 的核心差异化功能——wiki 可以**完全自主维护**：

```
Claude Routine (每夜运行):
  "Read the guide. Find everything added to the workspace
   since your last run — new sources, clips, and highlights.
   For each one, read it and update the wiki: write new pages,
   fold new material into existing pages, fix cross-references.
   Append to wiki/log.md."

调度方式:
  - Claude Code Routines (云端，笔记本关闭也运行)
  - Desktop Scheduled Tasks (本地机器)
  - Claude Cowork
```

### 6.2 Chrome Extension + Highlights

```
浏览器中:
  1. 阅读网页/PDF
  2. 高亮关键段落
  3. 添加评论/笔记
  
保存后:
  → highlights 存储到 document_chunks.source_content
  → Claude 通过 MCP 读取高亮和笔记
  → Claroutine 将高亮内容折叠到 wiki 页面对应位置
```

### 6.3 VaultFS 抽象层

```
mcp/vaultfs/
├── base.py       → VaultFS ABC
├── postgres.py   → 云端 (asyncpg)
└── sqlite.py     → 本地 (aiosqlite)

统一的文件操作接口:
  list_files(path), stat(path), read_file(path),
  write_file(path, content), delete_file(path)
```

**设计意义：** MCP tools 不直接访问数据库，全部通过 VaultFS 抽象。同一套 MCP tools 代码同时支持本地 SQLite 和云端 PostgreSQL。

---

## 7. 总结

| 维度 | llmwiki (lucasastorian) |
|------|------------------------|
| **部署复杂度** | 中等 (Python + Node.js + 可选 LibreOffice) |
| **LLM 调用模式** | 无内置 LLM——完全委托给外部 AI Agent (MCP) |
| **实体提取** | 无内置——由 Claude 自主完成 |
| **Embedding** | 无 |
| **向量搜索** | 无 |
| **分块策略** | 512 tokens, 128 overlap, 段落+标题感知 |
| **图算法** | 无——仅引用关系可视化 |
| **查询检索** | SQL LIKE 关键词搜索 |
| **数据库** | SQLite (本地) / PostgreSQL (云端) |
| **核心创新** | Claude Routines 自主维护、高亮笔记系统、MCP-first 架构 |
| **适用场景** | 个人知识管理、定时自主更新的 Wiki |
