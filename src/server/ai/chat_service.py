# -*- coding: utf-8 -*-
import json
import traceback

from sse_starlette.sse import EventSourceResponse

from src.configs import logger
from src.server.ai.llm_service import llm_service
from src.server.ai.prompt.prompt_config import get_prompt_template
from src.server.ai.rag.kb_service import get_kb_absolute_path, get_kb_record, read_metadata
from src.server.ai.rag.rag_service import rag_service
from src.server.dto import ApiCommonResponseDTO, ChatCompletionRequestDto


class ChatService:
    @staticmethod
    def get_messages(request_dto: ChatCompletionRequestDto) -> list[dict]:
        return [message.model_dump() for message in request_dto.messages]

    @staticmethod
    def get_last_user_query(messages: list[dict]) -> str:
        for message in reversed(messages):
            if message.get("role") == "user":
                return message.get("content") or ""
        return ""

    async def chat_completions(self, request_dto: ChatCompletionRequestDto):
        try:
            messages = self.get_messages(request_dto)
            if not self.get_last_user_query(messages):
                return ApiCommonResponseDTO(status=400, message="用户问题不能为空").model_dict()
            if request_dto.knowledge_base_id:
                if request_dto.is_stream:
                    return EventSourceResponse(self.stream_rag_chat(request_dto, messages))
                return await self.rag_chat(request_dto, messages)
            if request_dto.is_stream:
                return EventSourceResponse(self.stream_normal_chat(request_dto, messages))
            return await self.normal_chat(request_dto, messages)
        except BaseException as e:
            logger.error(e)
            logger.error(traceback.format_exc())
            return ApiCommonResponseDTO(status=500, message=str(e)).model_dict()

    async def normal_chat(self, request_dto: ChatCompletionRequestDto, messages: list[dict]):
        system_prompt = get_prompt_template("normal_chat", request_dto.business_type, request_dto.user_id)
        answer = await llm_service.complete(
            system_prompt=system_prompt,
            messages=messages,
            temperature=request_dto.temperature,
            max_tokens=request_dto.max_tokens,
        )
        return ApiCommonResponseDTO(status=200, message="success", data={
            "answer": answer,
            "sources": [],
            "knowledge_base_id": None,
            "is_rag": False,
        }).model_dict()

    async def stream_normal_chat(self, request_dto: ChatCompletionRequestDto, messages: list[dict]):
        try:
            system_prompt = get_prompt_template("normal_chat", request_dto.business_type, request_dto.user_id)
            async for token in llm_service.stream_complete(
                    system_prompt=system_prompt,
                    messages=messages,
                    temperature=request_dto.temperature,
                    max_tokens=request_dto.max_tokens):
                yield {"event": "message", "data": json.dumps({"content": token}, ensure_ascii=False)}
            yield {"event": "done", "data": json.dumps({"knowledge_base_id": None, "is_rag": False}, ensure_ascii=False)}
        except BaseException as e:
            logger.error(e)
            logger.error(traceback.format_exc())
            yield {"event": "error", "data": json.dumps({"message": str(e)}, ensure_ascii=False)}

    async def rag_chat(self, request_dto: ChatCompletionRequestDto, messages: list[dict]):
        record = get_kb_record(request_dto.knowledge_base_id)
        metadata = read_metadata(record.get("kb_path"))
        data = await rag_service.answer(
            messages=messages,
            kb_path=get_kb_absolute_path(record.get("kb_path")),
            knowledge_base_id=request_dto.knowledge_base_id,
            user_id=request_dto.user_id,
            business_type=request_dto.business_type or metadata.get("business_type"),
            embedding_model=metadata.get("embedding_model"),
            top_k=request_dto.top_k,
            fetch_k=request_dto.fetch_k,
            score_threshold=request_dto.score_threshold,
            temperature=request_dto.temperature,
            max_tokens=request_dto.max_tokens,
            enable_reranker=request_dto.reranker,
        )
        return ApiCommonResponseDTO(status=200, message="success", data=data).model_dict()

    async def stream_rag_chat(self, request_dto: ChatCompletionRequestDto, messages: list[dict]):
        try:
            record = get_kb_record(request_dto.knowledge_base_id)
            metadata = read_metadata(record.get("kb_path"))
            async for event in rag_service.stream_answer(
                    messages=messages,
                    kb_path=get_kb_absolute_path(record.get("kb_path")),
                    knowledge_base_id=request_dto.knowledge_base_id,
                    user_id=request_dto.user_id,
                    business_type=request_dto.business_type or metadata.get("business_type"),
                    embedding_model=metadata.get("embedding_model"),
                    top_k=request_dto.top_k,
                    fetch_k=request_dto.fetch_k,
                    score_threshold=request_dto.score_threshold,
                    temperature=request_dto.temperature,
                    max_tokens=request_dto.max_tokens,
                    enable_reranker=request_dto.reranker):
                yield event
        except BaseException as e:
            logger.error(e)
            logger.error(traceback.format_exc())
            yield {"event": "error", "data": json.dumps({"message": str(e)}, ensure_ascii=False)}


chat_service = ChatService()


async def chat_completions(request_dto: ChatCompletionRequestDto):
    return await chat_service.chat_completions(request_dto)
