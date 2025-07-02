# -*- coding: utf-8 -*-
from sqlalchemy import Column, DateTime, Integer, String, func
from src.server.db.base import Base


class BaseModel(Base):
    """
    base model for extend
    """
    __abstract__ = True
    id = Column(Integer, primary_key=True, autoincrement=True)
    created_user = Column(String(64), nullable=False, comment="创建人")
    created_time = Column(DateTime, nullable=False, default=func.current_timestamp())
