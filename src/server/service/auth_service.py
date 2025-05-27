from fastapi import Body
from src.server.dto import ApiCommonResponseDTO
from src.configs import logger

async def user_login(username: str = Body(..., description="用户名"), password: str = Body(..., description="密码")):
    if username == '0x7o7' and password == 'root':
        logger.info(ApiCommonResponseDTO(message="login success").model_dict())
        return ApiCommonResponseDTO(message="login success").model_dict()
    else:
        logger.info(ApiCommonResponseDTO(message="login success").model_dict())
        return ApiCommonResponseDTO(message="login error").model_dict()
