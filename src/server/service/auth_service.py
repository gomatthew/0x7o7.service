import traceback
from fastapi import Body, Request, Response, BackgroundTasks
from src.server.dto import UpdateUserDto, ApiCommonResponseDTO
from src.configs import logger, get_setting
from src.server.db.repository import get_user_id_from_db, update_user_to_db, get_user_by_id
from src.server.libs import bp, dt, token_handler, send_mail
from src.server.libs.redis_lib import async_rate_limit
from src.server.utils import TokenChecker, get_client_ip

setting = get_setting()


async def user_login(request: Request, response: Response, background_tasks: BackgroundTasks,
                     username: str = Body(..., description="用户名"),
                     password: str = Body(..., description="密码")):
    try:
        logger.info(f"🟢 用户登录:[START] ==> {username}")
        client_ip = get_client_ip(request)
        ip_limited, _ = await async_rate_limit(f"login_ip:{client_ip}", setting.LOGIN_IP_LIMIT, setting.LOGIN_IP_TTL)
        if ip_limited:
            return ApiCommonResponseDTO(message="login.rateLimited", data={}, status=429).model_dict()
        if user_obj := get_user_id_from_db(username):
            db_password = user_obj.password
            if bp.verify_password(password, db_password):
                token, expire_hours = token_handler.generate_token(user_obj.id)
                user_role = user_obj.role or setting.GUEST_ROLE
                update_user_to_db(user_obj.id, UpdateUserDto(token=token, last_login_time=dt.datetime, role=user_role))
                logger.info(f'🟢 用户登录:[END] ==> {username} 成功!')
                background_tasks.add_task(send_mail, message=f'用户登录:{user_obj.mail}',
                                          receiver_email=setting.RECEIVER,
                                          subject=f'用户{user_obj.mail}登录成功!')
                response.set_cookie(
                    key="access_token",
                    value=token,
                    httponly=True,  # JS 无法访问
                    secure=False,  # 生产环境 HTTPS 设置 True
                    samesite="lax",  # 防 CSRF
                    max_age=3600 * expire_hours
                )
                return ApiCommonResponseDTO(message="login.success",
                                            data={'user_id': user_obj.id, 'mail': user_obj.mail,
                                                  'role': user_role,
                                                  'created_time': user_obj.created_time}).model_dict()
            else:
                logger.info(f'🟢 用户登录:[END] ==> {username} 失败!')
                return ApiCommonResponseDTO(message="login.wrong", data={}, status=201).model_dict()
        logger.info(f'🟢 用户登录:[END] ==> {username} 未注册!')
        return ApiCommonResponseDTO(message="login.noUser", data={}, status=201).model_dict()
    except BaseException as e:
        logger.error("🔴 用户登录:[ERROR]")
        logger.error(e)
        logger.error(traceback.format_exc())
        return ApiCommonResponseDTO(status=500, message="fail", data={}).model_dict()


def reset_password(token_checker: TokenChecker,
                   old_password: str = Body(..., description="old password"),
                   new_password: str = Body(..., description="密码"),
                   ):
    try:
        if not (user_id := token_checker):
            return ApiCommonResponseDTO(message="请重新登录!", data={}, status=401).model_dict()
        logger.info(f"🟢 用户修改密码:[START] ==> user_id: {user_id}")
        if user_obj := get_user_by_id(user_id):
            db_password = user_obj.password
            if bp.verify_password(old_password, db_password):
                update_user_to_db(user_id, UpdateUserDto(password=bp.hash_password(new_password)))
                logger.info(f"🟢 用户修改密码:[END] ==> user_id: {user_id} 成功!")
                return ApiCommonResponseDTO(status=200, message="success", data={}).model_dict()
            return ApiCommonResponseDTO(status=400, message="wrongPassword", data={}).model_dict()
        else:
            return ApiCommonResponseDTO(status=400, message="invalidUser", data={}).model_dict()
        # 清理token
        response.delete_cookie(key="Authorization")
        return ApiCommonResponseDTO(status=200, message="修改成功!", data={}).model_dict()
    except BaseException as e:
        logger.error(e)
        logger.error(traceback.format_exc())
        return ApiCommonResponseDTO(status=500, message="fail", data={}).model_dict()
