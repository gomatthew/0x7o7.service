import json
import traceback
import requests
from fastapi import Body, File, UploadFile, Query
from typing import Optional
from urllib.parse import urljoin
from src.enum import FileTypeEnum
from src.configs import get_setting, logger
from src.server.dto import ApiCommonResponseDTO
from src.server.utils import TokenChecker
from src.server.db.repository.ai_repository import create_kb_to_db, get_kb_list_from_db, delete_kb_from_db

setting = get_setting()
kb_base_url = urljoin(setting.DIFY_SERVER_URL, 'datasets')
kb_file_base_url = urljoin(setting.DIFY_SERVER_URL, 'datasets/')


def create_kb(token_checker: TokenChecker,
              kb_name: str = Body(..., description="知识库名称"),
              kb_description: Optional[str] = Body(None, description="知识库描述")) -> ApiCommonResponseDTO:
    """创建 dify 知识库"""
    try:
        if not (user_id := token_checker):
            return ApiCommonResponseDTO(message="用户未登录!").model_dict()
        logger.info(kb_base_url)
        resp = requests.post(kb_base_url, headers={"Content-Type": "application/json",
                                                   "Authorization": f"Bearer {setting.DIFY_KB_SECRET_KEY}"},
                             json={'name': kb_name, 'description': kb_description})
        match resp.status_code:
            case 200:
                kb_id = resp.json().get('id')
                create_kb_to_db(kb_name=kb_name, kb_description=kb_description,
                                kb_id=kb_id, user_id=user_id)
                return ApiCommonResponseDTO(status=201, message='success', data={'kb_id': kb_id}).model_dict()
            case 409:
                logger.info(resp.json())
                return ApiCommonResponseDTO(status=400, message="知识库名称重复!").model_dict()
            case _:
                return ApiCommonResponseDTO(status=500, message="fail").model_dict()
    except BaseException as e:
        logger.error(e)
        logger.error(traceback.format_exc())
        return ApiCommonResponseDTO(status=500, message="fail").model_dict()


def get_kb_list(token_checker: TokenChecker,
                page: int = Query(1, description="页数"),
                limit: int = Query(default=10, description="每页数据数")) -> ApiCommonResponseDTO:
    """获取 Dify 知识库列表  """
    try:
        if not (user_id := token_checker):
            return ApiCommonResponseDTO(message="用户未登录!").model_dict()
        if data := get_kb_list_from_db(user_id=user_id, page_no=page, page_size=limit):
            return ApiCommonResponseDTO(status=200, data=data).model_dict()
        else:
            return ApiCommonResponseDTO(status=200, message="no data").model_dict()
    except BaseException as e:
        logger.error(e)
        logger.error(traceback.format_exc())
        return ApiCommonResponseDTO(status=500, message="fail").model_dict()


def delete_kb(token_checker: TokenChecker, kb_id: str = Body(..., description="kb_id")):
    """删除dify 知识库"""
    try:
        if not (user_id := token_checker):
            return ApiCommonResponseDTO(message="用户未登录!").model_dict()
        delete_kb_from_db(kb_id=kb_id)
        return ApiCommonResponseDTO().model_dict()
    except BaseException as e:
        logger.error(e)
        logger.error(traceback.format_exc())
        return ApiCommonResponseDTO(status=500, message="fail").model_dict()


def upload_file_to_kb(token_checker: TokenChecker,kb_id: str = Body(..., description="kb_id"),
                      file: UploadFile = File(..., description="上传图片")):
    """上传知识库文件"""
    try:
        if not (user_id := token_checker):
            return ApiCommonResponseDTO(message="用户未登录!").model_dict()
        file_upload_url = urljoin(kb_file_base_url, f'{kb_id}/document/create-by-file')
        logger.info(file_upload_url)
        resp = requests.post(file_upload_url, headers={"Authorization": f"Bearer {setting.DIFY_KB_SECRET_KEY}"},
                             files={'data': (None, json.dumps({
                                 "indexing_technique": "high_quality",
                                 "process_rule": {"mode": "automatic"},
                             }), "application/json"), 'file': (file.filename, file.file.read(), file.content_type)})
        logger.info(resp.text)
        if resp.status_code == 200:
            res_data = resp.json()
            document_id = res_data.get('document').get('id')
            logger.info('document_id: {}'.format(document_id))
            return ApiCommonResponseDTO(status=200, message='success').model_dict()
        else:
            return ApiCommonResponseDTO(status=400, message=resp.json().get('message')).model_dict()
    except BaseException as e:
        logger.error(e)
        logger.error(traceback.format_exc())
        return ApiCommonResponseDTO(status=500, message="fail").model_dict()


def upload_text_to_kb(token_checker: TokenChecker,kb_id: str = Body(..., description="kb_id")):
    """上传知识库文本 """
    try:
        if not (user_id := token_checker):
            return ApiCommonResponseDTO(message="用户未登录!").model_dict()
        text_upload_url = urljoin(kb_file_base_url, f'/{kb_id}/document/create-by-file')
        resp = requests.post(text_upload_url, headers={"Content-Type": "application/json",
                                                       "Authorization": f"Bearer {setting.DIFY_KB_SECRET_KEY}"},
                             json={"name": "<string>",
                                   "text": "<string>",
                                   "indexing_technique": "high_quality",
                                   "doc_form": "text_model",
                                   "doc_language": "中文",
                                   "process_rule": {
                                       "mode": "automatic",
                                       "rules": {
                                           "pre_processing_rules": [
                                               {
                                                   "id": "remove_extra_spaces",
                                                   "enabled": True
                                               }
                                           ],
                                           "segmentation": {
                                               "separator": "<string>",
                                               "max_tokens": 123
                                           },
                                           "parent_mode": "full-doc",
                                           "subchunk_segmentation": {
                                               "separator": "<string>",
                                               "max_tokens": 123,
                                               "chunk_overlap": 123
                                           }
                                       }
                                   },
                                   "retrieval_model": {
                                       "search_method": "hybrid_search",
                                       "reranking_enable": True,
                                       "reranking_mode": {
                                           "reranking_provider_name": "<string>",
                                           "reranking_model_name": "<string>"
                                       },
                                       "top_k": 123,
                                       "score_threshold_enabled": True,
                                       "score_threshold": 123,
                                       "weights": 123
                                   },
                                   "embedding_model": "<string>",
                                   "embedding_model_provider": "<string>"})
        return ApiCommonResponseDTO(status=400, message="fail").model_dict()
    except BaseException as e:
        logger.error(e)
        logger.error(traceback.format_exc())
        return ApiCommonResponseDTO(status=500, message="fail").model_dict()


def get_file_progress(kb_id: str = Body(..., description="kb_id"), batch: str = Body(..., description="batch")):
    try:
        progress_url = urljoin(kb_file_base_url, f'{kb_id}/documents/{batch}/indexing-status')
        resp = requests.get(progress_url, headers={"Content-Type": "application/json",
                                                   "Authorization": f"Bearer {setting.DIFY_KB_SECRET_KEY}"})
        if resp.status_code == 200:
            return ApiCommonResponseDTO(status=200, message="success").model_dict()
        else:
            return ApiCommonResponseDTO(status=500, message="fail").model_dict()
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
