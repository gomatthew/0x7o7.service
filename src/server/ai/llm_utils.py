# -*- coding: utf-8 -*-
import asyncio
from typing import Union, List, Tuple, Dict, Awaitable
from pydantic import BaseModel, Field
from langchain.chains import LLMChain
from langchain_openai.chat_models import ChatOpenAI
from langchain.prompts.chat import ChatMessagePromptTemplate, ChatPromptTemplate
from langchain.tools import BaseTool
from src.configs import get_setting, logger
from src.enum import ModelTypeEnum
from src.server.ai.agent.agents_registry import agents_registry
from src.server.ai.memory.memory import ConversationBufferDBMemory

setting = get_setting()
llm_setting = setting.LLM_SETTING


def get_model_info(model_name: str, model_type: str = ModelTypeEnum.LLM) -> dict:
    model_names = list()
    for llm_info in llm_setting:
        match model_type:
            case ModelTypeEnum.LLM:
                model_names = llm_info.get('llm_models')
            case ModelTypeEnum.EMBEDDING:
                model_names = llm_info.get('embedding_models')
        if model_name in model_names:
            return llm_info
    return dict()


def generate_llm_instance(llm_model_name: str = setting.DEFAULT_LLM, temperature: float = setting.DEFAULT_TEMPERATURE,
                          verbose: bool = setting.DEFAULT_VERBOSE, streaming: bool = setting.DEFAULT_STREAM,
                          max_tokens: int = setting.MAX_TOKENS, callbacks: list = None) -> ChatOpenAI:
    """获取模型配置信息"""
    llm_params = dict(
        streaming=streaming,
        verbose=verbose,
        callbacks=callbacks,
        model_name=llm_model_name,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    llm_info = get_model_info(llm_model_name)
    if llm_info:
        # llm_extend_keys = ['openai_api_url', 'openai_api_key']
        # llm_extend_param = dict(zip(llm_extend_keys, itemgetter(*llm_extend_keys)(llm_info)))
        llm_params.update(openai_api_base=llm_info.get("api_base_url"),
                          openai_api_key=llm_info.get("api_key"),
                          openai_proxy=llm_info.get("api_proxy"), )
    llm_instance = ChatOpenAI(**llm_params)
    return llm_instance


class History(BaseModel):
    role: str = Field(...)
    content: str = Field(...)

    def to_msg_tuple(self):
        return "ai" if self.role == "assistant" else "human", self.content

    def to_msg_template(self, is_raw=True) -> ChatMessagePromptTemplate:
        role_maps = {
            "ai": "assistant",
            "human": "user"
        }
        role = role_maps.get(self.role, self.role)

        if is_raw:
            content = "{% raw %}" + self.content + "{% endraw %}"
        else:
            content = self.content
        return ChatMessagePromptTemplate.from_template(content, template_format="jinja2", role=role)

    @classmethod
    def from_data(cls, h: Union[List, Tuple, Dict]) -> "History":
        if isinstance(h, (list, tuple) and len(h) == 2):
            h = cls(role=h[0], content=h[1])
        elif isinstance(h, dict):
            h = cls(**h)
        return h


def create_models_chains(
        history, history_len, prompts, models, tools, callbacks, conversation_id, metadata
):
    memory = None
    chat_prompt = None

    if history:
        history = [History.from_data(h) for h in history]
        input_msg = History(role="user", content=prompts["llm_model"]).to_msg_template(
            False
        )
        chat_prompt = ChatPromptTemplate.from_messages(
            [i.to_msg_template() for i in history] + [input_msg]
        )
    elif conversation_id and history_len > 0:
        memory = ConversationBufferDBMemory(
            conversation_id=conversation_id,
            llm=models["llm_model"],
            message_limit=history_len,
        )
    else:
        input_msg = History(role="user", content=prompts["llm_model"]).to_msg_template(
            False
        )
        chat_prompt = ChatPromptTemplate.from_messages([input_msg])

    if "action_model" in models and tools:
        llm = models["action_model"]
        llm.callbacks = callbacks
        agent_executor = agents_registry(
            llm=llm, callbacks=callbacks, tools=tools, prompt=None, verbose=True
        )
        full_chain = {"input": lambda x: x["input"]} | agent_executor
    else:
        llm = models["llm_model"]
        llm.callbacks = callbacks
        chain = LLMChain(prompt=chat_prompt, llm=llm, memory=memory)
        full_chain = {"input": lambda x: x["input"]} | chain
    return full_chain


async def wrap_done(fn: Awaitable, event: asyncio.Event):
    """Wrap an awaitable with a event to signal when it's done or an exception is raised."""
    try:
        await fn
    except Exception as e:
        msg = f"Caught exception: {e}"
        logger.error(f"{e.__class__.__name__}: {msg}")
    finally:
        # Signal the aiter to stop.
        event.set()


def get_tool(name: str = None) -> Union[BaseTool, Dict[str, BaseTool]]:
    import importlib

    from src.server.ai.agent.tools import tools_registry

    if name is None:
        return tools_registry._TOOLS_REGISTRY
    else:
        return tools_registry._TOOLS_REGISTRY.get(name)
