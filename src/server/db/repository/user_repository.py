# -*- coding: utf-8 -*-
from sqlalchemy import and_, or_
from src.server.db.session import with_session
from src.server.db.models import UserModel
from src.server.dto import AddUserDto, UpdateUserDto


@with_session
def user_checkin_from_db(session, user_phone: str, user_email: str) -> (str, bool):
    if user_obj := session.query(UserModel).filter(
            or_(UserModel.phone_number == user_phone, UserModel.mail == user_email)).first():
        # db 有记录
        match user_obj.status:
            case 1:
                return "已有账户,请直接登录", False
            case -1:
                return "用户已被封禁", False
            case 0:
                return "用户未激活", False
    # db 没有记录
    return None, True


@with_session
def update_user_to_db(session, user_id, new_user: UpdateUserDto) -> (str, bool):
    """更新用户信息"""
    if user_obj := get_user_by_id(user_id):
        for k, v in new_user.model_dump().items():
            if v:
                setattr(user_obj, k, v)
        session.add(user_obj)
        return True
    else:
        return None


@with_session
def add_user(session, user_obj: AddUserDto):
    session.add(UserModel(**user_obj.model_dump()))


@with_session
def get_user_by_id(session, user_id: str) -> UserModel | None:
    if user_obj := session.query(UserModel).filter(and_(UserModel.id == user_id, UserModel.status == 1)).first():
        return user_obj
    return None
