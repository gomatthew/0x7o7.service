# -*- coding: utf-8 -*-
from sqlalchemy import JSON, Column, DateTime, Integer, String, func, Text

from src.server.db.base import Base


class MessageModel(Base):
    """
    聊天记录详情
    """

    __tablename__ = "conversation_message"
    message_id = Column(String(64), primary_key=True, comment="聊天记录ID")
    conversation_id = Column(String(64), default=None, index=True, comment="对话框ID")
    # chat_type = Column(String(50), comment="聊天类型")
    user_query = Column(String(4096), comment="用户问题")
    ai_response = Column(String(4096), comment="模型回答")
    # 记录知识库id等，以便后续扩展
    meta_data = Column(JSON, default={})
    user_id = Column(String(64), comment='用户ID')
    status = Column(String(8), default='1', comment='0-已删除，1-有效')
    llm_model = Column(String(128), comment='llm model')
    # response_extension = Column(String(4096), comment="引申提问")
    create_time = Column(DateTime, default=func.now(), comment="创建时间")
    finish_time = Column(DateTime, comment='完成时间')

    def __repr__(self):
        return f"<message(id='{self.id}', conversation_id='{self.conversation_id}', create_time='{self.create_time}')>"
