from fastapi import APIRouter
from src.server.service import user_login, reset_password
from src.server.service.auth_service import request_email_code, verify_email_code

auth_router = APIRouter(prefix="/auth", tags=["用户登录注册服务"])
auth_router.post('/login')(user_login)
auth_router.post('/reset_password')(reset_password)
auth_router.post('/email/request-code')(request_email_code)
auth_router.post('/email/verify')(verify_email_code)
