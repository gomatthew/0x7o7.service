# -*- coding: utf-8 -*-
import uuid
from src.server.db.ai_models.message_model import MessageModel
from src.server.db.session import with_session


@with_session
def update_message(session):
    return


@with_session
def filter_message(session, conversation_id: str, limit: int = 10):
    messages = (
        session.query(MessageModel)
        .filter_by(conversation_id=conversation_id)
        .
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
