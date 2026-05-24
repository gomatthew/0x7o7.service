# -*- coding: utf-8 -*-
import asyncio
import io
import json
import os

from langchain_core.embeddings import Embeddings
from starlette.datastructures import UploadFile

from src.server.ai.chat_service import chat_service
from src.server.ai.prompt.prompt_config import get_prompt_template
from src.server.ai.rag.context_service import context_builder
from src.server.ai.rag.document_chunker_service import document_chunker
from src.server.ai.rag.kb_service import create_kb, get_kb_detail, get_kb_list, rag_retrieve, upload_file_to_kb
from src.server.ai.rag.query_service import query_processor
from src.server.ai.rag.rag_dto import LoadedDocumentDto, RetrievedDocumentDto
from src.server.ai.rag.retrieval_service import retrieval_pipeline
from src.server.ai.rag.vector_store_service import faiss_vector_store_service
from src.server.dto import ChatCompletionRequestDto, ChatMessageDto


class FakeEmbeddings(Embeddings):
    def embed_documents(self, texts):
        return [self.embed_query(text) for text in texts]

    def embed_query(self, text):
        values = [0.0, 0.0, 0.0, 0.0]
        for index, char in enumerate(text):
            values[index % 4] += float(ord(char) % 13)
        total = sum(values) or 1.0
        return [value / total for value in values]


def test_prompt_config_fallback():
    assert "专业、可靠" in get_prompt_template("normal_chat")
    assert "企业知识库助手" in get_prompt_template("rag_chat")
    assert "产品手册" in get_prompt_template("rag_chat", "product_manual")
    assert "企业知识库助手" in get_prompt_template("rag_chat", "unknown", user_id=1)


def test_query_processor_normalize_and_validate():
    assert query_processor.normalize("  你好\u3000 世界 \n ") == "你好 世界"
    assert query_processor.validate(" ")[0] is False
    assert query_processor.validate("产品怎么安装？")[1] == "产品怎么安装？"


def test_document_chunker_and_context_builder():
    docs = [LoadedDocumentDto(content="第一章 安装\n产品安装步骤如下。" * 80,
                              metadata={"filename": "manual.md", "page": 1})]
    chunks = document_chunker.split_documents(docs, chunk_size=120, chunk_overlap=20)
    assert len(chunks) > 1
    assert chunks[0].metadata["chunk_index"] == 0
    retrieved = [RetrievedDocumentDto(content=chunks[0].content, score=0.9, metadata=chunks[0].metadata)]
    context = context_builder.build(retrieved, max_chars=300)
    assert "来源：manual.md 第 1 页" in context
    assert context_builder.build([], max_chars=300) == ""


def test_faiss_vector_store_and_retrieval(tmp_path, monkeypatch):
    monkeypatch.setattr("src.server.ai.rag.vector_store_service.embedding_service.get_embeddings",
                        lambda model=None: FakeEmbeddings())
    chunks = [
        LoadedDocumentDto(content="产品支持本地部署和私有化部署", metadata={"filename": "a.txt"}),
        LoadedDocumentDto(content="售后电话是 400-000-0000", metadata={"filename": "b.txt"}),
    ]
    split_chunks = document_chunker.split_documents(chunks, chunk_size=80, chunk_overlap=0)
    faiss_vector_store_service.save_chunks(str(tmp_path), split_chunks, embedding_model="fake")
    assert os.path.exists(tmp_path / "index.faiss")
    docs = asyncio.run(retrieval_pipeline.retrieve(
        query="产品怎么部署",
        kb_path=str(tmp_path),
        top_k=1,
        fetch_k=2,
        embedding_model="fake",
        enable_reranker=False,
    ))
    assert len(docs) == 1
    assert docs[0].metadata.get("filename") in ["a.txt", "b.txt"]


def test_kb_create_detail_list_and_upload(tmp_path, monkeypatch):
    monkeypatch.setattr("src.server.ai.rag.kb_service.setting.BASE_PATH", str(tmp_path))
    monkeypatch.setattr("src.server.ai.rag.kb_service.create_kb_to_db", lambda **kwargs: None)
    monkeypatch.setattr("src.server.ai.rag.kb_service.get_kb_list_from_db",
                        lambda user_id, page_no, page_size: [{
                            "kb_id": "kb_test",
                            "kb_name": "测试知识库",
                            "kb_desc": "desc",
                            "kb_path": "kb/1/kb_test",
                            "created_user_id": "1",
                        }])
    monkeypatch.setattr("src.server.ai.rag.kb_service.get_kb_from_db",
                        lambda kb_id: {
                            "kb_id": kb_id,
                            "kb_name": "测试知识库",
                            "kb_desc": "desc",
                            "kb_path": "kb/1/kb_test",
                            "created_user_id": "1",
                        })
    monkeypatch.setattr("src.server.ai.rag.vector_store_service.embedding_service.get_embeddings",
                        lambda model=None: FakeEmbeddings())
    monkeypatch.setattr("src.server.ai.rag.kb_service.add_file_to_db", lambda file_dto: None)

    resp = create_kb(token_checker="1", kb_name="测试知识库", kb_description="desc",
                     business_type="product_manual", knowledge_base_id="kb_test")
    assert resp["status"] == 200
    metadata_path = tmp_path / "kb" / "1" / "kb_test" / "metadata.json"
    assert metadata_path.exists()
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert metadata["business_type"] == "product_manual"

    list_resp = get_kb_list(token_checker="1")
    assert list_resp["data"][0]["chunk_count"] == 0

    detail_resp = get_kb_detail(token_checker="1", kb_id="kb_test")
    assert detail_resp["data"]["knowledge_base_id"] == "kb_test"

    upload = UploadFile(file=io.BytesIO("产品支持本地部署。\n安装步骤非常简单。".encode("utf-8")), filename="manual.txt")
    upload_resp = upload_file_to_kb(token_checker="1", kb_id="kb_test", file=upload)
    assert upload_resp["status"] == 200
    assert upload_resp["data"]["chunk_count"] >= 1
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert metadata["document_count"] == 1
    assert (tmp_path / "kb" / "1" / "kb_test" / "index.faiss").exists()


def test_rag_retrieve_with_reranker_flag(tmp_path, monkeypatch):
    kb_path = tmp_path / "kb" / "1" / "kb_test"
    kb_path.mkdir(parents=True)
    metadata = {
        "knowledge_base_id": "kb_test",
        "embedding_model": "fake",
        "business_type": "default",
        "documents": [],
    }
    (kb_path / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr("src.server.ai.rag.kb_service.setting.BASE_PATH", str(tmp_path))
    monkeypatch.setattr("src.server.ai.rag.kb_service.get_kb_from_db",
                        lambda kb_id: {"kb_id": kb_id, "kb_path": "kb/1/kb_test"})

    async def fake_retrieve(**kwargs):
        assert kwargs["enable_reranker"] is True
        return [RetrievedDocumentDto(content="命中内容", score=0.8, metadata={"filename": "a.txt", "chunk_index": 1})]

    monkeypatch.setattr("src.server.ai.rag.kb_service.retrieval_pipeline.retrieve", fake_retrieve)
    resp = asyncio.run(rag_retrieve(token_checker="1", kb_id="kb_test", query="怎么部署", reranker=True))
    assert resp["status"] == 200
    assert resp["data"]["sources"][0]["metadata"]["filename"] == "a.txt"


def test_chat_service_normal_and_rag(monkeypatch, tmp_path):
    async def fake_complete(**kwargs):
        return "普通回答"

    async def fake_stream_complete(**kwargs):
        yield "流"
        yield "式"

    monkeypatch.setattr("src.server.ai.chat_service.llm_service.complete", fake_complete)
    monkeypatch.setattr("src.server.ai.chat_service.llm_service.stream_complete", fake_stream_complete)

    normal_req = ChatCompletionRequestDto(
        user_id=1,
        messages=[ChatMessageDto(role="user", content="你好")],
        is_stream=False,
    )
    resp = asyncio.run(chat_service.chat_completions(normal_req))
    assert resp["data"]["answer"] == "普通回答"

    stream_req = ChatCompletionRequestDto(
        user_id=1,
        messages=[ChatMessageDto(role="user", content="你好")],
        is_stream=True,
    )
    stream_resp = asyncio.run(chat_service.chat_completions(stream_req))
    assert stream_resp.status_code == 200

    monkeypatch.setattr("src.server.ai.chat_service.get_kb_record",
                        lambda kb_id: {"kb_id": kb_id, "kb_path": str(tmp_path)})
    monkeypatch.setattr("src.server.ai.chat_service.read_metadata",
                        lambda kb_path: {"embedding_model": "fake", "business_type": "default"})

    async def fake_answer(**kwargs):
        return {"answer": "RAG回答", "sources": [], "knowledge_base_id": "kb_test", "is_rag": True}

    monkeypatch.setattr("src.server.ai.chat_service.rag_service.answer", fake_answer)
    rag_req = ChatCompletionRequestDto(
        user_id=1,
        knowledge_base_id="kb_test",
        messages=[ChatMessageDto(role="user", content="资料是什么")],
        is_stream=False,
    )
    rag_resp = asyncio.run(chat_service.chat_completions(rag_req))
    assert rag_resp["data"]["answer"] == "RAG回答"
