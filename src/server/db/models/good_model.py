# -*- coding: utf-8 -*-
from sqlalchemy import Column, String, Integer, DateTime,func
from src.server.db.models.base import BaseModel


class GoodModel(BaseModel):
    __tablename__ = "goods"
    good_id = Column(Integer, primary_key=True)
    good_name = Column(String(128), comment="产品名称")
    created_user_id = Column(String(64), comment="创建人ID")
    created_user_name = Column(String(32), comment="创建人名称")
    created_time = Column(DateTime, default=func.now(), comment="创建时间")
    status = Column(String(2), default='1', comment="状态，0-已删除，1-有效")