# -*- coding: utf-8 -*-
from sqlalchemy import Column, String, Integer

from src.server.db.ai_models.base import BaseModel


class KnowledgeBase(BaseModel):
    __tablename__ = 'knowledge_base'
    id = Column(Integer, primary_key=True)
    server_kb_id= Column(String(64), nullable=False,comment="云上知识库id")
    knowledge_id = Column(String)
    kb_name = Column(String(32), nullable=False, comment="知识库名称")
    description = Column(String(128), nullable=True, comment="描述")
    status = Column(String(2), default='1', comment="记录状态，0-已删除，1-有效")
