from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from src.server.crm_db.base import get_crm_db
from src.server.dto.crm_dto import (
    ActivityCreate,
    CompanyCreate,
    CompanyUpdate,
    ContactCreate,
    ContactUpdate,
    DealCreate,
    DealUpdate,
    DraftDecision,
    FollowupCreate,
    FollowupUpdate,
    OutreachDraftCreate,
)
from src.server.dto.response_dto import ApiCommonResponseDTO
from src.server.service import crm_service


crm_router = APIRouter(prefix="/crm", tags=["CRM"])


def ok(data):
    return ApiCommonResponseDTO(status=200, message="success", data=data).model_dict()


@crm_router.get("/health", include_in_schema=False)
def crm_health(session: Session = Depends(get_crm_db)):
    session.execute(text("SELECT 1"))
    return ok({"database": "ok"})


@crm_router.get("/dashboard")
def get_dashboard(
    owner_user_id: str = Depends(crm_service.require_crm_admin),
    session: Session = Depends(get_crm_db),
):
    return ok(crm_service.dashboard(session, owner_user_id))


@crm_router.get("/companies")
def get_companies(
    owner_user_id: str = Depends(crm_service.require_crm_admin),
    session: Session = Depends(get_crm_db),
):
    return ok(crm_service.list_companies(session, owner_user_id))


@crm_router.post("/companies")
def post_company(
    payload: CompanyCreate,
    owner_user_id: str = Depends(crm_service.require_crm_admin),
    session: Session = Depends(get_crm_db),
):
    return ok(crm_service.create_company(session, owner_user_id, payload))


@crm_router.patch("/companies/{company_id}")
def patch_company(
    company_id: int,
    payload: CompanyUpdate,
    owner_user_id: str = Depends(crm_service.require_crm_admin),
    session: Session = Depends(get_crm_db),
):
    return ok(crm_service.update_company(session, owner_user_id, company_id, payload))


@crm_router.get("/contacts")
def get_contacts(
    owner_user_id: str = Depends(crm_service.require_crm_admin),
    session: Session = Depends(get_crm_db),
):
    return ok(crm_service.list_contacts(session, owner_user_id))


@crm_router.post("/contacts")
def post_contact(
    payload: ContactCreate,
    owner_user_id: str = Depends(crm_service.require_crm_admin),
    session: Session = Depends(get_crm_db),
):
    return ok(crm_service.create_contact(session, owner_user_id, payload))


@crm_router.patch("/contacts/{contact_id}")
def patch_contact(
    contact_id: int,
    payload: ContactUpdate,
    owner_user_id: str = Depends(crm_service.require_crm_admin),
    session: Session = Depends(get_crm_db),
):
    return ok(crm_service.update_contact(session, owner_user_id, contact_id, payload))


@crm_router.get("/deals")
def get_deals(
    owner_user_id: str = Depends(crm_service.require_crm_admin),
    session: Session = Depends(get_crm_db),
):
    return ok(crm_service.list_deals(session, owner_user_id))


@crm_router.post("/deals")
def post_deal(
    payload: DealCreate,
    owner_user_id: str = Depends(crm_service.require_crm_admin),
    session: Session = Depends(get_crm_db),
):
    return ok(crm_service.create_deal(session, owner_user_id, payload))


@crm_router.patch("/deals/{deal_id}")
def patch_deal(
    deal_id: int,
    payload: DealUpdate,
    owner_user_id: str = Depends(crm_service.require_crm_admin),
    session: Session = Depends(get_crm_db),
):
    return ok(crm_service.update_deal(session, owner_user_id, deal_id, payload))


@crm_router.get("/activities")
def get_activities(
    owner_user_id: str = Depends(crm_service.require_crm_admin),
    session: Session = Depends(get_crm_db),
):
    return ok(crm_service.list_activities(session, owner_user_id))


@crm_router.post("/activities")
def post_activity(
    payload: ActivityCreate,
    owner_user_id: str = Depends(crm_service.require_crm_admin),
    session: Session = Depends(get_crm_db),
):
    return ok(crm_service.create_activity(session, owner_user_id, payload))


@crm_router.get("/outreach-drafts")
def get_outreach_drafts(
    owner_user_id: str = Depends(crm_service.require_crm_admin),
    session: Session = Depends(get_crm_db),
):
    return ok(crm_service.list_drafts(session, owner_user_id))


@crm_router.post("/outreach-drafts")
def post_outreach_draft(
    payload: OutreachDraftCreate,
    owner_user_id: str = Depends(crm_service.require_crm_admin),
    session: Session = Depends(get_crm_db),
):
    return ok(crm_service.create_draft(session, owner_user_id, payload))


@crm_router.post("/outreach-drafts/{draft_id}/{action}")
def decide_outreach_draft(
    draft_id: int,
    action: str,
    payload: DraftDecision,
    owner_user_id: str = Depends(crm_service.require_crm_admin),
    session: Session = Depends(get_crm_db),
):
    return ok(crm_service.transition_draft(session, owner_user_id, draft_id, action, payload.note))


@crm_router.get("/followups")
def get_followups(
    owner_user_id: str = Depends(crm_service.require_crm_admin),
    session: Session = Depends(get_crm_db),
):
    return ok(crm_service.list_followups(session, owner_user_id))


@crm_router.post("/followups")
def post_followup(
    payload: FollowupCreate,
    owner_user_id: str = Depends(crm_service.require_crm_admin),
    session: Session = Depends(get_crm_db),
):
    return ok(crm_service.create_followup(session, owner_user_id, payload))


@crm_router.patch("/followups/{task_id}")
def patch_followup(
    task_id: int,
    payload: FollowupUpdate,
    owner_user_id: str = Depends(crm_service.require_crm_admin),
    session: Session = Depends(get_crm_db),
):
    return ok(crm_service.update_followup(session, owner_user_id, task_id, payload))
