from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, TypeVar

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.server.crm_db.models import (
    CRMActivityModel,
    CRMCompanyModel,
    CRMContactModel,
    CRMDealModel,
    CRMFollowupTaskModel,
    CRMOutreachDraftModel,
)
from src.server.dto.crm_dto import (
    ActivityCreate,
    CompanyCreate,
    CompanyUpdate,
    ContactCreate,
    ContactUpdate,
    DealCreate,
    DealUpdate,
    FollowupCreate,
    FollowupUpdate,
    OutreachDraftCreate,
)
from src.server.utils import TokenChecker, is_admin_user


ModelT = TypeVar("ModelT")
PIPELINE_STAGES = ("lead", "qualified", "proposal", "negotiation", "won", "lost")


def require_crm_admin(token_checker: TokenChecker) -> str:
    if not token_checker:
        raise HTTPException(status_code=401, detail="Authentication required")
    if not is_admin_user(token_checker):
        raise HTTPException(status_code=403, detail="CRM administrator access required")
    return str(token_checker)


def _iso(value: date | datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def _money(value: Decimal | int | float | None) -> float:
    return float(value or 0)


def _owned_record(session: Session, model: type[ModelT], owner_user_id: str, record_id: int) -> ModelT:
    record = session.scalar(
        select(model).where(model.id == record_id, model.owner_user_id == owner_user_id)
    )
    if record is None:
        raise HTTPException(status_code=404, detail=f"{model.__name__} not found")
    return record


def _apply_update(record: Any, values: dict[str, Any]) -> None:
    for field, value in values.items():
        setattr(record, field, value)


def company_dict(record: CRMCompanyModel) -> dict[str, Any]:
    return {
        "id": record.id,
        "name": record.name,
        "website": record.website,
        "country": record.country,
        "industry": record.industry,
        "employee_band": record.employee_band,
        "fit_score": record.fit_score,
        "status": record.status,
        "source_url": record.source_url,
        "buying_signal": record.buying_signal,
        "value_hypothesis": record.value_hypothesis,
        "notes": record.notes,
        "created_at": _iso(record.created_at),
        "updated_at": _iso(record.updated_at),
    }


def contact_dict(record: CRMContactModel, company_name: str | None = None) -> dict[str, Any]:
    return {
        "id": record.id,
        "company_id": record.company_id,
        "company_name": company_name,
        "full_name": record.full_name,
        "role": record.role,
        "email": record.email,
        "phone": record.phone,
        "linkedin_url": record.linkedin_url,
        "platform": record.platform,
        "platform_profile_url": record.platform_profile_url,
        "preferred_channel": record.preferred_channel,
        "verification_status": record.verification_status,
        "source_url": record.source_url,
        "notes": record.notes,
        "created_at": _iso(record.created_at),
        "updated_at": _iso(record.updated_at),
    }


def deal_dict(
    record: CRMDealModel,
    company_name: str | None = None,
    contact_name: str | None = None,
) -> dict[str, Any]:
    return {
        "id": record.id,
        "company_id": record.company_id,
        "company_name": company_name,
        "contact_id": record.contact_id,
        "contact_name": contact_name,
        "title": record.title,
        "stage": record.stage,
        "amount": _money(record.amount),
        "currency": record.currency,
        "probability": record.probability,
        "expected_close_date": _iso(record.expected_close_date),
        "owner_name": record.owner_name,
        "next_step": record.next_step,
        "notes": record.notes,
        "created_at": _iso(record.created_at),
        "updated_at": _iso(record.updated_at),
    }


def activity_dict(
    record: CRMActivityModel,
    company_name: str | None = None,
    contact_name: str | None = None,
    deal_title: str | None = None,
) -> dict[str, Any]:
    return {
        "id": record.id,
        "company_id": record.company_id,
        "company_name": company_name,
        "contact_id": record.contact_id,
        "contact_name": contact_name,
        "deal_id": record.deal_id,
        "deal_title": deal_title,
        "activity_type": record.activity_type,
        "direction": record.direction,
        "summary": record.summary,
        "outcome": record.outcome,
        "happened_at": _iso(record.happened_at),
        "next_followup_at": _iso(record.next_followup_at),
    }


def draft_dict(
    record: CRMOutreachDraftModel,
    contact_name: str | None = None,
    company_name: str | None = None,
) -> dict[str, Any]:
    return {
        "id": record.id,
        "contact_id": record.contact_id,
        "contact_name": contact_name,
        "company_name": company_name,
        "deal_id": record.deal_id,
        "channel": record.channel,
        "subject": record.subject,
        "body": record.body,
        "status": record.status,
        "approval_note": record.approval_note,
        "approved_by": record.approved_by,
        "approved_at": _iso(record.approved_at),
        "sent_at": _iso(record.sent_at),
        "created_at": _iso(record.created_at),
        "updated_at": _iso(record.updated_at),
    }


def followup_dict(
    record: CRMFollowupTaskModel,
    contact_name: str | None = None,
    company_name: str | None = None,
    deal_title: str | None = None,
) -> dict[str, Any]:
    return {
        "id": record.id,
        "contact_id": record.contact_id,
        "contact_name": contact_name,
        "company_name": company_name,
        "deal_id": record.deal_id,
        "deal_title": deal_title,
        "due_at": _iso(record.due_at),
        "task_type": record.task_type,
        "description": record.description,
        "status": record.status,
        "completed_at": _iso(record.completed_at),
        "created_at": _iso(record.created_at),
    }


def dashboard(session: Session, owner_user_id: str) -> dict[str, Any]:
    company_count = session.scalar(
        select(func.count()).select_from(CRMCompanyModel).where(CRMCompanyModel.owner_user_id == owner_user_id)
    ) or 0
    contact_count = session.scalar(
        select(func.count()).select_from(CRMContactModel).where(CRMContactModel.owner_user_id == owner_user_id)
    ) or 0
    pending_approvals = session.scalar(
        select(func.count()).select_from(CRMOutreachDraftModel).where(
            CRMOutreachDraftModel.owner_user_id == owner_user_id,
            CRMOutreachDraftModel.status == "pending_approval",
        )
    ) or 0
    open_followups = session.scalar(
        select(func.count()).select_from(CRMFollowupTaskModel).where(
            CRMFollowupTaskModel.owner_user_id == owner_user_id,
            CRMFollowupTaskModel.status == "open",
        )
    ) or 0
    deals = list(session.scalars(select(CRMDealModel).where(CRMDealModel.owner_user_id == owner_user_id)))
    pipeline = {stage: {"count": 0, "amount": 0.0} for stage in PIPELINE_STAGES}
    monthly: dict[str, float] = defaultdict(float)
    for deal in deals:
        stage = deal.stage if deal.stage in pipeline else "lead"
        pipeline[stage]["count"] += 1
        pipeline[stage]["amount"] += _money(deal.amount)
        month_source = deal.expected_close_date or deal.created_at.date()
        monthly[month_source.strftime("%Y-%m")] += _money(deal.amount)

    active_deals = [deal for deal in deals if deal.stage not in {"won", "lost"}]
    weighted_pipeline = sum(_money(deal.amount) * deal.probability / 100 for deal in active_deals)
    won_revenue = sum(_money(deal.amount) for deal in deals if deal.stage == "won")
    top_rows = session.execute(
        select(CRMDealModel, CRMCompanyModel.name, CRMContactModel.full_name)
        .join(CRMCompanyModel, CRMDealModel.company_id == CRMCompanyModel.id)
        .outerjoin(CRMContactModel, CRMDealModel.contact_id == CRMContactModel.id)
        .where(CRMDealModel.owner_user_id == owner_user_id, CRMDealModel.stage.notin_(("won", "lost")))
        .order_by(CRMDealModel.amount.desc())
        .limit(6)
    ).all()
    activity_rows = session.execute(
        select(CRMActivityModel, CRMCompanyModel.name, CRMContactModel.full_name, CRMDealModel.title)
        .outerjoin(CRMCompanyModel, CRMActivityModel.company_id == CRMCompanyModel.id)
        .outerjoin(CRMContactModel, CRMActivityModel.contact_id == CRMContactModel.id)
        .outerjoin(CRMDealModel, CRMActivityModel.deal_id == CRMDealModel.id)
        .where(CRMActivityModel.owner_user_id == owner_user_id)
        .order_by(CRMActivityModel.happened_at.desc())
        .limit(8)
    ).all()
    return {
        "metrics": {
            "companies": company_count,
            "contacts": contact_count,
            "active_deals": len(active_deals),
            "pipeline_amount": sum(_money(deal.amount) for deal in active_deals),
            "weighted_pipeline": weighted_pipeline,
            "won_revenue": won_revenue,
            "pending_approvals": pending_approvals,
            "open_followups": open_followups,
        },
        "pipeline": [{"stage": stage, **values} for stage, values in pipeline.items()],
        "monthly_sales": [{"month": month, "amount": monthly[month]} for month in sorted(monthly)[-8:]],
        "top_deals": [deal_dict(deal, company_name, contact_name) for deal, company_name, contact_name in top_rows],
        "recent_activities": [
            activity_dict(activity, company_name, contact_name, deal_title)
            for activity, company_name, contact_name, deal_title in activity_rows
        ],
    }


def list_companies(session: Session, owner_user_id: str) -> list[dict[str, Any]]:
    records = session.scalars(
        select(CRMCompanyModel)
        .where(CRMCompanyModel.owner_user_id == owner_user_id)
        .order_by(CRMCompanyModel.fit_score.desc(), CRMCompanyModel.id.desc())
    )
    return [company_dict(record) for record in records]


def create_company(session: Session, owner_user_id: str, payload: CompanyCreate) -> dict[str, Any]:
    record = CRMCompanyModel(owner_user_id=owner_user_id, **payload.model_dump())
    session.add(record)
    session.flush()
    return company_dict(record)


def update_company(
    session: Session, owner_user_id: str, company_id: int, payload: CompanyUpdate
) -> dict[str, Any]:
    record = _owned_record(session, CRMCompanyModel, owner_user_id, company_id)
    _apply_update(record, payload.model_dump(exclude_unset=True))
    session.flush()
    return company_dict(record)


def list_contacts(session: Session, owner_user_id: str) -> list[dict[str, Any]]:
    rows = session.execute(
        select(CRMContactModel, CRMCompanyModel.name)
        .join(CRMCompanyModel, CRMContactModel.company_id == CRMCompanyModel.id)
        .where(CRMContactModel.owner_user_id == owner_user_id)
        .order_by(CRMContactModel.id.desc())
    ).all()
    return [contact_dict(contact, company_name) for contact, company_name in rows]


def create_contact(session: Session, owner_user_id: str, payload: ContactCreate) -> dict[str, Any]:
    company = _owned_record(session, CRMCompanyModel, owner_user_id, payload.company_id)
    record = CRMContactModel(owner_user_id=owner_user_id, **payload.model_dump())
    session.add(record)
    session.flush()
    return contact_dict(record, company.name)


def update_contact(
    session: Session, owner_user_id: str, contact_id: int, payload: ContactUpdate
) -> dict[str, Any]:
    record = _owned_record(session, CRMContactModel, owner_user_id, contact_id)
    values = payload.model_dump(exclude_unset=True)
    if "company_id" in values:
        _owned_record(session, CRMCompanyModel, owner_user_id, values["company_id"])
    _apply_update(record, values)
    session.flush()
    company = _owned_record(session, CRMCompanyModel, owner_user_id, record.company_id)
    return contact_dict(record, company.name)


def list_deals(session: Session, owner_user_id: str) -> list[dict[str, Any]]:
    rows = session.execute(
        select(CRMDealModel, CRMCompanyModel.name, CRMContactModel.full_name)
        .join(CRMCompanyModel, CRMDealModel.company_id == CRMCompanyModel.id)
        .outerjoin(CRMContactModel, CRMDealModel.contact_id == CRMContactModel.id)
        .where(CRMDealModel.owner_user_id == owner_user_id)
        .order_by(CRMDealModel.updated_at.desc(), CRMDealModel.id.desc())
    ).all()
    return [deal_dict(deal, company_name, contact_name) for deal, company_name, contact_name in rows]


def create_deal(session: Session, owner_user_id: str, payload: DealCreate) -> dict[str, Any]:
    company = _owned_record(session, CRMCompanyModel, owner_user_id, payload.company_id)
    contact_name = None
    if payload.contact_id is not None:
        contact = _owned_record(session, CRMContactModel, owner_user_id, payload.contact_id)
        if contact.company_id != payload.company_id:
            raise HTTPException(status_code=400, detail="Contact does not belong to company")
        contact_name = contact.full_name
    record = CRMDealModel(owner_user_id=owner_user_id, **payload.model_dump())
    session.add(record)
    session.flush()
    return deal_dict(record, company.name, contact_name)


def update_deal(session: Session, owner_user_id: str, deal_id: int, payload: DealUpdate) -> dict[str, Any]:
    record = _owned_record(session, CRMDealModel, owner_user_id, deal_id)
    values = payload.model_dump(exclude_unset=True)
    if "contact_id" in values and values["contact_id"] is not None:
        contact = _owned_record(session, CRMContactModel, owner_user_id, values["contact_id"])
        if contact.company_id != record.company_id:
            raise HTTPException(status_code=400, detail="Contact does not belong to company")
    _apply_update(record, values)
    session.flush()
    company = _owned_record(session, CRMCompanyModel, owner_user_id, record.company_id)
    contact = (
        _owned_record(session, CRMContactModel, owner_user_id, record.contact_id)
        if record.contact_id is not None
        else None
    )
    return deal_dict(record, company.name, contact.full_name if contact else None)


def list_activities(session: Session, owner_user_id: str) -> list[dict[str, Any]]:
    rows = session.execute(
        select(CRMActivityModel, CRMCompanyModel.name, CRMContactModel.full_name, CRMDealModel.title)
        .outerjoin(CRMCompanyModel, CRMActivityModel.company_id == CRMCompanyModel.id)
        .outerjoin(CRMContactModel, CRMActivityModel.contact_id == CRMContactModel.id)
        .outerjoin(CRMDealModel, CRMActivityModel.deal_id == CRMDealModel.id)
        .where(CRMActivityModel.owner_user_id == owner_user_id)
        .order_by(CRMActivityModel.happened_at.desc(), CRMActivityModel.id.desc())
    ).all()
    return [
        activity_dict(activity, company_name, contact_name, deal_title)
        for activity, company_name, contact_name, deal_title in rows
    ]


def create_activity(session: Session, owner_user_id: str, payload: ActivityCreate) -> dict[str, Any]:
    values = payload.model_dump()
    if values["company_id"] is not None:
        _owned_record(session, CRMCompanyModel, owner_user_id, values["company_id"])
    if values["contact_id"] is not None:
        _owned_record(session, CRMContactModel, owner_user_id, values["contact_id"])
    if values["deal_id"] is not None:
        _owned_record(session, CRMDealModel, owner_user_id, values["deal_id"])
    if values["happened_at"] is None:
        values["happened_at"] = datetime.now(timezone.utc).replace(tzinfo=None)
    record = CRMActivityModel(owner_user_id=owner_user_id, **values)
    session.add(record)
    if payload.next_followup_at is not None:
        session.add(
            CRMFollowupTaskModel(
                owner_user_id=owner_user_id,
                contact_id=payload.contact_id,
                deal_id=payload.deal_id,
                due_at=payload.next_followup_at,
                task_type="follow_up",
                description=f"Follow up: {payload.summary[:200]}",
            )
        )
    session.flush()
    return activity_dict(record)


def list_drafts(session: Session, owner_user_id: str) -> list[dict[str, Any]]:
    rows = session.execute(
        select(CRMOutreachDraftModel, CRMContactModel.full_name, CRMCompanyModel.name)
        .join(CRMContactModel, CRMOutreachDraftModel.contact_id == CRMContactModel.id)
        .join(CRMCompanyModel, CRMContactModel.company_id == CRMCompanyModel.id)
        .where(CRMOutreachDraftModel.owner_user_id == owner_user_id)
        .order_by(CRMOutreachDraftModel.updated_at.desc(), CRMOutreachDraftModel.id.desc())
    ).all()
    return [draft_dict(draft, contact_name, company_name) for draft, contact_name, company_name in rows]


def create_draft(session: Session, owner_user_id: str, payload: OutreachDraftCreate) -> dict[str, Any]:
    contact = _owned_record(session, CRMContactModel, owner_user_id, payload.contact_id)
    if payload.deal_id is not None:
        _owned_record(session, CRMDealModel, owner_user_id, payload.deal_id)
    company = _owned_record(session, CRMCompanyModel, owner_user_id, contact.company_id)
    record = CRMOutreachDraftModel(owner_user_id=owner_user_id, **payload.model_dump())
    session.add(record)
    session.flush()
    return draft_dict(record, contact.full_name, company.name)


def transition_draft(
    session: Session,
    owner_user_id: str,
    draft_id: int,
    action: str,
    note: str | None,
) -> dict[str, Any]:
    record = _owned_record(session, CRMOutreachDraftModel, owner_user_id, draft_id)
    transitions = {
        "request-approval": ({"draft", "rejected"}, "pending_approval"),
        "approve": ({"pending_approval"}, "approved"),
        "reject": ({"pending_approval", "approved"}, "rejected"),
        "cancel": ({"draft", "pending_approval", "approved", "rejected"}, "cancelled"),
    }
    if action not in transitions:
        raise HTTPException(status_code=400, detail="Unsupported draft action")
    allowed, target = transitions[action]
    if record.status not in allowed:
        raise HTTPException(status_code=409, detail=f"Cannot {action} a {record.status} draft")
    record.status = target
    record.approval_note = note
    if action == "approve":
        record.approved_by = owner_user_id
        record.approved_at = datetime.now(timezone.utc).replace(tzinfo=None)
    else:
        record.approved_by = None
        record.approved_at = None
    session.flush()
    contact = _owned_record(session, CRMContactModel, owner_user_id, record.contact_id)
    company = _owned_record(session, CRMCompanyModel, owner_user_id, contact.company_id)
    return draft_dict(record, contact.full_name, company.name)


def list_followups(session: Session, owner_user_id: str) -> list[dict[str, Any]]:
    rows = session.execute(
        select(CRMFollowupTaskModel, CRMContactModel.full_name, CRMCompanyModel.name, CRMDealModel.title)
        .outerjoin(CRMContactModel, CRMFollowupTaskModel.contact_id == CRMContactModel.id)
        .outerjoin(CRMCompanyModel, CRMContactModel.company_id == CRMCompanyModel.id)
        .outerjoin(CRMDealModel, CRMFollowupTaskModel.deal_id == CRMDealModel.id)
        .where(CRMFollowupTaskModel.owner_user_id == owner_user_id)
        .order_by(CRMFollowupTaskModel.status.asc(), CRMFollowupTaskModel.due_at.asc())
    ).all()
    return [
        followup_dict(task, contact_name, company_name, deal_title)
        for task, contact_name, company_name, deal_title in rows
    ]


def create_followup(session: Session, owner_user_id: str, payload: FollowupCreate) -> dict[str, Any]:
    if payload.contact_id is not None:
        _owned_record(session, CRMContactModel, owner_user_id, payload.contact_id)
    if payload.deal_id is not None:
        _owned_record(session, CRMDealModel, owner_user_id, payload.deal_id)
    record = CRMFollowupTaskModel(owner_user_id=owner_user_id, **payload.model_dump())
    session.add(record)
    session.flush()
    return followup_dict(record)


def update_followup(
    session: Session, owner_user_id: str, task_id: int, payload: FollowupUpdate
) -> dict[str, Any]:
    record = _owned_record(session, CRMFollowupTaskModel, owner_user_id, task_id)
    values = payload.model_dump(exclude_unset=True)
    if values.get("status") == "done":
        values["completed_at"] = datetime.now(timezone.utc).replace(tzinfo=None)
    elif "status" in values and values["status"] != "done":
        values["completed_at"] = None
    _apply_update(record, values)
    session.flush()
    return followup_dict(record)
