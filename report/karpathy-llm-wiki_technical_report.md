# Astro-Han/karpathy-llm-wiki 深度技术研究报告

> **仓库地址**: [https://github.com/Astro-Han/karpathy-llm-wiki](https://github.com/Astro-Han/karpathy-llm-wiki)
> **Stars**: ~1,526
> **许可证**: MIT
> **分析日期**: 2026-07-16
> **本地路径**: `D:/llm-wiki/karpathy-llm-wiki-main`

---

## 1. 项目概述

`karpathy-llm-wiki` 是将 Andrej Karpathy 提出的 [LLM Wiki 构想](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) 封装为可安装的 **AI Agent Skill** 的开源项目。它不是一个独立运行的应用，而是一套供 AI 编程 Agent（如 Claude Code、Cursor、Codex CLI 等）遵循的**工作流规范和模板体系**。

核心思想源自 Karpathy 的原话：
> "The LLM writes and maintains the wiki; the human reads and asks questions."
> （LLM 负责编写和维护 Wiki；人类负责阅读和提问。）

项目基于真实生产环境验证：截至报告时，维护者已通过该 Skill 管理 **94 篇 wiki 文章**（覆盖 **13 个主题目录**）、**99 份原始资料**，近 7 天有 **87 条操作日志**。

---

## 2. 仓库文件结构

```
karpathy-llm-wiki-main/
├── SKILL.md                          # ★ 核心：Skill 定义文件（AI Agent 的行为规范）
├── README.md                         # 项目说明与快速入门
├── LICENSE                           # MIT 许可证
├── .gitignore                        # 忽略 .DS_Store, *.swp 等
├── assets/
│   └── karpathy-tweet.png            # Karpathy 原始推文截图
├── references/                       # ★ 模板目录
│   ├── raw-template.md               # raw/ 源文件模板
│   ├── article-template.md           # wiki/ 编译文章模板
│   ├── archive-template.md           # 存档页面模板（来自 Query 归档）
│   └── index-template.md             # wiki/index.md 全局索引模板
└── examples/                         # ★ 真实示例
    ├── README.md                     # 示例说明
    ├── ai-coding-tools-index.md      # 主题索引示例
    ├── claude-code-statusline-landscape.md   # 编译后的 Wiki 文章示例
    ├── 2026-03-19-claude-code-statusline-landscape.md  # 对应原始素材示例
    └── log-sample.md                 # 操作日志示例
```

**注意**：该仓库**不含任何可执行代码**（无 `.py`、`.js`、`.ts` 文件）。所有"逻辑"均以自然语言规则的形式写在 `SKILL.md` 中，由 AI Agent 在执行时理解并遵循。

---

## 3. Skill 定义机制（Agent Skills 标准）

### 3.1 SKILL.md 结构

`SKILL.md`（文件路径：`D:/llm-wiki/karpathy-llm-wiki-main/SKILL.md`，共 187 行）是整个系统的**唯一权威规范**。它遵循 [Agent Skills](https://agentskills.io) 开放标准，结构如下：

**YAML Frontmatter（第 1-4 行）**：
```yaml
---
name: karpathy-llm-wiki
description: "Use when building or maintaining a personal LLM-powered knowledge base.
  Triggers: ingesting sources into a wiki, querying wiki knowledge, linting wiki quality,
  'add to wiki', 'what do I know about', or any mention of 'LLM wiki' or 'Karpathy wiki'."
---
```

- `name`：Skill 的唯一标识符
- `description`：触发条件描述——当用户说出特定关键词（如 "add to wiki"、"what do I know about"、"LLM wiki"）时，Agent 应自动激活此 Skill

**正文部分**：纯 Markdown 格式的行为规范，包含以下章节：
- Architecture（架构，第 14-26 行）
- Initialization（初始化，第 28-37 行）
- Ingest（摄入，第 41-97 行）
- Query（查询，第 101-128 行）
- Lint（检查，第 133-177 行）
- Conventions（约定，第 181-187 行）

### 3.2 安装与分发的跨工具兼容性

支持多种 AI 编程工具的安装方式（`README.md` 第 50-108 行）：

| 工具 | 安装方式 |
|------|---------|
| Claude Code | `npx add-skill Astro-Han/karpathy-llm-wiki` |
| Cursor | `npx add-skill Astro-Han/karpathy-llm-wiki` |
| Codex CLI | 复制到 `.agents/skills/karpathy-llm-wiki/` |
| OpenCode | `npx add-skill Astro-Han/karpathy-llm-wiki` |
| 其他工具 | 手动复制 `SKILL.md` 和 `references/` 到工具的 Skill 目录 |

关键设计洞察：Skill 的本质是**可移植的提示词工程产物**——Agent 读取 `SKILL.md` 作为系统指令的一部分，按其中的规则执行操作。不同工具只需能读取该 Markdown 文件即可运行，无需任何运行时依赖。

---

## 4. Wiki 构建工作流（三层架构）

### 4.1 架构总览

`SKILL.md` 第 16-26 行定义了三个层次：

```
用户项目根目录/
├── raw/            ← 不可变源材料层（只读，Agent 只写入，不修改）
│   └── <topic>/
│       └── YYYY-MM-DD-descriptive-slug.md
├── wiki/           ← 编译知识层（Agent 完全掌控，可增删改）
│   ├── <topic>/
│   │   └── concept-name.md
│   ├── index.md    ← 全局目录
│   └── log.md      ← 仅追加操作日志
└── SKILL.md        ← 模式层（定义结构和规则）
```

### 4.2 初始化流程（SKILL.md 第 28-37 行）

仅在**首次 Ingest 时触发**。Agent 检查 `raw/` 和 `wiki/` 是否存在，只创建缺失的部分，**绝不覆盖已有文件**：

- 创建 `raw/` 目录（含 `.gitkeep`）
- 创建 `wiki/` 目录（含 `.gitkeep`）
- 创建 `wiki/index.md`（标题 `# Knowledge Base Index`，空内容）
- 创建 `wiki/log.md`（标题 `# Wiki Log`，空内容）

若 Query 或 Lint 时发现 Wiki 结构未初始化，Agent 应提示用户："Run an ingest first to initialize the wiki."，不自动创建。

---

## 5. 三大核心操作详解

### 5.1 Ingest（摄入操作）—— SKILL.md 第 41-97 行

Ingest 是 Wiki 的核心操作，**永远包含两步：Fetch + Compile**。

#### 5.1.1 Fetch（原始材料获取，第 45-58 行）

1. **获取内容**：使用 Agent 环境提供的 Web/文件工具获取源内容。若无法访问，请求用户直接粘贴。
2. **选择主题目录**：优先复用 `raw/` 中已有的子目录，仅当主题确实不同时才新建。
3. **保存文件**：格式为 `raw/<topic>/YYYY-MM-DD-descriptive-slug.md`
   - Slug：从源标题提取，kebab-case，最多 60 字符
   - 无发布日期：省略日期前缀（如 `descriptive-slug.md`），元数据中 Published 字段设为 `Unknown`
   - 重名处理：追加数字后缀（如 `descriptive-slug-2.md`）
   - **元数据头**：包含 Source URL、Collected date、Published date
   - **内容处理**：保留原文，清理格式噪声，不改写观点

   参考模板：`references/raw-template.md`（7 行）：
   ```markdown
   # {Title}
   > Source: {URL or origin description}
   > Collected: {YYYY-MM-DD}
   > Published: {YYYY-MM-DD or Unknown}
   {Original content below...}
   ```

#### 5.1.2 Compile（编译到 Wiki，第 60-74 行）

Agent 判断新内容归属的三条规则：

| 情况 | 行为 |
|------|------|
| **相同核心论点** | 合并到已有文章，添加新来源到 Sources/Raw 字段，更新受影响小节 |
| **全新概念** | 在相关主题目录下创建新文章，文件以概念命名（非 raw 文件名） |
| **跨多个主题** | 放在最相关目录，添加 See Also 跨引用到其他主题的文章 |

**关键特性**：
- 以上规则**非互斥**：一个源可能同时合并到已有文章 + 创建独立新文章
- **冲突检测**：若新源与已有内容矛盾，用来源归属标注分歧；合并时在文章内标注冲突；不同文章间则在两篇文章中标注并互相链接
- 文章模板参考 `references/article-template.md`（20 行）：
  ```markdown
  # {Title}
  > Sources: {Author1, YYYY-MM-DD; Author2, YYYY-MM-DD}
  > Raw: [{source1}](../../raw/{topic1}/{filename1}.md); ...
  ## Overview
  ## {Body Sections}
  ## See Also (可选)
  ```

#### 5.1.3 Cascade Updates（级联更新，第 76-83 行）

编译完主文章后，Agent 必须检查**涟漪效应**：

1. 扫描**同主题目录**下其他文章，找出内容受新源影响的文章
2. 扫描 `wiki/index.md` 中**其他主题**的条目，找出覆盖相关概念的文章
3. **更新所有内容受实质影响的文章**，刷新每篇的 Updated 日期

**存档页面永不参与级联更新**（它们是时间点快照）。

#### 5.1.4 Post-Ingest（后处理，第 85-97 行）

1. **更新 `wiki/index.md`**：为每篇被触及的文章添加/更新条目。新增主题时包含一行描述。Updated 日期反映知识内容最后变化时间（非文件系统时间戳）。格式参考 `references/index-template.md`。
2. **追加 `wiki/log.md`**：
   ```
   ## [YYYY-MM-DD] ingest | <primary article title>
   - Updated: <cascade-updated article title>
   - Updated: <another cascade-updated article title>
   ```

### 5.2 Query（查询操作）—— SKILL.md 第 101-128 行

触发条件：用户说 "What do I know about X?"、"Summarize everything related to Y"、"Compare A and B based on my wiki"。

#### 5.2.1 查询步骤（第 108-113 行）

1. **读取 `wiki/index.md`** 定位相关文章
2. **读取这些文章**并综合答案
3. **优先使用 Wiki 内容**而非 Agent 训练知识，引用来源时使用 Markdown 链接：`[Article Title](wiki/topic/article.md)`（会话中使用项目根相对路径）
4. **在对话中输出答案**，不写文件（除非用户要求存档）

#### 5.2.2 Archiving（存档，第 115-128 行）

当用户**明确要求存档**时：

1. 将答案写为新 Wiki 页面，参考 `references/archive-template.md`（21 行）
   - Sources：指向引用的 Wiki 文章链接（非 raw/ 文件）
   - 无 Raw 字段（内容来自综合而非原始材料）
   - 文件命名反映查询主题（如 `transformer-architectures-overview.md`）
   - 放在最相关主题目录
2. **始终创建新页面**，绝不合并到已有文章
3. 更新 `wiki/index.md`，Summary 前加 `[Archived]` 前缀
4. 追加 `wiki/log.md`：`## [YYYY-MM-DD] query | Archived: <page title>`

---

## 6. 实体提取与知识图谱

### 6.1 设计哲学：无显式实体提取

与传统知识图谱系统（如 Neo4j + NER pipeline）不同，`karpathy-llm-wiki` **没有显式的实体提取步骤**。实体发现和关系建立完全通过以下机制隐式完成：

1. **编译阶段的归属判断**（SKILL.md 第 60-68 行）：Agent 在编译时判断新内容是否与已有文章共享"核心论点"（core thesis）——这本质上是**语义级的实体匹配**，由 LLM 的理解能力驱动，而非基于规则或嵌入向量。

2. **Cascade Updates 的关系传播**（第 76-83 行）：通过扫描同主题和跨主题文章来发现受影响的页面，这类似于在知识图谱中沿边传播更新。

3. **See Also 交叉引用**（`article-template.md` 第 18-20 行）：文章模板中的 `## See Also` 部分手动维护跨文章链接，形成显式的**知识图谱边**：
   ```markdown
   ## See Also
   - Same topic: [Other Article](other-article.md)
   - Different topic: [Other Article](../other-topic/other-article.md)
   ```

### 6.2 图的表示形式

该系统不使用图数据库或向量数据库。它采用**文件系统 + Markdown 链接**作为图的存储和查询载体：

- **节点** = Markdown 文件（`wiki/<topic>/<article>.md`）
- **边** = Markdown 内部链接 + See Also 引用 + index.md 索引条目
- **图遍历** = Agent 顺序读取文件并跟随链接

这是极简主义的"poor man's knowledge graph"——零基础设施依赖，纯文件系统即可运行。

---

## 7. Lint 机制（质量检查）—— SKILL.md 第 133-177 行

Lint 分为两类，有**不同的权限级别**：

### 7.1 确定性检查（Deterministic Checks）—— 自动修复

| 检查项 | 规则 | 处理方式 |
|--------|------|----------|
| **索引一致性** | 比对 `wiki/index.md` 与实际 wiki/ 文件 | 缺条目→添加 `(no summary)`；死链→标记 `[MISSING]`（不删除，由用户决定） |
| **内部链接** | 检查 wiki/ 文章中的所有 Markdown 链接（不含 Raw 字段链接和 index/log） | 目标不存在→搜索同名文件；恰好一个匹配→修复路径；零个或多个→报告用户 |
| **Raw 引用** | Raw 字段中的每个链接必须指向存在的 raw/ 文件 | 同内部链接逻辑 |
| **See Also** | 同主题目录内的交叉引用 | 添加明显缺失的交叉引用；删除指向已删除文件的链接 |

### 7.2 启发式检查（Heuristic Checks）—— 仅报告

依赖 Agent 的判断力，**不自动修复**：

- 文章间的事实矛盾
- 被新源取代的过时声明
- 源间存在分歧但缺少冲突标注
- **孤儿页面**：无其他 Wiki 文章链入
- 缺失的跨主题引用
- 频繁提及但无专属页面的概念
- 存档页面引用的源文章在存档后有大幅更新

### 7.3 Post-Lint 日志

```
## [YYYY-MM-DD] lint | <N> issues found, <M> auto-fixed
```

---

## 8. 查询机制深度分析

### 8.1 无向量检索、无嵌入

查询过程**不涉及任何向量搜索或语义嵌入**（`README.md` 第 32-38 行明确将 LLM Wiki 与 RAG 对比）：

| 维度 | RAG | LLM Wiki |
|------|-----|----------|
| 知识存储 | 原始分块 + 嵌入向量 | 精心编排的 Markdown 页面 |
| 合成时机 | 查询时 | 摄入和维护时 |
| 优势场景 | 大规模语料库的广泛检索 | 知识复利、摘要、持久交叉链接 |

LLM Wiki 的查询流程极简：
1. 读取 `wiki/index.md`（全局索引，人工可读的目录）
2. Agent 基于 `index.md` 中的文章标题和摘要**自行判断**哪些文章相关
3. 读取相关文章全文
4. LLM 综合答案并引用来源

### 8.2 索引即查询入口

`wiki/index.md` 是整个查询系统的**唯一入口**。它的结构（参考 `references/index-template.md` 和 `examples/ai-coding-tools-index.md`）：

```markdown
# Knowledge Base Index

## {topic-name}
{One-line description of this topic.}

| Article | Summary | Updated |
|---------|---------|---------|
| [{Article Title}]({topic-name}/{article}.md) | {One-line summary} | {YYYY-MM-DD} |
| [{Archived Article}]({topic-name}/{archived}.md) | [Archived] {One-line summary} | {YYYY-MM-DD} |
```

真实示例（`examples/ai-coding-tools-index.md`）展示了 27 篇文章的索引，每行包含文章标题链接和一行摘要。Agent 通过扫描此表来定位相关文章。

### 8.3 知识复利（Compounding Knowledge）

这是 LLM Wiki 相对于 RAG 的核心优势。每次 Ingest 都会：
- 合并相同论点的多个来源
- 更新交叉引用
- 标注矛盾
- 刷新级联影响的文章

这意味着**知识质量随时间复利增长**，而非每次查询时从零开始推导关系。

---

## 9. 设计模式与工程洞察

### 9.1 Prompt-as-Code 模式

整个系统没有任何传统意义上的代码（Python/JS/TS），所有逻辑以**结构化自然语言**写在 `SKILL.md` 中。关键设计要素：

- **指令的精确性**：使用明确的动词（"Read"、"Create"、"Update"、"Append"、"Never modify"）
- **条件分支**：用自然语言描述 if-then 逻辑（"If Query or Lint cannot find the wiki structure..."）
- **状态管理**：通过文件系统状态（目录/文件存在性）隐式管理
- **幂等性**：强调"never overwrite existing files"、"append-only log"

### 9.2 模板继承体系

```
references/
├── raw-template.md       → 源材料标准格式
├── article-template.md   → Wiki 文章标准格式
└── archive-template.md   → 存档页面格式（继承 article 但有差异）
```

模板通过 `SKILL.md` 中的引用指令加载："See `references/raw-template.md` for the exact format."

### 9.3 相对路径约定（SKILL.md 第 181-187 行）

- Wiki 内部文件：使用相对于当前文件的路径
- 会话输出：使用项目根相对路径（如 `wiki/topic/article.md`）
- 存档时的路径转换：从项目根相对路径改写为文件相对路径

### 9.4 生产数据验证

来自 `README.md` 第 42-48 行的自述数据：

| 指标 | 数值 |
|------|------|
| Wiki 文章数 | 94 |
| 主题目录数 | 13 |
| 已摄入源材料 | 99 |
| 近 7 天日志条目 | 87 |
| 维护起始 | 2026 年 4 月 |

示例 `examples/log-sample.md` 展示了真实操作日志条目，包括多次级联更新的细节（如 "content-strategy audience correction" 导致 4 个文件被更新）。

---

## 10. LLM Wiki vs RAG：架构对比

```
┌─────────────────────────────────────────────────────────────────┐
│                         RAG 架构                                 │
│                                                                  │
│  [文档] → [分块] → [嵌入] → [向量DB]                              │
│                                      ↓                           │
│  [用户查询] → [嵌入] → [相似度搜索] → [LLM合成] → [回答]           │
│                                                                  │
│  知识在查询时合成  |  适合海量文档  |  无持久知识结构               │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                      LLM Wiki 架构                               │
│                                                                  │
│  [源材料] → [raw/ 不可变存储]                                      │
│       ↓                                                          │
│  [LLM编译] → [wiki/ 结构化文章] → [index.md 索引]                  │
│       ↓                    ↓                                     │
│  [级联更新] ← [交叉引用] ← [冲突标注]                              │
│                                                                  │
│  [用户查询] → [读index.md] → [读相关文章] → [LLM综合] → [回答]     │
│                                                                  │
│  知识在摄入时合成  |  适合个人知识库  |  知识复利增长               │
└─────────────────────────────────────────────────────────────────┘
```

---

## 11. 技术总结与关键发现

### 核心创新点

1. **零代码 Skill 定义**：`SKILL.md` 是唯一可执行规范，所有"逻辑"都是 LLM 可理解的自然语言规则。这代表了一种新的软件范式——**Prompt-as-Code**。

2. **文件系统即数据库**：不使用任何外部数据库或索引服务。Markdown 文件 + 目录结构 + 内部链接 = 完整的知识图谱。

3. **摄入时合成优于查询时合成**：将计算成本从查询时转移到摄入时，实现知识质量的复利增长。

4. **级联更新机制**：编译一篇文章后自动扫描并更新所有受影响的文章，这是系统最精妙的设计——模拟了人类知识管理中"新信息改变已有认知"的过程。

5. **冲突感知而非冲突解决**：系统标注矛盾但不自动解决，保留了知识的不确定性，交由人类判断。

### 局限与权衡

1. **无语义搜索**：查询完全依赖 `index.md` 的文本索引，当文章数量增长到数千篇时可能成为瓶颈。
2. **无版本控制**：虽然文件系统本身支持 Git，但 Skill 未定义版本回滚机制。
3. **Agent 能力强依赖**：所有智能操作（合并判断、冲突检测、级联范围确定）完全依赖 LLM 的理解能力。若底层模型能力不足，Wiki 质量将受损。
4. **无并发控制**：未定义多 Agent 同时操作的协调机制。

### 适用场景

- 个人知识管理（开发者、研究者、写作者）
- 需要持续积累和交叉引用的领域知识
- 希望 AI Agent 辅助维护而非手动编辑 Wiki 的用户

---

## 12. 文件完整性清单

| 文件 | 路径 | 行数 | 说明 |
|------|------|------|------|
| SKILL.md | `D:/llm-wiki/karpathy-llm-wiki-main/SKILL.md` | 187 | 核心 Skill 规范 |
| README.md | `D:/llm-wiki/karpathy-llm-wiki-main/README.md` | 132 | 项目说明 |
| raw-template.md | `D:/llm-wiki/karpathy-llm-wiki-main/references/raw-template.md` | 7 | 源文件模板 |
| article-template.md | `D:/llm-wiki/karpathy-llm-wiki-main/references/article-template.md` | 20 | 文章模板 |
| archive-template.md | `D:/llm-wiki/karpathy-llm-wiki-main/references/archive-template.md` | 21 | 存档模板 |
| index-template.md | `D:/llm-wiki/karpathy-llm-wiki-main/references/index-template.md` | 18 | 索引模板 |
| claude-code-statusline-landscape.md | `D:/llm-wiki/karpathy-llm-wiki-main/examples/` | 79 | 编译文章示例 |
| 2026-03-19-claude-code-statusline-landscape.md | `D:/llm-wiki/karpathy-llm-wiki-main/examples/` | 147 | 原始素材示例 |
| ai-coding-tools-index.md | `D:/llm-wiki/karpathy-llm-wiki-main/examples/` | 85 | 主题索引示例 |
| log-sample.md | `D:/llm-wiki/karpathy-llm-wiki-main/examples/` | 28 | 操作日志示例 |

---

> **报告结论**：`karpathy-llm-wiki` 是一个设计精巧的 AI Agent Skill，它用不到 200 行的结构化自然语言规范，定义了一套完整的知识管理生命周期（摄入→编译→级联更新→查询→质量检查）。其核心思想——"LLM 写 Wiki，人类读 Wiki"——代表了 AI 辅助知识管理的一种新范式：将 AI 从检索工具提升为知识策展人。
