# -*- coding: utf-8 -*-
import hashlib

from src.configs import get_setting
from src.server.ai.rag.rag_dto import RetrievedDocumentDto
from src.server.ai.rag.reranker_service import rerank_documents
from src.server.ai.rag.vector_store_service import faiss_vector_store_service

setting = get_setting()


class RetrievalPipeline:
    async def retrieve(self, query: str, kb_path: str, top_k: int | None = None, fetch_k: int | None = None,
                       score_threshold: float | None = None, embedding_model: str | None = None,
                       business_type: str | None = None, enable_reranker: bool = False) -> list[RetrievedDocumentDto]:
        top_k = top_k or setting.RAG_TOP_K
        fetch_k = fetch_k or setting.RAG_FETCH_K
        docs = faiss_vector_store_service.search(
            kb_path=kb_path,
            query=query,
            fetch_k=max(fetch_k, top_k),
            score_threshold=score_threshold,
            embedding_model=embedding_model,
        )
        docs = self.merge_results(docs)
        docs = await rerank_documents(query=query, docs=docs, enable_reranker=enable_reranker)
        return docs[:top_k]

    @staticmethod
    def merge_results(docs: list[RetrievedDocumentDto]) -> list[RetrievedDocumentDto]:
        seen_keys = set()
        results = []
        for doc in sorted(docs, key=lambda item: item.score, reverse=True):
            source = doc.metadata.get("source") or doc.metadata.get("filename") or ""
            chunk_index = doc.metadata.get("chunk_index")
            content_hash = hashlib.md5(doc.content.strip().encode("utf-8")).hexdigest()
            key = f"{source}:{chunk_index}:{content_hash}"
            if key in seen_keys:
                continue
            seen_keys.add(key)
            results.append(doc)
        return results


retrieval_pipeline = RetrievalPipeline()
