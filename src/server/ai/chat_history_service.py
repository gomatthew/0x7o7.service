# -*- coding: utf-8 -*-
from src.server.dto import ApiCommonResponseDTO
from src.server.db.repository import get_chat_history_detail_from_db, get_chat_history_list_from_db


async def get_chat_history_list():
    """
    获取聊天对话记录列表
    """
    if _history := get_chat_history_list_from_db():
        return ApiCommonResponseDTO(data=_history).model_dict()
    else:
        return ApiCommonResponseDTO(data={}).model_dict()


async def get_chat_history_detail():
    """
    获取聊天记录详情
    """
    if _conversation_list := get_chat_history_detail_from_db():
        return ApiCommonResponseDTO(data=_conversation_list).model_dict()
    else:
        return ApiCommonResponseDTO(data={}).model_dict()
