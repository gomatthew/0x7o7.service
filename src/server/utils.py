# -*- coding: utf-8 -*-
import json
import httpx
import requests
import traceback

from typing import Annotated, Any, Optional
from urllib.parse import urljoin
from fastapi import Depends, Request
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyCookie
from src.configs import logger, get_setting
from src.server.libs import token_handler, dt
from src.server.libs.redis_lib import async_rate_limit
from src.server.db.repository import add_message_to_db, add_conversation_to_db, get_user_by_id

setting = get_setting()
cookie_scheme = APIKeyCookie(name="access_token", auto_error=False)


def get_request_token(request: Request, token: Optional[str] = Depends(cookie_scheme)):
    if token:
        return token
    authorization = request.headers.get("authorization")
    if authorization and authorization.lower().startswith("bearer "):
        return authorization.split(" ", 1)[1].strip()
    return None


def is_admin_user(user_id: str | int | None):
    if not user_id:
        return False
    user_info = get_user_by_id(str(user_id))
    return bool(user_info and user_info.role == setting.ADMIN_ROLE)


def token_identify(token: Optional[str] = Depends(get_request_token)):
    # auth = request.cookies.get('access_token')
    # if checkout := token_handler.verify_token(auth):
    #     return checkout.get('data').get('id')
    # else:
    #     return None
    # return '1'
    if checkout := token_handler.verify_token(token):
        return str(checkout.get("data", {}).get("id"))
    return None


TokenChecker = Annotated[Any, Depends(token_identify)]


class RateLimitException(Exception):
    def __init__(self, message: str, status: int = 429):
        self.message = message
        self.status = status


def get_client_ip(request: Request):
    # Nginx overwrites X-Real-IP with the trusted Cloudflare/client address.
    # Do not prefer a caller-supplied X-Forwarded-For value: doing so lets a
    # public client rotate the rate-limit key by spoofing that header.
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[-1].strip()
    if request.client:
        return request.client.host
    return "unknown"


async def ai_rate_limit(request: Request, token: Optional[str] = Depends(cookie_scheme)):
    token = get_request_token(request, token)
    client_ip = get_client_ip(request)
    user_id = None
    if checkout := token_handler.verify_token(token):
        user_id = str(checkout.get("data", {}).get("id"))
    if user_id:
        if is_admin_user(user_id):
            return user_id
        ip_limited, _ = await async_rate_limit(f"ai_ip:{client_ip}", setting.AI_IP_LIMIT, setting.AI_IP_TTL)
        if ip_limited:
            raise RateLimitException("ai.ipLimit")
        user_limited, _ = await async_rate_limit(f"ai_user:{user_id}", setting.AI_USER_LIMIT, setting.AI_USER_TTL)
        if user_limited:
            raise RateLimitException("ai.userLimit")
        return user_id
    ip_limited, _ = await async_rate_limit(f"ai_ip:{client_ip}", setting.AI_IP_LIMIT, setting.AI_IP_TTL)
    if ip_limited:
        raise RateLimitException("ai.ipLimit")
    guest_limited, _ = await async_rate_limit(f"ai_guest:{client_ip}", setting.AI_GUEST_LIMIT, setting.AI_GUEST_TTL)
    if guest_limited:
        raise RateLimitException("ai.guestLimit")
    return None


async def rate_limit_exception_handler(request: Request, exc: RateLimitException):
    return JSONResponse(status_code=200, content={"status": exc.status, "message": exc.message, "data": {}})


def http_stream_request(url: str, http_method: str, headers: dict = dict(), data: Any = dict(), meta: dict = dict()):
    try:
        with httpx.stream(method=http_method, url=url, headers=headers, json=data, timeout=None) as response:
            for line in response.iter_lines():
                line = line.lstrip('data: ')
                if line and 'ping' not in line:
                    json_data = json.loads(line)
                    match json_data.get('event'):
                        # case "workflow_started":
                        #     query = json_data.get('inputs').get('sys.query')
                        case "node_finished":
                            if json_data.get('data').get('process_data').get('model_name') is not None:
                                model_name = json_data.get('data').get('process_data').get('model_name')
                        case 'workflow_finished':
                            add_conversation_to_db(conversation_id=json_data['conversation_id'],
                                                   title=meta.get('query'),
                                                   create_time=dt.ts2dt(json_data['data'].get('created_at')),
                                                   finish_time=dt.ts2dt(json_data['data'].get('finished_at')),
                                                   llm_model=model_name, user_id=meta.get('user_id'))
                            add_message_to_db(conversation_id=json_data['conversation_id'],
                                              create_time=dt.ts2dt(json_data['data'].get('created_at')),
                                              finish_time=dt.ts2dt(json_data['data'].get('finished_at')),
                                              message_id=json_data.get('message_id'), query=meta.get('query'),
                                              ai_response=json_data.get('data').get('outputs').get('answer'),
                                              llm_model=model_name, user_id=meta.get('user_id'))
                        case _:
                            pass
                    yield line.strip()
    except BaseException as e:
        logger.error(e)
        logger.error(traceback.format_exc())


def rag_retrieve(kb_id: str, query: str):
    try:
        logger.info("🟢 [START] hit the kb.")
        kb_file_base_url = setting.DIFY_SERVER_URL
        retrieve_url = urljoin(kb_file_base_url, f"datasets/{kb_id}/retrieve")
        payload = {
            "query": query,
            "retrieval_model": {
                "search_method": "hybrid_search",
                "reranking_enable": True,
                # "reranking_mode": {
                #     "reranking_provider_name": "<string>",
                #     "reranking_model_name": "<string>"
                # },
                "top_k": 1,
                "score_threshold_enabled": True,
                # "score_threshold": 123,
                # "weights": 123,
                # "metadata_filtering_conditions": {
                #     "logical_operator": "and",
                #     "conditions": [
                #         {
                #             "name": "<string>",
                #             "comparison_operator": "<string>",
                #             "value": "<string>"
                #         }
                #     ]
                # }
            }
        }
        resp = requests.post(retrieve_url, headers={"Content-Type": "application/json",
                                                    "Authorization": f"Bearer {setting.DIFY_KB_SECRET_KEY}"},
                             json=payload)
        logger.info('🟢[END] hit the kb finish.')
        return resp.json()
    except BaseException as e:
        logger.error(e)
        logger.error(traceback.format_exc())
