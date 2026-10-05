# -*- coding: utf-8 -*-
from typing import Literal, Optional

from pydantic import BaseModel, Field


class DocumentEvidenceDto(BaseModel):
    source_id: str = Field(..., description="检索返回的来源 ID")
    quote: str = Field(..., min_length=1, description="来源中的原文证据")


class DocumentFieldDto(BaseModel):
    id: Literal["project_client", "business_outcome", "primary_users", "required_outputs",
                "acceptance_criteria", "owner", "timeline", "data_privacy", "target_handoff"] = Field(..., description="交付字段 ID")
    value: Optional[str | list[str]] = Field(None, description="文档中明确提供的值")
    evidence: list[DocumentEvidenceDto] = Field(default_factory=list, description="字段原文证据")
    needs_review: bool = Field(False, description="是否存在冲突或需要人工确认")
    review_reason: Optional[str] = Field(None, description="人工确认原因")


class DocumentExtractionDto(BaseModel):
    document_type: Literal["client_brief", "other"] = Field(..., description="是否为客户需求或交付文档")
    fields: list[DocumentFieldDto] = Field(..., description="提取的交付字段")
