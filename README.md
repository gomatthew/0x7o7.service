# 0x7o7.service.v1 后端联调说明

本文档面向 `0x7o7.web.react-3.0` 前端 demo 联调使用，重点说明当前后端已经具备的 AI Chat + RAG 能力、推荐 demo 流程和接口调用方式。

## 1. 后端能力范围

当前后端已经支持：

- 普通 AI Chat
- RAG 知识库 Chat
- `/chat/completions` 统一聊天入口
- `is_stream=false` 普通 JSON 返回
- `is_stream=true` SSE 流式返回
- 本地知识库创建
- DB 保存知识库映射和本地 KB 路径
- 文档上传到本地知识库
- txt / md / pdf / docx 文档解析
- 中文友好文档切分
- OpenAI-compatible embedding
- FAISS 本地向量库持久化
- RAG 检索 sources 返回
- `top_k` / `fetch_k` / `score_threshold` 检索参数
- `reranker=true/false` 重排序开关
- Prompt 集中配置
- business_type prompt fallback

当前知识库存储规则：

```text
kb/{user_id}/{knowledge_base_id}
├── index.faiss
├── index.pkl
├── metadata.json
└── docs/
    └── uploaded-file.txt
```

数据库中 `knowledge_base.kb_dify_name` 当前保存本地 KB 相对路径，例如：

```text
kb/1/kb_product_manual
```

## 2. 启动后端

项目根目录：

```bash
cd /Users/0x7o7/workspace/0x7o7.service.v1
```

安装依赖：

```bash
.venv/bin/python -m pip install -r requirements.txt
```

启动：

```bash
.venv/bin/python main.py
```

默认服务地址：

```text
http://localhost:8001
```

Swagger：

```text
http://localhost:8001/docs
```

## 3. 通用响应格式

后端当前遵循项目既有响应格式：

```json
{
  "status": 200,
  "message": "success",
  "data": {}
}
```

注意：当前不是 `code/message/data`，前端判断成功时请优先使用 `status === 200`。

## 4. 推荐 Demo 流程

建议前端 demo 按以下顺序展示：

1. 普通 Chat
2. 创建知识库
3. 上传 txt / md 文档
4. 查看知识库列表 / 详情
5. 查看文档列表
6. RAG 问答
7. 展示引用 sources
8. 切换 `reranker=false/true`
9. 调整 `top_k` / `fetch_k` / `score_threshold`
10. 展示无命中时的兜底回答

## 5. 普通 Chat

接口：

```text
POST /chat/completions
```

请求示例：

```json
{
  "user_id": 1,
  "knowledge_base_id": null,
  "messages": [
    {
      "role": "user",
      "content": "你好，介绍一下你自己"
    }
  ],
  "business_type": "default",
  "is_stream": false,
  "temperature": 0.7,
  "max_tokens": 2048
}
```

返回示例：

```json
{
  "status": 200,
  "message": "success",
  "data": {
    "answer": "你好，我是一个专业、可靠的 AI 助手...",
    "sources": [],
    "knowledge_base_id": null,
    "is_rag": false
  }
}
```

## 6. 创建知识库

接口：

```text
POST /rag/create_kb
```

请求示例：

```json
{
  "user_id": 1,
  "knowledge_base_id": "kb_product_manual",
  "kb_name": "产品手册知识库",
  "kb_description": "用于产品手册问答",
  "business_type": "product_manual"
}
```

返回示例：

```json
{
  "status": 200,
  "message": "success",
  "data": {
    "knowledge_base_id": "kb_product_manual",
    "kb_id": "kb_product_manual",
    "path": "kb/1/kb_product_manual"
  }
}
```

前端建议：

- demo 阶段可以允许用户手动输入 `knowledge_base_id`。
- 如果不传 `knowledge_base_id`，后端会自动生成。
- `business_type` 会影响后续 RAG prompt。

## 7. 知识库列表

接口：

```text
GET /rag/get_kb_list?user_id=1&page=1&limit=10
```

返回字段重点：

```json
{
  "status": 200,
  "message": "success",
  "data": [
    {
      "kb_id": "kb_product_manual",
      "kb_name": "产品手册知识库",
      "kb_desc": "用于产品手册问答",
      "kb_path": "kb/1/kb_product_manual",
      "created_user_id": "1",
      "business_type": "product_manual",
      "embedding_model": "Qwen/Qwen3-Embedding-0.6B",
      "document_count": 1,
      "chunk_count": 32,
      "updated_at": "2026-05-23T18:30:00"
    }
  ]
}
```

## 8. 知识库详情

接口：

```text
GET /rag/get_kb_detail?kb_id=kb_product_manual
```

前端建议展示：

- 知识库名称
- 描述
- business_type
- embedding_model
- document_count
- chunk_count
- path
- created_at
- updated_at

## 9. 上传文档

接口：

```text
POST /rag/upload_file
Content-Type: multipart/form-data
```

表单字段：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| kb_id | string | 是 | 知识库 ID |
| user_id | number | 建议传 | 用户 ID |
| file | file | 是 | 上传文件 |

支持文件：

- `.txt`
- `.md`
- `.pdf`
- `.docx`

返回示例：

```json
{
  "status": 200,
  "message": "success",
  "data": {
    "knowledge_base_id": "kb_product_manual",
    "filename": "manual.txt",
    "chunk_count": 12,
    "embedding_model": "Qwen/Qwen3-Embedding-0.6B",
    "status": "success"
  }
}
```

前端建议：

- 上传成功后刷新知识库详情和文档列表。
- demo 首选 `.txt` / `.md`，最稳定。
- PDF / DOCX 可作为扩展展示。

## 10. 文档列表

接口：

```text
GET /rag/get_kb_file_list?kb_id=kb_product_manual
```

返回示例：

```json
{
  "status": 200,
  "message": "success",
  "data": {
    "documents": [
      {
        "document_id": "doc_xxx",
        "filename": "manual.txt",
        "original_filename": "manual.txt",
        "file_path": "docs/manual.txt",
        "file_type": "txt",
        "chunk_count": 12,
        "created_at": "2026-05-23T18:30:00"
      }
    ],
    "db_files": []
  }
}
```

## 11. RAG 检索

接口：

```text
POST /rag/retrieve
```

请求示例：

```json
{
  "kb_id": "kb_product_manual",
  "query": "这个产品如何本地部署？",
  "top_k": 5,
  "fetch_k": 20,
  "score_threshold": null,
  "reranker": false
}
```

返回示例：

```json
{
  "status": 200,
  "message": "success",
  "data": {
    "knowledge_base_id": "kb_product_manual",
    "sources": [
      {
        "content": "产品支持本地部署...",
        "score": 0.82,
        "metadata": {
          "document_id": "doc_xxx",
          "filename": "manual.txt",
          "page": null,
          "section_title": "部署说明",
          "chunk_index": 3
        }
      }
    ],
    "records": [],
    "reranker": false
  }
}
```

前端建议：

- 这个接口适合做“检索调试面板”。
- 展示 `content`、`score`、`filename`、`chunk_index`。
- 可以加 `reranker` 开关做命中结果对比。

## 12. RAG Chat

接口：

```text
POST /chat/completions
```

请求示例：

```json
{
  "user_id": 1,
  "knowledge_base_id": "kb_product_manual",
  "messages": [
    {
      "role": "user",
      "content": "这个产品如何本地部署？"
    }
  ],
  "business_type": "product_manual",
  "is_stream": false,
  "top_k": 5,
  "fetch_k": 20,
  "score_threshold": null,
  "temperature": 0.7,
  "max_tokens": 2048,
  "reranker": false
}
```

返回示例：

```json
{
  "status": 200,
  "message": "success",
  "data": {
    "answer": "根据产品手册，该产品支持本地部署...",
    "sources": [
      {
        "content": "产品支持本地部署...",
        "score": 0.82,
        "metadata": {
          "filename": "manual.txt",
          "chunk_index": 3
        }
      }
    ],
    "knowledge_base_id": "kb_product_manual",
    "is_rag": true
  }
}
```

## 13. SSE 流式输出

普通 Chat 或 RAG Chat 都可以设置：

```json
{
  "is_stream": true
}
```

接口仍然是：

```text
POST /chat/completions
```

SSE 事件格式：

```text
event: source
data: {"sources":[...]}

event: message
data: {"content":"回答 token"}

event: done
data: {"knowledge_base_id":"kb_product_manual","is_rag":true}

event: error
data: {"message":"错误信息"}
```

前端建议：

- RAG 流式时先处理 `source`，提前展示引用来源。
- `message` 事件用于逐步拼接回答。
- `done` 事件结束 loading。
- `error` 事件展示错误提示。

## 14. Reranker 开关

当前两个入口都支持 `reranker`：

```json
{
  "reranker": true
}
```

行为：

- `reranker=false`：FAISS vector search -> 去重 -> score_threshold -> top_k
- `reranker=true`：FAISS 用 `fetch_k` 多召回 -> reranker 重排 -> top_k

前端 demo 建议：

- 做一个“启用重排序”开关。
- 同一个问题分别请求 `reranker=false` 和 `reranker=true`。
- 展示 sources 顺序和 score 差异。

## 15. 检索参数说明

| 参数 | 默认值 | 说明 |
| --- | --- | --- |
| top_k | 5 | 最终进入 prompt 的文档数量 |
| fetch_k | 20 | 初始召回候选数量 |
| score_threshold | null | 相似度阈值，为空时不过滤 |
| reranker | false | 是否启用重排序 |

前端 demo 可以把这些参数做成高级配置区。

## 16. 前端推荐页面

建议在 `0x7o7.web.react-3.0` 做以下页面：

```text
AI Chat Playground
├── 普通 Chat
├── 流式 / 非流式切换

Knowledge Base
├── 创建知识库
├── 知识库列表
├── 知识库详情

Document Upload
├── 上传文档
├── 文档列表
├── chunk_count 展示

RAG Playground
├── 选择知识库
├── 输入问题
├── top_k / fetch_k / score_threshold / reranker
├── AI 回答
└── 引用 sources
```

## 17. 联调注意事项

- `/chat/completions` 是推荐的新统一入口。
- `/rag/*` 是知识库管理和检索调试入口。
- `/rag/upload_file` 必须使用 `multipart/form-data`。
- 后端返回字段是 `status`，不是 `code`。
- RAG Chat 前必须先完成：创建知识库 -> 上传文档 -> FAISS 入库。
- 如果知识库没有上传文档，检索会返回“知识库尚未上传文档或尚未生成向量”。
- 如果没有命中资料，RAG Chat 会回答“根据当前知识库资料无法确定”。
- 当前未实现单文档删除；后续建议通过重建 FAISS 实现。

## 18. 最小联调顺序

1. 调 `/chat/completions` 普通 Chat。
2. 调 `/rag/create_kb` 创建知识库。
3. 调 `/rag/upload_file` 上传 `txt` 文档。
4. 调 `/rag/get_kb_detail` 确认 `document_count/chunk_count`。
5. 调 `/rag/retrieve` 看 sources。
6. 调 `/chat/completions`，带 `knowledge_base_id` 做 RAG Chat。
7. 切换 `is_stream=true` 验证 SSE。
8. 切换 `reranker=true` 验证重排序链路。
