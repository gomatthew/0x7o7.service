# -*- coding: utf-8 -*-
from sqlalchemy import or_, and_
from src.server.db.models.user_model import UserModel
from src.server.dto.user_dto import UserDto
from src.server.db.session import with_session


@with_session
def get_user_id_from_db(session, account: str) -> UserDto | None:
    if user_obj := session.query(UserModel).filter(and_(UserModel.status == 1, or_(UserModel.mail == account,
                                                                                   UserModel.phone_number == account))).first():
        return UserDto.model_validate(user_obj)
    return None
