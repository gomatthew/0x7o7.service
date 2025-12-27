import json
# import uuid
# import asyncio
import traceback
from urllib.parse import urljoin
# from typing import AsyncIterable, Optional

from fastapi import Body
# from langchain.chains import LLMChain
# from langchain_core.messages import convert_to_messages
from sse_starlette.sse import EventSourceResponse
from src.configs import logger, get_setting
from src.server.dto import ApiCommonResponseDTO
# from src.server.dto.response_dto import OpenAIOutputDTO
# from src.server.ai.callback_handler.agent_callback_handler import AgentExecutorAsyncIteratorCallbackHandler, AgentStatus
#
# from src.enum.emuns import MessageTypeEnum
# from src.server.ai.llm_utils import History, generate_llm_instance, create_models_chains, wrap_done, get_tool
# from src.server.ai.prompt.prompt import prompt_dict
# from src.server.db.repository import add_message_to_db, get_chat_history_detail_from_db, add_conversation_to_db
from src.server.utils import TokenChecker, http_stream_request, rag_retrieve

setting = get_setting()


# async def chat(
#         token_checker: TokenChecker,
#         query: str = Body(None, description="用户输入", examples=["恼羞成怒"]),
#         # metadata: dict = Body({}, description="附件，可能是图像或者其他功能", examples=[]),
#         conversation_id: Optional[str] = Body("", description="对话框ID"),
#         history_len: int = Body(10, description="从数据库中取历史消息的数量"),
#         stream: bool = Body(True, description="流式输出"),
#         chat_model_config: dict = Body({}, description="LLM 模型配置", examples=[]),
#         tool_config: dict = Body({}, description="工具配置", examples=[]),
#         max_tokens: int = Body(None, description="LLM最大token数配置", example=4096)):
#     """Agent 对话"""
#     message_id = uuid.uuid4().hex
#     if not token_checker:
#         return ApiCommonResponseDTO(message="用户未登录!").model_dict()
#     if not conversation_id: conversation_id = add_conversation_to_db(title=query, user_id=token_checker)
#
#     async def chat_iterator(conversation_id, message_id) -> AsyncIterable[OpenAIOutputDTO.model_dict]:
#         try:
#             if not conversation_id:
#                 conversation_id = uuid.uuid4().hex
#
#             add_message_to_db(conversation_id=conversation_id, message_id=message_id, query=query,
#                               user_id=token_checker)
#             callback = AgentExecutorAsyncIteratorCallbackHandler(message_id=message_id)
#             callbacks = [callback]
#             import os
#
#             llm_model = generate_llm_instance()
#             prompt = prompt_dict.get('llm_chat_default')
#
#             history = get_chat_history_detail_from_db(conversation_id=conversation_id)
#
#             all_tools = get_tool().values()
#             tools = [tool for tool in all_tools if tool.name in tool_config]
#             tools = [t.copy(update={"callbacks": callbacks}) for t in tools]
#             full_chain = create_models_chains(
#                 prompts=prompt,
#                 models=llm_model,
#                 conversation_id=conversation_id,
#                 tools=tools,
#                 callbacks=callbacks,
#                 history=history,
#                 history_len=history_len,
#                 # metadata=metadata,
#             )
#
#             _history = [History.from_data(h) for h in history]
#             chat_history = [h.to_msg_tuple() for h in _history]
#
#             history_message = convert_to_messages(chat_history)
#
#             task = asyncio.create_task(
#                 wrap_done(
#                     full_chain.ainvoke(
#                         {
#                             "input": query,
#                             "chat_history": history_message,
#                         }
#                     ),
#                     callback.done,
#                 )
#             )
#
#             last_tool = {}
#             async for chunk in callback.aiter():
#                 message_id = uuid.uuid4().hex
#                 data = json.loads(chunk)
#                 data["tool_calls"] = []
#                 data["message_type"] = MessageTypeEnum.TEXT
#
#                 if data["status"] == AgentStatus.tool_start:
#                     last_tool = {
#                         "index": 0,
#                         "id": data["run_id"],
#                         "type": "function",
#                         "function": {
#                             "name": data["tool"],
#                             "arguments": data["tool_input"],
#                         },
#                         "tool_output": None,
#                         "is_error": False,
#                     }
#                     data["tool_calls"].append(last_tool)
#                 if data["status"] in [AgentStatus.tool_end]:
#                     last_tool.update(
#                         tool_output=data["tool_output"],
#                         is_error=data.get("is_error", False),
#                     )
#                     data["tool_calls"] = [last_tool]
#                     last_tool = {}
#                     try:
#                         tool_output = json.loads(data["tool_output"])
#                         if message_type := tool_output.get("message_type"):
#                             data["message_type"] = message_type
#                     except:
#                         ...
#                 elif data["status"] == AgentStatus.agent_finish:
#                     try:
#                         tool_output = json.loads(data["text"])
#                         if message_type := tool_output.get("message_type"):
#                             data["message_type"] = message_type
#                     except:
#                         ...
#                 text_value = data.get("text", "")
#                 content = text_value if isinstance(text_value, str) else str(text_value)
#                 ret = OpenAIOutputDTO(
#                     llm_status=data["status"],
#                     content=content,
#                     tool=data["tool_calls"],
#                     status=data["status"],
#                     message_id=message_id,
#                 )
#                 yield ret.model_dump_json()
#
#             await task
#         except asyncio.exceptions.CancelledError:
#             logger.warning("streaming progress has been interrupted by user.")
#             return
#         except Exception as e:
#             logger.error(f"error in chat: {e}")
#             logger.error(traceback.format_exc())
#             yield {"data": json.dumps({"error": str(e)})}
#             return
#
#     if stream:
#         return EventSourceResponse(chat_iterator(conversation_id=conversation_id, message_id=message_id))
#     else:
#         ret = OpenAIOutputDTO(
#             message_id=f"chat{uuid.uuid4()}",
#             content="",
#             tool=[],
#             llm_status=AgentStatus.agent_finish,
#         )
#
#         async for chunk in chat_iterator(conversation_id=conversation_id, message_id=message_id):
#             data = json.loads(chunk)
#             if text := data["choices"][0]["delta"]["content"]:
#                 ret.content += text
#             if data["status"] == AgentStatus.tool_end:
#                 ret.tool_calls += data["choices"][0]["delta"]["tool_calls"]
#             ret.model = data["model"]
#             ret.created = data["created"]
#
#         return ret.model_dump()


async def chat_dify(token_checker: TokenChecker,
                    conversation_id: str = Body('', description="conversation_id"),
                    kb_id: str = Body(..., description="kb_id"),
                    query: str = Body(..., description="chat message input"),
                    lang: str = Body('en', description="en & zh")):
    try:
        if not token_checker:
            return ApiCommonResponseDTO(message="用户未登录!").model_dict()
        logger.info(f"🟢[START] chat_dify user_id:{token_checker}-query:{query}")
        chat_dify_url = urljoin(setting.DIFY_SERVER_URL, 'chat-messages')
        segments = rag_retrieve(kb_id, query)
        if records := segments.get('records'):
            _segments = [_.get('segment').get('content') for _ in records]
        else:
            _segments = []
        response = http_stream_request(url=chat_dify_url, http_method="POST",
                                       headers={"Content-Type": "application/json",
                                                "Authorization": f"Bearer {setting.DIFY_CHAT_SECRET_KEY}"},
                                       meta={'query': query, 'user_id': token_checker},
                                       data={
                                           'inputs': {'segments': json.dumps(_segments), 'lang': lang},
                                           'query': query,
                                           'conversation_id': conversation_id,
                                           'user': token_checker,
                                           'response_mode': 'streaming'})
        # requests.post(url=chat_dify_url, headers={"Content-Type": "application/json",
        #                                           "Authorization": f"Bearer {setting.DIFY_CHAT_SECRET_KEY}"},
        #               json={'query': query, 'segments': segments, 'lang': lang,'response_mode':'streaming'})
        logger.info(f"🟢[END] chat_dify user_id:{token_checker}-query:{query}")
        return EventSourceResponse(response)
    except BaseException as e:
        logger.error(f"error in chat: {e}")
        logger.error(traceback.format_exc())

