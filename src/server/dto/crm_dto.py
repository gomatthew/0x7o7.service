# -*- coding: utf-8 -*-
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


CompanyStatus = Literal[
    "researching", "qualified", "contacted", "responded", "call_booked", "won", "lost", "do_not_contact"
]
DealStage = Literal["lead", "qualified", "proposal", "negotiation", "won", "lost"]
DraftStatus = Literal["draft", "pending_approval", "approved", "rejected", "sent", "cancelled"]


class CRMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class CompanyCreate(CRMModel):
    name: str = Field(min_length=1, max_length=180, description="公司名称")
    website: str | None = Field(default=None, max_length=512, description="公司官网")
    country: str = Field(default="US", max_length=64, description="国家或地区")
    industry: str | None = Field(default=None, max_length=120, description="行业")
    employee_band: str | None = Field(default=None, max_length=32, description="员工规模")
    fit_score: int = Field(default=50, ge=0, le=100, description="CRM 契合度")
    status: CompanyStatus = Field(default="researching", description="公司状态")
    source_url: str | None = Field(default=None, max_length=1024, description="公开来源链接")
    buying_signal: str | None = Field(default=None, description="购买信号")
    value_hypothesis: str | None = Field(default=None, description="价值假设")
    notes: str | None = Field(default=None, description="备注")


class CompanyUpdate(CRMModel):
    name: str | None = Field(default=None, min_length=1, max_length=180, description="公司名称")
    website: str | None = Field(default=None, max_length=512, description="公司官网")
    country: str | None = Field(default=None, max_length=64, description="国家或地区")
    industry: str | None = Field(default=None, max_length=120, description="行业")
    employee_band: str | None = Field(default=None, max_length=32, description="员工规模")
    fit_score: int | None = Field(default=None, ge=0, le=100, description="CRM 契合度")
    status: CompanyStatus | None = Field(default=None, description="公司状态")
    source_url: str | None = Field(default=None, max_length=1024, description="公开来源链接")
    buying_signal: str | None = Field(default=None, description="购买信号")
    value_hypothesis: str | None = Field(default=None, description="价值假设")
    notes: str | None = Field(default=None, description="备注")


class ContactCreate(CRMModel):
    company_id: int = Field(..., description="CRM 公司 ID")
    full_name: str = Field(min_length=1, max_length=160, description="联系人姓名")
    role: str | None = Field(default=None, max_length=160, description="联系人职位")
    email: str | None = Field(default=None, max_length=254, description="公开邮箱")
    phone: str | None = Field(default=None, max_length=64, description="公开电话")
    linkedin_url: str | None = Field(default=None, max_length=1024, description="LinkedIn 链接")
    platform: str | None = Field(default=None, max_length=64, description="公开平台")
    platform_profile_url: str | None = Field(default=None, max_length=1024, description="平台资料链接")
    preferred_channel: str | None = Field(default=None, max_length=32, description="首选渠道")
    verification_status: str = Field(default="unverified", max_length=32, description="公开信息核验状态")
    source_url: str | None = Field(default=None, max_length=1024, description="联系人来源")
    notes: str | None = Field(default=None, description="备注")


class ContactUpdate(CRMModel):
    company_id: int | None = Field(default=None, description="CRM 公司 ID")
    full_name: str | None = Field(default=None, min_length=1, max_length=160, description="联系人姓名")
    role: str | None = Field(default=None, max_length=160, description="联系人职位")
    email: str | None = Field(default=None, max_length=254, description="公开邮箱")
    phone: str | None = Field(default=None, max_length=64, description="公开电话")
    linkedin_url: str | None = Field(default=None, max_length=1024, description="LinkedIn 链接")
    platform: str | None = Field(default=None, max_length=64, description="公开平台")
    platform_profile_url: str | None = Field(default=None, max_length=1024, description="平台资料链接")
    preferred_channel: str | None = Field(default=None, max_length=32, description="首选渠道")
    verification_status: str | None = Field(default=None, max_length=32, description="公开信息核验状态")
    source_url: str | None = Field(default=None, max_length=1024, description="联系人来源")
    notes: str | None = Field(default=None, description="备注")


class DealCreate(CRMModel):
    company_id: int = Field(..., description="CRM 公司 ID")
    contact_id: int | None = Field(default=None, description="CRM 联系人 ID")
    market_opportunity_id: str | None = Field(default=None, max_length=40, description="市场机会 ID")
    title: str = Field(min_length=1, max_length=240, description="Deal 名称")
    stage: DealStage = Field(default="lead", description="销售阶段")
    amount: Decimal = Field(default=Decimal("0"), ge=0, description="Deal 金额")
    currency: str = Field(default="USD", max_length=8, description="币种")
    probability: int = Field(default=10, ge=0, le=100, description="成交概率")
    expected_close_date: date | None = Field(default=None, description="预计成交日期")
    owner_name: str | None = Field(default=None, max_length=120, description="负责人")
    next_step: str | None = Field(default=None, description="下一步")
    notes: str | None = Field(default=None, description="备注")


class DealUpdate(CRMModel):
    contact_id: int | None = Field(default=None, description="CRM 联系人 ID")
    market_opportunity_id: str | None = Field(default=None, max_length=40, description="市场机会 ID")
    title: str | None = Field(default=None, min_length=1, max_length=240, description="Deal 名称")
    stage: DealStage | None = Field(default=None, description="销售阶段")
    amount: Decimal | None = Field(default=None, ge=0, description="Deal 金额")
    currency: str | None = Field(default=None, max_length=8, description="币种")
    probability: int | None = Field(default=None, ge=0, le=100, description="成交概率")
    expected_close_date: date | None = Field(default=None, description="预计成交日期")
    owner_name: str | None = Field(default=None, max_length=120, description="负责人")
    next_step: str | None = Field(default=None, description="下一步")
    notes: str | None = Field(default=None, description="备注")


class ActivityCreate(CRMModel):
    company_id: int | None = Field(default=None, description="CRM 公司 ID")
    contact_id: int | None = Field(default=None, description="CRM 联系人 ID")
    deal_id: int | None = Field(default=None, description="CRM Deal ID")
    activity_type: str = Field(max_length=32, description="活动类型")
    direction: Literal["outbound", "inbound", "internal"] = Field(default="internal", description="活动方向")
    summary: str = Field(min_length=1, description="活动摘要")
    outcome: str | None = Field(default=None, max_length=120, description="活动结果")
    happened_at: datetime | None = Field(default=None, description="活动发生时间")
    next_followup_at: datetime | None = Field(default=None, description="下次跟进时间")


class OutreachDraftCreate(CRMModel):
    contact_id: int = Field(..., description="CRM 联系人 ID")
    deal_id: int | None = Field(default=None, description="CRM Deal ID")
    channel: Literal["email", "linkedin", "platform", "contact_form"] = Field(..., description="外联渠道")
    subject: str | None = Field(default=None, max_length=300, description="草稿主题")
    body: str = Field(min_length=1, description="草稿正文")


class DraftDecision(CRMModel):
    note: str | None = Field(default=None, description="草稿决策说明")


class FollowupCreate(CRMModel):
    contact_id: int | None = Field(default=None, description="CRM 联系人 ID")
    deal_id: int | None = Field(default=None, description="CRM Deal ID")
    due_at: datetime = Field(..., description="到期时间")
    task_type: str = Field(default="follow_up", max_length=32, description="跟进类型")
    description: str = Field(min_length=1, description="跟进说明")


class FollowupUpdate(CRMModel):
    due_at: datetime | None = Field(default=None, description="到期时间")
    task_type: str | None = Field(default=None, max_length=32, description="跟进类型")
    description: str | None = Field(default=None, description="跟进说明")
    status: Literal["open", "done", "cancelled"] | None = Field(default=None, description="跟进状态")


ApprovalStatus = Literal[
    "draft",
    "pending_approval",
    "approved_not_executed",
    "executed_confirmed",
    "returned_for_revision",
    "rejected",
    "cancelled",
]


class ApprovalCreate(CRMModel):
    request_type: Literal["research_focus", "create_lead", "outreach", "platform_application", "demo", "follow_up"] = Field(..., description="审批类型")
    subject: str = Field(..., min_length=1, max_length=300, description="审批对象")
    subject_type: str | None = Field(default=None, max_length=32, description="审批对象类型")
    subject_id: str | None = Field(default=None, max_length=96, description="审批对象 ID")
    market_opportunity_id: str | None = Field(default=None, max_length=40, description="市场机会 ID")
    company_id: int | None = Field(default=None, description="CRM 公司 ID")
    contact_id: int | None = Field(default=None, description="CRM 联系人 ID")
    title: str = Field(..., min_length=1, max_length=300, description="审批标题")
    recommendation: str = Field(default="", description="审批建议")
    evidence: list[str] = Field(default_factory=list, description="证据引用")
    impact: str = Field(default="internal", max_length=32, description="影响范围")
    effort: str = Field(default="", description="投入说明")
    risk: str = Field(default="", description="风险说明")
    constraints: str = Field(default="", description="执行约束")
    action_pack: str = Field(default="", description="行动包")
    status: Literal["draft", "pending_approval"] = Field(default="pending_approval", description="初始审批状态")
    execution_owner: str | None = Field(default=None, max_length=32, description="期望执行方")


class ApprovalDecision(CRMModel):
    status: ApprovalStatus = Field(..., description="目标审批状态")
    note: str | None = Field(default=None, description="决策说明")
    output_note: str | None = Field(default=None, description="执行结果")
    output_refs: list[str] = Field(default_factory=list, description="执行结果引用")


class ExecutionTaskTransition(CRMModel):
    status: Literal["in_progress", "completed", "cancelled"] = Field(..., description="目标任务状态")
    output_note: str | None = Field(default=None, description="任务产出说明")
    output_refs: list[str] = Field(default_factory=list, description="任务产出引用")


class MarketSourceDto(CRMModel):
    source_id: str = Field(..., description="市场来源 ID")
    canonical_url: str = Field(..., description="原始来源链接")
    source_type: str = Field(..., description="来源类型")
    title: str | None = Field(default=None, description="来源标题")
    published_at: date | None = Field(default=None, description="来源发布日期")
    last_verified_at: datetime | None = Field(default=None, description="最后核验时间")
    access_status: str = Field(..., description="来源可访问状态")
    fact_summary: str | None = Field(default=None, description="来源事实摘要")


class MarketSignalDto(CRMModel):
    signal_id: str = Field(..., description="市场信号 ID")
    subject_name: str = Field(..., description="研究对象")
    subject_type: str = Field(..., description="研究对象类型")
    source_date: date | None = Field(default=None, description="来源日期")
    fact_description: str = Field(..., description="已验证事实")
    agent_inference: str | None = Field(default=None, description="Agent 推断")
    workflow_problem: str | None = Field(default=None, description="工作流问题")
    commercial_signal: str | None = Field(default=None, description="商业信号")
    evidence_level: str = Field(..., description="证据等级")
    research_status: str = Field(..., description="研究状态")
    last_verified_at: datetime | None = Field(default=None, description="最后核验时间")
    data_version: str = Field(..., description="数据版本")
    source: MarketSourceDto = Field(..., description="原始来源")
    link_type: str | None = Field(default=None, description="与机会的关联类型")


class MarketAgencyDto(CRMModel):
    candidate_id: str = Field(..., description="代理商候选 ID")
    company: str = Field(..., description="公司名称")
    country: str | None = Field(default=None, description="国家或地区")
    team_size: str | None = Field(default=None, description="团队规模")
    timezone_fit: str | None = Field(default=None, description="时区适配")
    service_match: str = Field(..., description="服务匹配")
    fact_description: str = Field(..., description="已验证事实")
    agent_inference: str | None = Field(default=None, description="Agent 推断")
    async_fit: str | None = Field(default=None, description="异步合作适配")
    research_risk: str | None = Field(default=None, description="研究风险")
    evidence_level: str = Field(..., description="证据等级")
    research_status: str = Field(..., description="研究状态")
    last_verified_at: datetime | None = Field(default=None, description="最后核验时间")
    data_version: str = Field(..., description="数据版本")
    source: MarketSourceDto = Field(..., description="原始来源")


class MarketOpportunityDto(CRMModel):
    opportunity_id: str = Field(..., description="市场机会 ID")
    title: str = Field(..., description="机会标题")
    target_buyer: str = Field(..., description="目标买方")
    buyer_role: str | None = Field(default=None, description="买方角色")
    workflow_problem: str = Field(..., description="工作流问题")
    commercial_signal: str | None = Field(default=None, description="商业信号")
    delivery_fit: str | None = Field(default=None, description="交付适配")
    evidence_level: str = Field(..., description="证据等级")
    research_status: str = Field(..., description="研究状态")
    blocking_questions: str | None = Field(default=None, description="阻塞问题")
    fact_description: str = Field(..., description="已验证事实")
    agent_inference: str | None = Field(default=None, description="Agent 推断")
    source_date: date | None = Field(default=None, description="来源日期")
    first_discovered_at: datetime = Field(..., description="首次发现时间")
    last_verified_at: datetime | None = Field(default=None, description="最后核验时间")
    data_version: str = Field(..., description="数据版本")
    no_auto_outreach: bool = Field(..., description="禁止自动外联")
    primary_source: MarketSourceDto | None = Field(default=None, description="主要原始来源")
    linked_signals: list[MarketSignalDto] = Field(default_factory=list, description="关联市场信号")
