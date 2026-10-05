# -*- coding: utf-8 -*-
import traceback
from typing import Optional
from urllib.parse import urlparse

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai.chat_models import ChatOpenAI

from src.configs import get_setting, logger

setting = get_setting()


class LLMService:
    def get_llm(self, temperature: Optional[float] = None, max_tokens: Optional[int] = None,
                streaming: bool = False) -> ChatOpenAI:
        model_kwargs = {}
        token_limit = setting.LLM_MAX_TOKENS if max_tokens is None else max_tokens
        if urlparse(setting.LLM_BASE_URL).hostname in {"api.siliconflow.cn", "api.siliconflow.com"}:
            # ChatOpenAI renames max_tokens; this provider still expects max_tokens.
            extra_body = {}
            if token_limit is not None:
                extra_body["max_tokens"] = token_limit
            if "/qwen3" in setting.LLM_MODEL.lower():
                extra_body["enable_thinking"] = setting.LLM_ENABLE_THINKING
            model_kwargs["extra_body"] = extra_body
        elif token_limit is not None:
            model_kwargs["max_completion_tokens"] = token_limit
        return ChatOpenAI(
            model=setting.LLM_MODEL,
            api_key=setting.LLM_API_KEY,
            base_url=setting.LLM_BASE_URL,
            temperature=setting.LLM_TEMPERATURE if temperature is None else temperature,
            top_p=setting.LLM_TOP_P,
            streaming=streaming,
            request_timeout=setting.LLM_REQUEST_TIMEOUT,
            max_retries=setting.LLM_MAX_RETRIES,
            **model_kwargs,
        )

    @staticmethod
    def build_messages(system_prompt: str, messages: list[dict]) -> list:
        chat_messages = [SystemMessage(content=system_prompt)]
        for message in messages:
            role = message.get("role")
            content = message.get("content", "")
            if not content:
                continue
            if role == "assistant":
                chat_messages.append(AIMessage(content=content))
            else:
                chat_messages.append(HumanMessage(content=content))
        return chat_messages

    async def complete(self, system_prompt: str, messages: list[dict],
                       temperature: Optional[float] = None, max_tokens: Optional[int] = None) -> str:
        try:
            llm = self.get_llm(temperature=temperature, max_tokens=max_tokens, streaming=False)
            response = await llm.ainvoke(self.build_messages(system_prompt, messages))
            return response.content if isinstance(response.content, str) else str(response.content)
        except BaseException as e:
            logger.error(e)
            logger.error(traceback.format_exc())
            raise

    async def stream_complete(self, system_prompt: str, messages: list[dict],
                              temperature: Optional[float] = None, max_tokens: Optional[int] = None):
        try:
            llm = self.get_llm(temperature=temperature, max_tokens=max_tokens, streaming=True)
            async for chunk in llm.astream(self.build_messages(system_prompt, messages)):
                content = chunk.content if isinstance(chunk.content, str) else str(chunk.content)
                if content:
                    yield content
        except BaseException as e:
            logger.error(e)
            logger.error(traceback.format_exc())
            raise


llm_service = LLMService()
