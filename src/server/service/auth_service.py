import secrets
import traceback
from fastapi import Body, Request, Response, BackgroundTasks
from src.server.dto import AddUserDto, UpdateUserDto, ApiCommonResponseDTO
from src.configs import logger, get_setting
from src.server.db.repository import add_user, get_user_by_email, get_user_id_from_db, update_user_to_db, get_user_by_id
from src.server.libs import bp, dt, token_handler, send_mail
from src.server.libs.redis_lib import async_delete, async_exists, async_get, async_rate_limit, async_set
from src.server.utils import TokenChecker, get_client_ip

setting = get_setting()


def set_auth_cookie(response: Response, token: str, expire_hours: int):
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=setting.COOKIE_SECURE,
        samesite="lax",
        max_age=3600 * expire_hours,
        path="/",
    )


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
                set_auth_cookie(response, token, expire_hours)
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


async def request_email_code(request: Request, background_tasks: BackgroundTasks,
                             email: str = Body(..., embed=True)):
    """Send a one-time code without revealing account existence."""
    normalized = str(email).strip().lower()
    if not normalized or "@" not in normalized or len(normalized) > 254:
        return ApiCommonResponseDTO(status=400, message="email.invalid", data={}).model_dict()
    try:
        client_ip = get_client_ip(request)
        if await async_exists(f"passwordless:cooldown:{normalized}"):
            return ApiCommonResponseDTO(status=200, message="email.codeAccepted", data={}).model_dict()
        limited, _ = await async_rate_limit(
            f"passwordless:ip:{client_ip}", setting.VERIFY_IP_LIMIT, setting.VERIFY_IP_TTL
        )
        if limited:
            return ApiCommonResponseDTO(status=200, message="email.codeAccepted", data={}).model_dict()
        code = f"{secrets.randbelow(1_000_000):06d}"
        await async_set(f"passwordless:code:{normalized}", code, ex=setting.VERIFY_CODE_TTL)
        await async_set(f"passwordless:cooldown:{normalized}", "1", ex=setting.VERIFY_COOLDOWN_TTL)
        background_tasks.add_task(
            send_mail,
            message=f"Your 0x7o7 AI Studio sign-in code is {code}. It expires in 10 minutes.",
            receiver_email=normalized,
            subject="Your 0x7o7 AI Studio sign-in code",
        )
    except BaseException as error:
        logger.error(error)
        logger.error(traceback.format_exc())
        # Preserve a uniform response. Operators can see delivery failures in logs.
    return ApiCommonResponseDTO(status=200, message="email.codeAccepted", data={}).model_dict()


async def verify_email_code(request: Request, response: Response,
                            email: str = Body(...), code: str = Body(...)):
    normalized = str(email).strip().lower()
    supplied_code = str(code).strip()
    if not normalized or "@" not in normalized or len(normalized) > 254:
        return ApiCommonResponseDTO(status=400, message="email.invalid", data={}).model_dict()
    try:
        client_ip = get_client_ip(request)
        limited, _ = await async_rate_limit(
            f"passwordless:verify:{client_ip}:{normalized}", setting.VERIFY_FAIL_LIMIT, setting.VERIFY_FAIL_TTL
        )
        if limited:
            return ApiCommonResponseDTO(status=429, message="email.tooManyAttempts", data={}).model_dict()
        expected_code = await async_get(f"passwordless:code:{normalized}")
        if not expected_code or not secrets.compare_digest(str(expected_code), supplied_code):
            return ApiCommonResponseDTO(status=400, message="email.invalidCode", data={}).model_dict()
        user = get_user_by_email(normalized)
        if not user:
            user_id = add_user(AddUserDto(
                user_nick_name=normalized.split("@", 1)[0][:32],
                phone_number=None,
                mail=normalized,
                password=bp.hash_password(secrets.token_urlsafe(32)),
                role=setting.GUEST_ROLE,
                created_user="passwordless",
            ))
            user = get_user_by_id(str(user_id))
        token, expire_hours = token_handler.generate_token(user.id)
        update_user_to_db(user.id, UpdateUserDto(token=token, last_login_time=dt.datetime,
                                                  role=user.role or setting.GUEST_ROLE))
        await async_delete(f"passwordless:code:{normalized}")
        set_auth_cookie(response, token, expire_hours)
        return ApiCommonResponseDTO(status=200, message="email.signedIn", data={
            "user_id": user.id,
            "mail": user.mail,
            "role": user.role or setting.GUEST_ROLE,
        }).model_dict()
    except BaseException as error:
        logger.error(error)
        logger.error(traceback.format_exc())
        return ApiCommonResponseDTO(status=500, message="email.signInFailed", data={}).model_dict()


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
