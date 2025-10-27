# -*- coding: utf-8 -*-
import uuid
from sqlalchemy import and_
from src.server.db.ai_models.message_model import MessageModel
from src.server.db.ai_models.conversation_model import ConversationModel
from src.server.db.session import with_session
from src.server.libs.datetime_lib import dt


@with_session
def update_message(session, message_id, ai_response):
    session.query(MessageModel).filter(MessageModel.message_id == message_id).update(
        {MessageModel.ai_response: ai_response, MessageModel.finish_time: dt.method_datetime()})
    session.commit()
    return


@with_session
def filter_message(session, conversation_id: str, limit: int = 10):
    messages = (
        session.query(MessageModel).filter_by(conversation_id=conversation_id).
        # 用户最新的query 也会插入到db，忽略这个message record
        filter(MessageModel.ai_response != "")
        .
        # 返回最近的limit 条记录
        order_by(MessageModel.create_time.desc())
        .limit(limit)
        .all()
    )
    # 直接返回 List[MessageModel] 报错
    data = []
    for m in messages:
        data.append({"query": m.query, "response": m.response})
    return data


@with_session
def get_chat_history_detail_from_db(session, conversation_id: None | str, page_no: int = 1, page_size: int = 10):
    """
    获取聊天记录详情
    """
    if not conversation_id:
        return []
    data = list()
    messages = session.query(MessageModel).filter(
        and_(MessageModel.conversation_id == conversation_id, MessageModel.ai_response != "")).order_by(
        MessageModel.create_time.desc()).offset((page_no - 1) * page_size).limit(page_size)
    for m in messages:
        data.append({"query": m.query, "response": m.response})
    return data


@with_session
def get_chat_history_list_from_db(session, user_id: str, page_no: int = 1, page_size: int = 10):
    filters = set()
    filters.add(ConversationModel.user_id == user_id)
    if _conversations := session.query(ConversationModel).filter(*filters).order_by(
            ConversationModel.create_time.desc()).offset((page_no - 1) * page_size).limit(page_size):
        return _conversations
    else:
        return []


@with_session
def add_message_to_db(session, conversation_id=None, message_id=None, query=None, llm_model=None, user_id=None):
    """
    新增对话
    """
    new_message = MessageModel()
    new_message.conversation_id = conversation_id
    new_message.message_id = message_id
    new_message.user_query = query
    new_message.llm_model = llm_model
    new_message.user_id = user_id
    session.add(new_message)
    session.commit()
    return message_id


@with_session
def add_conversation_to_db(session, title=None, llm_model=None, user_id=None):
    new_conversation = ConversationModel()
    new_conversation.title = title
    new_conversation.llm_model = llm_model
    new_conversation.user_id = user_id
    session.add(new_conversation)
    session.commit()
    return new_conversation.conversation_id
