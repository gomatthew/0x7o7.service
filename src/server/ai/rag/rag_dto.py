# -*- coding: utf-8 -*-
from typing import Any

from pydantic import BaseModel, Field


class LoadedDocumentDto(BaseModel):
    content: str = Field(..., description="文档内容")
    metadata: dict[str, Any] = Field(default={}, description="文档元数据")


class DocumentChunkDto(BaseModel):
    content: str = Field(..., description="切片内容")
    metadata: dict[str, Any] = Field(default={}, description="切片元数据")


class RetrievedDocumentDto(BaseModel):
    content: str = Field(..., description="召回内容")
    score: float = Field(0, description="相关度分数")
    metadata: dict[str, Any] = Field(default={}, description="召回元数据")
