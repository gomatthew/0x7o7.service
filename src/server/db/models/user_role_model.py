# -*- coding: utf-8 -*-
from sqlalchemy import Column, String, Integer, DateTime
from src.server.db.models.base import BaseModel
from src.enum import RecordStatusEnum

class UserRoleModel(BaseModel):
    __tablename__ = "user_role"
    role_name = Column(String(32), nullable=False, comment="用户昵称")
    role_desc = Column(String(128), comment="角色描述")
    status = Column(Integer, default=RecordStatusEnum.ACTIVATE.value, comment="角色状态 -1-无效 1-有效 0-未激活")
    version = Column(Integer, default=0, comment="乐观锁")
    __mapper_args__ = {
        "version_id_col": version  # 开启乐观锁支持
    }


class RolePermissionModel(BaseModel):
    __tablename__ = "role_permission_relation"
    role_id = Column(Integer, comment="role_id")
    permission_id = Column(Integer, comment="permission_id")
    version = Column(Integer, default=0, comment="乐观锁")
    __mapper_args__ = {
        "version_id_col": version  # 开启乐观锁支持
    }
