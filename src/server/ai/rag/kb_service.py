import traceback

from fastapi import Body
from typing import Optional
from src.enum import FileTypeEnum
from src.configs import get_setting, logger
from src.server.dto import ApiCommonResponseDTO

setting = get_setting()


def create_kb(kb_name: str = Body(..., description="知识库名称"),
              description: Optional[str] = Body(None, description="知识库描述")) -> ApiCommonResponseDTO:
    """创建 dify 知识库"""
    try:
        url = setting.DIFY_SERVER_URL
        setting.DIFY_KB_SECRET_KEY
        return ApiCommonResponseDTO().model_dict()

    except BaseException as e:
        logger.error(e)
        logger.error(traceback.format_exc())
        return ApiCommonResponseDTO(status=500, message="fail").model_dict()


def get_kb_list():
    """获取 dify 知识库列表  """
    try:
        return ApiCommonResponseDTO().model_dict()
    except BaseException as e:
        logger.error(e)
        logger.error(traceback.format_exc())
        return ApiCommonResponseDTO(status=500, message="fail").model_dict()


def delete_kb():
    """删除dify 知识库"""
    try:
        return ApiCommonResponseDTO().model_dict()
    except BaseException as e:
        logger.error(e)
        logger.error(traceback.format_exc())
        return ApiCommonResponseDTO(status=500, message="fail").model_dict()


def upload_file_to_kb():
    """上传知识库文件 """
    try:
        return ApiCommonResponseDTO().model_dict()
    except BaseException as e:
        logger.error(e)
        logger.error(traceback.format_exc())
        return ApiCommonResponseDTO(status=500, message="fail").model_dict()


def get_kb_file_list():
    """获取知识库文件列表"""
    try:
        return ApiCommonResponseDTO().model_dict()
    except BaseException as e:
        logger.error(e)
        logger.error(traceback.format_exc())
        return ApiCommonResponseDTO(status=500, message="fail").model_dict()


def delete_file_to_kb():
    """删除知识库文件"""
    try:
        return ApiCommonResponseDTO().model_dict()
    except BaseException as e:
        logger.error(e)
        logger.error(traceback.format_exc())
        return ApiCommonResponseDTO(status=500, message="fail").model_dict()


def get_file_seg_list():
    """获得文件切片"""
    try:
        return ApiCommonResponseDTO().model_dict()
    except BaseException as e:
        logger.error(e)
        logger.error(traceback.format_exc())
        return ApiCommonResponseDTO(status=500, message="fail").model_dict()
