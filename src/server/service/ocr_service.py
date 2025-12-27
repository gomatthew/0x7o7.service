# encoding:utf-8
import traceback

import requests
import base64
from urllib.parse import urljoin
from sse_starlette.sse import EventSourceResponse
from fastapi import UploadFile, File, Body
from src.configs import get_setting, logger
from src.server.dto import ApiCommonResponseDTO
from src.server.utils import TokenChecker, http_stream_request

setting = get_setting()
OCR_BASE_URL = setting.OCR_BASE_URL

"""
{
    "words_result": [
        {
            "words": "http://www.baidu.com"
        },
        {
            "words": "北京市海淀区上地十街10号100085"
        },
        {
            "words": "No. 10 Shangdi 10th Street, Haidian District, Beijing 100085"
        },
        {
            "words": "Tel:+8610-5292-2888 Fax:+8610-5992-0900"
        }
    ],
    "words_result_num": 4,
    "log_id": "2004833624655595471"
}"""


def ocr_auth(client_id, client_secret):
    params = {"client_id": client_id, "client_secret": client_secret, "grant_type": "client_credentials"}
    # payload = json.dumps("", ensure_ascii=False)
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }

    response = requests.post(setting.OCR_AUTH_URL, headers=headers, params=params)

    response.encoding = "utf-8"
    if response.status_code == 200:
        return response.json().get('access_token')
    return None


async def ocr_chat(token_checker: TokenChecker, query: str = Body(default=None, description="用户输入"),
                   conversation_id: str = Body(default=None, description="conversation_id"),
                   lang: str = Body(default='en', description="zh & en"),
                   file: UploadFile = File(None, description="上传的图片")):
    if not (user_id := token_checker):
        return ApiCommonResponseDTO(message="请重新登录!", data={}, status=401).model_dict()
    try:
        logger.info(f"🟢 OCR服务:[START] ==> user_id: {user_id}")
        if not conversation_id:
            # 首次上传图片,使用ocr
            query = '以下是OCR 文本:\r\n'
            if not (access_token := ocr_auth(client_id=setting.OCR_API_KEY, client_secret=setting.OCR_API_SECRET)):
                logger.info(f"🔴 OCR服务:[END] ==> OCR校验失败!")
                return ApiCommonResponseDTO(status=401, message='网络延迟,等会儿再发送').model_dict()
            img = base64.b64encode(file.file.read())
            params = {"access_token": access_token}
            payload = {"image": img}
            headers = {'content-type': 'application/x-www-form-urlencoded'}
            ocr_request_resp = requests.post(setting.OCR_BASE_URL, headers=headers, params=params, data=payload)
            if ocr_request_resp.status_code == 200:
                raw_ocr_text = '\n'.join([words.get('words') for words in ocr_request_resp.json().get('words_result')])
                query = ''.join([query, raw_ocr_text])
            else:
                return ApiCommonResponseDTO(status=401, message='OCR繁忙').model_dict()
        chat_dify_url = urljoin(setting.DIFY_SERVER_URL, 'chat-messages')
        response = http_stream_request(url=chat_dify_url, http_method="POST",
                                       headers={"Content-Type": "application/json",
                                                "Authorization": f"Bearer {setting.DIFY_OCR_SECRET_KEY}"},
                                       # meta={'query': query if conversation_id else ocr_data, 'user_id': token_checker},
                                       data={
                                           'inputs': {'lang': lang},
                                           'query': query,
                                           'conversation_id': conversation_id,
                                           'user': token_checker,
                                           'response_mode': 'streaming'})
        logger.info(f"🟢 OCR服务:[END] ==> user_id: {user_id} 成功!")
        return EventSourceResponse(response)
    except BaseException as e:
        logger.info(f"🔴 OCR服务:[ERROR] ==> user_id: {user_id}")
        logger.error(e)
        logger.error(traceback.format_exc())
        return ApiCommonResponseDTO(status=500, message='error').model_dict()

# if __name__ == '__main__':
#     ocr_auth(setting.OCR_API_KEY, setting.OCR_API_SECRET)
