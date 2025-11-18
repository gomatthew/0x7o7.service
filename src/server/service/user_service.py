import uuid
import traceback
from typing import Optional
import bcrypt as bp
from fastapi import Body

from src.configs import logger
from src.server.db.repository import add_user, user_checkin_from_db
from src.server.dto import AddUserDto, ApiCommonResponseDTO
from src.server.libs import bp


def user_register(user_nickname: Optional[str] = Body(None, description="用户昵称"),
                  mail: str = Body(..., description="邮箱"),
                  phone: Optional[str] = Body(None, description="手机"),
                  user_password: str = Body(..., description="用户密码")) -> ApiCommonResponseDTO:
    try:
        logger.info(f"🟢 新增用户:[START] ==> {mail}")
        check_message, check_tag, check_status = user_checkin_from_db(user_phone=phone, user_email=mail)
        if check_tag:
            # 新增用户
            # user_id = uuid.uuid4().hex
            user_hash_password = bp.hash_password(user_password)
            user_obj = AddUserDto(
                # id=user_id,
                user_nick_name=user_nickname,
                phone_number=phone,
                mail=mail,
                password=user_hash_password,
                created_user='admin')
            user_id = add_user(user_obj)
            logger.info("🟢 新增用户:[END] 结果: SUCCESS!")
            return ApiCommonResponseDTO(message="success", data={'user_id': user_id, 'token': ''},
                                        status=check_status).model_dict()
        logger.info(f"🟢 新增用户:[END] 结果: {check_message}")
        return ApiCommonResponseDTO(message=check_message, data={}, status=check_status).model_dict()
    except BaseException as e:
        logger.error("🔴 新增用户:[ERROR]")
        logger.error(e)
        logger.error(traceback.format_exc())
        return ApiCommonResponseDTO(status=500, message="fail", data={}).model_dict()
