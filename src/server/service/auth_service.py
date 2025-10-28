import traceback
from fastapi import Body, Response
from src.server.dto import UpdateUserDto, ApiCommonResponseDTO
from src.configs import logger
from src.server.db.repository import get_user_id_from_db, update_user_to_db
from src.server.libs import bp, dt, token_handler


def user_login(response: Response, username: str = Body(..., description="用户名"),
               password: str = Body(..., description="密码")):
    try:
        logger.info(f"🟢 用户登录:[START] ==> {username}")
        if user_obj := get_user_id_from_db(username):
            db_password = user_obj.password
            if bp.verify_password(password, db_password):
                token, expire_hours = token_handler.generate_token(user_obj.id)
                update_user_to_db(user_obj.id, UpdateUserDto(token=token, last_login_time=dt.datetime))
                logger.info(f'🟢 用户登录:[END] ==> {username} 成功!')
                response.set_cookie(
                    key="Authorization",
                    value=token,
                    httponly=True,  # JS 无法访问
                    secure=False,  # 生产环境 HTTPS 设置 True
                    samesite="lax",  # 防 CSRF
                    max_age=3600 * expire_hours  # 1小时过期
                )
                return ApiCommonResponseDTO(message="success",
                                            data={'user_id': user_obj.id}).model_dict()
            else:
                logger.info(f'🟢 用户登录:[END] ==> {username} 失败!')
                return ApiCommonResponseDTO(message="账户密码错误", data={}).model_dict()
        logger.info(f'🟢 用户登录:[END] ==> {username} 未注册!')
        return ApiCommonResponseDTO(message="该用户未注册!", data={}).model_dict()
    except BaseException as e:
        logger.error("🔴 用户登录:[ERROR]")
        logger.error(e)
        logger.error(traceback.format_exc())
        return ApiCommonResponseDTO(status=500, message="fail", data={}).model_dict()
