import traceback
import random
from typing import Optional
from fastapi import Body, Request, Response, BackgroundTasks

from src.configs import logger, get_setting
from src.server.db.repository import add_user, user_checkin_from_db, get_user_info_from_db
from src.server.dto import AddUserDto, ApiCommonResponseDTO
from src.server.libs import bp, send_mail
from src.server.libs.redis_lib import async_delete, async_exists, async_get, async_rate_limit, async_set
from src.server.utils import TokenChecker, get_client_ip

setting = get_setting()


async def send_verify_code(request: Request, background_tasks: BackgroundTasks,
                           email: str = Body(..., description="邮箱")) -> ApiCommonResponseDTO:
    try:
        email = email.strip().lower()
        client_ip = get_client_ip(request)
        logger.info(f"🟢 发送邮箱验证码:[START] ==> {email}")
        if await async_exists(f"verify_cooldown:{email}"):
            return ApiCommonResponseDTO(status=429, message="verify.cooldown", data={}).model_dict()
        ip_limited, _ = await async_rate_limit(f"verify_ip:{client_ip}", setting.VERIFY_IP_LIMIT,
                                               setting.VERIFY_IP_TTL)
        if ip_limited:
            return ApiCommonResponseDTO(status=429, message="verify.ipLimit", data={}).model_dict()
        verify_code = f"{random.randint(0, 999999):06d}"
        await async_set(f"verify_code:{email}", verify_code, ex=setting.VERIFY_CODE_TTL)
        await async_set(f"verify_cooldown:{email}", "1", ex=setting.VERIFY_COOLDOWN_TTL)
        background_tasks.add_task(send_mail, message=f"您的验证码是：{verify_code}，10分钟内有效。",
                                  receiver_email=email, subject="0x7o7 注册验证码")
        logger.info(f"🟢 发送邮箱验证码:[END] ==> {email}")
        return ApiCommonResponseDTO(status=200, message="success", data={}).model_dict()
    except BaseException as e:
        logger.error("🔴 发送邮箱验证码:[ERROR]")
        logger.error(e)
        logger.error(traceback.format_exc())
        return ApiCommonResponseDTO(status=500, message="fail", data={}).model_dict()


async def user_register(request: Request, background_tasks: BackgroundTasks,
                        user_nickname: Optional[str] = Body(None, description="用户昵称"),
                        mail: str = Body(..., description="邮箱"),
                        phone: Optional[str] = Body(None, description="手机"),
                        user_password: str = Body(..., description="用户密码"),
                        verify_code: str = Body(..., description="邮箱验证码")) -> ApiCommonResponseDTO:
    try:
        mail = mail.strip().lower()
        logger.info(f"🟢 新增用户:[START] ==> {mail}")
        fail_key = f"verify_fail:{mail}"
        if await async_exists(fail_key):
            fail_count = await async_get(fail_key)
            if int(fail_count or 0) >= setting.VERIFY_FAIL_LIMIT:
                return ApiCommonResponseDTO(message="verify.locked", status=429, data={}).model_dict()
        cache_code = await async_get(f"verify_code:{mail}")
        if not cache_code:
            return ApiCommonResponseDTO(message="verify.expired", status=400, data={}).model_dict()
        if str(cache_code) != str(verify_code).strip():
            fail_limited, _ = await async_rate_limit(fail_key, setting.VERIFY_FAIL_LIMIT, setting.VERIFY_FAIL_TTL)
            if fail_limited:
                return ApiCommonResponseDTO(message="verify.locked", status=429, data={}).model_dict()
            return ApiCommonResponseDTO(message="verify.invalid", status=400, data={}).model_dict()
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
                role=setting.GUEST_ROLE,
                created_user='admin')
            user_id = add_user(user_obj)
            await async_delete(f"verify_code:{mail}")
            await async_delete(fail_key)
            logger.info("🟢 新增用户:[END] 结果: SUCCESS!")
            background_tasks.add_task(send_mail, message=f'新增用户:{mail}', receiver_email=setting.RECEIVER,
                                      subject='0x7o7新增用户!')
            return ApiCommonResponseDTO(message="success", data={'user_id': user_id, 'token': ''},
                                        status=check_status).model_dict()
        logger.info(f"🟢 新增用户:[END] 结果: {check_message}")
        return ApiCommonResponseDTO(message=check_message, data={}, status=check_status).model_dict()
    except BaseException as e:
        logger.error("🔴 新增用户:[ERROR]")
        logger.error(e)
        logger.error(traceback.format_exc())
        return ApiCommonResponseDTO(status=500, message="fail", data={}).model_dict()


def get_userinfo(token_checker: TokenChecker):
    try:
        logger.info(f"🟢 查询用户:[START] {token_checker}")
        if not (user_id := token_checker):
            return ApiCommonResponseDTO(message="由于长时间未登录请重新登录", data={}, status=401).model_dict()
        user_info = get_user_info_from_db(user_id=user_id)
        logger.info(f"🟢 查询用户:[END] {token_checker} 成功!")
        return ApiCommonResponseDTO(message="success", data=user_info, status=200).model_dict()
    except BaseException as e:
        logger.error(e)
        logger.error(traceback.format_exc())
        return ApiCommonResponseDTO(status=500, message="fail", data={}).model_dict()


def user_logout(token_checker: TokenChecker, response: Response):
    try:
        if not (user_id := token_checker):
            return ApiCommonResponseDTO(message="请重新登录!", data={}, status=401).model_dict()
        response.delete_cookie(key="access_token")
        return ApiCommonResponseDTO(message="success", data={}, status=200).model_dict()
    except BaseException as e:
        logger.error(e)
        logger.error(traceback.format_exc())
        return ApiCommonResponseDTO(status=500, message="fail", data={}).model_dict()
