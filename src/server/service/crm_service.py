# -*- coding: utf-8 -*-
import uuid
from datetime import datetime, timezone

from src.configs import logger
from src.server.db.crm_base import get_crm_owner_id
from src.server.db.repository import crm_repository, market_repository
from src.server.dto import ApiCommonResponseDTO
from src.server.dto.crm_dto import (
    ActivityCreate,
    ApprovalCreate,
    ApprovalDecision,
    CompanyCreate,
    CompanyUpdate,
    ContactCreate,
    ContactUpdate,
    DealCreate,
    DealUpdate,
    ExecutionTaskTransition,
    FollowupCreate,
    FollowupUpdate,
    MarketAgencyDto,
    MarketOpportunityDto,
    MarketSignalDto,
    OutreachDraftCreate,
)
from src.server.utils import TokenChecker, is_admin_user


APPROVAL_EXECUTION = {
    "research_focus": ("research_agent", "research"),
    "create_lead": ("crm_agent", "lead_qualification"),
    "demo": ("code_agent", "demo_design"),
    "follow_up": ("user", "manual_external"),
    "outreach": ("user", "manual_external"),
    "platform_application": ("user", "manual_external"),
}
APPROVAL_TRANSITIONS = {
    "draft": {"pending_approval", "cancelled"},
    "pending_approval": {"approved_not_executed", "returned_for_revision", "rejected", "cancelled"},
    "returned_for_revision": {"pending_approval", "cancelled"},
    "approved_not_executed": {"executed_confirmed", "cancelled"},
    "executed_confirmed": set(),
    "rejected": set(),
    "cancelled": set(),
}
TASK_TRANSITIONS = {
    "queued": {"in_progress", "cancelled"},
    "in_progress": {"completed", "cancelled"},
    "completed": set(),
    "cancelled": set(),
}


def _utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _response(status=200, message="success", data=None):
    return ApiCommonResponseDTO(status=status, message=message, data=data if data is not None else {}).model_dict()


def _authorize(token_checker):
    if not token_checker:
        return None, _response(401, "auth.required")
    if not is_admin_user(token_checker):
        return None, _response(403, "auth.adminRequired")
    return str(get_crm_owner_id()), None


def _failure(error, operation):
    logger.exception("CRM %s failed: %s", operation, error)
    return _response(500, "crm.unavailable")


def _dump_rows(model, rows):
    return [model.model_validate(row).model_dump(mode="json") for row in rows]


def get_crm_health(token_checker: TokenChecker):
    owner_user_id, denied = _authorize(token_checker)
    if denied:
        return denied
    del owner_user_id
    checks = {"crm_data": "ok", "market_source": "ok"}
    try:
        crm_repository.check_crm_database()
    except Exception as error:
        logger.exception("CRM database health check failed: %s", error)
        checks["crm_data"] = "unavailable"
    try:
        market_repository.check_market_database()
    except Exception as error:
        logger.exception("Market database health check failed: %s", error)
        checks["market_source"] = "unavailable"
    if "unavailable" in checks.values():
        return _response(500, "crm.healthFailed", {"checks": checks})
    return _response(data={"checks": checks})


def get_dashboard(token_checker: TokenChecker):
    owner_user_id, denied = _authorize(token_checker)
    if denied:
        return denied
    try:
        return _response(data={
            "market_metrics": market_repository.get_market_dashboard_from_db(),
            "crm_metrics": crm_repository.get_crm_dashboard_from_db(owner_user_id),
            "opportunities": _dump_rows(MarketOpportunityDto, market_repository.list_market_opportunities_from_db()),
            "companies": crm_repository.list_companies_from_db(owner_user_id),
            "approvals": crm_repository.list_approvals_from_db(owner_user_id),
            "tasks": crm_repository.list_execution_tasks_from_db(owner_user_id),
            "activities": crm_repository.list_activities_from_db(owner_user_id, 50),
        })
    except Exception as error:
        return _failure(error, "dashboard")


def get_market_dashboard(token_checker: TokenChecker):
    owner_user_id, denied = _authorize(token_checker)
    if denied:
        return denied
    del owner_user_id
    try:
        return _response(data=market_repository.get_market_dashboard_from_db())
    except Exception as error:
        return _failure(error, "market dashboard")


def get_market_opportunities(token_checker: TokenChecker):
    owner_user_id, denied = _authorize(token_checker)
    if denied:
        return denied
    del owner_user_id
    try:
        rows = market_repository.list_market_opportunities_from_db()
        return _response(data={"items": _dump_rows(MarketOpportunityDto, rows), "total": len(rows)})
    except Exception as error:
        return _failure(error, "list market opportunities")


def get_market_opportunity(opportunity_id: str, token_checker: TokenChecker):
    owner_user_id, denied = _authorize(token_checker)
    if denied:
        return denied
    try:
        row = market_repository.get_market_opportunity_from_db(opportunity_id)
        if not row:
            return _response(404, "crm.marketOpportunityNotFound")
        data = MarketOpportunityDto.model_validate(row).model_dump(mode="json")
        data["crm"] = {
            "deals": [item for item in crm_repository.list_deals_from_db(owner_user_id) if item.get("market_opportunity_id") == opportunity_id],
            "approvals": [item for item in crm_repository.list_approvals_from_db(owner_user_id) if item.get("market_opportunity_id") == opportunity_id],
        }
        return _response(data=data)
    except Exception as error:
        return _failure(error, "get market opportunity")


def get_market_signals(token_checker: TokenChecker):
    owner_user_id, denied = _authorize(token_checker)
    if denied:
        return denied
    del owner_user_id
    try:
        rows = market_repository.list_market_signals_from_db()
        return _response(data={"items": _dump_rows(MarketSignalDto, rows), "total": len(rows)})
    except Exception as error:
        return _failure(error, "list market signals")


def get_market_signal(signal_id: str, token_checker: TokenChecker):
    owner_user_id, denied = _authorize(token_checker)
    if denied:
        return denied
    del owner_user_id
    try:
        row = market_repository.get_market_signal_from_db(signal_id)
        if not row:
            return _response(404, "crm.marketSignalNotFound")
        return _response(data=MarketSignalDto.model_validate(row).model_dump(mode="json"))
    except Exception as error:
        return _failure(error, "get market signal")


def get_market_agencies(token_checker: TokenChecker):
    owner_user_id, denied = _authorize(token_checker)
    if denied:
        return denied
    del owner_user_id
    try:
        rows = market_repository.list_market_agencies_from_db()
        return _response(data={"items": _dump_rows(MarketAgencyDto, rows), "total": len(rows)})
    except Exception as error:
        return _failure(error, "list market agencies")


def get_market_research_runs(token_checker: TokenChecker):
    owner_user_id, denied = _authorize(token_checker)
    if denied:
        return denied
    del owner_user_id
    try:
        return _response(data={"items": market_repository.list_market_research_runs_from_db()})
    except Exception as error:
        return _failure(error, "list market research runs")


def get_market_publication(token_checker: TokenChecker):
    owner_user_id, denied = _authorize(token_checker)
    if denied:
        return denied
    del owner_user_id
    try:
        return _response(data=market_repository.get_market_publication_from_db())
    except Exception as error:
        return _failure(error, "get market publication")


def get_companies(token_checker: TokenChecker):
    owner_user_id, denied = _authorize(token_checker)
    if denied:
        return denied
    try:
        return _response(data={"items": crm_repository.list_companies_from_db(owner_user_id)})
    except Exception as error:
        return _failure(error, "list companies")


def get_company(company_id: int, token_checker: TokenChecker):
    owner_user_id, denied = _authorize(token_checker)
    if denied:
        return denied
    try:
        row = crm_repository.get_company_from_db(owner_user_id, company_id)
        return _response(data=row) if row else _response(404, "crm.companyNotFound")
    except Exception as error:
        return _failure(error, "get company")


def create_company(payload: CompanyCreate, token_checker: TokenChecker):
    owner_user_id, denied = _authorize(token_checker)
    if denied:
        return denied
    try:
        return _response(data=crm_repository.create_company_in_db(owner_user_id, payload.model_dump()))
    except Exception as error:
        return _failure(error, "create company")


def update_company(company_id: int, payload: CompanyUpdate, token_checker: TokenChecker):
    owner_user_id, denied = _authorize(token_checker)
    if denied:
        return denied
    try:
        row = crm_repository.update_company_in_db(owner_user_id, company_id, payload.model_dump(exclude_unset=True))
        return _response(data=row) if row else _response(404, "crm.companyNotFound")
    except Exception as error:
        return _failure(error, "update company")


def get_contacts(token_checker: TokenChecker, company_id: int | None = None):
    owner_user_id, denied = _authorize(token_checker)
    if denied:
        return denied
    try:
        return _response(data={"items": crm_repository.list_contacts_from_db(owner_user_id, company_id)})
    except Exception as error:
        return _failure(error, "list contacts")


def create_contact(payload: ContactCreate, token_checker: TokenChecker):
    owner_user_id, denied = _authorize(token_checker)
    if denied:
        return denied
    try:
        row = crm_repository.create_contact_in_db(owner_user_id, payload.model_dump())
        return _response(data=row) if row else _response(400, "crm.companyNotFound")
    except Exception as error:
        return _failure(error, "create contact")


def update_contact(contact_id: int, payload: ContactUpdate, token_checker: TokenChecker):
    owner_user_id, denied = _authorize(token_checker)
    if denied:
        return denied
    try:
        row = crm_repository.update_contact_in_db(owner_user_id, contact_id, payload.model_dump(exclude_unset=True))
        return _response(data=row) if row else _response(404, "crm.contactNotFound")
    except Exception as error:
        return _failure(error, "update contact")


def get_deals(token_checker: TokenChecker, company_id: int | None = None):
    owner_user_id, denied = _authorize(token_checker)
    if denied:
        return denied
    try:
        return _response(data={"items": crm_repository.list_deals_from_db(owner_user_id, company_id)})
    except Exception as error:
        return _failure(error, "list deals")


def create_deal(payload: DealCreate, token_checker: TokenChecker):
    owner_user_id, denied = _authorize(token_checker)
    if denied:
        return denied
    try:
        row = crm_repository.create_deal_in_db(owner_user_id, payload.model_dump())
        return _response(data=row) if row else _response(400, "crm.invalidCompanyOrContact")
    except Exception as error:
        return _failure(error, "create deal")


def update_deal(deal_id: int, payload: DealUpdate, token_checker: TokenChecker):
    owner_user_id, denied = _authorize(token_checker)
    if denied:
        return denied
    try:
        row = crm_repository.update_deal_in_db(owner_user_id, deal_id, payload.model_dump(exclude_unset=True))
        return _response(data=row) if row else _response(404, "crm.dealNotFound")
    except Exception as error:
        return _failure(error, "update deal")


def get_activities(token_checker: TokenChecker):
    owner_user_id, denied = _authorize(token_checker)
    if denied:
        return denied
    try:
        return _response(data={"items": crm_repository.list_activities_from_db(owner_user_id)})
    except Exception as error:
        return _failure(error, "list activities")


def create_activity(payload: ActivityCreate, token_checker: TokenChecker):
    owner_user_id, denied = _authorize(token_checker)
    if denied:
        return denied
    try:
        return _response(data=crm_repository.create_activity_in_db(owner_user_id, payload.model_dump()))
    except Exception as error:
        return _failure(error, "create activity")


def get_outreach_drafts(token_checker: TokenChecker):
    owner_user_id, denied = _authorize(token_checker)
    if denied:
        return denied
    try:
        return _response(data={"items": crm_repository.list_outreach_drafts_from_db(owner_user_id)})
    except Exception as error:
        return _failure(error, "list outreach drafts")


def create_outreach_draft(payload: OutreachDraftCreate, token_checker: TokenChecker):
    owner_user_id, denied = _authorize(token_checker)
    if denied:
        return denied
    try:
        row = crm_repository.create_outreach_draft_in_db(owner_user_id, payload.model_dump())
        return _response(data=row) if row else _response(400, "crm.contactNotFound")
    except Exception as error:
        return _failure(error, "create outreach draft")


def get_followups(token_checker: TokenChecker):
    owner_user_id, denied = _authorize(token_checker)
    if denied:
        return denied
    try:
        return _response(data={"items": crm_repository.list_followups_from_db(owner_user_id)})
    except Exception as error:
        return _failure(error, "list followups")


def create_followup(payload: FollowupCreate, token_checker: TokenChecker):
    owner_user_id, denied = _authorize(token_checker)
    if denied:
        return denied
    try:
        return _response(data=crm_repository.create_followup_in_db(owner_user_id, payload.model_dump()))
    except Exception as error:
        return _failure(error, "create followup")


def update_followup(followup_id: int, payload: FollowupUpdate, token_checker: TokenChecker):
    owner_user_id, denied = _authorize(token_checker)
    if denied:
        return denied
    try:
        row = crm_repository.update_followup_in_db(owner_user_id, followup_id, payload.model_dump(exclude_unset=True))
        return _response(data=row) if row else _response(404, "crm.followupNotFound")
    except Exception as error:
        return _failure(error, "update followup")


def _external_gate(owner_user_id, payload):
    if payload.request_type not in {"outreach", "platform_application"}:
        return None
    if not payload.company_id or not payload.contact_id:
        return "crm.externalCompanyContactRequired"
    company = crm_repository.get_company_from_db(owner_user_id, payload.company_id)
    contact = crm_repository.get_contact_from_db(owner_user_id, payload.contact_id)
    if not company or not contact or contact.get("company_id") != payload.company_id:
        return "crm.invalidCompanyOrContact"
    if company.get("status") != "qualified" or not company.get("value_hypothesis") or not company.get("source_url"):
        return "crm.externalCompanyNotQualified"
    has_public_channel = bool(contact.get("email") or contact.get("platform_profile_url") or contact.get("linkedin_url"))
    if contact.get("verification_status") != "verified" or not contact.get("source_url") or not has_public_channel:
        return "crm.externalContactNotVerified"
    if not payload.action_pack.strip():
        return "crm.externalActionPackRequired"
    return None


def get_approvals(token_checker: TokenChecker):
    owner_user_id, denied = _authorize(token_checker)
    if denied:
        return denied
    try:
        return _response(data={"items": crm_repository.list_approvals_from_db(owner_user_id)})
    except Exception as error:
        return _failure(error, "list approvals")


def create_approval(payload: ApprovalCreate, token_checker: TokenChecker):
    owner_user_id, denied = _authorize(token_checker)
    if denied:
        return denied
    try:
        gate_error = _external_gate(owner_user_id, payload)
        if gate_error:
            return _response(400, gate_error)
        execution_owner, execution_kind = APPROVAL_EXECUTION[payload.request_type]
        values = payload.model_dump(exclude={"evidence", "constraints"})
        values.update({
            "id": f"APR-{uuid.uuid4().hex[:12].upper()}",
            "evidence_json": payload.evidence,
            "constraints_text": payload.constraints,
            "execution_owner": execution_owner,
            "execution_kind": execution_kind,
        })
        return _response(data=crm_repository.create_approval_in_db(owner_user_id, values))
    except Exception as error:
        return _failure(error, "create approval")


def decide_approval(approval_id: str, payload: ApprovalDecision, token_checker: TokenChecker):
    owner_user_id, denied = _authorize(token_checker)
    if denied:
        return denied
    try:
        current = crm_repository.get_approval_from_db(owner_user_id, approval_id)
        if not current:
            return _response(404, "crm.approvalNotFound")
        if payload.status not in APPROVAL_TRANSITIONS.get(current["status"], set()):
            return _response(400, "crm.invalidApprovalTransition", {
                "current_status": current["status"], "requested_status": payload.status,
            })
        is_external = current["execution_kind"] == "manual_external"
        if payload.status == "executed_confirmed":
            if not is_external:
                return _response(400, "crm.internalExecutionUsesTask")
            if not payload.output_note or not payload.output_refs:
                return _response(400, "crm.externalResultRequired")
        now = _utcnow()
        values = {
            "status": payload.status,
            "decision_note": payload.note,
            "output_note": payload.output_note,
            "output_refs": payload.output_refs or None,
        }
        if payload.status in {"approved_not_executed", "returned_for_revision", "rejected", "cancelled"}:
            values["decided_at"] = now
        if payload.status == "executed_confirmed":
            values["started_at"] = current.get("started_at") or now
            values["completed_at"] = now
        task_values = None
        if payload.status == "approved_not_executed" and not is_external:
            task_values = {
                "task_id": f"TASK-{uuid.uuid4().hex[:12].upper()}",
                "approval_id": approval_id,
                "execution_owner": current["execution_owner"],
                "execution_kind": current["execution_kind"],
                "task_status": "queued",
                "title": current["title"],
                "action_pack": current["action_pack"],
            }
        result = crm_repository.transition_approval_in_db(
            owner_user_id, approval_id, current["status"], values, task_values
        )
        return _response(data=result) if result else _response(409, "crm.approvalChanged")
    except Exception as error:
        return _failure(error, "decide approval")


def get_execution_tasks(token_checker: TokenChecker):
    owner_user_id, denied = _authorize(token_checker)
    if denied:
        return denied
    try:
        return _response(data={"items": crm_repository.list_execution_tasks_from_db(owner_user_id)})
    except Exception as error:
        return _failure(error, "list execution tasks")


def transition_execution_task(task_id: str, payload: ExecutionTaskTransition, token_checker: TokenChecker):
    owner_user_id, denied = _authorize(token_checker)
    if denied:
        return denied
    try:
        current = crm_repository.get_execution_task_from_db(owner_user_id, task_id)
        if not current:
            return _response(404, "crm.taskNotFound")
        if payload.status not in TASK_TRANSITIONS.get(current["task_status"], set()):
            return _response(400, "crm.invalidTaskTransition", {
                "current_status": current["task_status"], "requested_status": payload.status,
            })
        if payload.status == "completed" and (not payload.output_note or not payload.output_refs):
            return _response(400, "crm.taskResultRequired")
        now = _utcnow()
        values = {
            "task_status": payload.status,
            "output_note": payload.output_note,
            "output_refs": payload.output_refs or None,
        }
        if payload.status == "in_progress":
            values["started_at"] = now
        if payload.status == "completed":
            values["completed_at"] = now
            values["started_at"] = current.get("started_at") or now
        result = crm_repository.transition_execution_task_in_db(
            owner_user_id, task_id, current["task_status"], values
        )
        return _response(data=result) if result else _response(409, "crm.taskChanged")
    except Exception as error:
        return _failure(error, "transition execution task")
