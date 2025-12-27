# -*- coding: utf-8 -*-
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


class UserDto(BaseModel):
    id: int = Field(..., description="id")
    user_nick_name: Optional[str] = Field(None, max_length=32, description="用户昵称")
    phone_number: Optional[str] = Field(None, max_length=11, description="手机号")
    password: str = Field(..., description="密码")
    mail: Optional[str] = Field(None, description="邮箱")
    status: Optional[int] = Field(1, description="用户状态 -1-无效 1-有效 0-未激活")
    token: Optional[str] = Field(None, description="token")
    last_login_time: Optional[datetime] = Field(None, description="最后登录时间")
    model_config = {"from_attributes": True}
    created_time: Optional[datetime] = None

class AddUserDto(BaseModel):
    # id: str
    user_nick_name: Optional[str]
    phone_number: Optional[str]
    mail: str
    password: str
    created_user: str


class UpdateUserDto(BaseModel):
    user_nick_name: Optional[str] = None
    phone_number: str = None
    password: str = None
    status: int = None
    token: str | None = None
    last_login_time: datetime = None


class UserInfoDto(BaseModel):
    id: str | int
    user_nick_name: Optional[str] = None
    mail: str
    password: str
    phone_number: Optional[str] = None
    avatar: Optional[str] = None
    last_login_time: Optional[datetime] = None
    created_time: Optional[datetime] = None
