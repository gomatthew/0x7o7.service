# -*- coding: utf-8 -*-
from typing import Any
from pydantic import BaseModel, Field


class BaseResponseDTO(BaseModel):
    status: int = Field(200, description="api 状态码")
    message: str = Field("success", description="返回信息")

    class Config:
        json_schema_extra = {
            "example": {
                "status": 200,
                "message": "success",
            }
        }


class ApiCommonResponseDTO(BaseResponseDTO):
    status: int = 200
    message: str = "success"
    data: Any = None

    def model_dict(self):
        return {'status': self.status, 'message': self.message, 'data': self.data}


class OpenAIOutputDTO(BaseResponseDTO):
    ...
