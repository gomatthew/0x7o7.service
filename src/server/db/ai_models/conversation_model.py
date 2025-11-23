# -*- coding: utf-8 -*-
from src.server.db.base import Base
from sqlalchemy import JSON, Column, DateTime, String, func
from src.enum import RecordStatusEnum

class ConversationModel(Base):
    """
    聊天对话
    """
    __tablename__ = 'conversation'
    conversation_id = Column(String(64), primary_key=True)
    conversation_title = Column(String(128), comment="对话主题")
    user_id = Column(String(64), comment='user_id')
    status = Column(String(8), default=RecordStatusEnum.ACTIVATE.value, comment='0-已删除，1-有效')

    create_time = Column(DateTime, default=func.now(), comment="创建时间")
    finish_time = Column(DateTime, comment='完成时间')
