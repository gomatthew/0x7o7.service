# -*- coding: utf-8 -*-
import json
from typing import Any
from pydantic import BaseModel, Field


class BaseResponseDTO(BaseModel):
    status: int = 200
    message: str = 'success'

    class Config:
        json_schema_extra = {
            "example": {
                "status": 200,
                "message": "success",
            }
        }


class ApiCommonResponseDTO(BaseResponseDTO):
    data: Any = Field({}, description="返回数据")

    def model_dict(self):
        return {'status': self.status, 'message': self.message, 'data': self.data}


class OpenAIOutputDTO(BaseResponseDTO):
    content: str = Field('', description="AI output")
    message_id: str = Field('', description='信息id')
    tool: Any = Field('', description="调用工具")
    llm_status: str | int = Field('', description='Chain 过程状态')

    def model_dict(self):
        return {
            'status': self.status, 'content': self.content, 'llm_status': self.llm_status, 'tool_calls': self.tool}

    def model_dump_json(self):
        return json.dumps(self.model_dict(), ensure_ascii=False)
