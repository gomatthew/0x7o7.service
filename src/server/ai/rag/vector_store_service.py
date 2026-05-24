# -*- coding: utf-8 -*-
import os
import traceback

from langchain_core.documents import Document

from src.configs import logger
from src.server.ai.embedding_service import embedding_service
from src.server.ai.rag.rag_dto import DocumentChunkDto, RetrievedDocumentDto

_VECTOR_STORE_CACHE = {}


class FaissVectorStoreService:
    @staticmethod
    def index_file_exists(kb_path: str) -> bool:
        return os.path.exists(os.path.join(kb_path, "index.faiss")) and os.path.exists(os.path.join(kb_path, "index.pkl"))

    def load_vector_store(self, kb_path: str, embedding_model: str | None = None):
        try:
            from langchain_community.vectorstores import FAISS

            cache_key = (kb_path, embedding_model)
            if cache_key in _VECTOR_STORE_CACHE:
                return _VECTOR_STORE_CACHE[cache_key]
            if not self.index_file_exists(kb_path):
                raise FileNotFoundError("知识库尚未上传文档或尚未生成向量")
            embeddings = embedding_service.get_embeddings(model=embedding_model)
            vector_store = FAISS.load_local(
                kb_path,
                embeddings,
                allow_dangerous_deserialization=True,
            )
            _VECTOR_STORE_CACHE[cache_key] = vector_store
            return vector_store
        except BaseException as e:
            logger.error(e)
            logger.error(traceback.format_exc())
            raise

    def save_chunks(self, kb_path: str, chunks: list[DocumentChunkDto], embedding_model: str | None = None):
        try:
            from langchain_community.vectorstores import FAISS

            if not chunks:
                raise ValueError("文档切分结果为空")
            os.makedirs(kb_path, exist_ok=True)
            docs = [Document(page_content=chunk.content, metadata=chunk.metadata) for chunk in chunks]
            embeddings = embedding_service.get_embeddings(model=embedding_model)
            if self.index_file_exists(kb_path):
                vector_store = self.load_vector_store(kb_path, embedding_model=embedding_model)
                vector_store.add_documents(docs)
            else:
                vector_store = FAISS.from_documents(docs, embeddings)
            vector_store.save_local(kb_path)
            self.refresh_cache(kb_path, embedding_model=embedding_model, vector_store=vector_store)
            return vector_store
        except BaseException as e:
            logger.error(e)
            logger.error(traceback.format_exc())
            raise

    def search(self, kb_path: str, query: str, fetch_k: int, score_threshold: float | None = None,
               embedding_model: str | None = None) -> list[RetrievedDocumentDto]:
        try:
            vector_store = self.load_vector_store(kb_path, embedding_model=embedding_model)
            docs_with_scores = vector_store.similarity_search_with_relevance_scores(query, k=fetch_k)
            results = []
            for doc, score in docs_with_scores:
                if score_threshold is not None and score < score_threshold:
                    continue
                results.append(RetrievedDocumentDto(content=doc.page_content, score=float(score), metadata=doc.metadata))
            return results
        except BaseException as e:
            logger.error(e)
            logger.error(traceback.format_exc())
            raise

    @staticmethod
    def refresh_cache(kb_path: str, embedding_model: str | None = None, vector_store=None):
        cache_key = (kb_path, embedding_model)
        if vector_store is None:
            _VECTOR_STORE_CACHE.pop(cache_key, None)
        else:
            _VECTOR_STORE_CACHE[cache_key] = vector_store


faiss_vector_store_service = FaissVectorStoreService()
