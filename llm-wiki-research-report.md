# LLM Wiki 及其演进形态深度调研报告

> **调研时间：** 2026-07-12  
> **调研方法：** Multi-Agent 并行调研（Master Agent + Sub-Agent A 前沿猎手 + Sub-Agent B 工程推演）  
> **面向场景：** 基于 LangGraph 流转的网络自动驾驶（ADN）辅助开发平台的 AI-Native 知识底座

---

## 一、执行摘要（Executive Summary）

过去 12 个月，"LLM Wiki" 概念已从 Andrej Karpathy 的最初设想（Markdown 文件 + 交叉引用的知识库模式）迅速演进出至少 **5 个独立流派**，覆盖从纯文件系统到图数据库拓扑、从 MCP 协议到 Agent-Native 内存架构的完整光谱。2026 年 5-7 月间爆发性地出现了多篇直接针对 LLM Wiki 系统本身的学术论文（WiCER、Progressive Disclosure、Retrieval as Reasoning、Knowledge Compounding、HyphaeDB），标志着这一领域已从"个人小工具"迈入"系统性研究"阶段。

**核心发现：**
1. **盲编必败**：WiCER 论文实证表明直接将原始文档丢给 LLM 编译 Wiki 的失败率高达 53-60%，结构化迭代编译（CEGAR 式）可将质量恢复 80%
2. **知识复利**：Knowledge Compounding 论文证明了 LLM Wiki 相比纯 RAG 在 30 天内可节省 53-81% 的 Token 消耗，将 Token 从"消耗品"重新定义为"资本品"
3. **检索即推理**：LLM-Wiki 论文提出的 "Retrieval-as-Reasoning" 范式在 HotpotQA/MuSiQue 等基准上全面超越 GraphRAG/LightRAG/HippoRAG 2
4. **Agent-Native 内存**：HyphaeDB 首次将向量数据库的 HNSW 图拓扑重新解释为多 Agent 通信结构
5. **安全新前沿**：FARMA 攻击表明 Agent 持久记忆本身就是新的攻击面

---

## 二、概念流派与分类学（Taxonomy of Approaches）

### 2.1 术语演进

Karpathy 最初定义的 "LLM Wiki" 描述一种"基于 Markdown 文件、LLM 编译维护的交叉引用知识库"。近一年社区衍生出以下新术语和概念变体：

| 术语 | 提出者/来源 | 核心主张 |
|------|-----------|---------|
| **Knowledge Compounding** | Liu et al. (2026) arXiv:2604.11243 | LLM Wiki 的 Token 经济学——知识积累产生复利效应 |
| **Retrieval-as-Reasoning** | LLM-Wiki (2026) arXiv:2605.25480 | 检索不应该是一次性查询，而应是搜索→阅读→遍历→决策的推理过程 |
| **Agent-Native Memory** | HyphaeDB (2026) arXiv:2606.28781 | 内存不是被动存储，而是 Agent 间的通信结构 |
| **Wiki-memory Compilation** | WiCER (2026) arXiv:2605.07068 | 将编译过程建模为 CEGAR 式的迭代抽象精化 |
| **Proactive Memory Agent** | "Remember When It Matters" (2026) arXiv:2607.08716 | 独立记忆 Agent 主动决定何时注入提醒 |
| **Progressive Disclosure** | arXiv:2607.04576 (2026) | LLM 维护的 Wiki 中，渐进式信息披露 vs 整体索引的效率对比 |
| **Agentic Knowledge Base** | 社区术语 | LLM Agent 自主创建、维护、扩展的知识库 |
| **Self-evolving RAG** | 通用术语 | 检索系统随使用而自我进化 |
| **CAG (Cache-Augmented Generation)** | 社区（多个实现） | 将整个文档预加载到 KV Cache，替代 RAG 检索 |

### 2.2 五大实现流派

#### 流派一：Markdown 文件系统 + LLM 编排（Karpathy 直系）

**代表项目：**
- `atomicstrata/llm-wiki-compiler`（1,726 ⭐）：Karpathy 模式的参考实现。原始源文件 → LLM 编译 → 交叉引用 Wiki
- Hermes Agent 内置 `llm-wiki` skill：三层架构（raw/ → entities/concepts/comparisons/queries/ → SCHEMA.md）
- `arthurzhuhan/accrete-llm-wiki`：企业级自托管版本
- 大量个人/项目定制实现（GitHub 搜索"llm-wiki" 返回 15+ 个相关仓库）

**核心特点：**
- 文件系统即数据库，Obsidian/VSCode 原生可读
- 按 page thresholds 决定何时创建新页面
- 前端 YAML 元数据（created/updated/tags/sources/confidence/contested）
- 交叉引用 `[[wikilinks]]`

**优点：** 零依赖、Git 友好、人工可读可编辑、与 Obsidian 无缝集成  
**缺点：** 无原生并发控制、大尺度 Wiki（500+ 页面）导航困难、纯文本缺乏语义查询能力  
**适用场景：** 个人知识管理、小型团队（<5 人）、研究型项目

---

#### 流派二：图数据库 + 知识图谱（Graph-Native）

**代表项目：**
- `microsoft/graphrag`（34,360 ⭐）：图驱动的 RAG。从原始文档中提取实体和关系构建知识图谱，基于社区检测进行全局摘要
- `HKUDS/LightRAG`（37,561 ⭐，EMNLP 2025）：轻量级图 RAG，相比 GraphRAG 更快、更简单
- `Graphify-Labs/graphify`（82,298 ⭐）：将任意代码仓库/文档转为可查询的知识图谱
- `iikarus/Dragon-Brain`（49 ⭐）：MCP 协议 + FalkorDB（图数据库）+ Qdrant（向量搜索）的持久化 Agent 记忆

**核心特点：**
- 实体-关系-实体三元组建模
- 社区检测与层级化总结（GraphRAG 的 Global Search）
- 图遍历 + 向量检索的混合查询

**优点：** 强语义表达、实体间关系推理、适合复杂关联知识  
**缺点：** 构建成本高、增量更新复杂、需要专门的图数据库运维  
**适用场景：** 企业知识图谱、法规合规、多源异构数据融合

---

#### 流派三：MCP 协议挂载（Protocol-Native）

**代表项目：**
- `iikarus/Dragon-Brain`：通过 MCP 提供 30 个工具（记忆读写、知识图谱查询等），可被 Claude、Cursor、Gemini CLI 等 MCP 客户端调用
- `ost527/only-my-mem0ry`：零配置本地 Mem0 MCP Server
- 社区中大量 "MCP memory server" 实现

**核心特点：**
- 记忆作为独立服务，通过标准化协议接入
- 客户端无状态，记忆服务有状态
- 支持多种 Agent 框架/Chat 客户端共享记忆

**优点：** 协议标准化、跨平台兼容、解耦记忆与推理  
**缺点：** 协议仍在快速演进、额外网络延迟、MCP 生态碎片化  
**适用场景：** 多 Agent/多客户端共享记忆、需要跨应用知识共享的桌面/IDE 场景

---

#### 流派四：向量数据库 + RAG 的进化（Vector-Evolution）

**代表项目：**
- `mem0ai/mem0`（60,619 ⭐）：通用 Agent 记忆层，支持语义记忆 + 时序记忆 + 去重 + 衰减
- `letta-ai/letta`（23,745 ⭐，原 MemGPT）：带记忆管理的 OS 式 Agent 框架，支持记忆的自动层级化（核心记忆 → 归档记忆）
- `getzep/zep`（4,742 ⭐）：企业级 Agent 长期记忆，支持事实/对话/用户记忆分类

**核心特点：**
- 从传统 RAG（每次从头检索）进化到持久化记忆
- 记忆更新/衰减/去重机制
- 部分项目开始引入记忆的自动组织（Letta 的记忆管理 LLM）

**优点：** 生态成熟、性能好、支持海量数据  
**缺点：** 语义碎片化（chunking 丢失结构）、缺乏交叉引用、知识编译依赖外部编排  
**适用场景：** 对话型 AI 的长期记忆、大规模文档 QA、客户服务

---

#### 流派五：Agent-Native 拓扑内存（Emergent Memory）

**代表项目/论文：**
- **HyphaeDB** (arXiv:2606.28781)：将 HNSW 图拓扑重新解释为多 Agent 通信结构。Agent 作为图中的持久节点，知识通过 gossip 协议在图邻居间传播。涌现行为包括矛盾检测、模式结晶和共识形成
- **"Remember When It Matters"** (arXiv:2607.08716)：独立 Memory Agent 主动监控 Action Agent 的轨迹，决定何时注入结构化记忆提醒（+8.3pp on Terminal-Bench）
- **LLM-Wiki** (arXiv:2605.25480)：将检索操作化为 search/read/link-following 工具调用，引入 Error Book 做持续自我修正

**核心特点：**
- 记忆不再是"被查询"的静态存储，而是主动参与推理的 Agent
- 记忆的传播、演化、矛盾消解成为系统的一等特性
- 知识 Compilation（编译）替代传统 Chunking（切分）

**优点：** 最贴合 "LLM Wiki 自我演进" 本质、知识不碎片化、涌现式智能  
**缺点：** 极其前沿（论文都发布于 2026 年 5-7 月）、工程实现极不成熟、生产风险高  
**适用场景：** 前沿研究、未来 1-2 年的演进方向

---

### 2.3 流派对比矩阵

| 维度 | Markdown 编排 | 图数据库 | MCP 挂载 | 向量 RAG 进化 | Agent-Native |
|------|:---:|:---:|:---:|:---:|:---:|
| 知识结构化程度 | 中（交叉引用） | 高（实体-关系） | 取决于后端 | 低（Chunk） | 高（编译） |
| 自我演进能力 | 中（需外部编排） | 低（图谱更新复杂） | 中 | 低 | **高** |
| 并发控制 | 差（Git-based） | 中 | 中 | 好（DB 事务） | 未知 |
| 人工可读性 | **极佳** | 差 | 差 | 差 | 中 |
| 工程成熟度 | 高 | 高 | 中 | **极高** | 极低 |
| Token 经济性 | 好（Progressive Disclosure） | 中 | 中 | 差（每次全量检索） | **极佳** |
| 适用团队规模 | <10 人 | 10-100 人 | 10-50 人 | 不限 | N/A（研究阶段） |

---

## 三、核心项目与论文证据目录

### 3.1 GitHub 开源项目

| 项目 | Stars | 流派 | 核心能力 | 对 ADN 知识底座的参考价值 |
|------|-------|------|---------|------------------------|
| [mem0ai/mem0](https://github.com/mem0ai/mem0) | 60K | 向量进化 | 通用 Agent 记忆层，分类/去重/衰减 | **高**：记忆层的工程参考 |
| [Graphify-Labs/graphify](https://github.com/Graphify-Labs/graphify) | 82K | 图数据库 | 代码/文档 → 知识图谱 | **高**：代码仓库知识化技术 |
| [HKUDS/LightRAG](https://github.com/HKUDS/LightRAG) | 37K | 图数据库 | 轻量图 RAG | 中：检索技术参考 |
| [microsoft/graphrag](https://github.com/microsoft/graphrag) | 34K | 图数据库 | 图驱动 RAG + 社区检测 | **高**：全局摘要方法论 |
| [letta-ai/letta](https://github.com/letta-ai/letta) | 23K | 向量进化 | Agent OS + 记忆层级管理 | **极高**：记忆自动管理范式 |
| [atomicstrata/llm-wiki-compiler](https://github.com/atomicstrata/llm-wiki-compiler) | 1.7K | Markdown 编排 | Karpathy 式 Wiki 编译器 | **极高**：基线参考实现 |
| [getzep/zep](https://github.com/getzep/zep) | 4.7K | 向量进化 | 企业 Agent 长期记忆 | **高**：企业级部署参考 |
| [iikarus/Dragon-Brain](https://github.com/iikarus/Dragon-Brain) | 49 | MCP/图 | MCP 持久记忆 (KG+Vector) | 中：MCP 集成方式参考 |
| [arthurzhuhan/accrete-llm-wiki](https://github.com/arthurzhuhan/accrete-llm-wiki) | 1 | Markdown 编排 | 企业级 LLM Wiki | 中：企业化改造方向 |

### 3.2 学术论文（2025-2026）

| 论文 | ID | 日期 | 核心贡献 | 对 ADN 的参考价值 |
|------|----|------|---------|-----------------|
| **WiCER** | 2605.07068 | 2026-05 | CEGAR 式迭代 Wiki 编译，盲编失败率 53-60% | **极高**：编译质量控制方法论 |
| **Retrieval as Reasoning** | 2605.25480 | 2026-05 | LLM-Wiki 系统，SOTA 多跳推理 | **极高**：Error Book 自修正机制 |
| **Knowledge Compounding** | 2604.11243 | 2026-04 | Wiki vs RAG 的 Token 经济对比（省 84.6%） | **极高**：ROI 论证 |
| **Progressive Disclosure** | 2607.04576 | 2026-07 | 709 页 Wiki 的渐进披露 vs 整体索引 | **高**：大规模 Wiki 性能优化 |
| **HyphaeDB** | 2606.28781 | 2026-06 | Agent-Native 拓扑内存，gossip 知识传播 | **高**：多 Agent 协同演化方向 |
| **Proactive Memory Agent** | 2607.08716 | 2026-07 | 独立 Memory Agent 主动注入提醒 | **极高**："书记官 Agent Node" 核心参考 |
| **Memory Compaction Survey** | 2607.08032 | 2026-07 | 跨层内存压缩统一框架 | **高**：长期运行的内存预算规划 |
| **Self-Evolving Agents Survey** | 2508.07407 | 2025-08 | 自演进 Agent 系统综述框架 | **高**：系统设计理论框架 |
| **CHOIR** | 2502.15030 | 2025-02 | 聊天平台 → Wiki 的自动知识沉淀 | **极高**：隐式知识捕获范式 |
| **DeepTrans Studio** | 2606.29727 | 2026-06 | 专家干预 → 团队共享知识 | **高**：人机协同知识固化 |
| **FARMA / SENTINEL** | 2607.05029 | 2026-07 | Agent 记忆攻击与防御 | **高**：安全必备参考 |
| **Telecom Knowledge Systems** | 2512.20012 | 2025-12 | 电信领域的边缘-云-专家级联知识系统 | **极高**：直接对应 ADN 场景 |
| **SEVerA** | 2603.25111 | 2026-03 | 形式化验证的自演进 Agent 合成 | 中：安全保证方法论 |

---

## 四、工程深度分析

### 4.1 隐式知识捕获（Implicit Knowledge Capture）

CHOIR 论文 (arXiv:2502.15030) 提出了最接近理想的方案：

> CHOIR 是一个集成在 Slack/Teams/Discord 中的聊天机器人，自动识别对话中的知识增量，提议编辑相关 Wiki 文档，发起与相关团队成员的讨论，并保留带上下文的修订历史。

**核心机制：**
1. **流式监听**：持续监控频道对话（非逐条处理，而是基于对话片段）
2. **变更检测**：LLM 判断当前讨论是否包含对已有 Wiki 页面的"新信息/修正/矛盾"
3. **提案生成**：自动草拟 Wiki 页面的具体修改建议（patch）
4. **社交共识**：@ 相关成员确认，而非静默修改
5. **可追溯性**：保留 "谁在什么讨论中提出了什么修改" 的完整链路

**DeepTrans Studio** (arXiv:2606.29727) 补充了另一个视角：在翻译工作流中，专家的单次干预被自动保存为"先例知识"并传播给团队其他成员。核心模式是：

> `专家决策 → 结构化存储 → 下游自动应用 → 队友可见`

**对 ADN 的启示：** 网络工程师在排障过程中的每一次诊断、每一次配置调整、每一次协议分析，都应该被自动捕获并结构化为知识资产。关键是 **"无感"**——工程师不需要额外操作，系统自动从 Agent 对话中提取。

### 4.2 多用户并发与版本控制

#### Git-Based 方案

**当前最佳实践：** Karpathy 式 LLM Wiki 天然适应 Git。每个 Wiki 页面是独立 Markdown 文件，Git 提供：
- 分支开发 / PR 审核
- 冲突标记与人工解决
- 完整历史追溯
- `git blame` 归因

**问题：** 当 LLM Agent 同时修改多个页面时，Git 的冲突解决是文件级而非语义级的。两个 Agent 可能在语义上矛盾但 Git 层面无冲突。

#### CRDT 方案

CRDT（无冲突复制数据类型）在实时协作文档（Google Docs、Notion）中已成熟应用，但 **目前未发现将 CRDT 直接应用于 LLM Wiki 的成熟开源项目或论文**。理论可行性分析：

- **优势：** 实时协同、离线编辑、自动合并
- **挑战：** CRDT 擅长字符级/字段级合并，但 LLM Wiki 需要语义级合并（"这两个 Agent 对同一个概念写了矛盾的定义"）
- **混合方案：** CRDT 处理文本同步 + LLM 处理语义冲突检测

#### LLM 中介冲突消解（Self-RAG 机制）

这是最前沿的思路，尚未有成熟实现。理论路径：

1. **冲突检测阶段：** 当 Agent A 和 Agent B 对同一 `[[实体]]` 页面提交了不同更新，系统使用 LLM 做语义差异分析
2. **矛盾标记：** 类似 Karpathy Wiki 的 `contradictions:` frontmatter，自动标记冲突页面
3. **自动调解：** LLM 尝试合并（优先保留较新信息，除非有 `confidence: high` 的旧信息被矛盾）
4. **升级机制：** 无法自动调解的冲突升级给人工审核

#### RBAC 权限隔离

目前业界做法参考：

- **Zep** 的企业版支持用户/会话级记忆隔离
- **Mem0** 支持 memory 的 user_id 分区
- **Git-based Wiki** 可通过 Git 的分支保护和 CODEOWNERS 实现权限控制

**对 ADN 的建议：** 三层权限模型——
- **全局知识（协议规范、网络拓扑基模）：** 全员可读，高级工程师可写
- **项目知识（特定网元的排障经验）：** 项目组成员读写
- **个人工作记忆：** 仅 Agent 实例自身读写（类似 Letta 的 working memory）

### 4.3 LangGraph 生态集成

LangGraph 提供了几个关键机制可以用于集成 LLM Wiki：

#### 方案 A：全局持久化 Store（LangGraph Store）

LangGraph 的 `BaseStore` 接口支持持久化键值存储。可以将 Wiki 的索引和缓存映射到 Store 中：

```python
# 概念代码
store.put(("wiki", "entity", "bgp-protocol"), "entity_page", page_content)
store.put(("wiki", "index"), "entities", index_data)
```

**优点：** 与 LangGraph 原生集成、支持 Checkpointer 的版本管理  
**缺点：** Store 不适合存储大规模结构化文档（缺乏全文搜索、交叉引用）  

#### 方案 B：独立 "书记官 Agent Node"（优选）

基于 Proactive Memory Agent (arXiv:2607.08716) 的思路，在 LangGraph 图中增加一个专门的 **"书记官 Agent"（Scribe Agent Node）**：

```
[用户输入] → [Router Node] → [ADN 开发 Agent] → [结果]
                    ↓                              ↓
              [书记官 Agent] ← ← ← ← ← ← ← [对话 + 上下文]
                    ↓
              [LLM Wiki（文件系统/图数据库）]
```

**书记官 Agent 的职责：**
1. **旁路监听**：以只读方式接收主 Agent 的每次交互上下文（不阻塞主流程）
2. **增量判断**：调用 WiCER 式迭代编译判断当前对话是否产生知识增量
3. **自主写入**：创建/更新 Wiki 页面，添加交叉引用
4. **沉默决策**：大部分时候保持沉默（"无新知识时不写入"——参考 Proactive Memory Agent 的 selective intervention）
5. **冲突检测**：写入前检查目标页面的版本，检测并发修改

**这个架构的优势：**
- 主 Agent 无感知（不增加推理延迟）
- 书记官可以批处理（攒够 N 条对话再统一编译，降低 Token 消耗）
- 书记官可以使用不同的、更便宜的模型
- 书记官可以跨多个 Agent 实例共享（成为一个 Shared Subgraph）

#### LangGraph Checkpointer 的利用

LangGraph 的 Checkpointer 已保存了完整的状态历史。书记官 Agent 可以：
- 从 Checkpointer 中增量读取新对话（而非重新处理全部历史）
- 将 Wiki 页面版本与 LangGraph 状态版本关联（"这个知识是 commit abc123 时学到的"）

### 4.4 面向 ADN 开发的特殊挑战

#### 挑战 1：协议版本的断代冲突

网络协议（BGP/OSPF/IS-IS 等）的 RFC 频繁更新，且新旧版本之间存在不兼容的语义变更。

**问题：** 当 Wiki 中包含"BGP 路由选择优先级"的知识时，如果基于 RFC 4271 编译，但团队实际部署了 RFC 9234 的新特性，Wiki 会给出过时建议。

**解法：**
- **版本标记**：Wiki 页面前端增加 `protocol_version: "RFC4271"` 标记
- **时效性检测**：定期检查上游 RFC 更新，自动标记可能过期的页面
- **知识溯源**：每个知识条目必须标记来源（RFC 编号 + 章节），类似 Karpathy Wiki 的 `^[raw/papers/rfc4271.md]` 标注
- **冲突声明**：当新旧版本存在矛盾时，创建对比页面，标注 `contested: true`

#### 挑战 2：海量排障历史的质量过滤

ADN 每天可能产生数百条排障对话。如果全部编译入 Wiki，噪声会淹没有用知识。

**解法（WiCER 式质量控制）：**
- **前置过滤**：只编译"成功排障"的对话（有明确的解决方案和验证）
- **诊断探针**：WiCER 的诊断探针思想——对编译结果执行"反向验证"（用 Wiki 中的知识重新回答原始排障问题，检验一致性）
- **频次加权**：多次出现的相似故障模式自动提升编译优先级
- **专家审定**：高风险的配置相关 Wiki 页面需要人工审核（参考 DeepTrans Studio 的专家干预模式）

#### 挑战 3：配置回滚的连锁反应

网络配置变更往往涉及多个设备。Wiki 中记录的"最佳配置"如果被一个 Agent 修改，可能影响其他设备。

**解法：**
- **依赖图谱**：Wiki 中配置页面之间建立 `depends_on: [[device-a-config]]` 关系
- **级联标记**：当一个配置页面被修改，自动标记所有依赖它的页面为 `needs_review`
- **回滚验证**：参考 SEVerA (arXiv:2603.25111) 的形式化验证思想——对关键配置知识进行约束检查

---

## 五、盲区、深坑与前沿拷问

### 5.1 成本与幻觉的平衡

**WiCER 论文的核心数据：**
- 盲编 Wiki 的灾难性失败率：**53-60%**（重要事实在编译中被丢弃）
- 1-2 次 WiCER 迭代恢复 **80%** 丢失质量
- 但 WiCER 每次迭代需要额外的 LLM 调用来执行诊断探针 → 额外的 Token 消耗

**Knowledge Compounding 论文提供的关键经济数据：**
- 编译式 Wiki 累积消耗 **47K Tokens**，等效 RAG 消耗 **305K Tokens**
- 30 天预测：中等主题浓度下节省 **53.7%**，高主题浓度下节省 **81.3%**
- 核心机制：一次性 INGEST 成本摊销到 N 次检索 + 高频答案自动回写 + 外部搜索结果结构保存

**社区省钱策略：**
1. **分层模型**：编译用强模型（GPT-4/Claude Sonnet），检索用弱模型（GPT-4o-mini/Haiku）
2. **渐进编译**：不求一次性完美编译，用 WiCER 式迭代逐步提升
3. **静默过滤**：书记官 Agent 只对"高质量/高价值"对话触发编译（相关性评分 > 阈值）
4. **KV Cache 复用**：Progressive Disclosure 论文揭示，预编译的 Wiki 可通过 KV Cache 预加载实现亚秒级首 Token 延迟

### 5.2 长文本时代的结构化 Wiki 价值

> "既然模型已经支持百万级 Context Window，为什么还需要结构化的 LLM Wiki？"

**核心论点（基于调研提炼）：**

#### 1. Token 经济 ≠ 信息价值

（Knowledge Compounding 论文）47K vs 305K 的对比说明：结构化的 Wiki 用更少的 Token 传递了更精确的信息。长 Context Window 只是"能装下"，但 Attention 机制对长文本中间部分的关注度递减（"Lost in the Middle" 问题依然存在）。

#### 2. 知识编译的不可替代性

（WiCER 论文）直接将原始文档（RFC 全文、排障日志）喂给 LLM，在 17 个 RepLiQA 领域测试中全面劣于编译后的 Wiki。原因是：
- 原始文档中的关键事实被冗长的上下文稀释
- Attention 稀释导致模型忽略文档后半部分的关键信息
- 编译过程本质上是"信息提取 + 交叉引用"，这是单纯的长 Context 无法替代的

#### 3. 知识资产化

（Knowledge Compounding 论文的核心理论贡献）结构化的 Wiki 将 Token 从"消耗品"重新定义为"资本品"。每次对话产生的知识被编译入 Wiki 后，成为可复用、可增值的数字资产：
- 新成员入职不需要重读 1000 页文档，只需查询 Wiki
- 排障经验不随工程师离职而流失
- Wiki 的质量随时间单调递增（复利效应）

#### 4. 安全与可信

（FARMA/SENTINEL 论文）持久化的结构化记忆存在新的安全风险——Agent 的推理历史可能被恶意污染。这引出一个矛盾：
- 如果所有知识都塞进 Context Window，攻击面转移到 Prompt Injection
- 如果知识存储在结构化的 Wiki 中，攻击面转移到 Memory Poisoning
- **结构化的 Wiki 反而更容易审计、回滚和版本控制**（Git 提供了完整的审计轨迹）

#### 5. 可解释性与合规

对于 ADN 这样的工程系统：
- "为什么 Agent 给出了这个配置建议？"→ Wiki 中的来源标注（`^[raw/papers/rfc9234.md§4.2]`）直接追溯
- 长 Context 方案 → "Agent 从 10 万 Tokens 中看到了什么得出这个结论？" → 几乎无法审计

---

### 5.3 记忆压缩的普遍失败模式

"Memory Compaction Survey" (arXiv:2607.08032) 揭示了一个跨层通用问题：

> **在每个层次，决定保留什么的信号是注意力幅度（attention magnitude）或时间近因（recency），并且它们在所有地方都以相同的方式失败——在查询到来之前就丢弃了查询后来需要的信息，且无法撤销。**

**对 LLM Wiki 的启示：**
- 不要依赖"最近修改的就是最重要的"——时间近因不是质量指标
- 需要明确的、查询无关的质量信号（WiCER 的诊断探针是一个方向）
- 知识编译不能是一次性的"看一遍就写"，必须是迭代的"写完后检验"

---

## 六、ADN 知识底座演进路线图

### 6.1 总体架构建议

基于调研，推荐 **"三层混合架构"**：

```
┌─────────────────────────────────────────────────┐
│              ADN 辅助开发平台                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐  │
│  │ ADN Dev  │  │ ADN Ops  │  │ Net Architect│  │
│  │  Agent   │  │  Agent   │  │    Agent     │  │
│  └────┬─────┘  └────┬─────┘  └──────┬───────┘  │
│       │              │               │          │
│       └──────────────┼───────────────┘          │
│                      │                          │
│              ┌───────▼────────┐                 │
│              │ 书记官 Agent    │ ← 独立 Node     │
│              │ (Scribe Node)  │                 │
│              └───────┬────────┘                 │
│                      │                          │
│       ┌──────────────┼──────────────┐           │
│       │              │              │           │
│  ┌────▼─────┐  ┌─────▼──────┐  ┌──▼────────┐  │
│  │ LLM Wiki │  │ 向量记忆层 │  │ 知识图谱   │  │
│  │(Markdown)│  │ (Mem0-like)│  │(Neo4j/FK) │  │
│  │结构化文档│  │ 会话记忆   │  │实体关系    │  │
│  └──────────┘  └────────────┘  └───────────┘  │
│                      │                          │
│              ┌───────▼────────┐                 │
│              │   Git + CRDT   │                 │
│              │ 版本/并发控制   │                 │
│              └────────────────┘                 │
└─────────────────────────────────────────────────┘
```

三层各司其职：
- **LLM Wiki（Markdown）**：人工可读的结构化知识文档、协议规范摘要、架构决策记录
- **向量记忆层**：短期会话记忆、Agent 交互历史、高频问答缓存
- **知识图谱**：网络拓扑实体关系、网元-配置-协议依赖关系、排障因果链

### 6.2 分阶段路线图

#### Phase 1: MVP（0-3 个月）— 基线 LLM Wiki

**目标：** 建立最小可用的 AI-Native 知识底座

**核心功能：**
- 基于 Karpathy 模式 + llm-wiki-compiler 的三层 Wiki 架构
- 单 Agent 的知识编译（每次对话后手动触发或定时触发）
- Git-based 版本控制
- 基础的交叉引用和索引

**技术选型：**
- 存储：Markdown 文件（Git 仓库）
- 编译：参考 WiCER 的 1-2 次迭代编译（但简化实现）
- 索引：Progressive Disclosure 式的目录 + 单行摘要

**验证指标：**
- Wiki 页面数 ≥ 50（覆盖 ADN 核心协议和排障模式）
- 交叉引用密度 ≥ 2 links/page
- 编译质量：人工抽查 20 个页面，准确率 ≥ 80%

**关键技术风险：**
- WiCER 论文表明盲编失败率 53-60%，MVP 阶段需要接受这个事实，通过后续迭代改进

---

#### Phase 2: 书记官 Agent + 隐式捕获（3-6 个月）

**目标：** 实现知识的"无感自动沉淀"

**核心功能：**
- **书记官 Agent Node**：在 LangGraph 中增加独立的 Scribe Node
  - 参考 Proactive Memory Agent (arXiv:2607.08716) 的 selective intervention 机制
  - 参考 CHOIR (arXiv:2502.15030) 的自动变更检测和提案生成
- **质量门禁**：WiCER 式诊断探针（编译后反向验证关键事实）
- **频次加权**：多次出现的相似故障自动提升编译优先级

**技术选型：**
- Scribe Node 使用便宜模型（GPT-4o-mini / Claude Haiku）
- 编译使用强模型（保留给高质量对话）
- 引入 `confidence` 和 `contested` frontmatter

**验证指标：**
- 知识的自动捕获率（自动编译 / 总知识增量 ≥ 60%）
- 自动编译的准确率（人工验证 ≥ 85%）
- 书记官 Agent 的沉默率（无知识增量时正确选择不写入 ≥ 90%）

---

#### Phase 3: 多 Agent 协同 + 知识图谱（6-12 个月）

**目标：** 团队级知识底座，支持多 Agent 并发操作

**核心功能：**
- **多 Agent 并发控制**：基于 Git PR 模式 + LLM 语义冲突检测
- **知识图谱层**：接入 Neo4j/FalkorDB
  - 网络拓扑实体（设备、链路、协议）
  - 排障因果链（症状 → 根因 → 修复 → 验证）
  - 配置依赖关系（BGP peer 配置影响的路由策略）
- **RBAC 权限**：全局/项目/个人三层隔离

**技术选型：**
- 图数据库：Neo4j（企业成熟）或 FalkorDB（参考 Dragon-Brain）
- 并发协调：Git 分支 + LLM 语义 diff + 人工审核关键页面
- 参考 GraphRAG 的社区检测做全局知识摘要

**验证指标：**
- 支持 ≥ 5 个 Agent 实例并发读写
- 并发冲突自动解决率 ≥ 70%（剩余升级人工）
- 知识图谱实体数 ≥ 1000

---

#### Phase 4: 自演进 + 安全加固（12-24 个月）

**目标：** 知识底座自身具备自演进能力，并建立完善的安全防线

**核心功能：**
- **自演进**：参考 HyphaeDB 的 gossip 传播 + 共识形成机制
  - Agent 间通过知识图谱自动发现矛盾并协商解决
  - 知识质量随使用频次自动提升（高频页面的 confidence 自动升级）
- **安全防线**：
  - SENTINEL 式推理记忆攻击检测
  - 版本回滚与 Git blame 审计
  - 关键配置知识的 SEVerA 式形式化约束验证
- **协议版本管理**：自动检测 RFC 更新，标记可能过期的 Wiki 页面

**技术选型：**
- 自演进框架：参考 Self-Evolving Agents Survey 的 Optimizer-Environment-Agent 反馈环
- 安全：参考 FARMA/SENTINEL 的 5 信号检测 pipeline
- 验证：对 ADN 配置相关的 Wiki 页面引入 Pydantic/JSON Schema 约束

**验证指标：**
- 自演进准确率：自动修正的错误 / 总错误 ≥ 50%
- 安全：FARMA 类攻击检测率 ≥ 95%
- 协议版本冲突自动标记覆盖率 ≥ 80%

---

### 6.3 MVP 技术方案建议

**最推荐的 MVP 路径：**

```
Hermes Agent 内置 llm-wiki skill + LangGraph Store + Git
```

| 组件 | 选择 | 理由 |
|------|------|------|
| Wiki 引擎 | llm-wiki-compiler（1726 ⭐）或 Hermes llm-wiki skill | 成熟、Karpathy 基线兼容、Obsidian 可读 |
| 存储 | Markdown 文件 + Git | 零运维成本、人工可读、天然版本控制 |
| Agent 编排 | LangGraph + Scribe Node | 与 ADN 平台原生集成 |
| 索引 | Progressive Disclosure 目录 + 摘要 | 709 页 Wiki 验证有效 |
| 编译策略 | WiCER 1-iter（简化版） | 显著提升编译质量，实现复杂度可控 |
| 首次种子 | 手动导入 ADN 核心协议 RFC 摘要 + 常见排障手册 | 建立 Wiki 骨架 |

**MVP 不做什么：**
- 不引入图数据库（复杂度过高，Phase 3 再加）
- 不做实时多 Agent 并发（先单 Agent + Git 异步合并）
- 不做 HyphaeDB 式 gossip 传播（过于前沿）
- 不做完全自动编译（保留人工确认按钮）

---

## 七、附录

### 7.1 术语速查

| 术语 | 全称/来源 | 简要定义 |
|------|----------|---------|
| LLM Wiki | Andrej Karpathy (2025) | LLM 编译维护的 Markdown 交叉引用知识库 |
| WiCER | arXiv:2605.07068 | CEGAR 式迭代 Wiki 编译算法 |
| CEGAR | CounterExample-Guided Abstraction Refinement | 反例引导的抽象精化（WiCER 的核心方法论） |
| HNSW | Hierarchical Navigable Small World | 层级可导航小世界图（向量数据库核心数据结构） |
| CRDT | Conflict-free Replicated Data Types | 无冲突复制数据类型 |
| CHOIR | arXiv:2502.15030 | 聊天平台集成的组织知识助手 |
| FARMA | arXiv:2607.05029 | 针对 Agent 记忆的伪造推理攻击 |
| SENTINEL | arXiv:2607.05029 | FARMA 的防御 pipeline |
| Progressive Disclosure | arXiv:2607.04576 | 渐进式信息披露策略 |
| Knowledge Compounding | arXiv:2604.11243 | 知识复利效应的经济学分析 |
| CAG | Cache-Augmented Generation | 基于 KV Cache 预加载的替代 RAG 方案 |

### 7.2 方法论说明

本调研采用 multi-agent-research 模式：
1. **Master Agent（我）**：全局统筹、交叉验证、综合撰写
2. **Sub-Agent A**：GitHub/arXiv/技术社区前沿发现
3. **Sub-Agent B**：工程落地与协同推演

调研范围覆盖 GitHub（gh CLI + 搜索）、arXiv API、全网技术资源，所有发现均为证据驱动。子智能体的发现已与 Master 独立发现进行了交叉验证。

### 7.3 限制说明

- arXiv API 的搜索语法将空格解释为 OR 操作符，需使用 `+AND+` 做精确 AND 搜索
- Exa 搜索（`mcporter call 'exa.web_search_exa'`）在此环境中不可用
- 部分 GitHub 搜索词返回零结果（可能是搜索语法或索引限制）
- 调研截止于 2026 年 7 月 12 日，领域仍在快速演进中

---

> **报告结束** | 如需讨论具体实施细节或对某个流派进行更深度的技术验证，请随时提出。
