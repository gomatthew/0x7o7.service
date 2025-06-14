# -*- coding: utf-8 -*-
from sqlalchemy import Column, String, Integer, DateTime
from src.server.db.models.base import BaseModel


class UserModel(BaseModel):
    __tablename__ = "user"
    user_nick_name = Column(String(32), nullable=False, comment="用户昵称")
    phone_number = Column(String(11), nullable=True, unique=True, index=True, default=None, comment="手机号")
    mail = Column(String(64), nullable=True, default=None, comment="邮箱")
    password = Column(String(128), nullable=False, comment="登录密码")
    token = Column(String(256), nullable=True)
    status = Column(Integer, default=1, comment="用户状态 -1-无效 1-有效 0-未激活")
    version = Column(Integer, default=0, comment="乐观锁")
    last_login_time = Column(DateTime, nullable=True, comment="最后登录时间")
    __mapper_args__ = {
        "version_id_col": version  # 开启乐观锁支持
    }
