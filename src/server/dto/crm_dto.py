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
    name: str = Field(min_length=1, max_length=180)
    website: str | None = Field(default=None, max_length=512)
    country: str = Field(default="US", max_length=64)
    industry: str | None = Field(default=None, max_length=120)
    employee_band: str | None = Field(default=None, max_length=32)
    fit_score: int = Field(default=50, ge=0, le=100)
    status: CompanyStatus = "researching"
    source_url: str | None = Field(default=None, max_length=1024)
    buying_signal: str | None = None
    value_hypothesis: str | None = None
    notes: str | None = None


class CompanyUpdate(CRMModel):
    name: str | None = Field(default=None, min_length=1, max_length=180)
    website: str | None = Field(default=None, max_length=512)
    country: str | None = Field(default=None, max_length=64)
    industry: str | None = Field(default=None, max_length=120)
    employee_band: str | None = Field(default=None, max_length=32)
    fit_score: int | None = Field(default=None, ge=0, le=100)
    status: CompanyStatus | None = None
    source_url: str | None = Field(default=None, max_length=1024)
    buying_signal: str | None = None
    value_hypothesis: str | None = None
    notes: str | None = None


class ContactCreate(CRMModel):
    company_id: int
    full_name: str = Field(min_length=1, max_length=160)
    role: str | None = Field(default=None, max_length=160)
    email: str | None = Field(default=None, max_length=254)
    phone: str | None = Field(default=None, max_length=64)
    linkedin_url: str | None = Field(default=None, max_length=1024)
    platform: str | None = Field(default=None, max_length=64)
    platform_profile_url: str | None = Field(default=None, max_length=1024)
    preferred_channel: str | None = Field(default=None, max_length=32)
    verification_status: str = Field(default="unverified", max_length=32)
    source_url: str | None = Field(default=None, max_length=1024)
    notes: str | None = None


class ContactUpdate(CRMModel):
    company_id: int | None = None
    full_name: str | None = Field(default=None, min_length=1, max_length=160)
    role: str | None = Field(default=None, max_length=160)
    email: str | None = Field(default=None, max_length=254)
    phone: str | None = Field(default=None, max_length=64)
    linkedin_url: str | None = Field(default=None, max_length=1024)
    platform: str | None = Field(default=None, max_length=64)
    platform_profile_url: str | None = Field(default=None, max_length=1024)
    preferred_channel: str | None = Field(default=None, max_length=32)
    verification_status: str | None = Field(default=None, max_length=32)
    source_url: str | None = Field(default=None, max_length=1024)
    notes: str | None = None


class DealCreate(CRMModel):
    company_id: int
    contact_id: int | None = None
    title: str = Field(min_length=1, max_length=240)
    stage: DealStage = "lead"
    amount: Decimal = Field(default=Decimal("0"), ge=0)
    currency: str = Field(default="USD", max_length=8)
    probability: int = Field(default=10, ge=0, le=100)
    expected_close_date: date | None = None
    owner_name: str | None = Field(default=None, max_length=120)
    next_step: str | None = None
    notes: str | None = None


class DealUpdate(CRMModel):
    contact_id: int | None = None
    title: str | None = Field(default=None, min_length=1, max_length=240)
    stage: DealStage | None = None
    amount: Decimal | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, max_length=8)
    probability: int | None = Field(default=None, ge=0, le=100)
    expected_close_date: date | None = None
    owner_name: str | None = Field(default=None, max_length=120)
    next_step: str | None = None
    notes: str | None = None


class ActivityCreate(CRMModel):
    company_id: int | None = None
    contact_id: int | None = None
    deal_id: int | None = None
    activity_type: str = Field(max_length=32)
    direction: Literal["outbound", "inbound", "internal"] = "internal"
    summary: str = Field(min_length=1)
    outcome: str | None = Field(default=None, max_length=120)
    happened_at: datetime | None = None
    next_followup_at: datetime | None = None


class OutreachDraftCreate(CRMModel):
    contact_id: int
    deal_id: int | None = None
    channel: Literal["email", "linkedin", "platform", "contact_form"]
    subject: str | None = Field(default=None, max_length=300)
    body: str = Field(min_length=1)


class DraftDecision(CRMModel):
    note: str | None = None


class FollowupCreate(CRMModel):
    contact_id: int | None = None
    deal_id: int | None = None
    due_at: datetime
    task_type: str = Field(default="follow_up", max_length=32)
    description: str = Field(min_length=1)


class FollowupUpdate(CRMModel):
    due_at: datetime | None = None
    task_type: str | None = Field(default=None, max_length=32)
    description: str | None = None
    status: Literal["open", "done", "cancelled"] | None = None
