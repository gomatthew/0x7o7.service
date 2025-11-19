# -*- coding: utf-8 -*-
from typing import Tuple
from sqlalchemy import and_, or_
from src.server.db.session import with_session
from src.server.db.models import UserModel
from src.server.dto import AddUserDto, UpdateUserDto,UserInfoDto

@with_session
def get_user_info_from_db(session, user_id: str) -> UserInfoDto | None:
    if user_obj := session.query(UserModel).filter(UserModel.id == user_id).first():

        return UserInfoDto(**user_obj.__dict__)
    return None


@with_session
def user_checkin_from_db(session, user_phone: str, user_email: str) -> Tuple[str | None, bool, int]:
    filters = set()
    filters.add(UserModel.phone_number == user_phone) if user_phone else None
    filters.add(UserModel.mail == user_email) if user_email else None
    if user_obj := session.query(UserModel).filter(*filters).first():
        # db 有记录
        match user_obj.status:
            case 1:
                return "已有账户,请直接登录", False, 201
            case -1:
                return "用户已被封禁", False, 204
            case 0:
                return "用户未激活", False, 203
    # db 没有记录
    return None, True, 200


@with_session
def update_user_to_db(session, user_id, new_user: UpdateUserDto) -> (str, bool):
    """更新用户信息"""
    if user_obj := get_user_by_id(user_id):
        for k, v in new_user.model_dump().items():
            if v:
                setattr(user_obj, k, v)
        session.add(user_obj)
        return '',True
    else:
        return '',None


@with_session
def add_user(session, user_obj: AddUserDto):
    _user = UserModel(**user_obj.model_dump())
    session.add(_user)
    session.flush()
    return _user.id


@with_session
def get_user_by_id(session, user_id: str) -> UserModel | None:
    if user_obj := session.query(UserModel).filter(and_(UserModel.id == user_id, UserModel.status == 1)).first():
        return user_obj
    return None


@with_session
def get_user_token_by_id(session, user_id: str) -> str | None:
    if user_obj := session.query(UserModel).filter(UserModel.id == user_id).first():
        return user_obj.token
    return None
