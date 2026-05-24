# -*- coding: utf-8 -*-
from sqlalchemy import Column, String, Integer, DateTime, func, ForeignKey
from src.server.db.models.base import BaseModel
from src.enum import RecordStatusEnum

class OrderModel(BaseModel):
    __tablename__ = "order"
    good_name = Column(String(128), comment="产品名称")
    created_user_id = Column(String(64), comment="创建人ID")
    created_user_name = Column(String(32), comment="创建人名称")
    created_time = Column(DateTime, default=func.now(), comment="创建时间")
    status = Column(String(2), default=RecordStatusEnum.ACTIVATE.value, comment="状态，0-已删除，1-有效")


class OrderGoodModel(BaseModel):
    __tablename__ = "order_good_rel"
    order_id = Column(Integer, ForeignKey("order.id", ondelete="CASCADE"), primary_key=True)
    good_id = Column(Integer, ForeignKey("good.id", ondelete="CASCADE"), primary_key=True)