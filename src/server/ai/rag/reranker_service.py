# -*- coding: utf-8 -*-
import traceback

import httpx

from src.configs import get_setting, logger
from src.server.ai.rag.rag_dto import RetrievedDocumentDto

setting = get_setting()


class NoopReranker:
    async def rerank(self, query: str, docs: list[RetrievedDocumentDto]) -> list[RetrievedDocumentDto]:
        return docs


class SiliconFlowReranker:
    async def rerank(self, query: str, docs: list[RetrievedDocumentDto]) -> list[RetrievedDocumentDto]:
        if not docs:
            return []
        try:
            payload = {
                "model": setting.RERANKER_MODEL,
                "query": query,
                "documents": [doc.content for doc in docs],
                "top_n": len(docs),
                "return_documents": False,
            }
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(
                    f"{setting.LLM_BASE_URL.rstrip('/')}/rerank",
                    headers={"Authorization": f"Bearer {setting.LLM_API_KEY}", "Content-Type": "application/json"},
                    json=payload,
                )
            if resp.status_code != 200:
                logger.error(resp.text)
                return docs
            data = resp.json()
            results = data.get("results") or []
            reranked_docs = []
            for item in results:
                index = item.get("index")
                if index is None or index >= len(docs):
                    continue
                doc = docs[index]
                score = item.get("relevance_score", doc.score)
                reranked_docs.append(RetrievedDocumentDto(content=doc.content, score=score, metadata=doc.metadata))
            return reranked_docs or docs
        except BaseException as e:
            logger.error(e)
            logger.error(traceback.format_exc())
            return docs


noop_reranker = NoopReranker()
silicon_flow_reranker = SiliconFlowReranker()


async def rerank_documents(query: str, docs: list[RetrievedDocumentDto],
                           enable_reranker: bool = False) -> list[RetrievedDocumentDto]:
    if not enable_reranker:
        return await noop_reranker.rerank(query, docs)
    return await silicon_flow_reranker.rerank(query, docs)
