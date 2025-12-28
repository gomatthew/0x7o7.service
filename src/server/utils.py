# -*- coding: utf-8 -*-
import json
import httpx
import requests
import traceback

from typing import Annotated, Any, Optional
from urllib.parse import urljoin
from fastapi import Depends
from fastapi.security import APIKeyCookie
from src.configs import logger, get_setting
from src.server.libs import token_handler, dt
from src.server.db.repository import add_message_to_db, add_conversation_to_db

setting = get_setting()
cookie_scheme = APIKeyCookie(name="access_token", auto_error=False)


def token_identify(token: Optional[str] = Depends(cookie_scheme)):
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
