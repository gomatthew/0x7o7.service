import traceback
from fastapi import Body
from src.server.dto import UpdateUserDto, ApiCommonResponseDTO
from src.configs import logger
from src.server.db.repository import get_user_id_from_db, update_user_to_db
from src.server.libs import bp, dt, token_handler


def user_login(account: str = Body(..., description="用户名"), password: str = Body(..., description="密码")):
    try:
        logger.info(f"🟢 用户登录:[START] ==> {account}")
        if user_obj := get_user_id_from_db(account):
            db_password = user_obj.password
            if bp.verify_password(password, db_password):
                token = token_handler.generate_token(account)
                update_user_to_db(user_obj.id, UpdateUserDto(token=token, last_login_time=dt.datetime))
                return ApiCommonResponseDTO(message="success").model_dict()
            else:
                return ApiCommonResponseDTO(message="账户密码错误").model_dict()
        return
    except BaseException as e:
        logger.error("🔴 用户登录:[ERROR]")
        logger.error(e)
        logger.error(traceback.format_exc())
        return ApiCommonResponseDTO(status=500, message="fail").model_dict()
