# 全球 AI Agent 产品竞品全景扫描（2025-2026）

> 编制说明：本报告基于 GitHub 仓库数据、官方文档、技术博客及社区反馈（截至 2026 年 7 月）编写。所有产品信息均来自公开可验证的来源。

---

## 赛道一：企业级 / 多 Agent 协同开发平台

### 1. LangGraph / LangGraph Cloud
- 开发方：LangChain Inc.（美国）
- 仓库：github.com/langchain-ai/langgraph（37K stars, MIT）
- 开源：核心 MIT 开源；Cloud 商业 SaaS
- 交互：Python SDK -> LangGraph Studio 可视化调试 -> Cloud 托管
- 受众：企业后端工程师 / ML 工程师
- Killer Feature 1：图状态机（Graph-based State Machine）Agent 控制范式——有向图+显式状态管理，每个节点可以是 LLM/工具/条件分支/人机交互，图边带条件路由
- Killer Feature 2：内置 Human-in-the-Loop interrupt 机制——关键决策点自动暂停等待人工审批，审批后从断点无缝恢复

### 2. AutoGen / AG2
- 开发方：Microsoft Research / AG2AI 社区
- 仓库：github.com/microsoft/autogen（60K stars, CC-BY-4.0）/ github.com/ag2ai/ag2（4.8K stars, Apache-2.0）
- 开源：是
- 交互：Python SDK -> AutoGen Studio 低代码 Web UI
- 受众：企业 R&D、学术研究者
- 2025 关键事件：AutoGen 核心团队离开微软创建 AG2（自称 AgentOS），采用 Apache-2.0 许可
- Killer Feature 1：对话即编排（Conversation-Driven Multi-Agent）——Agent 之间用自然语言对话通信、辩论/协商
- Killer Feature 2：Code Executor 沙箱——Agent 可直接生成并执行 Python/shell 代码（Docker 沙箱）

### 3. CrewAI Enterprise
- 开发方：CrewAI Inc.（巴西/美国）
- 仓库：github.com/crewAIInc/crewAI（55K stars, MIT）
- 开源：核心 MIT 开源；Enterprise 商业 SaaS
- 交互：Python SDK + Web 控制台
- 受众：中小企业技术团队
- Killer Feature 1：角色扮演范式——用自然语言定义 Agent 的 Role/Goal/Backstory，业务专家用领域语言描述 Agent
- Killer Feature 2：层级制任务委托（Hierarchical Process）——Manager Agent 自动分解任务、分配给 Specialist、汇总结果

### 4. Dify
- 开发方：LangGenius Inc.（中国/新加坡）
- 仓库：github.com/langgenius/dify（149K stars）
- 开源：Apache-2.0 + 商业限制条款
- 交互：可视化画布拖拽（几乎零代码）
- 受众：企业运营、产品经理、低代码开发者
- Killer Feature 1：Prompt -> 工作流 -> Agent -> 应用四层递进式抽象——覆盖业务人员到高级开发者全谱系
- Killer Feature 2：微信/飞书/钉钉一键发布——消除开发完 Agent 但无法触达用户的最后一公里

---

## 赛道二：AI 程序员 / 终端级 Action Agent

### 5. Claude Code（Anthropic）
- 开发方：Anthropic（美国）
- 官网：docs.anthropic.com/en/docs/claude-code（闭源）
- 开源：完全闭源
- 交互：终端命令行（纯文本，自然语言驱动文件编辑/命令执行/Git）
- 受众：专业软件工程师
- Killer Feature 1：上下文工程（Context Engineering）——CLAUDE.md + /init 自动构建代码库深层理解（社区 coleam00/context-engineering-intro 13K stars）
- Killer Feature 2：Agent Skills 插件生态——2025 年推出标准，社区已创建如 Anthropic-Cybersecurity-Skills（25K stars, 817 个安全技能）

### 6. Cursor
- 开发方：Anysphere Inc.（美国）
- 官网：cursor.com（闭源 VS Code Fork）；社区 awesome-cursorrules（40K stars）
- 开源：闭源
- 交互：IDE 内嵌对话 + 内联补全 + Composer 多文件编辑
- 受众：全栈/前端开发者
- Killer Feature 1：Tab-Tab-Tab 预测流 + Composer——预测下一步编辑，连续 Tab 完成小重构；Composer 模式下自然语言描述跨文件重构
- Killer Feature 2：.cursorrules 项目级 Agent 行为契约——团队精确控制框架/代码风格/错误处理，社区 400+ 模板

### 7. Devin（Cognition AI）
- 开发方：Cognition AI Inc.（美国）
- 官网：devin.ai（闭源 SaaS, USD 500+/月）
- 开源：完全闭源
- 交互：全自动后台运行——Web UI 分配任务，沙箱独立工作，完成提交 PR
- 受众：工程团队（虚拟初级工程师）、创业团队
- Killer Feature 1：自主沙箱开发——不附着于 IDE，给 GitHub issue 云端沙箱独立完成，唯一做到异步 AI 编程
- Killer Feature 2：调试循环（Self-Debugging Loop）——写代码->运行->读报错->分析堆栈->修改->重跑，SWE-Bench Verified 长期领先

### 8. Bolt.new（StackBlitz）
- 开发方：StackBlitz Inc.（美国）
- 仓库：github.com/stackblitz/bolt.new（16K stars, MIT）
- 开源：MIT
- 交互：浏览器内对话 + 实时预览
- 受众：非程序员、产品原型、创业者 MVP
- Killer Feature 1：描述即部署全栈 Web 应用——WebContainer 沙箱运行完整 Node.js，生成前后端完整应用并浏览器内实时运行
- Killer Feature 2：一键 Fork -> 一键部署零摩擦——浏览器内完成从描述到部署，5-10 分钟从想法到分享 URL

---

## 赛道三：日常办公与端侧个人助手

### 9. ChatGPT Operator（OpenAI）
- 开发方：OpenAI（美国）
- 官网：chatgpt.com（闭源）
- 开源：闭源（CUA 模型可通过 API 调用）
- 交互：远程浏览器操作 + 自然语言指令
- 受众：普通消费者、办公白领
- Killer Feature 1：看屏幕+操作屏幕视觉-操作闭环——CUA 模型直接看浏览器截图生成操作，能处理任何网站无需 DOM 选择器
- Killer Feature 2：主动确认+接管安全边界——敏感操作自动暂停要求用户接管，AI 做 95% 用户审核关键 5%

### 10. Microsoft Copilot / Copilot Studio
- 开发方：Microsoft（美国）
- 仓库：Agent SDK github.com/microsoft/Agents（993 stars, MIT）
- 开源：Agent SDK 开源；产品闭源（USD 30/用户/月）
- 交互：Office 内嵌侧边栏 + Teams 集成 + 声明式 Agent
- 受众：全球 4 亿+ M365 企业用户
- Killer Feature 1：Microsoft Graph 企业知识底座——邮件+日历+Teams+SharePoint+OneDrive 统一语义索引，跨应用综合回答，零配置
- Killer Feature 2：声明式 Agent——自然语言即 Agent 定义，一键部署到 Teams/M365，社区 78 个现成模板

### 11. Google Project Mariner / Astra
- 开发方：Google DeepMind / Google（美国）
- 仓库：ADK github.com/google/adk-python（21K stars, Apache-2.0）
- 开源：产品闭源；ADK 和 Void 编辑器开源
- 交互：Astra 摄像头+语音；Mariner Chrome 同页操作；Antigravity IDE Agent
- 受众：Android/Chrome 用户（20 亿+）、Google Workspace 用户
- Killer Feature 1：Astra 实时物理世界理解——手机摄像头对着书架找书、对着白板生成 Slides（Gemini 2.5 多模态）
- Killer Feature 2：Mariner Chrome 同页操作——利用 Chrome 密码管理器、自动填充和 Google 账户信息，零摩擦网页自动化

### 12. Manus（蝴蝶效应 / Monica）
- 开发方：蝴蝶效应 / Monica（中国）
- 官网：manus.im（闭源，邀请制）；社区复刻 OpenManus（917 stars）
- 开源：完全闭源
- 交互：Web 界面 + 全自动后台 VM 执行
- 受众：知识工作者、分析师、研究员
- Killer Feature 1：端到端虚拟机自主操作（VM-Native Autonomy）——每任务启动完整 Linux VM，自主搜索/编码/生成报告，完成后 VM 销毁
- Killer Feature 2：透明执行信任构建——后台执行时提供实时屏幕录像，所有操作可见，用户可随时暂停或接管

---

## 附录：赛道全景速览表

### 赛道一：企业级多 Agent 平台
LangGraph | LangChain | 37K stars | MIT | 状态机 Agent、人机协同循环
AutoGen | Microsoft | 60K stars | CC-BY-4.0 | 对话式多 Agent、Code Executor
AG2 | AG2AI | 4.8K stars | Apache-2.0 | AutoGen 宽松许可 Fork
CrewAI | CrewAI Inc. | 55K stars | MIT | 角色扮演范式、层级任务委托
Dify | LangGenius | 149K stars | Apache-2.0+ | 渐进式复杂度、中国企业 IM 集成
n8n | n8n GmbH | 196K stars | Fair-code | 400+ 集成、原生 AI 节点
Langflow | Langflow AI | 152K stars | MIT | 低代码可视化编排
FastGPT | Labring | 29K stars | Apache-2.0 | RAG+Agent，中文优先
Coze | ByteDance | 闭源 | 闭源 | 抖音/飞书生态、插件市场
OpenAI Agents SDK | OpenAI | 28K stars | MIT | 轻量级多 Agent
Google ADK | Google | 21K stars | Apache-2.0 | 代码优先 Agent 工具包

### 赛道二：AI 程序员 / 终端 Agent
Claude Code | Anthropic | 闭源 | 闭源 | 上下文工程、Agent Skills 生态
Cursor | Anysphere | 闭源 | 闭源 | Tab-Tab-Tab 预测流、.cursorrules
Devin | Cognition AI | 闭源 | 闭源 | 自主调试循环、异步 AI 编程
Bolt.new | StackBlitz | 16K stars | MIT | 描述即部署、WebContainer 全栈
Aider | Aider AI | 47K stars | Apache-2.0 | Git-aware 结对编程
Plandex | Plandex AI | 16K stars | MIT | 大项目上下文管理
Replit Agent | Replit | 闭源 | 闭源 | 云端全栈 + 一键部署
Windsurf | Codeium | 闭源 | 闭源 | AI Flow 范式、Cascade Agent
OpenHands | All Hands AI | 80K stars | MIT | 开源 Devin 替代
Cline | Cline | 65K stars | Apache-2.0 | VSCode 终端融合 Agent
Warp | WarpDev | 63K stars | AGPL-3.0 | 知识图谱辅助开发

### 赛道三：日常办公与端侧个人助手
ChatGPT Operator | OpenAI | 闭源 | CUA 视觉操作、主动确认安全模式
Microsoft Copilot | Microsoft | SDK 开源 | Graph 知识底座、声明式 Agent
Google Mariner/Astra | Google | 闭源 | 物理世界实时感知、Chrome 同页操作
Manus | 蝴蝶效应(CN) | 闭源 | VM-Native 自主操作、透明执行录屏
Claude Computer Use | Anthropic | 闭源 | 视觉理解屏幕操作
Amazon Q Developer | AWS | 闭源 | AWS 生态深度集成
Rabbit R1 | Rabbit Inc. | 闭源 | LAM 大行动模型、专用硬件
Browser Use | 社区 | 104K stars/MIT | 开源 Web Agent 框架
Nanobrowser | 社区 | 13K stars/Apache-2.0 | 开源 Operator 替代

---

## 关键趋势观察（2025-2026）

1. Agent 框架从模型差异转向编排差异——GPT-5、Claude 4、Gemini 2.5 能力差距缩小，产品竞争力体现在编排、人机协同、长期状态管理
2. Agent OS 概念兴起——AG2 自称 AgentOS，Google 推 Antigravity；MCP/A2A 协议、沙箱、状态管理快速标准化
3. 从 IDE Agent 到终端 Agent——Claude Code 和 Warp 的成功表明越来越多开发者偏好终端而非 IDE
4. 中国企业 Agent 生态崛起——Dify (149K)、FastGPT (29K)、Coze（字节）、Manus（蝴蝶效应）快速增长，在 IM 集成和零代码方面形成独特竞争力
5. Agent Skills/Tools 标准化——Anthropic 的 MCP + Agent Skills 成为事实标准，Google 的 A2A 试图解决跨 Agent 通信

> 编制日期：2026 年 7 月 12 日 | 数据来源：GitHub API、官方文档、社区仓库
