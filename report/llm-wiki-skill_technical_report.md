# llm-wiki-skill 技术深度研究报告

> 项目：sdyckjq-lab/llm-wiki-skill（GitHub ~2,171 stars）
> 版本：v3.6.72（SKILL.md 版本号 3.6.4）
> 分析日期：2026-07-16
> 分析路径：D:/llm-wiki/llm-wiki-skill-main/

---

## 目录

1. [项目概览](#1-项目概览)
2. [Skill 定义格式与架构](#2-skill-定义格式与架构)
3. [核心工作流管线（Pipeline）](#3-核心工作流管线pipeline)
4. [工具集成体系（Tool Integrations）](#4-工具集成体系tool-integrations)
5. [查询机制（Query Mechanism）](#5-查询机制query-mechanism)
6. [知识图谱引擎](#6-知识图谱引擎)
7. [多平台适配机制](#7-多平台适配机制)
8. [关键算法与数据结构](#8-关键算法与数据结构)
9. [架构决策记录（ADR）精华](#9-架构决策记录adr精华)
10. [总结与评价](#10-总结与评价)

---

## 1. 项目概览

### 1.1 项目定位

llm-wiki-skill 是基于 Andrej Karpathy 的 [llm-wiki 方法论](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) 实现的开源个人知识库构建系统。核心思想为：**知识被编译一次，然后持续维护，而不是每次查询都重新推导**。

### 1.2 Monorepo 结构

项目是一个 monorepo（`AGENTS.md:5-11`），包含三大区域：

| 区域 | 位置 | 状态 | 说明 |
|------|------|------|------|
| **Skill 形态** | 根目录 `SKILL.md` / `scripts/` / `templates/` / `platforms/` | ❄️ 成熟·维护冻结 | 嵌入外部 AI CLI 的知识库维护入口 |
| **Agent 工作台** | `workbench/`（server + web） | 🚧 活跃开发 | 本地 Web 应用，对话为中心 |
| **共享图谱引擎** | `packages/graph-engine/` | 🚧 随工作台演进 | 工作台图谱视图 + Skill 离线 HTML 共用 |

关键架构关系（`AGENTS.md:23-29`）：
```
workbench/web (React 19, SSE) ──HTTP POST + SSE──▶ workbench/server (Hono + @earendil-works/pi-coding-agent)
                                                          │
                                                          ├─ spawn 根目录 scripts/（Skill 已有能力）
                                                          └─ 依赖 @llm-wiki/graph-engine
packages/graph-engine ──ESM + IIFE 双产物──▶ workbench/web 图谱视图 + Skill 离线 HTML
```

### 1.3 两种入口形态

根据 ADR-27（`docs/adr/0027-one-product-two-entry-points.md`），llm-wiki 是一个产品，两种入口：

- **Skill 形态**：让用户把 llm-wiki 带进已有 AI 工具（Claude Code、Codex、OpenClaw、Hermes）
- **工作台形态**：本地应用，承载对话、图谱、产出物和多模型流程

两者读写**同一份本地知识库格式**，以 Markdown 文件 + `[[双向链接]]` 为核心。

---

## 2. Skill 定义格式与架构

### 2.1 SKILL.md 核心结构

SKILL.md（`D:/llm-wiki/llm-wiki-skill-main/SKILL.md`，共 1133 行）是整个 Skill 形态的**权威工作流定义文件**。其结构为：

```yaml
---
name: llm-wiki
version: 3.6.4
author: sdyckjq-lab
license: MIT
description: |
  个人知识库构建系统（基于 Karpathy llm-wiki 方法论）...
metadata:
  hermes:
    tags: [knowledge-base, wiki, research, note-taking]
---
```

#### 2.1.1 工作流路由表（`SKILL.md:122-138`）

Skill 通过**关键词匹配**将用户意图路由到 10 个工作流：

| 用户意图关键词 | 路由目标 | 说明 |
|---|---|---|
| "初始化知识库"、"新建 wiki"、"创建知识库" | **init** | 创建知识库骨架 |
| URL/文件路径/"添加素材"/"消化" | **ingest** | 消化单个素材 |
| "批量消化"/文件夹路径 | **batch-ingest** | 批量消化 |
| "关于 XX"/"查询" | **query** | 快速问答 |
| "深度分析"/"综述"/"digest" | **digest** | 深度综合报告 |
| "对比"/"比较" | **digest**（对比表格式） | 对比分析 |
| "时间线"/"按时间排列" | **digest**（时间线格式） | 时间线梳理 |
| "健康检查"/"lint" | **lint** | 知识库健康检查 |
| "知识库状态"/"现在有什么" | **status** | 状态概览 |
| "画个知识图谱"/"graph" | **graph** | 生成知识图谱 |
| "删除素材"/"remove" | **delete** | 级联删除 |
| "结晶化"/"crystallize" | **crystallize** | 对话结晶沉淀 |

### 2.2 通用前置检查机制

除 `init` 外，所有工作流都执行**通用前置检查**（`SKILL.md:142-156`）：

1. 检查当前工作目录是否包含 `.wiki-schema.md`
2. 回退读取 `~/.llm-wiki-path`
3. 读取 `.wiki-schema.md` 判断 `WIKI_LANG`（zh/en）
4. 根据语言切换所有输出和新页面内容

### 2.3 脚本目录定位

所有脚本通过 `${SKILL_DIR}/scripts/<name>` 定位，`SKILL_DIR` 定义为 SKILL.md 所在目录（`SKILL.md:48-54`）。

### 2.4 知识库目录结构

Skill 初始化的标准知识库结构（`SKILL.md:224-248`）：

```
知识库/
├── raw/                    # 原始素材（不可变）
│   ├── articles/           # 网页文章
│   ├── tweets/             # X/Twitter
│   ├── wechat/             # 微信公众号
│   ├── xiaohongshu/        # 小红书
│   ├── zhihu/              # 知乎
│   ├── pdfs/               # PDF
│   ├── notes/              # 笔记
│   └── assets/             # 图片等附件
├── wiki/                   # AI 生成的知识库
│   ├── entities/           # 实体页（人物、概念、工具）
│   ├── topics/             # 主题页
│   ├── sources/            # 素材摘要
│   ├── comparisons/        # 对比分析
│   ├── synthesis/          # 综合分析
│   │   └── sessions/       # 对话结晶页面
│   └── queries/            # 保存的查询结果
├── purpose.md              # 研究方向与目标
├── index.md                # 索引
├── log.md                  # 操作日志
├── .wiki-schema.md         # 配置
└── .wiki-cache.json        # 素材去重缓存
```

---

## 3. 核心工作流管线（Pipeline）

### 3.1 ingest（消化素材）—— 最核心工作流

ingest 是整个系统最复杂的管线（`SKILL.md:245-515`），包含以下几个关键阶段：

#### 3.1.1 隐私自查

首次进入 ingest 时，强制执行隐私自查提示，要求用户确认素材中不包含手机号、身份证号、API key、明文密码等敏感信息。采用**自查清单**而非正则脚本方案，因为正则在非结构化文本中误报率高。

#### 3.1.2 素材提取路由

文件：`scripts/source-registry.sh` + `scripts/source-registry.tsv` + `scripts/adapter-state.sh`

素材路由的三步决策：

1. **URL 类**：`source-registry.sh match-url "<url>"` → 返回 10 列来源定义
2. **本地文件**：`source-registry.sh match-file "<path>"` → 按文件扩展名匹配
3. **纯文本**：直接作为 `plain_text` 处理

然后调用 `adapter-state.sh check <source_id>` 获取外挂状态（8 列），状态分为五类：
- `available`：可用，继续自动提取
- `not_installed`：未安装，提示用户补安装或走手动入口
- `env_unavailable`：环境不满足（如缺少 `uv`）
- `unsupported`：该来源只支持手动
- `empty_result`：自动提取无有效内容

来源总表（`scripts/source-registry.tsv`）定义了 9 种来源：

| source_id | 分类 | 提取器 | 依赖类型 |
|---|---|---|---|
| local_pdf | core_builtin | - | none |
| local_document | core_builtin | - | none |
| plain_text | core_builtin | - | none |
| web_article | optional_adapter | baoyu-url-to-markdown | bundled |
| x_twitter | optional_adapter | baoyu-url-to-markdown | bundled |
| wechat_article | optional_adapter | wechat-article-to-markdown | install_time |
| youtube_video | optional_adapter | youtube-transcript | bundled |
| zhihu_article | optional_adapter | baoyu-url-to-markdown | bundled |
| xiaohongshu_post | manual_only | - | none |

#### 3.1.3 内容分级处理

根据素材长度自动分级（`SKILL.md:327-333`）：
- **> 1000 字** → 完整处理（两步式：Step 1 结构化分析 + Step 2 页面生成）
- **≤ 1000 字** → 简化处理（只生成摘要页 + 提取 1-3 个关键概念）

#### 3.1.4 完整处理流程：两步式链式思考

**Step 1：结构化分析**（`SKILL.md:375-404`）

AI 分析素材输出临时 JSON：

```json
{
  "source_summary": "一句话概括",
  "entities": [{"name": "xxx", "type": "concept", "relevance": "high", "confidence": "EXTRACTED", "evidence": "原文摘录"}],
  "topics": [{"name": "xxx", "importance": "high"}],
  "connections": [{"from": "A", "to": "B", "type": "因果", "confidence": "INFERRED", "evidence": "推理依据"}],
  "contradictions": [{"claim_a": "...", "claim_b": "...", "context": "..."}],
  "new_vs_existing": {"new_entities": [], "updates": []}
}
```

置信度赋值规则（4 级）：

| 级别 | 定义 | evidence 要求 |
|---|---|---|
| EXTRACTED | 原文直接出现 | **必须**（≤50 字原文摘录） |
| INFERRED | 从多处推断 | **必须**（说明推理依据） |
| AMBIGUOUS | 说法有歧义 | 可选 |
| UNVERIFIED | 来自背景知识 | 可选 |

Step 1 完成后必须通过 `validate-step1.sh` 验证（`scripts/validate-step1.sh`，共 144 行）：
- 使用 `jq` 验证 JSON 格式
- 检查 `entities`、`topics`、`connections`、`contradictions`、`new_vs_existing` 字段类型
- 验证每个 entity 的 `name`/`type`/`confidence` 非空
- `confidence` 值必须是四值之一
- `EXTRACTED`/`INFERRED` 实体必须提供 `evidence`（缺失时 WARN 但不阻塞）
- 验证失败 → 回退到单步 ingest 并加 `UNVERIFIED` 标注

**Step 2：页面生成**（`SKILL.md:406-458`）

1. 从 Step 1 读取 `new_vs_existing.updates` 列表，只加载需要更新的已有页面
2. 页面超过 2000 字时，只读 frontmatter + 需更新的章节
3. 生成/更新素材摘要页 → `create-source-page.sh` 原子写入 + 缓存更新
4. 更新/创建实体页（`wiki/entities/`）
5. 更新/创建主题页（`wiki/topics/`）
6. 更新 `index.md` 和 `log.md`

**容错回退**：如果 Step 1 不是有效 JSON 或缺少必需字段，自动回退到原单步流程，所有新内容加 `<!-- confidence: UNVERIFIED -->`。

#### 3.1.5 缓存机制

文件：`scripts/cache.sh`（352 行）

基于 SHA256 的内容去重缓存，存储于 `.wiki-cache.json`。

**cache check 返回值**（`cache.sh:133-241`）：

| 返回值 | 含义 | 处理 |
|---|---|---|
| `HIT` | 素材未变，source 页面存在 | 跳过 LLM 处理 |
| `HIT(repaired)` | 缓存缺失但通过 stem+source_path 自愈恢复 | 复用已有结果 |
| `MISS:no_entry` | 首次处理 | 继续处理 |
| `MISS:hash_changed` | 素材内容变化 | 重新处理 |
| `MISS:no_source` | 有缓存记录但 source 页面被删 | 重新处理 |
| `MISS:repaired_needs_verify` | stem 匹配但 source_path 不一致 | 重新处理确认 |

**自愈安全网**（`cache.sh:170-217`）：当缓存条目缺失时，通过精确匹配文件名 stem + 验证 source 页面 frontmatter 中 `source_path` 字段来尝试恢复。这个设计确保了即使弱模型跳过 `cache.sh update`，后续处理也能自动发现并修复。

**原子写入保证**（`create-source-page.sh`，100 行）：
1. 写入临时文件
2. 原子 rename
3. 更新缓存
4. 缓存更新失败 → 回滚删除已写入文件

### 3.2 batch-ingest（批量消化）

文件：`SKILL.md:518-582`

逐个文件执行 ingest，关键设计：
- 每 5 个文件暂停展示进度
- 每个文件先做 `cache check`，命中直接跳过
- 完成后全量更新 index.md
- 输出含跳过/成功/失败分类的总结报告

### 3.3 lint（健康检查）

文件：`scripts/lint-runner.sh`（217 行）+ `SKILL.md:634-712`

两步式检查：

**Step 0：机械检查**（脚本自动完成）：
1. 孤立页面检测（entities/topics/sources 中没有被其他页面 `[[引用]]` 的页面）
2. 断链检测（`[[X]]` 指向不存在的 `X.md`，支持 `[[X|别名]]` 语法）
3. index 一致性（index.md 有记录但文件缺失 / 文件存在但 index.md 未收录）
4. 图片资产一致性（source 页面 `image_paths` 声明但文件缺失）
5. source-signal 覆盖情况（通过 `source-signal-coverage.js` 统计）

**Step AI 判断**：
- 矛盾信息（不同页面说法不一致）
- 交叉引用缺失
- 置信度报告（统计 + 抽查 EXTRACTED 条目是否可回溯原文）

### 3.4 graph（知识图谱）

文件：`SKILL.md:929-1040` + `scripts/build-graph-data.sh`（395 行）+ `scripts/build-graph-html.sh`（459 行）

生成两个产物：
1. **Mermaid 静态图**（`wiki/knowledge-graph.md`）：> 50 条关系时只保留 degree 最高的 30 个节点
2. **交互式 HTML**（`wiki/knowledge-graph.html`）：离线双击可用，三栏国风布局

图谱构建流程：
```
wiki/*.md 扫描 ──▶ nodes.tsv + edges_raw.tsv ──▶ graph-analysis.js ──▶ graph-data.json ──▶ knowledge-graph.html
```

### 3.5 delete（级联删除）

文件：`scripts/delete-helper.sh`（68 行）+ `SKILL.md:1043-1103`

级联清理流程：
1. 扫描影响范围（`delete-helper.sh scan-refs`）
2. 超过 5 个受影响页面时二次确认
3. 删除 raw 文件 + source 页面 + 移除其他页面引用 + 更新 index/log
4. 清理缓存（`cache.sh invalidate`）
5. 断链检查

---

## 4. 工具集成体系（Tool Integrations）

### 4.1 来源总表驱动的统一路由

文件：`scripts/source-registry.tsv`（10 行 TSV 定义）+ `scripts/source-registry.sh`（349 行）

所有素材路由通过来源总表统一管理，不手写域名判断。来源分为三类：
- **core_builtin**（3 个）：local_pdf、local_document、plain_text
- **optional_adapter**（5 个）：web_article、x_twitter、wechat_article、youtube_video、zhihu_article
- **manual_only**（1 个）：xiaohongshu_post

### 4.2 外挂状态机

文件：`scripts/adapter-state.sh`（424 行）

五种外挂状态流转：

```
not_installed ──▶ install ──▶ available ──▶ runtime_failed ──▶ retry/fallback
                                     │
env_unavailable ──▶ install dep ──▶ available
                                     │
unsupported ──▶ manual entry         │
                                     ▼
                              empty_result ──▶ manual supplement
```

状态判断逻辑（`adapter-state.sh:162-276`）：
- `core_builtin` → 总是 `available`
- `manual_only` → 总是 `unsupported`
- `optional_adapter` → 检查依赖安装 + 环境条件
  - wechat_article：额外检查 `uv` 是否安装
  - web_article/x_twitter/zhihu_article：检查 baoyu-url-to-markdown 是否存在 + Chrome 9222 端口
  - youtube_video：检查 youtube-transcript + `uv`

### 4.3 可选提取器

| 提取器 | 位置 | 依赖类型 | 覆盖来源 |
|---|---|---|---|
| `baoyu-url-to-markdown` | `deps/baoyu-url-to-markdown/` | bundled（随仓库分发） | 网页、X/Twitter、知乎 |
| `wechat-article-to-markdown` | 外部（uv tool install） | install_time | 微信公众号 |
| `youtube-transcript` | `deps/youtube-transcript/` | bundled | YouTube |

baoyu-url-to-markdown 的核心脚本（`deps/baoyu-url-to-markdown/scripts/main.ts`）使用 Chrome CDP 协议实现网页内容提取，包含 HTML-to-Markdown 转换、媒体本地化等功能。

### 4.4 Step 1 格式验证

文件：`scripts/validate-step1.sh`（144 行）

使用 `jq` 进行严格的 JSON schema 验证，包括：
- 顶层字段类型检查（entities/topics 为 array，new_vs_existing 为 object）
- 子字段非空检查（name/type/confidence）
- confidence 值域检查（必须是 EXTRACTED/INFERRED/AMBIGUOUS/UNVERIFIED 之一）
- evidence 字段存在性检查（EXTRACTED/INFERRED 必须提供）

---

## 5. 查询机制（Query Mechanism）

### 5.1 query 工作流

文件：`SKILL.md:585-631`

查询流程：

1. **通用前置检查** → 获取知识库路径和语言
2. **读取 index.md** → 了解知识库全貌
3. **别名展开**（`SKILL.md:594-596`）：
   - 从 `.wiki-schema.md` 的"别名词表"中查找用户关键词
   - 命中某组别名 → 将组内所有同义词纳入搜索
   - 规则：不跨组传递（A=B 和 B=C 是两组时，搜 A 只展开第一组）
   - 自动去重、忽略空项

4. **搜索 + 排序**（`SKILL.md:597-602`）：
   - 在 index.md 中定位相关分类
   - Grep 搜索 `wiki/` 下所有关键词（原始 + 别名展开）
   - 相关性排序：文件名精确命中 > index.md 条目命中 > 正文关键词命中次数
   - 同一别名组命中同一页面只计一次
   - 每个关键词最多取 3 个命中段落，总段落数 ≤ 15

5. **综合回答**：
   - 标注来源（`[[页面名]]` 格式）
   - 多观点分别列出
   - 引用 ≥ 3 个来源的综合分析 → 建议持久化保存

6. **重复检测 + 保存**：
   - 在 `wiki/queries/` 下搜索同主题页面
   - 使用 `templates/query-template.md` 生成
   - 使用 short-hash 命名避免冲突

### 5.2 digest 工作流

文件：`SKILL.md:783-926`

区别于 query：digest 生成**持久化报告**，query 是即时问答。

三种输出格式：
- **深度报告格式**（默认）：背景概述 → 核心观点 → 不同视角对比 → 知识脉络 → 待解决问题
- **对比表格式**（触发词"对比/比较"）：多维度对比表
- **时间线格式**（触发词"时间线/按时间"）：Mermaid gantt 图 + 事件说明

### 5.3 别名展开机制

文件：`templates/schema-template.md:127-145`

别名词表格式：
```
LLM = 大语言模型 = 大模型 = Large Language Model
RAG = 检索增强生成 = Retrieval Augmented Generation
```

维护原则：
- 只收录实际出现过的同义词
- 每组 ≤ 5 个
- 中英文混用时最常用的放第一个
- ingest 发现新同义词时 AI 主动建议添加

---

## 6. 知识图谱引擎

### 6.1 引擎架构

文件：`packages/graph-engine/src/`（50+ 源文件）

根据 ADR-32（`docs/adr/0032-one-graph-engine-two-hosts.md`），同一个图谱引擎产生两种产物：
- **ESM** → 工作台图谱视图
- **IIFE** → Skill 离线 HTML

### 6.2 图分析算法（graph-analysis.js）

文件：`scripts/graph-analysis.js`（732 行）

核心算法流程（`graph-analysis.js:615-671`，`analyzeGraph` 函数）：

```
输入: nodes[], edges[]
  │
  ├─ 1. loadNodeDetails()       → 加载节点正文 + 解析 frontmatter 的 sources 信号
  │
  ├─ 2. computePairMetrics()    → 计算每条边的 3 信号权重
  │     ├─ co_citation         → 共引强度（共享入链数 / max(入度数)）
  │     ├─ source_overlap      → 来源重叠（共同 sources 数 / min(sources数)）
  │     └─ type_affinity       → 类型亲和度（entity:entity=1, topic:topic=0.8, source:source=0.3...）
  │     └─ weight = avg(可用信号)
  │
  ├─ 3. runLouvain()            → Louvain 社区发现
  │     ├─ runLocalMove()       → 局部移动优化（最多 50 轮）
  │     └─ aggregateGraph()     → 图聚合
  │
  ├─ 4. chooseCommunityLabels() → 社区标签选择（优先 topic 类型，按 degree 排序）
  │
  ├─ 5. buildInsights()         → 生成洞察
  │     ├─ isolated_nodes       → 度数 ≤ 1 的孤立节点
  │     ├─ bridge_nodes         → 连接 ≥ 2 个社区的桥节点
  │     ├─ sparse_communities   → 密度 < 0.15 的稀疏社区
  │     └─ surprising_connections → 跨社区且权重 ≥ 0.75 的惊人连接（最多 8 条）
  │
  └─ 6. buildLearning()         → 学习路径构建
        ├─ path view            → 从推荐起始节点的一阶邻居路径
        ├─ community view       → 最大社区的节点集合
        └─ global view          → 全图节点（按 degree 降序）
```

**Louvain 算法实现**（`graph-analysis.js:283-314`）：
- 构建无向加权图
- Phase 1：局部移动（`runLocalMove`），使用模块度增益公式
- Phase 2：图聚合（`aggregateGraph`），将社区合并为超节点
- 迭代 Phase 1→2 直到不再改进或节点数不变

**3 信号边权重公式**（`graph-analysis.js:104-150`）：
```
co_citation = |inlinks(A) ∩ inlinks(B)| / max(|inlinks(A)|, |inlinks(B)|, 1)
source_overlap = |sources(A) ∩ sources(B)| / min(|sources(A)|, |sources(B)|)  (仅当双方都有 sources 信号时)
type_affinity = lookup(type_pair)  // 基于类型对的硬编码亲和度
weight = clamp01(avg(available_signals))
```

### 6.3 图谱数据生成管线

文件：`scripts/build-graph-data.sh`（395 行）

```
1. scan_kind entities/topics/sources/comparisons/synthesis/queries
   → nodes.tsv (id, label, type, path)

2. 扫描每个页面中的 [[双向链接]] + <!-- confidence 注释 -->
   → edges_raw.tsv (from, line_no, to, conf, relation_type)

3. 边去重合并（同 from+to 的 conf 升级规则：空→有则升级）
   → edges.tsv

4. 内容降级判断（总大小 > 2MB → DEGRADE=1，每节点最多 500 行）

5. 调用 node graph-analysis.js
   → analysis.json

6. 组装最终 graph-data.json：
   { meta, nodes, edges, insights, learning }
```

降级策略：
- 内容降级：总大小 > 2MB → `degraded=true`，每节点只保留前 500 行
- 洞察降级：节点 > 250 或边 > 1000 → `insights_degraded=true`，只保留基础权重和社区

### 6.4 离线 HTML 生成

文件：`scripts/build-graph-html.sh`（459 行）

关键步骤：
1. 读取 `packages/graph-engine/dist/engine.iife.js`
2. 内嵌 `graph-data.json`（`</script>` 转义处理）
3. 注入离线启动脚本
4. 生成单文件 `knowledge-graph.html`

---

## 7. 多平台适配机制

### 7.1 平台入口文件

| 平台 | 入口文件 | 默认安装路径 |
|---|---|---|
| Claude Code | `platforms/claude/CLAUDE.md` | `~/.claude/skills/llm-wiki` |
| Codex | `platforms/codex/AGENTS.md` | `~/.codex/skills/llm-wiki` |
| OpenClaw | `platforms/openclaw/README.md` | `~/.openclaw/skills/llm-wiki` |
| Hermes | `platforms/hermes/README.md` | `~/.hermes/skills/llm-wiki` |

每个平台入口文件是**薄入口**，共享说明指向根 `README.md`，核心能力指向根 `SKILL.md`。

### 7.2 SessionStart Hook

文件：`scripts/hook-session-start.sh`（46 行）

在会话启动时自动注入知识库上下文：
1. 读取 `~/.llm-wiki-path` 获取知识库路径
2. 检查 `.wiki-schema.md` 确认有效性
3. 输出 JSON 格式的 `hookSpecificOutput`，包含 `additionalContext` 消息
4. 强制 stdout 为 UTF-8（解决 Windows GBK 乱码问题）

### 7.3 跨平台安装

`install.sh` 支持 `--platform` 参数（claude/codex/openclaw/hermes），核心流程：
1. 复制 `SKILL.md`、`scripts/`、`templates/`、`platforms/<name>/` 到目标平台目录
2. `--with-optional-adapters` 可选安装提取器依赖
3. `--upgrade` 模式：git pull + 重新复制核心文件
4. Windows 额外提供 `install.ps1` 处理编码问题（UTF-8 强制设置）

---

## 8. 关键算法与数据结构

### 8.1 缓存系统

**数据结构**（`.wiki-cache.json`）：
```json
{
  "version": 1,
  "entries": {
    "raw/articles/2024-01-15-ai.md": {
      "hash": "sha256:abc123...",
      "ingested_at": "2024-01-15T10:30:00Z",
      "source_page": "wiki/sources/2024-01-15-ai.md"
    }
  }
}
```

**Hash 算法**：`SHA256(relative_path + "\0" + file_content)`，包含路径以防止同名文件碰撞。

**写入策略**：原子写入（临时文件 + `os.replace` 重命名）。

### 8.2 来源信号覆盖分析

文件：`scripts/source-signal-coverage.js`（83 行）+ `scripts/lib/source-signal-eligibility.js`

扫描 `wiki/` 下所有页面，分析 frontmatter 中 `sources` 字段的覆盖情况：
- `ok`：sources 字段存在且有效
- `missing_sources`：缺少 sources 字段
- `empty_sources`：sources 为空数组
- `invalid_sources`：sources 格式无效
- `not_applicable`：该页面类型不参与（如 queries/、sessions/ 等 derived 页面）

### 8.3 置信度体系

贯穿整个系统的 4 级置信度：

| 级别 | 含义 | 在页面中的标注 | 在图谱中的表现 |
|---|---|---|---|
| EXTRACTED | 原文直接出现 | 无需标注（默认） | 默认边类型 |
| INFERRED | 从多处推断 | `<!-- confidence: INFERRED -->` | 边的 confidence 字段 |
| AMBIGUOUS | 说法有歧义 | `<!-- confidence: AMBIGUOUS -->` | 低置信度边 |
| UNVERIFIED | 背景知识 | `<!-- confidence: UNVERIFIED -->` | 最低置信度边 |

边类型合并规则（`build-graph-data.sh:193-234`）：同一对节点的多条 `[[引用]]`，空 confidence 遇到显式标注时**升级**，确保不会因为正文中的无标注引用永久锁定为 EXTRACTED。

---

## 9. 架构决策记录（ADR）精华

项目包含 32+ 个 ADR（`docs/adr/`），以下为与 Skill 形态最相关的关键决策：

| ADR | 决策 | 影响 |
|---|---|---|
| ADR-16 | Skill 脚本纳入 monorepo | 统一维护，工作台 spawn 复用 Skill 脚本 |
| ADR-20 | monorepo 根保持 CommonJS 兼容 | 根 `package.json` 不设 `"type": "module"`，ESM 声明在各子包 |
| ADR-21 | 图谱引擎为活地图 | Sigma/Graphology 为主路径，DOM/SVG 为回退 |
| ADR-27 | 一个产品两种入口 | Skill 形态与工作台共存，共享知识库格式 |
| ADR-29 | 图谱是 wiki 结构的视图 | 图谱不定义第二套知识来源 |
| ADR-31 | monorepo 根保持 CommonJS | 确保 Skill 脚本兼容 |
| ADR-32 | 一个图谱引擎两个宿主 | ESM + IIFE 双产物，不分叉两套引擎 |

---

## 10. 总结与评价

### 10.1 架构亮点

1. **来源总表驱动**：所有素材路由通过 `source-registry.tsv` + `source-registry.sh` + `adapter-state.sh` 三层统一管理，新增来源只需加一行 TSV 记录，无需修改核心逻辑。

2. **两步式 ingest**：先分析后生成，中间通过 `validate-step1.sh` 做格式校验，即使弱模型也不会写出残缺数据。失败自动回退到单步流程并加 `UNVERIFIED` 标注。

3. **自愈缓存**：`cache.sh` 不仅能检测 hash 变化，还能通过 stem + source_path 匹配自动修复因 `cache.sh update` 被跳过导致的缓存不一致。

4. **原子写入 + 回滚**：`create-source-page.sh` 保证 source 页面和缓存状态强一致——写入失败则回滚。

5. **降级机制完善**：图谱引擎在内容 > 2MB 和节点/边超预算时自动降级，不会因数据量过大而崩溃。

6. **多平台薄入口**：SKILL.md 为核心，各平台入口只有几十行 README，避免多份维护。

### 10.2 技术栈

| 层面 | 技术 |
|---|---|
| Skill 定义 | Markdown (SKILL.md) |
| 脚本 | Bash（17 个 .sh 文件），Python（内联 in cache.sh/hook），Node.js（graph-analysis.js） |
| 数据交换 | TSV（来源注册表），JSON（缓存/图谱数据），YAML（SKILL.md frontmatter） |
| 验证 | jq（JSON schema 校验） |
| 图谱引擎 | TypeScript → ESM + IIFE（rollup/vite 构建） |
| 图谱渲染 | Sigma.js / Graphology（主路径），DOM/SVG（回退） |
| 离线 HTML | D3.js + marked.js + DOMPurify + Rough.js |

### 10.3 关键文件清单

| 文件 | 行数 | 职责 |
|---|---|---|
| `SKILL.md` | 1133 | 10 个工作流的完整定义 |
| `scripts/cache.sh` | 352 | SHA256 去重 + 自愈安全网 |
| `scripts/source-registry.sh` | 349 | 来源总表读取 + URL/文件匹配 |
| `scripts/adapter-state.sh` | 424 | 五状态外挂状态机 |
| `scripts/graph-analysis.js` | 732 | 3 信号权重 + Louvain 社区发现 + 洞察生成 |
| `scripts/build-graph-data.sh` | 395 | 图谱数据扫描 + 组装管线 |
| `scripts/build-graph-html.sh` | 459 | 离线 HTML 生成 |
| `scripts/validate-step1.sh` | 144 | Step 1 JSON 格式校验 |
| `scripts/lint-runner.sh` | 217 | 机械健康检查（6 项） |
| `scripts/init-wiki.sh` | 95 | 知识库目录结构初始化 |
| `templates/schema-template.md` | 185 | 知识库配置规范模板 |

### 10.4 与 llm_wiki 方法论的关系

项目严格遵循 Karpathy llm-wiki 的核心理念（`CONTEXT.md` 定义的术语体系）：
- **消化（ingest）** 而非"总结"：强调持续积累
- **编译一次，持续维护**：通过缓存机制避免重复 LLM 调用
- **本地 markdown**：Obsidian 兼容，所有内容可独立查看
- **双向链接**：`[[wiki链接]]` 实现知识网络
- **置信度标注**：区分直接提取与推理，保持知识溯源能力

在此基础上，llm-wiki-skill 做出了重大扩展：
- 从纯 Claude 使用扩展到 4 个 AI 平台
- 从手工操作变为 10 个自动化工作流
- 增加了可选提取器体系（网页/X/公众号/YouTube/知乎）
- 新增了交互式知识图谱（数字山水风格）
- 增加了工作台形态（本地 Web 应用）
- 设计了完善的缓存自愈、格式验证、降级回退机制

---

*报告基于对 `D:/llm-wiki/llm-wiki-skill-main/` 目录下完整源代码的深度阅读生成，所有文件路径、函数名、算法描述均来自实际代码。*
