import asyncio
import json
import traceback
import uuid
from typing import AsyncIterable, List

from fastapi import Body
from langchain.chains import LLMChain
from langchain_core.messages import AIMessage, HumanMessage, convert_to_messages
from sse_starlette.sse import EventSourceResponse
from src.configs import logger
from src.server.ai.agent.agents_registry import agents_registry
from src.server.dto.response_dto import OpenAIOutputDTO
from src.server.ai.callback_handler.agent_callback_handler import AgentExecutorAsyncIteratorCallbackHandler, AgentStatus

from src.enum.emuns import MessageTypeEnum
from src.server.ai.llm_utils import History, generate_llm_instance, create_models_chains, wrap_done, get_tool
from src.server.ai.prompt.prompt import prompt_dict


async def chat(
        query: str = Body(..., description="用户输入", examples=["恼羞成怒"]),
        # metadata: dict = Body({}, description="附件，可能是图像或者其他功能", examples=[]),
        conversation_id: str = Body("", description="对话框ID"),
        message_id: str = Body(None, description="数据库消息ID"),
        history_len: int = Body(-1, description="从数据库中取历史消息的数量"),
        history: List[History] = Body(
            [],
            description="历史对话，设为一个整数可以从数据库中读取历史消息",
            examples=[
                [
                    {"role": "user", "content": "我们来玩成语接龙，我先来，生龙活虎"},
                    {"role": "assistant", "content": "虎头虎脑"},
                ]
            ],
        ),
        stream: bool = Body(True, description="流式输出"),
        chat_model_config: dict = Body({}, description="LLM 模型配置", examples=[]),
        tool_config: dict = Body({}, description="工具配置", examples=[]),
        max_tokens: int = Body(None, description="LLM最大token数配置", example=4096),
):
    """Agent 对话"""

    async def chat_iterator() -> AsyncIterable[OpenAIOutputDTO]:
        try:
            callback = AgentExecutorAsyncIteratorCallbackHandler()
            callbacks = [callback]

            # Enable langchain-chatchat to support langfuse
            import os

            langfuse_secret_key = os.environ.get("LANGFUSE_SECRET_KEY")
            langfuse_public_key = os.environ.get("LANGFUSE_PUBLIC_KEY")
            langfuse_host = os.environ.get("LANGFUSE_HOST")
            # if langfuse_secret_key and langfuse_public_key and langfuse_host:
            #     from langfuse import Langfuse
            #     from langfuse.callback import CallbackHandler
            #
            #     langfuse_handler = CallbackHandler()
            #     callbacks.append(langfuse_handler)

            llm_model = generate_llm_instance()
            prompt = prompt_dict.get('llm_chat_default')

            all_tools = get_tool().values()
            tools = [tool for tool in all_tools if tool.name in tool_config]
            tools = [t.copy(update={"callbacks": callbacks}) for t in tools]
            full_chain = create_models_chains(
                prompts=prompt,
                models=llm_model,
                conversation_id=conversation_id,
                tools=tools,
                callbacks=callbacks,
                history=history,
                history_len=history_len,
                # metadata=metadata,
            )

            _history = [History.from_data(h) for h in history]
            chat_history = [h.to_msg_tuple() for h in _history]

            history_message = convert_to_messages(chat_history)

            task = asyncio.create_task(
                wrap_done(
                    full_chain.ainvoke(
                        {
                            "input": query,
                            "chat_history": history_message,
                        }
                    ),
                    callback.done,
                )
            )

            last_tool = {}
            async for chunk in callback.aiter():
                data = json.loads(chunk)
                data["tool_calls"] = []
                data["message_type"] = MessageTypeEnum.TEXT

                if data["status"] == AgentStatus.tool_start:
                    last_tool = {
                        "index": 0,
                        "id": data["run_id"],
                        "type": "function",
                        "function": {
                            "name": data["tool"],
                            "arguments": data["tool_input"],
                        },
                        "tool_output": None,
                        "is_error": False,
                    }
                    data["tool_calls"].append(last_tool)
                if data["status"] in [AgentStatus.tool_end]:
                    last_tool.update(
                        tool_output=data["tool_output"],
                        is_error=data.get("is_error", False),
                    )
                    data["tool_calls"] = [last_tool]
                    last_tool = {}
                    try:
                        tool_output = json.loads(data["tool_output"])
                        if message_type := tool_output.get("message_type"):
                            data["message_type"] = message_type
                    except:
                        ...
                elif data["status"] == AgentStatus.agent_finish:
                    try:
                        tool_output = json.loads(data["text"])
                        if message_type := tool_output.get("message_type"):
                            data["message_type"] = message_type
                    except:
                        ...
                text_value = data.get("text", "")
                content = text_value if isinstance(text_value, str) else str(text_value)
                ret = OpenAIOutputDTO(
                    llm_status=data["status"],
                    content=content,
                    tool=data["tool_calls"],
                    status=data["status"],
                    message_id=message_id,
                )
                yield ret.model_dump_json()

            await task
        except asyncio.exceptions.CancelledError:
            logger.warning("streaming progress has been interrupted by user.")
            return
        except Exception as e:
            logger.error(f"error in chat: {e}")
            logger.error(traceback.format_exc())
            yield {"data": json.dumps({"error": str(e)})}
            return

    if stream:
        return EventSourceResponse(chat_iterator())
    else:
        ret = OpenAIOutputDTO(
            message_id=f"chat{uuid.uuid4()}",
            content="",
            tool=[],
            llm_status=AgentStatus.agent_finish,
        )

        async for chunk in chat_iterator():
            data = json.loads(chunk)
            if text := data["choices"][0]["delta"]["content"]:
                ret.content += text
            if data["status"] == AgentStatus.tool_end:
                ret.tool_calls += data["choices"][0]["delta"]["tool_calls"]
            ret.model = data["model"]
            ret.created = data["created"]

        return ret.model_dump()
