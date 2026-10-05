# -*- coding: utf-8 -*-
from datetime import datetime, timezone

from sqlalchemy import func, select

from src.server.db.crm_base import with_crm_session
from src.server.db.models.crm_model import (
    CRMActivityModel,
    CRMApprovalRequestModel,
    CRMCompanyModel,
    CRMContactModel,
    CRMDecisionActivityModel,
    CRMDealModel,
    CRMExecutionTaskModel,
    CRMFollowupTaskModel,
    CRMOutreachDraftModel,
)


def _model_dict(model):
    return {column.name: getattr(model, column.name) for column in model.__table__.columns}


def _update_model(model, values):
    for key, value in values.items():
        if hasattr(model, key):
            setattr(model, key, value)


def _owned_query(session, model, owner_user_id):
    return session.query(model).filter(model.owner_user_id == str(owner_user_id))


def _utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


@with_crm_session
def check_crm_database(session):
    session.execute(select(1))
    return True


@with_crm_session
def get_crm_dashboard_from_db(session, owner_user_id):
    owner_user_id = str(owner_user_id)
    counts = {}
    for key, model in (
        ("company_count", CRMCompanyModel),
        ("contact_count", CRMContactModel),
        ("deal_count", CRMDealModel),
        ("approval_count", CRMApprovalRequestModel),
        ("task_count", CRMExecutionTaskModel),
        ("draft_count", CRMOutreachDraftModel),
        ("followup_count", CRMFollowupTaskModel),
    ):
        counts[key] = session.query(func.count()).select_from(model).filter(
            model.owner_user_id == owner_user_id
        ).scalar() or 0
    counts["pending_approval_count"] = _owned_query(
        session, CRMApprovalRequestModel, owner_user_id
    ).filter(CRMApprovalRequestModel.status == "pending_approval").count()
    counts["open_task_count"] = _owned_query(
        session, CRMExecutionTaskModel, owner_user_id
    ).filter(CRMExecutionTaskModel.task_status.in_(["queued", "in_progress"])).count()
    counts["open_followup_count"] = _owned_query(
        session, CRMFollowupTaskModel, owner_user_id
    ).filter(CRMFollowupTaskModel.status == "open").count()
    return counts


@with_crm_session
def list_companies_from_db(session, owner_user_id):
    rows = _owned_query(session, CRMCompanyModel, owner_user_id).order_by(
        CRMCompanyModel.updated_at.desc(), CRMCompanyModel.id.desc()
    ).all()
    return [_model_dict(row) for row in rows]


@with_crm_session
def get_company_from_db(session, owner_user_id, company_id):
    company = _owned_query(session, CRMCompanyModel, owner_user_id).filter(
        CRMCompanyModel.id == company_id
    ).first()
    if not company:
        return None
    contacts = _owned_query(session, CRMContactModel, owner_user_id).filter(
        CRMContactModel.company_id == company_id
    ).order_by(CRMContactModel.id).all()
    deals = _owned_query(session, CRMDealModel, owner_user_id).filter(
        CRMDealModel.company_id == company_id
    ).order_by(CRMDealModel.updated_at.desc()).all()
    return {
        **_model_dict(company),
        "contacts": [_model_dict(row) for row in contacts],
        "deals": [_model_dict(row) for row in deals],
    }


@with_crm_session
def create_company_in_db(session, owner_user_id, values):
    model = CRMCompanyModel(owner_user_id=str(owner_user_id), **values)
    session.add(model)
    session.flush()
    return _model_dict(model)


@with_crm_session
def update_company_in_db(session, owner_user_id, company_id, values):
    model = _owned_query(session, CRMCompanyModel, owner_user_id).filter(
        CRMCompanyModel.id == company_id
    ).first()
    if not model:
        return None
    _update_model(model, values)
    session.flush()
    return _model_dict(model)


@with_crm_session
def list_contacts_from_db(session, owner_user_id, company_id=None):
    query = _owned_query(session, CRMContactModel, owner_user_id)
    if company_id is not None:
        query = query.filter(CRMContactModel.company_id == company_id)
    return [_model_dict(row) for row in query.order_by(CRMContactModel.updated_at.desc()).all()]


@with_crm_session
def get_contact_from_db(session, owner_user_id, contact_id):
    model = _owned_query(session, CRMContactModel, owner_user_id).filter(
        CRMContactModel.id == contact_id
    ).first()
    return _model_dict(model) if model else None


@with_crm_session
def create_contact_in_db(session, owner_user_id, values):
    company = _owned_query(session, CRMCompanyModel, owner_user_id).filter(
        CRMCompanyModel.id == values["company_id"]
    ).first()
    if not company:
        return None
    model = CRMContactModel(owner_user_id=str(owner_user_id), **values)
    session.add(model)
    session.flush()
    return _model_dict(model)


@with_crm_session
def update_contact_in_db(session, owner_user_id, contact_id, values):
    model = _owned_query(session, CRMContactModel, owner_user_id).filter(
        CRMContactModel.id == contact_id
    ).first()
    if not model:
        return None
    if values.get("company_id") is not None:
        company = _owned_query(session, CRMCompanyModel, owner_user_id).filter(
            CRMCompanyModel.id == values["company_id"]
        ).first()
        if not company:
            return None
    _update_model(model, values)
    session.flush()
    return _model_dict(model)


@with_crm_session
def list_deals_from_db(session, owner_user_id, company_id=None):
    query = _owned_query(session, CRMDealModel, owner_user_id)
    if company_id is not None:
        query = query.filter(CRMDealModel.company_id == company_id)
    return [_model_dict(row) for row in query.order_by(CRMDealModel.updated_at.desc()).all()]


@with_crm_session
def create_deal_in_db(session, owner_user_id, values):
    company = _owned_query(session, CRMCompanyModel, owner_user_id).filter(
        CRMCompanyModel.id == values["company_id"]
    ).first()
    if not company:
        return None
    if values.get("contact_id"):
        contact = _owned_query(session, CRMContactModel, owner_user_id).filter(
            CRMContactModel.id == values["contact_id"],
            CRMContactModel.company_id == values["company_id"],
        ).first()
        if not contact:
            return None
    model = CRMDealModel(owner_user_id=str(owner_user_id), **values)
    session.add(model)
    session.flush()
    return _model_dict(model)


@with_crm_session
def update_deal_in_db(session, owner_user_id, deal_id, values):
    model = _owned_query(session, CRMDealModel, owner_user_id).filter(
        CRMDealModel.id == deal_id
    ).first()
    if not model:
        return None
    if values.get("contact_id") is not None:
        contact = _owned_query(session, CRMContactModel, owner_user_id).filter(
            CRMContactModel.id == values["contact_id"],
            CRMContactModel.company_id == model.company_id,
        ).first()
        if not contact:
            return None
    _update_model(model, values)
    session.flush()
    return _model_dict(model)


@with_crm_session
def list_activities_from_db(session, owner_user_id, limit=100):
    rows = _owned_query(session, CRMActivityModel, owner_user_id).order_by(
        CRMActivityModel.happened_at.desc(), CRMActivityModel.id.desc()
    ).limit(int(limit)).all()
    return [_model_dict(row) for row in rows]


@with_crm_session
def create_activity_in_db(session, owner_user_id, values):
    values = dict(values)
    values["happened_at"] = values.get("happened_at") or _utcnow()
    model = CRMActivityModel(owner_user_id=str(owner_user_id), **values)
    session.add(model)
    session.flush()
    return _model_dict(model)


@with_crm_session
def list_outreach_drafts_from_db(session, owner_user_id):
    rows = _owned_query(session, CRMOutreachDraftModel, owner_user_id).order_by(
        CRMOutreachDraftModel.updated_at.desc()
    ).all()
    return [_model_dict(row) for row in rows]


@with_crm_session
def create_outreach_draft_in_db(session, owner_user_id, values):
    contact = _owned_query(session, CRMContactModel, owner_user_id).filter(
        CRMContactModel.id == values["contact_id"]
    ).first()
    if not contact:
        return None
    model = CRMOutreachDraftModel(owner_user_id=str(owner_user_id), status="draft", **values)
    session.add(model)
    session.flush()
    return _model_dict(model)


@with_crm_session
def list_followups_from_db(session, owner_user_id):
    rows = _owned_query(session, CRMFollowupTaskModel, owner_user_id).order_by(
        CRMFollowupTaskModel.status, CRMFollowupTaskModel.due_at
    ).all()
    return [_model_dict(row) for row in rows]


@with_crm_session
def create_followup_in_db(session, owner_user_id, values):
    model = CRMFollowupTaskModel(owner_user_id=str(owner_user_id), status="open", **values)
    session.add(model)
    session.flush()
    return _model_dict(model)


@with_crm_session
def update_followup_in_db(session, owner_user_id, followup_id, values):
    model = _owned_query(session, CRMFollowupTaskModel, owner_user_id).filter(
        CRMFollowupTaskModel.id == followup_id
    ).first()
    if not model:
        return None
    _update_model(model, values)
    if values.get("status") == "done":
        model.completed_at = _utcnow()
    elif values.get("status") in {"open", "cancelled"}:
        model.completed_at = None
    session.flush()
    return _model_dict(model)


@with_crm_session
def list_approvals_from_db(session, owner_user_id):
    rows = _owned_query(session, CRMApprovalRequestModel, owner_user_id).order_by(
        CRMApprovalRequestModel.requested_at.desc()
    ).all()
    return [_model_dict(row) for row in rows]


@with_crm_session
def get_approval_from_db(session, owner_user_id, approval_id):
    model = _owned_query(session, CRMApprovalRequestModel, owner_user_id).filter(
        CRMApprovalRequestModel.id == approval_id
    ).first()
    return _model_dict(model) if model else None


@with_crm_session
def create_approval_in_db(session, owner_user_id, values):
    model = CRMApprovalRequestModel(owner_user_id=str(owner_user_id), **values)
    session.add(model)
    session.flush()
    session.add(CRMDecisionActivityModel(
        owner_user_id=str(owner_user_id), approval_id=model.id,
        event_text=f"审批请求 {model.title} 已创建", event_tone="system",
        actor="agent", event_type="approval_created", entity_type="approval",
        entity_id=model.id, metadata_json={"status": model.status},
    ))
    return _model_dict(model)


@with_crm_session
def transition_approval_in_db(session, owner_user_id, approval_id, expected_status, values, task_values=None):
    model = _owned_query(session, CRMApprovalRequestModel, owner_user_id).filter(
        CRMApprovalRequestModel.id == approval_id,
        CRMApprovalRequestModel.status == expected_status,
    ).with_for_update().first()
    if not model:
        return None
    _update_model(model, values)
    session.add(CRMDecisionActivityModel(
        owner_user_id=str(owner_user_id), approval_id=model.id,
        event_text=f"审批状态从 {expected_status} 变更为 {model.status}",
        event_tone="success" if model.status in {"approved_not_executed", "executed_confirmed"} else "system",
        actor="user", event_type="approval_transition", entity_type="approval",
        entity_id=model.id, metadata_json={"from": expected_status, "to": model.status},
    ))
    task = None
    if task_values:
        task = CRMExecutionTaskModel(owner_user_id=str(owner_user_id), **task_values)
        session.add(task)
    session.flush()
    return {"approval": _model_dict(model), "task": _model_dict(task) if task else None}


@with_crm_session
def list_execution_tasks_from_db(session, owner_user_id):
    rows = _owned_query(session, CRMExecutionTaskModel, owner_user_id).order_by(
        CRMExecutionTaskModel.created_at.desc()
    ).all()
    return [_model_dict(row) for row in rows]


@with_crm_session
def get_execution_task_from_db(session, owner_user_id, task_id):
    model = _owned_query(session, CRMExecutionTaskModel, owner_user_id).filter(
        CRMExecutionTaskModel.task_id == task_id
    ).first()
    return _model_dict(model) if model else None


@with_crm_session
def transition_execution_task_in_db(session, owner_user_id, task_id, expected_status, values):
    model = _owned_query(session, CRMExecutionTaskModel, owner_user_id).filter(
        CRMExecutionTaskModel.task_id == task_id,
        CRMExecutionTaskModel.task_status == expected_status,
    ).with_for_update().first()
    if not model:
        return None
    _update_model(model, values)
    approval = _owned_query(session, CRMApprovalRequestModel, owner_user_id).filter(
        CRMApprovalRequestModel.id == model.approval_id
    ).with_for_update().first()
    if approval and model.task_status == "in_progress" and not approval.started_at:
        approval.started_at = model.started_at
    if approval and model.task_status == "completed":
        approval.status = "executed_confirmed"
        approval.completed_at = model.completed_at
        approval.output_note = model.output_note
        approval.output_refs = model.output_refs
    session.add(CRMDecisionActivityModel(
        owner_user_id=str(owner_user_id), approval_id=model.approval_id,
        event_text=f"执行任务状态从 {expected_status} 变更为 {model.task_status}",
        event_tone="success" if model.task_status == "completed" else "system",
        actor=model.execution_owner, event_type="task_transition", entity_type="execution_task",
        entity_id=model.task_id, metadata_json={"from": expected_status, "to": model.task_status},
    ))
    session.flush()
    return {"task": _model_dict(model), "approval": _model_dict(approval) if approval else None}
