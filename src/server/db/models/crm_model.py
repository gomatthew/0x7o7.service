# -*- coding: utf-8 -*-
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import JSON, CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.server.db.crm_base import CRMBase


class CRMTimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.current_timestamp())
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.current_timestamp(), onupdate=func.current_timestamp())


class CRMOwnedMixin:
    owner_user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)


class CRMCompanyModel(CRMBase, CRMTimestampMixin, CRMOwnedMixin):
    __tablename__ = "crm_companies"
    __table_args__ = (
        UniqueConstraint("owner_user_id", "website", name="uq_crm_company_owner_website"),
        CheckConstraint("fit_score >= 0 AND fit_score <= 100", name="ck_crm_company_fit_score"),
        Index("ix_crm_company_owner_status", "owner_user_id", "status"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(180), nullable=False, comment="公司名称")
    website: Mapped[str | None] = mapped_column(String(512), nullable=True, comment="公司官网")
    country: Mapped[str] = mapped_column(String(64), nullable=False, default="US", comment="国家或地区")
    industry: Mapped[str | None] = mapped_column(String(120), nullable=True, comment="行业")
    employee_band: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="员工规模")
    fit_score: Mapped[int] = mapped_column(Integer, nullable=False, default=50, comment="CRM 契合度")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="researching", comment="公司状态")
    source_url: Mapped[str | None] = mapped_column(String(1024), nullable=True, comment="公开来源链接")
    buying_signal: Mapped[str | None] = mapped_column(Text, nullable=True, comment="购买信号")
    value_hypothesis: Mapped[str | None] = mapped_column(Text, nullable=True, comment="价值假设")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True, comment="备注")
    contacts: Mapped[list["CRMContactModel"]] = relationship(back_populates="company", cascade="all, delete-orphan")
    deals: Mapped[list["CRMDealModel"]] = relationship(back_populates="company", cascade="all, delete-orphan")


class CRMContactModel(CRMBase, CRMTimestampMixin, CRMOwnedMixin):
    __tablename__ = "crm_contacts"
    __table_args__ = (
        UniqueConstraint("owner_user_id", "company_id", "email", name="uq_crm_contact_company_email"),
        Index("ix_crm_contact_owner_company", "owner_user_id", "company_id"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("crm_companies.id", ondelete="CASCADE"), nullable=False)
    full_name: Mapped[str] = mapped_column(String(160), nullable=False, comment="联系人姓名")
    role: Mapped[str | None] = mapped_column(String(160), nullable=True, comment="联系人职位")
    email: Mapped[str | None] = mapped_column(String(254), nullable=True, comment="公开邮箱")
    phone: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="公开电话")
    linkedin_url: Mapped[str | None] = mapped_column(String(1024), nullable=True, comment="LinkedIn 链接")
    platform: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="公开平台")
    platform_profile_url: Mapped[str | None] = mapped_column(String(1024), nullable=True, comment="平台资料链接")
    preferred_channel: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="首选渠道")
    verification_status: Mapped[str] = mapped_column(String(32), nullable=False, default="unverified", comment="公开信息核验状态")
    source_url: Mapped[str | None] = mapped_column(String(1024), nullable=True, comment="联系人来源")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True, comment="备注")
    company: Mapped[CRMCompanyModel] = relationship(back_populates="contacts")
    deals: Mapped[list["CRMDealModel"]] = relationship(back_populates="contact")
    drafts: Mapped[list["CRMOutreachDraftModel"]] = relationship(back_populates="contact", cascade="all, delete-orphan")


class CRMDealModel(CRMBase, CRMTimestampMixin, CRMOwnedMixin):
    __tablename__ = "crm_deals"
    __table_args__ = (
        CheckConstraint("probability >= 0 AND probability <= 100", name="ck_crm_deal_probability"),
        Index("ix_crm_deal_owner_stage", "owner_user_id", "stage"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("crm_companies.id", ondelete="CASCADE"), nullable=False)
    contact_id: Mapped[int | None] = mapped_column(ForeignKey("crm_contacts.id", ondelete="SET NULL"), nullable=True)
    market_opportunity_id: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True, comment="市场机会引用")
    title: Mapped[str] = mapped_column(String(240), nullable=False, comment="Deal 名称")
    stage: Mapped[str] = mapped_column(String(32), nullable=False, default="lead", comment="销售阶段")
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0, comment="金额")
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="USD", comment="币种")
    probability: Mapped[int] = mapped_column(Integer, nullable=False, default=10, comment="成交概率")
    expected_close_date: Mapped[date | None] = mapped_column(Date, nullable=True, comment="预计成交日期")
    owner_name: Mapped[str | None] = mapped_column(String(120), nullable=True, comment="负责人")
    next_step: Mapped[str | None] = mapped_column(Text, nullable=True, comment="下一步")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True, comment="备注")
    company: Mapped[CRMCompanyModel] = relationship(back_populates="deals")
    contact: Mapped[CRMContactModel | None] = relationship(back_populates="deals")
    activities: Mapped[list["CRMActivityModel"]] = relationship(back_populates="deal", cascade="all, delete-orphan")
    tasks: Mapped[list["CRMFollowupTaskModel"]] = relationship(back_populates="deal", cascade="all, delete-orphan")


class CRMActivityModel(CRMBase, CRMOwnedMixin):
    __tablename__ = "crm_activities"
    __table_args__ = (Index("ix_crm_activity_owner_happened", "owner_user_id", "happened_at"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_id: Mapped[int | None] = mapped_column(ForeignKey("crm_companies.id", ondelete="SET NULL"), nullable=True)
    contact_id: Mapped[int | None] = mapped_column(ForeignKey("crm_contacts.id", ondelete="SET NULL"), nullable=True)
    deal_id: Mapped[int | None] = mapped_column(ForeignKey("crm_deals.id", ondelete="CASCADE"), nullable=True)
    activity_type: Mapped[str] = mapped_column(String(32), nullable=False, comment="活动类型")
    direction: Mapped[str] = mapped_column(String(16), nullable=False, default="internal", comment="活动方向")
    summary: Mapped[str] = mapped_column(Text, nullable=False, comment="活动摘要")
    outcome: Mapped[str | None] = mapped_column(String(120), nullable=True, comment="活动结果")
    happened_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.current_timestamp())
    next_followup_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="下次跟进时间")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.current_timestamp())
    deal: Mapped[CRMDealModel | None] = relationship(back_populates="activities")


class CRMOutreachDraftModel(CRMBase, CRMTimestampMixin, CRMOwnedMixin):
    __tablename__ = "crm_outreach_drafts"
    __table_args__ = (Index("ix_crm_draft_owner_status", "owner_user_id", "status"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    contact_id: Mapped[int] = mapped_column(ForeignKey("crm_contacts.id", ondelete="CASCADE"), nullable=False)
    deal_id: Mapped[int | None] = mapped_column(ForeignKey("crm_deals.id", ondelete="SET NULL"), nullable=True)
    channel: Mapped[str] = mapped_column(String(32), nullable=False, comment="外联渠道")
    subject: Mapped[str | None] = mapped_column(String(300), nullable=True, comment="草稿主题")
    body: Mapped[str] = mapped_column(Text, nullable=False, comment="草稿正文")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft", comment="草稿状态")
    approval_note: Mapped[str | None] = mapped_column(Text, nullable=True, comment="审批说明")
    approved_by: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="审批人")
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="审批时间")
    sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="人工发送时间")
    external_message_id: Mapped[str | None] = mapped_column(String(256), nullable=True, comment="人工回填的外部消息 ID")
    contact: Mapped[CRMContactModel] = relationship(back_populates="drafts")


class CRMInteractionModel(CRMBase, CRMOwnedMixin):
    __tablename__ = "crm_interactions"
    __table_args__ = (Index("ix_crm_interaction_contact_time", "contact_id", "occurred_at"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    contact_id: Mapped[int] = mapped_column(ForeignKey("crm_contacts.id", ondelete="CASCADE"), nullable=False)
    draft_id: Mapped[int | None] = mapped_column(ForeignKey("crm_outreach_drafts.id", ondelete="SET NULL"), nullable=True)
    channel: Mapped[str] = mapped_column(String(32), nullable=False, comment="互动渠道")
    direction: Mapped[str] = mapped_column(String(32), nullable=False, comment="互动方向")
    occurred_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, comment="互动发生时间")
    summary: Mapped[str] = mapped_column(Text, nullable=False, comment="互动摘要")
    outcome: Mapped[str | None] = mapped_column(Text, nullable=True, comment="互动结果")
    next_followup_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="下次跟进时间")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.current_timestamp())


class CRMFollowupTaskModel(CRMBase, CRMTimestampMixin, CRMOwnedMixin):
    __tablename__ = "crm_followup_tasks"
    __table_args__ = (Index("ix_crm_task_owner_due", "owner_user_id", "status", "due_at"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    contact_id: Mapped[int | None] = mapped_column(ForeignKey("crm_contacts.id", ondelete="SET NULL"), nullable=True)
    deal_id: Mapped[int | None] = mapped_column(ForeignKey("crm_deals.id", ondelete="CASCADE"), nullable=True)
    due_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, comment="到期时间")
    task_type: Mapped[str] = mapped_column(String(32), nullable=False, default="follow_up", comment="任务类型")
    description: Mapped[str] = mapped_column(Text, nullable=False, comment="任务说明")
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="open", comment="任务状态")
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="完成时间")
    deal: Mapped[CRMDealModel | None] = relationship(back_populates="tasks")


class CRMApprovalRequestModel(CRMBase):
    __tablename__ = "crm_approval_requests"
    __table_args__ = (Index("ix_crm_approval_owner_status", "owner_user_id", "status", "requested_at"),)
    id: Mapped[str] = mapped_column(String(48), primary_key=True)
    owner_user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    request_type: Mapped[str] = mapped_column(String(32), nullable=False, comment="审批类型")
    subject: Mapped[str] = mapped_column(String(300), nullable=False, comment="审批对象")
    subject_type: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="对象类型")
    subject_id: Mapped[str | None] = mapped_column(String(96), nullable=True, comment="对象 ID")
    market_opportunity_id: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True, comment="市场机会引用")
    company_id: Mapped[int | None] = mapped_column(ForeignKey("crm_companies.id", ondelete="SET NULL"), nullable=True)
    contact_id: Mapped[int | None] = mapped_column(ForeignKey("crm_contacts.id", ondelete="SET NULL"), nullable=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False, comment="审批标题")
    recommendation: Mapped[str] = mapped_column(Text, nullable=False, comment="建议")
    evidence_json: Mapped[list[Any]] = mapped_column(JSON, nullable=False, default=list, comment="证据引用")
    impact: Mapped[str] = mapped_column(String(32), nullable=False, comment="影响范围")
    effort: Mapped[str] = mapped_column(Text, nullable=False, comment="投入说明")
    risk: Mapped[str] = mapped_column(Text, nullable=False, comment="风险说明")
    constraints_text: Mapped[str] = mapped_column(Text, nullable=False, comment="约束")
    action_pack: Mapped[str] = mapped_column(Text, nullable=False, comment="行动包")
    status: Mapped[str] = mapped_column(String(32), nullable=False, comment="审批状态")
    execution_owner: Mapped[str] = mapped_column(String(32), nullable=False, default="user", comment="执行方")
    execution_kind: Mapped[str] = mapped_column(String(32), nullable=False, default="manual_external", comment="执行类型")
    requested_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.current_timestamp())
    decision_note: Mapped[str | None] = mapped_column(Text, nullable=True, comment="决策说明")
    decided_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="决策时间")
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="开始时间")
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="完成时间")
    output_refs: Mapped[list[Any] | None] = mapped_column(JSON, nullable=True, comment="产出引用")
    output_note: Mapped[str | None] = mapped_column(Text, nullable=True, comment="产出说明")
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.current_timestamp(), onupdate=func.current_timestamp())


class CRMExecutionTaskModel(CRMBase, CRMTimestampMixin, CRMOwnedMixin):
    __tablename__ = "crm_execution_tasks"
    __table_args__ = (
        UniqueConstraint("owner_user_id", "approval_id", name="uq_crm_execution_task_approval"),
        Index("ix_crm_execution_task_queue", "owner_user_id", "execution_owner", "task_status"),
    )
    task_id: Mapped[str] = mapped_column(String(96), primary_key=True)
    approval_id: Mapped[str] = mapped_column(String(48), nullable=False, comment="审批 ID")
    execution_owner: Mapped[str] = mapped_column(String(32), nullable=False, comment="执行方")
    execution_kind: Mapped[str] = mapped_column(String(32), nullable=False, comment="执行类型")
    task_status: Mapped[str] = mapped_column(String(24), nullable=False, default="queued", comment="任务状态")
    title: Mapped[str] = mapped_column(String(300), nullable=False, comment="任务标题")
    action_pack: Mapped[str] = mapped_column(Text, nullable=False, comment="行动包")
    output_refs: Mapped[list[Any] | None] = mapped_column(JSON, nullable=True, comment="产出引用")
    output_note: Mapped[str | None] = mapped_column(Text, nullable=True, comment="产出说明")
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="开始时间")
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="完成时间")


class CRMDecisionActivityModel(CRMBase, CRMOwnedMixin):
    __tablename__ = "crm_decision_activities"
    __table_args__ = (Index("ix_crm_decision_activity_created", "owner_user_id", "created_at"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    approval_id: Mapped[str | None] = mapped_column(String(48), nullable=True, comment="审批 ID")
    event_text: Mapped[str] = mapped_column(Text, nullable=False, comment="事件文本")
    event_tone: Mapped[str] = mapped_column(String(16), nullable=False, default="system", comment="事件语气")
    actor: Mapped[str] = mapped_column(String(32), nullable=False, default="user", comment="操作方")
    event_type: Mapped[str] = mapped_column(String(48), nullable=False, default="legacy", comment="事件类型")
    entity_type: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="实体类型")
    entity_id: Mapped[str | None] = mapped_column(String(96), nullable=True, comment="实体 ID")
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="事件元数据")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.current_timestamp())


class CRMOpportunityLinkModel(CRMBase, CRMOwnedMixin):
    __tablename__ = "crm_opportunity_links"
    market_opportunity_id: Mapped[str] = mapped_column("opportunity_id", String(40), primary_key=True, comment="市场机会 ID")
    market_signal_id: Mapped[str | None] = mapped_column(String(40), nullable=True, comment="市场信号 ID")
    market_source_id: Mapped[str | None] = mapped_column(String(40), nullable=True, comment="市场来源 ID")
    entity_type: Mapped[str] = mapped_column(String(32), primary_key=True, comment="CRM 实体类型")
    entity_id: Mapped[str] = mapped_column(String(96), primary_key=True, comment="CRM 实体 ID")
    relation_type: Mapped[str] = mapped_column(String(32), primary_key=True, comment="关联类型")
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="关联元数据")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.current_timestamp())


class CRMLegacyImportModel(CRMBase):
    __tablename__ = "crm_legacy_imports"
    source_key: Mapped[str] = mapped_column(String(160), primary_key=True)
    source_hash: Mapped[str] = mapped_column(String(64), nullable=False, comment="源数据哈希")
    imported_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.current_timestamp(), onupdate=func.current_timestamp())


class CRMLegacyRecordMapModel(CRMBase):
    __tablename__ = "crm_legacy_record_maps"
    source_system: Mapped[str] = mapped_column(String(64), primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(32), primary_key=True)
    source_record_id: Mapped[str] = mapped_column(String(96), primary_key=True)
    target_record_id: Mapped[str] = mapped_column(String(96), nullable=False)
    source_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    imported_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.current_timestamp(), onupdate=func.current_timestamp())
