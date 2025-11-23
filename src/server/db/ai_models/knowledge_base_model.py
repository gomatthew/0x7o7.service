# -*- coding: utf-8 -*-
from sqlalchemy import Column, String, Integer, DateTime, func

from src.server.db.ai_models.base import BaseModel
from src.enum import RecordStatusEnum

class KnowledgeBase(BaseModel):
    __tablename__ = 'knowledge_base'
    # id = Column(Integer, primary_key=True)
    knowledge_id = Column(String(64), primary_key=True, nullable=False, comment="云上知识库id")
    # knowledge_id = Column(String(64), nullable=False)
    kb_name = Column(String(64), nullable=False, comment="知识库名称")
    kb_dify_name = Column(String(64), nullable=False, comment="dify 知识库名称")
    description = Column(String(128), nullable=True, comment="描述")
    status = Column(String(2), default=RecordStatusEnum.ACTIVATE.value, comment="记录状态，0-已删除，1-有效")
    created_user_id = Column(String(64), comment="创建用户")
