from fastapi import APIRouter
from src.server.service import user_login

auth_router = APIRouter(prefix="/auth", tags=["用户登录注册服务"])
auth_router.post('/login')(user_login)
