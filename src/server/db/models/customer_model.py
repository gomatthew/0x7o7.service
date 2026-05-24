# -*- coding: utf-8 -*-
from sqlalchemy import Column, String, Integer, DateTime
from src.server.db.models.base import BaseModel
from src.enum import RecordStatusEnum


class CustomerModel(BaseModel):
    __tablename__ = "customer"
    # id = Column(String(64), primary_key=True)
    tenant_id = Column(String(64), comment='组织id')
    owner_id = Column(String(64), comment='所有者id')
    phone_number = Column(String(11), nullable=True, unique=True, index=True, default=None, comment="手机号")
    mail = Column(String(64), nullable=True, default=None, comment="邮箱")
    password = Column(String(128), nullable=False, comment="登录密码")
    describe = Column(String(256), nullable=True, comment="备注")
    # token = Column(String(256), nullable=True)
    # avatar = Column(String(256), nullable=True, comment='头像')
    status = Column(Integer, default=RecordStatusEnum.ACTIVATE.value, comment="用户状态 -1-无效 1-有效 0-未激活")
    version = Column(Integer, default=0, comment="乐观锁")
    subscribe_time = Column(DateTime, nullable=True, comment="订阅到期时间")
    __mapper_args__ = {
        "version_id_col": version  # 开启乐观锁支持
    }
