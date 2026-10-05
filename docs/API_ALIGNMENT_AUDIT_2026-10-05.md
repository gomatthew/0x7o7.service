# 前后端能力对齐与 Dify 迁移梳理

梳理日期：2026-10-05（Asia/Shanghai）。

后端：`/Users/0x7o7/workspace/0x7o7.service.v1`。
前端：`/Users/0x7o7/workspace/0x7o7.web.react-3.0`。

## 实施结果（2026-10-05）

用户随后授权修改代码并部署 server2。下文的“当前实现”和待处理描述保留梳理时的证据；实施后的状态以本节为准。

- 已采用 LangChain + LangGraph：复用现有模型调用与本地 RAG；文档分析按识别、提取、引用校验、审核四个节点运行。没有启用图检查点、审核持久化或外部交接。
- 已移除活跃文档分析与 OCR 后处理的 Dify 调用。百度 OCR 继续负责图片识别，LangChain 负责根据用户问题和语言作答；OCR 追问恢复本人会话，保留首轮图片文字及最近六轮。
- 真实交付字段改为模型结构化输出；缺失字段不填固定默认值。来源 ID 和引用原文必须在检索结果中存在，否则标记待审核。该检查验证引用存在，不能保证每个值都在语义上被引用充分支持。
- 修复演示身份冒充真实登录、注册后登录失败被掩盖，以及 SSE 末帧丢失、业务错误 JSON 被当作成功、部分响应中断被当作完成的问题。
- 修复没有待审核项时交接预览仍被禁止的问题；有阻塞项或必需字段未确认时仍不能预览。审核修改仍仅保存于浏览器。
- 使用兼容现有 LangChain 0.3 依赖的 LangGraph 1.0.1，没有整体升级旧 Agent 栈。修复 SiliconFlow 的输出长度参数，并关闭 Qwen3 默认思考模式；真实文档测试从 90 秒超时恢复为约 16 秒完成。
- 后端已部署至 `/root/project/0x7o7.service`，由 `0x7o7-api.service` 管理；生产配置、知识库、上传文件和日志保留。原始代码备份位于 `/root/project/backend-backups/20261005-161948`，参数修复发布备份位于 `/root/project/backend-backups/20261005-163059`。
- server2 使用临时测试账户完成实际上传、文档字段提取、聊天、百度 OCR 和 OCR 追问联调；测试账户与其业务数据已清理。CRM 看板仍返回 40 条来源。
- 前端发布目录为 `/home/ubuntu/releases/react-0x7o7-20261005-163748`。真实浏览器验证访客示例、审核后预览、访客上传限制和登录后真实上传分析均通过；全字段确认时可预览，没有页面脚本错误。前端回退链接为 `/home/ubuntu/react-0x7o7-previous`。
- 最终本地验证：后端 `uv run python -m pytest -q` 为 **54 passed、2 skipped**（需独立市场数据库的集成测试未配置）；前端类型检查、相关 ESLint、生产构建和 `npm run test:ai` 的 **5 项测试**通过。线上真实调用另行验证如上，未把 mock 测试当作真实模型联调。
- 用户确认的展示边界保持：示例动画、浏览器内 Confirm edit、交接 JSON 预览、模板 mailto。完整来源 API、自动研究执行和官网线索转 CRM 留待另行确认。

模型参数依据：[SiliconFlow Chat Completions](https://docs.siliconflow.cn/docs/api/chat-completions-post)。

## 范围与验证结论

- 以两个项目当前工作目录为准，包含原有未提交改动；未覆盖或清理这些改动。
- 已完整阅读 `docs/AI_ENGINEERING_STYLE_GUIDE.md`。它记录的是 2026-05-19 状态；实际代码已经使用环境变量、测试和本地 RAG。遵循现有代码和本次用户要求，保留扁平模块、现有响应格式及路由/服务/仓储分工。
- 当前真实页面为首页、`/demo/document-to-decision`、`/crm` 和三个模板页。`/demo/chat`、`/demo/ocr`、`/demo/workspace` 都重定向至文档 Demo；对应旧组件仍在代码中，但不能算作当前可访问的独立页面。
- 本地路由静态清点与 server2 正在运行的 OpenAPI 对比：双方均为 **64 个接口（方法 + 路径）**，没有缺失或多出的接口。该结论不代表实现内容完全相同。
- server2 `/health/live` 返回 `ok`；`/health/ready` 返回 `ready`，数据库、Redis 与模型密钥配置检查均通过。模型配置检查不等于真实模型调用已验证。
- 现有相关测试：`test_ai_rag_services.py`、`test_sales_demo.py`、`test_ocr_service.py`、`test_utils_sse.py`、`test_security_layer.py`、`test_crm_api.py`，共 **45 passed**。未增加测试框架。这些测试不能替代真实浏览器、OCR 和模型联调。
- 本阶段进行了代码审查、接口对比和线上只读检查；没有修改业务代码、重启服务或部署。

## 已经接入后端的当前功能

| 页面 / 操作 | 实际调用 | 后端位置 | 结论 |
| --- | --- | --- | --- |
| 首页提交项目咨询 | `POST /leads` | `service/demo_service.py:create_lead` | 已落库，再安排邮件通知；不是空按钮 |
| 文档 Demo 载入示例 | `GET /demo/v1/sample` | `demo_service.py:get_sample` | 返回预先核验的示例包 |
| 文档 Demo 邮箱验证码 / 验证 | `POST /auth/email/request-code`、`POST /auth/email/verify` | `service/auth_service.py` | 已接入真实验证码和 Cookie 会话 |
| 文档 Demo 上传文件 | `POST /demo/v1/uploads` | `demo_service.py:upload_demo_document` | 已接入解析、索引、上传会话 |
| 文档 Demo 分析真实文件 | `POST /demo/v1/analyze`，`analysis_type=delivery_handoff` | `demo_service.py:analyze_demo` | 已调用后端；结构化字段存在下文所述语义缺口 |
| CRM 看板、机会、公司详情 | `/crm/dashboard`、`/crm/market/opportunities/{id}`、`/crm/companies/{id}` | `service/crm_service.py` | 前端通过 `/crm-api` 代理调用 |
| CRM 市场信号 / 代理商 | `/crm/market/signals`、`/crm/market/agencies` | `crm_service.py`、`repository/market_repository.py` | 已读取后端数据 |
| CRM 请求研究审批 | `POST /crm/approvals` | `crm_service.py:create_approval` | 已保存审批请求 |
| CRM 批准 / 退回 / 拒绝 / 人工结果确认 | `POST /crm/approvals/{id}/decision` | `crm_service.py:decide_approval` | 已保存状态；内部批准可创建队列任务 |
| CRM 开始 / 完成 / 取消任务 | `POST /crm/tasks/{id}/transition` | `crm_service.py:transition_execution_task` | 已保存状态和产出说明；不是自动研究执行器 |
| CRM 密码登录 / 注册 / 退出 | `/auth/login`、`/user/add`、`/user/logout` 等 | `auth_service.py`、`user_service.py` | 已接入；演示会话分支另有问题 |

前端依据：`src/lib/api/client.ts`、`src/components/sales/lead-form.tsx`、`src/components/sales/document-to-decision-demo.tsx`、`src/components/crm/crm-dashboard.tsx`、`src/components/crm/crm-data.ts`。

## 需要修复或进一步确定的差异

### 1. 真实文档的部分交付字段仍来自固定文案（优先处理）

前端真实上传后请求 `delivery_handoff`。后端确实运行 Dify 并取得 `answer`，但最后调用的是 `build_delivery_package(context, sources, "live_model")`，没有把模型结果用于交付字段生成。

`primary_users`、`required_outputs`、`acceptance_criteria` 是固定文案，仍被标为 `confirmed`；`business_outcome` 也有固定回退值。姓名与时间主要靠英文正则提取。`_source_ids_for` 按英文单词交集挑选来源，找不到时回退到第一条来源，无法证明字段事实由引用支持。

依据：后端 `src/server/service/demo_service.py:188`、`:245`、`:267`、`:541`。

建议：迁移时让真实分析输出结构化字段；校验字段、真实来源 ID、缺失值和冲突，不能将固定文案作为已确认的真实结果。预先核验的示例继续保持固定、明确标识。

### 2. 演示会话与真实登录状态混在一起（现有后端登录可复用）

AuthModal 的“演示会话”按钮仅调用 `createDemoSession`，没有请求后端或取得认证 Cookie。Provider 使用 `Boolean(user)` 判断 `isAuthenticated`，所以 `source="demo"` 也会被当作已登录。注册成功后自动登录失败时，也会创建同类演示身份。

结果：CRM 可显示为已登录后再被后端拒绝；同一 Provider 下的文档上传 UI 也可能误显示验证完成。

依据：前端 `src/components/auth/auth-modal.tsx:263`；`src/components/auth/auth-usage-provider.tsx:143`、`:221`、`:232`。

建议：演示身份只允许查看示例；真实权限以有效后端会话为准，不把注册后登录失败包装为已认证。无需新建演示登录 API。

### 3. CRM 的“来源”列表依赖关联记录（当前数据完整，后续存在范围风险）

看板 `source_count` 统计完整 `market_sources`。前端的来源列表却只把信号和代理商内嵌的 `source` 合并去重。未关联这些记录的来源无法进入列表，因此统计卡的数量不能保证等于点击后可浏览的数量。

server2 只读查询实测：完整来源 **40** 条，信号 **26** 条，代理商 **14** 条，前端可合并出的来源也是 **40** 条。因此当前快照没有漏列来源；这里是关联方式带来的后续风险，不能报告为当前已经少了来源。

依据：前端 `src/components/crm/crm-dashboard.tsx:119`；后端 `src/server/db/repository/market_repository.py:get_market_dashboard_from_db`。

当前路由没有完整来源列表接口。若要求完整来源浏览，需要确认新增来源 API；也可以明确将列表范围标为“关联来源”。本轮没有擅自新增接口。

### 4. CRM“研究 Agent”目前只体现在任务元数据中

审批按钮和执行任务按钮均已调用后端。批准生成 `queued` 任务，“开始”只写为 `in_progress`，“完成”要求人工提供说明与引用。当前后端没有研究执行循环、LangGraph worker 或自动任务消费流程。

依据：前端 `crm-dashboard.tsx:131`；后端 `crm_service.py:449`、`:508`。

这不是漏接现有 API，而是执行能力尚未实现。若要让研究 Agent 真正自动运行，需要另行确认范围；本次 Dify 迁移不自动扩大到市场研究或外联。

### 5. 官网咨询线索与 CRM 公司是两条独立链路

`POST /leads` 写入业务库 `leads`。CRM 公司列表读 CRM 库的公司模型；没有自动转入 CRM 公司/联系人/跟进任务的逻辑。现有 `scripts/import_crm_leads.py` 是另一套 CSV 导入流程，不是官网线索同步器。

依据：后端 `demo_service.py:create_lead`、`db/models/demo_model.py:41`、`db/repository/demo_repository.py:add_lead`、`crm_service.py:get_companies`。

首页咨询已经成功保存，不能判作未接后端。但若期待它立即出现在 CRM，尚缺导入/转化流程，需确定去重、负责人和审核规则。

### 6. 流式客户端对结束帧与非流式错误处理不一致

`streamDemoAnalysis` 检查 SSE 类型并处理末尾无换行的缓冲区。旧 `streamChatCompletion`、`runOcrDemo` 没有等价处理：HTTP 200 的业务错误 JSON 可能变成空结果；无换行的最后一帧可能被丢掉；普通聊天部分异常会被当作文本追加。

依据：前端 `src/lib/api/client.ts:409`、`:475`、`:511`、`:663`。

旧聊天和 OCR 页面当前重定向，因此这些问题属于保留组件/客户端的潜在兼容问题。后端迁移仍需明确 SSE 事件和失败行为，不能靠空文本表示成功。

### 7. OCR 的输入与追问语义不完整

OCR 首次请求覆盖前端传入的 `query`，`lang` 未用于后处理指令。追问时绕过 OCR，但 `conversation_id` 不传入 Dify Workflow payload，无法据此继续会话。仅传 query 且没有 conversation_id 时仍可能读取不存在的 file。

当前仍是百度 OCR → Dify Workflow。百度 OCR 本身是识别供应方，与 Dify 编排是两件事；推荐保留百度识别，替换文本后处理。

依据：后端 `src/server/service/ocr_service.py:60`、`:78`、`:100`、`:122`。

迁移验收应覆盖图片识别、用户问题和语言、业务错误、流式终止。若要增加可靠的多轮 OCR 追问，需要明确历史恢复策略。

## 用户已确认保留的展示行为

| 功能 | 当前行为 | 2026-10-05 用户决定 |
| --- | --- | --- |
| 文档 Demo `Confirm edit` | `setReviewed`，修改和记录只保存在浏览器组件状态中，刷新丢失；没有审核保存 API | 继续纯展示，不新增接口 |
| 文档 Demo `Preview system handoff` | 本地拼装并展示 JSON；后端返回 `handoff.mode="preview_only"` | 继续预览，不实现真实外部交接 |
| 文档 Demo `Run sample` | 首次读取后端示例，再本地按阶段延时展示；点击本身不重新调用分析 | 保留展示性质；不能称作实时模型运行 |
| 三个模板页咨询表单 | `<form action="mailto:...">`，交给邮件客户端；不是 `/leads` | 保留邮件客户端作为模板展示 |

依据：前端 `document-to-decision-demo.tsx:39`、`:50`、`:52`、`:56`；三个 `src/app/templates/*/page.tsx` 的 `form action`。

文档页面 `track()` 只发送浏览器 CustomEvent，当前未找到后端采集调用。后端只记录服务端分析等事件；不应将页面按钮事件误认为已经落库。若日后需要转化统计，应另定采集范围。

## 后端已有但前端未充分提供入口的能力

- CRM 公司/联系人/Deal 创建与编辑、活动新增、外联草稿、跟进任务创建与更新已有 API；当前 CRM 页面主要提供读取、审批和执行状态操作。不要把缺少管理表单误判为后端缺失。
- `/demo/v1/uploads/{id}` 已有状态查询 API，客户端有包装，但当前页面未恢复上传会话。
- 摘要、需求、风险、自由提问仍由 `/demo/v1/analyze` 接受；当前文档工作台只调用 `delivery_handoff`。
- 保留聊天组件已有创建 KB、上传、读取文件、删除文件、普通/RAG 提问调用。KB 列表/详情/检索有客户端函数，但当前公开聊天路由不展示这些管理入口。
- 知识库分段 `GET /rag/get_file_seg` 仍返回 `not supported yet`；文本上传函数也未实现且未绑定路由。当前页面没有对应操作，不属于活跃页面按钮漏接。
- 老 Workspace 组件的数据来自词典，导出按钮下载的是浏览器生成的演示 `.xls`；搜索区域是占位展示。当前 `/demo/workspace` 已重定向，不把它当作真实 CRM 管理页。

## Dify 实际依赖范围

| 能力 | 当前实现 | 推荐迁移 |
| --- | --- | --- |
| 普通聊天 `/chat/completions` | `chat_service.py` → `llm_service.py` → LangChain `ChatOpenAI` | 保留现有路径 |
| 兼容接口 `/ai/chat` | 函数名仍叫 `chat_dify`，实际转调本地 ChatService | 清楚区分遗留命名与实际依赖 |
| KB / RAG | 本地文件、LangChain 文档组件/Embedding、FAISS | 保留，不重复迁移 |
| OCR `/ai/ocr` | 百度 OCR → Dify `/workflows/run` | 百度识别 → LangChain 文本后处理 |
| 真实文档 `/demo/v1/analyze` | 本地检索 → `dify_workflow_service.stream_document_analysis` → 固定规则交付包 | LangGraph 编排 → LangChain 模型 → 字段/引用校验 → 原有 SSE/任务结果 |
| 旧 `utils.rag_retrieve` | 仍有 Dify dataset 调用，活跃 RAG 使用 `ai/rag/kb_service.py` | 确认调用关系后处理遗留函数，不能当作当前 KB 仍托管在 Dify |

现有文档 Dify DSL 已在 `deploy/dify/document_to_decision_v1.yml`，可以迁移其中的任务指令、文档不可信边界和来源引用规则。其主流程只有 Start → LLM → End；LangGraph 的分阶段设计是建议的后续实现，不能宣称现有 Dify 已有这些验证节点。

现有依赖为 LangChain 0.3 系列，没有 LangGraph。引入前必须验证与当前 `langchain-core`、`langchain-openai`、旧 agent 导入兼容，不把升级整个旧 agent 栈当作默认前提。

### 框架关系及待确认决定

LangChain 提供模型、检索和工具组件；LangGraph 提供流程编排与状态运行能力。LangGraph 可以不依赖完整 LangChain 框架，但那时模型与检索仍需要其他 SDK 或自行实现。对现有项目，组合使用可复用已经工作的 LangChain/RAG 代码。

官方来源：

- [LangGraph overview](https://docs.langchain.com/oss/python/langgraph/overview)
- [LangChain overview](https://docs.langchain.com/oss/python/langchain/overview)

用户询问两者关系后，授权尝试代码修改并部署；本轮按推荐组合实现，文档审核/交接继续保持已确认的展示边界。

## server2 部署情况与后续步骤

- SSH `root@server2` 已成功；实际运行后端目录为 `/root/project/0x7o7.service`。
- 活跃 Gunicorn 监听 `172.18.0.1:8000`，父进程为 PID 1。`0x7o7-api.service` 当前 inactive，仍指向旧 `/opt/0x7o7/current-api`，不能直接重启这个旧 unit 后假定线上生效。
- Docker Nginx 的 `/api/` 代理到后端。CRM `/crm-api/` 在 `preview.0x7o7.top` 配置中代理到同一后端 `/crm/`，并有 Basic Auth；不是当前前端访问旧 Node CRM 服务。
- 本地后端 `deploy.sh` 指向 `root@server`，并采用 `rsync --delete`；与本次目标不符，不能原样运行。同步还必须保留远端 KB、上传数据、虚拟环境、日志与生产配置。
- 前端 `deploy.sh` 已指向 server2，采用静态构建和发布目录/符号链接切换。如果修复前端认证等问题，需要同时部署前端构建。

框架确认后的顺序：确定兼容依赖 → 替换两条 Dify 活跃链路 → 修正与迁移有关的输入/字段/SSE 问题 → 运行现有测试及针对迁移的必要验证 → 在 server2 备份并分阶段发布 → 用实际入口检查健康、上传/分析与失败响应 → 保留回退目标。

新能力（完整来源 API、研究自动执行、官网线索转 CRM、审核持久化、真实交接）没有被默认混入本次迁移；其中审核与模板展示已按用户决定保留。
