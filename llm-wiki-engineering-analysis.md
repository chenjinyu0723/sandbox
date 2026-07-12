# LLM Wiki 知识底座：工程可行性、技术债与边界推演

> 撰写日期：2026-07-12
> 调研范围：GitHub 仓库搜索（gh api）+ 已知技术推演
> 搜索限制声明：未使用 Exa/Google 搜索引擎（工具不可用），仅通过 GitHub API 搜索仓库；搜索结果受 API rate limit 和搜索关键词覆盖度限制。

---

## 1. 团队协作与动态知识沉淀的工程解法

### 1.1 隐式知识捕获（Implicit Knowledge Capture）

核心问题：在团队日常 LLM 交互中，如何"无感"且"高质"地把零散知识自动固化为 Wiki？

#### 证据：已有项目的做法

| 项目 | Stars | 关键机制 |
|------|-------|----------|
| Gyst (chaydavs/gyst) | 4 (新) | 自动从 git history、代码注释、markdown、session transcripts 挖掘上下文，产出 Ghost Knowledge、Conventions、Decisions、Error Patterns 四类。Post-commit hook 自动更新。 |
| Arkon (nduckmink/arkon) | 1050 | MRP Pipeline：Map->Reduce->Plan-review->Refine->Verify->Commit。人工可审查 Plan，LLM-merge 非覆盖写入，每页追溯源文档。 |
| claude-obsidian (AgriciDaniel) | 9192 | Drop any source -> Claude reads, links, and files it。零结构化输入到结构化知识图谱。 |
| SwarmVault (swarmclawai) | 603 | Local-first LLM Wiki，内置 RAG 知识库和 agent memory store。 |
| llm-wiki-compiler (atomicstrata) | 1726 | Raw sources in, interlinked wiki out -- 编译型知识底座。 |

#### 推演：关键设计原则

1. "编译"而非"转储"（Compile, not Dump）
   Arkon 的 MRP 流水线和 llm-wiki-compiler 都采用多阶段 LLM 编译：Map->Reduce->Plan->Write。避免简单 RAG "垃圾进垃圾出"。

2. "幽灵知识"（Ghost Knowledge）模式
   Gyst 提出从代码库和 git 历史自动提取四类上下文。挑战：信噪比（git message 质量参差）、置信度管理（事实 vs 推测）。

3. Provenance（溯源）是质量的锚
   Arkon 强制每页记录源文档，llm-wiki-kit 通过 journal.jsonl 记录状态变更。ADN 场景下追溯知识来源对审计合规至关重要。

4. 渐进式审查闭环
   Arkon draft->review->approve 流程和 wiki-teams opt-in contribute-back review 表明：安全敏感场景需要人工闸门。

---

### 1.2 多用户并发与版本控制

#### Git-based 方案（证据充分）

- llm-wiki-kit：每个 vault 默认 git init。safe_write drift detection 将冲突写入 .proposed sidecar。永不静默覆盖。
- osmosis（xkcoding）：GitHub Actions 抓取 -> 自动 PR -> 人工审查合并到 Obsidian vault。
- wiki-teams（mattdweigand-sketch）：Git-backed + opt-in contribute-back review。

Git 优劣：成熟可审计、天然分支回滚、GitHub 生态无缝；但并发需 merge、非技术用户门槛高、频繁小写入产生 commit 噪音。

#### CRDT 方案（证据：多个早期项目）

| 项目 | Stars | 描述 |
|------|-------|------|
| silk-graph (Kieleth/silk-graph) | 3 | Merkle-DAG + CRDT 分布式无冲突知识图谱引擎。Rust+Python。无需 leader/共识/coordinator。形式化收敛证明。 |
| Cortivex (AhmedRaoofuddin) | 12 | Raft 共识 + CRDT 知识图谱，Agent 编排。 |
| PsiNet (WGlynn/psinet) | 1 | P2P + IPFS + CRDT merging，AI Agent 共享会话历史。 |
| Knowdex (Krishna-Mehta-135) | 0 | Local-first markdown + 实时 CRDT 协作。 |
| Agrama-v2 (nibzard/agrama-v2) | 0 | 时序知识图谱 + CRDT + HNSW 向量索引。 |
| project-mycelium (Zorvia) | 0 | Local-first 知识图谱 + CRDT sync + 加密存储。 |

CRDT 推演：
- 可行：silk-graph 证明 Merkle-CRDT 用于类型化属性图可行
- 限制：语义冲突无法自动消解（需 LLM 介入）；向量索引冲突无法自动调和

#### LLM Self-RAG 辅助冲突消解（纯推演，无项目证据）

Self-RAG 机制可辅助：
1. 冲突检测：LLM 判断事实矛盾 vs 文本差异
2. 消解策略：同事实不同方面->合并；事实矛盾->标记冲突+优先强 provenance 版本；时序信息->append-only log
3. 风险评估：LLM 评估消解风险得分，高风险推人工审查

#### 做法对比与 ADN 建议

| 做法 | 代表 | 成熟度 | 适用场景 |
|------|------|--------|----------|
| Git + PR Review | llm-wiki-kit, wiki-teams | 最高 | 低频率变更，强审计 |
| Git + Auto-PR | osmose | 中高 | Agent 自动 PR+人工 approve |
| CRDT 纯文本 | Yjs, Automerge | 最高 | 实时多人协作文档 |
| CRDT 知识图谱 | silk-graph | 低 | 去中心化知识图谱同步 |

ADN 建议：Git + Agent-driven PR 作为第一步，同时跟踪 silk-graph CRDT 方案成熟度。

---

### 1.3 权限隔离（RBAC）

#### 证据：Arkon 的 RBAC 设计（1050 stars，最成熟）

- 内置角色：Viewer / Contributor / Editor / Admin
- 细粒度权限：doc:read:own_dept、wiki:edit:all、org:settings:manage
- 部门级隔离：Department scope + Global scope
- 硬隔离：API/MCP/搜索层均强制 scope
- 审计日志 + OAuth 2.1 + PKCE

#### ADN 场景 RBAC 推演

建议角色模型：
- admin: wiki:*, system:config
- senior_engineer: wiki:read:all, wiki:write:owned, wiki:approve:owned, config:rollback
- engineer: wiki:read:dept, wiki:propose:owned, config:view
- agent: wiki:read:dept, wiki:propose:auto（标记 AI-generated）, config:query
- auditor: wiki:read:all, audit:log

关键原则：
1. Agent 写入必须标记 source: ai-generated，进人工审批
2. 排障知识分级：通用知识全局共享，网元细节隔离
3. 配置回滚知识需单独 approval chain

---

## 2. LangGraph 生态集成推演

### 2.1 LangGraph 的 Store 与 Checkpointer 机制

LangGraph 提供两层持久化（基于公开文档）：

| 机制 | 用途 | 生命周期 | 典型后端 |
|------|------|----------|----------|
| Checkpointer | 保存图执行状态（节点、消息历史） | 单次会话/线程 | SQLite、Postgres |
| BaseStore | 跨会话持久化记忆（长期知识） | 跨会话、跨线程 | 可自定义 |

BaseStore 提供 put/get/search/delete 等 KV 操作，支持语义搜索。

关键洞察：BaseStore 天然适合作为知识库后端，但它是被动存储，缺乏编译、交叉引用、版本控制能力。

### 2.2 三种集成姿势

方案 A：Wiki 作为全局 Store
- 优点：简单，LangGraph 原生支持，所有 Agent 共享知识源
- 缺点：被动 KV 缺乏编译能力；缺版本控制/RBAC/审计；语义搜索有限
- 证据：pixeltable/langgraph-store-pixeltable 正扩展 BaseStore 的持久化和版本化

方案 B：知识书记官 Agent Node（推荐）
在 LangGraph 图中引入专门的 Scribe Agent Node：
1. 接收知识提交：其他 Agent 通过 State 传递结构化知识请求
2. 执行 MRP 编译：Map->Reduce->Plan-review->Refine->Verify->Commit
3. 自主决策：知识新颖度判断、交叉引用检查、冲突检测、置信度评估
4. 条件路由：安全敏感主题 -> 人工审批；常规 -> 自动写入

LangGraph 原生支持：add_conditional_edges（按 Scribe 决策路由）、共享 State（Agent 间传知识）、interrupt（暂停等人工审批）

方案 C：旁路独立服务（MCP）
- 优点：解耦，可复用 Arkon/Gyst/SwarmVault 的 MCP server
- 缺点：增加网络延迟，失去 LangGraph 事务性和可恢复性

### 2.3 已知的 LangGraph + Knowledge Base 开源项目

| 项目 | Stars | 相关度 |
|------|-------|--------|
| Azure-Samples/adaptive-rag-workbench | 51 | 自维护知识库 + LangGraph Agent（Microsoft 官方） |
| Kkkirito-123/mutil-rag-agent | 101 | AIOps + RAG + LangGraph，面向 OnCall 排障 |
| aws-samples/langgraph-bedrock-knowledge-bases | 22 | LangGraph + Bedrock KB 官方示例 |
| ChPi/deep-sql-copilot | 16 | 知识库管理 + 自演进 + LangGraph |
| pixeltable/langgraph-store-pixeltable | 0 | LangGraph BaseStore 持久化扩展 |
| awais-aman/langgraph-knowledge-orchestrator | - | 知识编排器 |

关键发现：
- 社区正快速探索 LangGraph + KB，多数在 POC 阶段（stars < 100）
- adaptive-rag-workbench 是 Microsoft 官方 self-curating KB 参考
- mutil-rag-agent（AIOps 排障方向）与 ADN 场景高度相关

---

## 3. 面向 ADN（网络自动驾驶）的特殊性分析

### 3.1 领域特殊性矩阵

| ADN 特征 | Wiki 挑战 | 与传统软件开发差异 |
|----------|-----------|-------------------|
| RFC/3GPP/IEEE 协议规范 | 版本断代导致知识过期 | 代码文档向前兼容，协议可能完全重写 |
| 海量排障 Debug 历史 | 知识爆炸（每天数百条） | 软件 bug 有限收敛，网络排障是持续流 |
| 配置回滚连锁反应 | 需建模因果关系图，非简单条目 | 软件配置变更影响可控 |
| 协议版本断代冲突 | 同名概念不同版本含义不同 | API 版本化在代码层解决 |

### 3.2 四大挑战与推演解法

挑战 1：知识的时效性（Temporal Validity）
问题：BGP route reflector 最佳实践在 RFC 变化后可能失效。
推演：Wiki 条目增加时效性元数据：
  - effective_from / effective_until
  - protocol_versions（如 ["BGP-4"]）
  - staleness_check schedule（每月检查 rfc-editor.org）
参考：Gyst 的 post-commit hook 模式可扩展到协议变更监控

挑战 2：因果知识图谱 vs 线性 Wiki
问题：配置回滚连锁反应非线性的（OSPF cost -> 流量重路由 -> BGP 收敛 -> MPLS LSP）。
推演：Wiki 需升级为因果知识图谱，建模：
  - CAUSED_BY（症状->根因）
  - TRIGGERED（变更事件->症状）
  - CASCADES_TO（症状->下游症状）
  - RESOLVED_BY（症状->缓解措施）
  - ROLLBACK_OF（缓解->变更事件）
证据：silk-graph 已实现 CRDT 类型化属性图；Agrama-v2 探索时序知识图谱；mutil-rag-agent 用 LangGraph 做 OnCall 排障（101 stars）

挑战 3：知识密度与信噪比
问题：99% 排障对话是常规问题，仅 1% 含价值知识。
推演：分层知识模型：
  L0 即时上下文（日志/配置快照，会话后丢弃）
  L1 排障总结（Agent 自动生成，低门槛写入）
  L2 固化知识（人工审查后写入 Wiki，高门槛）
  L3 协议规范知识（RFC/3GPP 自动同步）
三级流水线：自动摘要 -> 自动去重 -> 人工筛选

挑战 4：跨协议版本的语义对齐
问题：OSPFv2 的 area 和 OSPFv3 的 area 同名不同义。
推演：
  - 版本感知命名空间：protocol/ospf/v2/area vs protocol/ospf/v3/area
  - 继承与差异标注：v3 页面引用 v2 页面并标注差异
  - 有效性区间：每条目标注适用协议版本范围

---

## 4. 团队协作工具的集成

### 4.1 Slack/Teams/飞书等集成

证据：

| 项目 | Stars | 集成方式 |
|------|-------|----------|
| osmosis (xkcoding) | - | GitHub Actions -> Obsidian vault -> LLM 摘要 -> 企微/飞书推送 |
| Arkon (nduckmink) | 1050 | MCP Server -> 任意 MCP 客户端（含 Slack bot via MCP bridge） |
| bran_bot (mishanaimer) | - | Telegram bot + Obsidian vault + LLM |
| openclaw-llm-wiki-skill | 0 | Discord-first 查询，Markdown vault |

推演：
- 直接 Slack/Teams 集成成熟度较低（多为个人项目），但 MCP 生态正改变此格局
- 企微/飞书集成：osmosis 展示推送模式，但缺"从 IM 捕获知识"的反向通道--关键 gap
- IM 中团队讨论是隐性知识重要来源，急需双向集成

### 4.2 Cursor/IDE 中对话自动沉淀为文档

证据：

| 项目 | Stars | 描述 |
|------|-------|------|
| Gyst (chaydavs) | 4 | 从 git history、代码注释、session transcripts 自动提取知识。支持 Claude Code、Cursor、Codex CLI、Windsurf、Gemini CLI |
| deepwiki-rs (sopaco) | 1352 | "Turn code into clarity"--面向人类和 AI Agent 的技术文档生成 |
| cupple (masonthemaker) | 2 | 跨多 IDE + Agent 自动文档共享 |
| agentready (makalin) | 2 | 自动生成 CLAUDE.md 和 CONTRIBUTING.md，适配 AI Agent |
| ai-coding-runbook (NickCollect) | 6 | 多厂商 AI coding 知识库自动同步 |
| htmldock (leeguooooo) | 0 | 团队 HTML doc hub for AI coding agents |

关键发现：
- "AI-Native documentation" 正快速成为独立品类（deepwiki-rs 1352 stars 证明需求旺盛）
- post-commit hook + auto-injection 是最常见模式
- SKILL.md / CLAUDE.md / AGENTS.md 正成为 AI 可消费文档标准格式

ADN IDE 集成推演：
  触发：工程师在 IDE 中完成排障
  捕获：对话日志 + CLI 命令序列 + 解决方案
  流水线：LLM 生成排障摘要 -> LLM 去重检查 -> 自动提交 PR 到 Wiki -> 企微/飞书通知 reviewer

---

## 5. 综合评估：技术债与边界

### 5.1 技术可行性矩阵

| 维度 | 可行性 | 成熟度 | 风险 |
|------|--------|--------|------|
| 单用户 LLM Wiki | 极高 | 高（claude-obsidian 9192 stars） | 低 |
| Git-backed 团队 Wiki | 高 | 中高（llm-wiki-kit 等实践中） | 中（并发冲突） |
| Agent 自动知识提取 | 中高 | 中（Gyst, Arkon 有实现但新） | 中高（信噪比/置信度） |
| CRDT 知识图谱 | 低 | 低（silk-graph 唯一年轻验证） | 高（社区极小） |
| LangGraph 深度集成 | 中高 | 中（adaptive-rag-workbench 参考） | 中（API 稳定性） |
| 协议版本感知 Wiki | 低 | 低（未见直接项目） | 高（领域特殊性） |
| Slack/IM 知识回流 | 低 | 低（多为单向推送） | 中高 |

### 5.2 五大关键技术债

1. "知识腐烂"（Knowledge Rot）
   LLM 编译的知识随时间失效（协议更新、最佳实践变化），但 Wiki 无自愈机制。需定期重新验证 pipeline。

2. 幻觉的传播性（Hallucination Cascade）
   Agent 产生幻觉 -> 写入 Wiki -> 被其他 Agent 引用 -> 级联错误。这是 LLM Wiki 独有风险类型，传统 Wiki 不存在此问题。

3. Embedding 漂移（Embedding Drift）
   Embedding 模型升级时，已有向量索引失效。Arkon 通过"在线重嵌入迁移 + 原子切换"解决，但多数项目未考虑。

4. MCP 协议稳定性
   多个核心项目依赖 MCP 协议。MCP 2024年底发布，仍在快速演进，API breaking changes 风险高。

5. ADN 领域"冷启动"
   通用 LLM 对 RFC/3GPP 理解深度有限。Wiki 初始编译质量取决于 LLM 领域知识--可能需要大量人工 curation 才能达到可用水平。

### 5.3 边界与盲区（诚实声明）

搜索盲区：
- 学术论文（arXiv）中的知识库 CRDT 研究未被覆盖（无搜索引擎可用）
- 中文社区（Gitee）的企微/飞书集成项目可能遗漏
- 企业闭源产品（Confluence AI、Notion AI）内部实现不可见

评估盲区（未找到直接证据的领域）：
- 知识条目级别的 RBAC（非文档级）
- LLM Wiki 在 100+ 人团队的使用数据
- 网络协议规范自动同步的工具链
- Wiki 自演进中的"知识一致性"形式化验证
- LangGraph + CRDT 知识库的联合方案（未见相关项目）

工程假设：
- 知识沉淀质量由底层 LLM 能力保障。LLM 能力不足则系统质量坍塌。
- CRDT 收敛速度假设低网络延迟。跨地域团队场景可能退化。
- 所有 Markdown-based Wiki 方案假设知识可被线性文本充分表达。ADN 的因果网络拓扑可能超出纯文本的表达能力。

---

## 6. 建议的工程路线图（推演，非实证）

### Phase 1：MVP（1-2 月）

Git-backed Markdown Wiki + 单 Agent 自动编译
- 基于 llm-wiki-kit 的 work-os starter
- 手动触发知识编译（非实时）
- Git PR review 作为质量闸门
- 面向单个 ADN 团队的 pilot

### Phase 2：Agent 自动化（3-4 月）

LangGraph Scribe Agent Node + 自动知识提取
- Scribe Agent 接入排障/配置 Agent 的知识流
- 自动提案（auto-propose）-> 人工审批
- 知识去重与置信度评估
- protocol/ 命名空间（版本感知的目录结构）
- LangGraph BaseStore 集成

### Phase 3：企业级（5-8 月）

RBAC + 多团队 + CRDT 探索
- Arkon-style RBAC（部门隔离 + 审计日志）
- 多团队共享的因果知识图谱
- silk-graph CRDT 方案 POC
- 协作工具集成（企微/飞书通知）
- 知识腐烂检测 pipeline（定期重新验证）

### Phase 4：自演进（长期）

全自动知识生命周期管理
- 协议规范变更自动同步 and Wiki 更新
- 跨团队因果推理（CASCADES_TO 关系）
- Self-RAG 冲突消解
- 知识一致性形式化验证

---

## 附录 A：关键项目速查表

| 项目 | Stars | 核心价值 | 关注度 |
|------|-------|----------|--------|
| claude-obsidian (AgriciDaniel) | 9192 | Karpathy 模式最大实现，Obsidian + Claude Code | 最高 |
| Arkon (nduckmink) | 1050 | 企业级 RBAC + MRP Pipeline + MCP Server | 最高 |
| llm-wiki-compiler (atomicstrata) | 1726 | 编译型知识底座，raw -> interlinked wiki | 很高 |
| SwarmVault (swarmclawai) | 603 | Local-first LLM Wiki + agent memory store | 很高 |
| Gyst (chaydavs) | 4 | 自动知识捕获最前瞻：git mining + ghost knowledge | 很高 |
| deepwiki-rs (sopaco) | 1352 | AI-Native 文档生成，Rust 实现 | 很高 |
| llm-wiki-kit (eugenelim) | 11 | 团队 starter 模板 + Agent Skills 标准 | 高 |
| silk-graph (Kieleth) | 3 | CRDT 知识图谱唯一形式化验证实现 | 高 |
| adaptive-rag-workbench (Azure) | 51 | Microsoft 官方 LangGraph + 自维护 KB | 很高 |
| mutil-rag-agent (Kkkirito-123) | 101 | AIOps + LangGraph 排障 RAG | 很高 |
| osmose (xkcoding) | - | 企微/飞书推送集成 | 高 |
| Cortivex (AhmedRaoofuddin) | 12 | Raft 共识 + CRDT agent 编排 | 中 |
| multimodal-wiki (kigner) | 16 | 基于 Hermes llm-wiki skill，多模态+溯源硬化 | 中 |
| wiki-teams (mattdweigand-sketch) | 1 | 自维护团队知识库 + opt-in review | 中 |

## 附录 B：搜索方法说明

- 工具：GitHub CLI (gh) + GitHub API (gh api search/repositories)
- 搜索次数：共发起 30+ 次搜索请求
- 覆盖范围：GitHub 公开仓库（含 description、topics、readme）
- 未覆盖：arXiv 论文、Google/Exa 网页搜索、中文社区（Gitee）、闭源产品
- Rate limit：部分搜索因 API rate limit 返回空或 403
- 所有标注"推演"的内容均基于已知技术推理，缺乏直接项目证据
