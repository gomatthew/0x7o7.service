# -*- coding: utf-8 -*-
from sqlalchemy import Column, String, Integer, DateTime
from src.server.db.models.base import BaseModel
from src.enum import RecordStatusEnum

class PermissionsModel(BaseModel):
    __tablename__ = "permissions"
    code = Column(String, comment="权限标识,如 order:create")
    name = Column(String, comment="显示名称:新增订单")
    version = Column(Integer, default=0, comment="version")
    __mapper_args__ = {
        "version_id_col": version  # 开启乐观锁支持
    }
