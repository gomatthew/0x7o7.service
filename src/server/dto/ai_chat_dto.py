# -*- coding: utf-8 -*-
from typing import Optional

from pydantic import BaseModel, Field


class ChatMessageDto(BaseModel):
    role: str = Field(..., description="消息角色")
    content: str = Field(..., description="消息内容")


class ChatCompletionRequestDto(BaseModel):
    user_id: Optional[int] = Field(None, description="用户ID")
    knowledge_base_id: Optional[str] = Field(None, description="知识库ID")
    messages: list[ChatMessageDto] = Field(default=[], description="对话消息")
    business_type: str = Field("default", description="业务类型")
    is_stream: bool = Field(False, description="是否流式输出")
    top_k: Optional[int] = Field(None, description="最终召回数量")
    fetch_k: Optional[int] = Field(None, description="初始召回数量")
    score_threshold: Optional[float] = Field(None, description="相似度阈值")
    temperature: Optional[float] = Field(None, description="温度")
    max_tokens: Optional[int] = Field(None, description="最大token数")
    reranker: bool = Field(False, description="是否启用重排序")


class CreateKnowledgeBaseDto(BaseModel):
    user_id: Optional[int] = Field(None, description="用户ID")
    knowledge_base_id: Optional[str] = Field(None, description="知识库ID")
    name: str = Field(..., description="知识库名称")
    description: Optional[str] = Field(None, description="知识库描述")
    business_type: str = Field("default", description="业务类型")
    embedding_model: Optional[str] = Field(None, description="向量模型")
    chunk_size: Optional[int] = Field(None, description="切片长度")
    chunk_overlap: Optional[int] = Field(None, description="切片重叠长度")
