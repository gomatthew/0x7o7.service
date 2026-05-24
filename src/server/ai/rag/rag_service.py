# -*- coding: utf-8 -*-
import json
import traceback

from src.configs import get_setting, logger
from src.server.ai.llm_service import llm_service
from src.server.ai.prompt.prompt_config import get_prompt_template
from src.server.ai.rag.context_service import context_builder
from src.server.ai.rag.query_service import query_processor
from src.server.ai.rag.retrieval_service import retrieval_pipeline

setting = get_setting()


class RagService:
    @staticmethod
    def get_question(messages: list[dict]) -> str:
        for message in reversed(messages):
            if message.get("role") == "user" and message.get("content"):
                return message.get("content")
        return ""

    async def answer(self, messages: list[dict], kb_path: str, knowledge_base_id: str,
                     user_id: int | str | None = None, business_type: str | None = None,
                     embedding_model: str | None = None, top_k: int | None = None,
                     fetch_k: int | None = None, score_threshold: float | None = None,
                     temperature: float | None = None, max_tokens: int | None = None,
                     enable_reranker: bool = False) -> dict:
        question = self.get_question(messages)
        valid, query = query_processor.validate(question)
        if not valid:
            return {
                "answer": query,
                "sources": [],
                "knowledge_base_id": knowledge_base_id,
                "is_rag": True,
            }
        docs = await retrieval_pipeline.retrieve(
            query=query,
            kb_path=kb_path,
            top_k=top_k,
            fetch_k=fetch_k,
            score_threshold=score_threshold,
            embedding_model=embedding_model,
            business_type=business_type,
            enable_reranker=enable_reranker,
        )
        sources = context_builder.to_sources(docs)
        context = context_builder.build(docs)
        if not context:
            return {
                "answer": "根据当前知识库资料无法确定",
                "sources": sources,
                "knowledge_base_id": knowledge_base_id,
                "is_rag": True,
            }
        prompt_template = get_prompt_template("rag_chat", business_type=business_type, user_id=user_id)
        system_prompt = prompt_template.format(context=context, question=query)
        answer = await llm_service.complete(
            system_prompt=system_prompt,
            messages=[{"role": "user", "content": query}],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return {
            "answer": answer,
            "sources": sources,
            "knowledge_base_id": knowledge_base_id,
            "is_rag": True,
        }

    async def stream_answer(self, messages: list[dict], kb_path: str, knowledge_base_id: str,
                            user_id: int | str | None = None, business_type: str | None = None,
                            embedding_model: str | None = None, top_k: int | None = None,
                            fetch_k: int | None = None, score_threshold: float | None = None,
                            temperature: float | None = None, max_tokens: int | None = None,
                            enable_reranker: bool = False):
        try:
            question = self.get_question(messages)
            valid, query = query_processor.validate(question)
            if not valid:
                yield {"event": "error", "data": json.dumps({"message": query}, ensure_ascii=False)}
                return
            docs = await retrieval_pipeline.retrieve(
                query=query,
                kb_path=kb_path,
                top_k=top_k,
                fetch_k=fetch_k,
                score_threshold=score_threshold,
                embedding_model=embedding_model,
                business_type=business_type,
                enable_reranker=enable_reranker,
            )
            sources = context_builder.to_sources(docs)
            yield {"event": "source", "data": json.dumps({"sources": sources}, ensure_ascii=False)}
            context = context_builder.build(docs)
            if not context:
                yield {"event": "message", "data": json.dumps({"content": "根据当前知识库资料无法确定"}, ensure_ascii=False)}
                yield {"event": "done", "data": json.dumps({"knowledge_base_id": knowledge_base_id, "is_rag": True}, ensure_ascii=False)}
                return
            prompt_template = get_prompt_template("rag_chat", business_type=business_type, user_id=user_id)
            system_prompt = prompt_template.format(context=context, question=query)
            async for token in llm_service.stream_complete(
                    system_prompt=system_prompt,
                    messages=[{"role": "user", "content": query}],
                    temperature=temperature,
                    max_tokens=max_tokens):
                yield {"event": "message", "data": json.dumps({"content": token}, ensure_ascii=False)}
            yield {"event": "done", "data": json.dumps({"knowledge_base_id": knowledge_base_id, "is_rag": True}, ensure_ascii=False)}
        except BaseException as e:
            logger.error(e)
            logger.error(traceback.format_exc())
            yield {"event": "error", "data": json.dumps({"message": str(e)}, ensure_ascii=False)}


rag_service = RagService()
