# -*- coding: utf-8 -*-
import uuid
from sqlalchemy import and_
from src.server.db.ai_models.message_model import MessageModel
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
def get_chat_history_from_db(session, conversation_id: None | str, limit: int = 10):
    if not conversation_id:
        return []
    data = list()
    messages = session.query(MessageModel).filter(
        and_(MessageModel.conversation_id == conversation_id, MessageModel.ai_response != "")).order_by(
        MessageModel.create_time.desc()).limit(limit)
    for m in messages:
        data.append({"query": m.query, "response": m.response})
    return data


@with_session
def add_message_to_db(session, conversation_id=None, message_id=None, query=None, llm_model=None, user_id=None):
    new_message = MessageModel()
    new_message.conversation_id = conversation_id
    new_message.message_id = message_id
    new_message.user_query = query
    new_message.llm_model = llm_model
    new_message.user_id = user_id
    session.add(new_message)
    session.commit()
    return message_id
