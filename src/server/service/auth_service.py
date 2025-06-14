from fastapi import Body
from src.server.dto import ApiCommonResponseDTO
from src.configs import logger
from src.server.db.repository import get_user_by_account



async def user_login(account: str = Body(..., description="用户名"), password: str = Body(..., description="密码")):
    return