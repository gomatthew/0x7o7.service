# -*- coding: utf-8 -*-
from typing import Optional
from pydantic import BaseModel


class AddUserDto(BaseModel):
    id: str
    user_nick_name: str
    phone_number: int
    mail: str
    password: str
    created_user: str
