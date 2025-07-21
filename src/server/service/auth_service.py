import traceback
from fastapi import Body
from src.server.dto import UpdateUserDto, ApiCommonResponseDTO
from src.configs import logger
from src.server.db.repository import get_user_id_from_db, update_user_to_db
from src.server.libs import bp, dt, token_handler


def user_login(username: str = Body(..., description="用户名"), password: str = Body(..., description="密码")):
    try:
        logger.info(f"🟢 用户登录:[START] ==> {username}")
        if user_obj := get_user_id_from_db(username):
            db_password = user_obj.password
            if bp.verify_password(password, db_password):
                token = token_handler.generate_token(username)
                update_user_to_db(user_obj.id, UpdateUserDto(token=token, last_login_time=dt.datetime))
                logger.info(f'🟢 用户登录:[END] ==> {username} 成功!')
                return ApiCommonResponseDTO(message="success",
                                            data={'user_id': user_obj.id, 'token': token}).model_dict()
            else:
                logger.info(f'🟢 用户登录:[END] ==> {username} 失败!')
                return ApiCommonResponseDTO(message="账户密码错误").model_dict()
        logger.info(f'🟢 用户登录:[END] ==> {username} 未注册!')
        return ApiCommonResponseDTO(message="该用户未注册!").model_dict()
    except BaseException as e:
        logger.error("🔴 用户登录:[ERROR]")
        logger.error(e)
        logger.error(traceback.format_exc())
        return ApiCommonResponseDTO(status=500, message="fail").model_dict()
