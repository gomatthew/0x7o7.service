# -*- coding: utf-8 -*-
from src.configs import get_setting
from src.enum import ModelTypeEnum
from langchain_openai.chat_models import ChatOpenAI

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


def generate_llm_instance(llm_model_name: str, temperature: float = setting.DEFAULT_TEMPERATURE,
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
