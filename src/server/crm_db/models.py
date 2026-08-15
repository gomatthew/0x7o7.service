from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.server.crm_db.base import CRMBase


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )


class OwnedMixin:
    owner_user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)


class CRMCompanyModel(CRMBase, TimestampMixin, OwnedMixin):
    __tablename__ = "crm_companies"
    __table_args__ = (
        UniqueConstraint("owner_user_id", "website", name="uq_crm_company_owner_website"),
        CheckConstraint("fit_score >= 0 AND fit_score <= 100", name="ck_crm_company_fit_score"),
        Index("ix_crm_company_owner_status", "owner_user_id", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    website: Mapped[str | None] = mapped_column(String(512), nullable=True)
    country: Mapped[str] = mapped_column(String(64), nullable=False, default="US")
    industry: Mapped[str | None] = mapped_column(String(120), nullable=True)
    employee_band: Mapped[str | None] = mapped_column(String(32), nullable=True)
    fit_score: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="researching")
    source_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    buying_signal: Mapped[str | None] = mapped_column(Text, nullable=True)
    value_hypothesis: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    contacts: Mapped[list["CRMContactModel"]] = relationship(back_populates="company", cascade="all, delete-orphan")
    deals: Mapped[list["CRMDealModel"]] = relationship(back_populates="company", cascade="all, delete-orphan")


class CRMContactModel(CRMBase, TimestampMixin, OwnedMixin):
    __tablename__ = "crm_contacts"
    __table_args__ = (
        UniqueConstraint("owner_user_id", "company_id", "email", name="uq_crm_contact_company_email"),
        Index("ix_crm_contact_owner_company", "owner_user_id", "company_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("crm_companies.id", ondelete="CASCADE"), nullable=False)
    full_name: Mapped[str] = mapped_column(String(160), nullable=False)
    role: Mapped[str | None] = mapped_column(String(160), nullable=True)
    email: Mapped[str | None] = mapped_column(String(254), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    linkedin_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    platform: Mapped[str | None] = mapped_column(String(64), nullable=True)
    platform_profile_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    preferred_channel: Mapped[str | None] = mapped_column(String(32), nullable=True)
    verification_status: Mapped[str] = mapped_column(String(32), nullable=False, default="unverified")
    source_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    company: Mapped[CRMCompanyModel] = relationship(back_populates="contacts")
    deals: Mapped[list["CRMDealModel"]] = relationship(back_populates="contact")
    drafts: Mapped[list["CRMOutreachDraftModel"]] = relationship(back_populates="contact", cascade="all, delete-orphan")


class CRMDealModel(CRMBase, TimestampMixin, OwnedMixin):
    __tablename__ = "crm_deals"
    __table_args__ = (
        CheckConstraint("probability >= 0 AND probability <= 100", name="ck_crm_deal_probability"),
        Index("ix_crm_deal_owner_stage", "owner_user_id", "stage"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("crm_companies.id", ondelete="CASCADE"), nullable=False)
    contact_id: Mapped[int | None] = mapped_column(ForeignKey("crm_contacts.id", ondelete="SET NULL"), nullable=True)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    stage: Mapped[str] = mapped_column(String(32), nullable=False, default="lead")
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="USD")
    probability: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    expected_close_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    owner_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    next_step: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    company: Mapped[CRMCompanyModel] = relationship(back_populates="deals")
    contact: Mapped[CRMContactModel | None] = relationship(back_populates="deals")
    activities: Mapped[list["CRMActivityModel"]] = relationship(back_populates="deal", cascade="all, delete-orphan")
    tasks: Mapped[list["CRMFollowupTaskModel"]] = relationship(back_populates="deal", cascade="all, delete-orphan")


class CRMActivityModel(CRMBase, OwnedMixin):
    __tablename__ = "crm_activities"
    __table_args__ = (Index("ix_crm_activity_owner_happened", "owner_user_id", "happened_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_id: Mapped[int | None] = mapped_column(ForeignKey("crm_companies.id", ondelete="SET NULL"), nullable=True)
    contact_id: Mapped[int | None] = mapped_column(ForeignKey("crm_contacts.id", ondelete="SET NULL"), nullable=True)
    deal_id: Mapped[int | None] = mapped_column(ForeignKey("crm_deals.id", ondelete="CASCADE"), nullable=True)
    activity_type: Mapped[str] = mapped_column(String(32), nullable=False)
    direction: Mapped[str] = mapped_column(String(16), nullable=False, default="internal")
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    outcome: Mapped[str | None] = mapped_column(String(120), nullable=True)
    happened_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    next_followup_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    deal: Mapped[CRMDealModel | None] = relationship(back_populates="activities")


class CRMOutreachDraftModel(CRMBase, TimestampMixin, OwnedMixin):
    __tablename__ = "crm_outreach_drafts"
    __table_args__ = (Index("ix_crm_draft_owner_status", "owner_user_id", "status"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    contact_id: Mapped[int] = mapped_column(ForeignKey("crm_contacts.id", ondelete="CASCADE"), nullable=False)
    deal_id: Mapped[int | None] = mapped_column(ForeignKey("crm_deals.id", ondelete="SET NULL"), nullable=True)
    channel: Mapped[str] = mapped_column(String(32), nullable=False)
    subject: Mapped[str | None] = mapped_column(String(300), nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    approval_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    approved_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    external_message_id: Mapped[str | None] = mapped_column(String(256), nullable=True)

    contact: Mapped[CRMContactModel] = relationship(back_populates="drafts")


class CRMFollowupTaskModel(CRMBase, TimestampMixin, OwnedMixin):
    __tablename__ = "crm_followup_tasks"
    __table_args__ = (Index("ix_crm_task_owner_due", "owner_user_id", "status", "due_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    contact_id: Mapped[int | None] = mapped_column(ForeignKey("crm_contacts.id", ondelete="SET NULL"), nullable=True)
    deal_id: Mapped[int | None] = mapped_column(ForeignKey("crm_deals.id", ondelete="CASCADE"), nullable=True)
    due_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    task_type: Mapped[str] = mapped_column(String(32), nullable=False, default="follow_up")
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="open")
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    deal: Mapped[CRMDealModel | None] = relationship(back_populates="tasks")
