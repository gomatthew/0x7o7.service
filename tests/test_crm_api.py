# -*- coding: utf-8 -*-
from datetime import datetime

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.server import create_app
from src.server.db import crm_base
from src.server.db.models import crm_model  # noqa: F401
from src.server.dto.crm_dto import MarketOpportunityDto
from src.server.service import crm_service
from src.server.utils import token_identify


def market_source(source_id="SRC-1"):
    return {
        "source_id": source_id,
        "canonical_url": "https://example.com/source",
        "source_type": "official",
        "title": "Verified source",
        "published_at": "2026-08-01",
        "last_verified_at": "2026-08-20T00:00:00",
        "access_status": "accessible",
        "fact_summary": "Verified source fact",
    }


def market_signal(signal_id="SIG-1", link_type="direct_demand"):
    return {
        "signal_id": signal_id,
        "subject_name": "Northstar",
        "subject_type": "company",
        "source_date": "2026-08-01",
        "fact_description": "A verified workflow demand",
        "agent_inference": "A delivery opportunity may exist",
        "workflow_problem": "Manual document review",
        "commercial_signal": "Public buying request",
        "evidence_level": "high",
        "research_status": "verified",
        "last_verified_at": "2026-08-20T00:00:00",
        "data_version": "v4",
        "source": market_source(),
        "link_type": link_type,
    }


def market_opportunity(index=1, qualified=True):
    return {
        "opportunity_id": f"O-{index:03d}",
        "title": f"Opportunity {index}",
        "target_buyer": "Operations lead",
        "buyer_role": "Director",
        "workflow_problem": "Manual document review",
        "commercial_signal": "Public buying request",
        "delivery_fit": "Source-cited pilot",
        "evidence_level": "high",
        "research_status": "qualified_opportunity" if qualified else "needs_research",
        "blocking_questions": "Confirm budget",
        "fact_description": "A verified workflow demand",
        "agent_inference": "A delivery opportunity may exist",
        "source_date": "2026-08-01",
        "first_discovered_at": "2026-08-02T00:00:00",
        "last_verified_at": "2026-08-20T00:00:00",
        "data_version": "v4",
        "no_auto_outreach": True,
        "primary_source": market_source(),
        "linked_signals": [market_signal()] if index == 1 else [],
    }


def build_client(monkeypatch, token="admin"):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    crm_base.CRMBase.metadata.create_all(engine)
    testing_session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    monkeypatch.setattr(crm_base, "CRMSessionLocal", testing_session)
    monkeypatch.setattr(crm_service, "is_admin_user", lambda user_id: user_id == "admin")
    monkeypatch.setattr(crm_service, "get_crm_owner_id", lambda: "owner-1")

    opportunities = [market_opportunity(i, i <= 4) for i in range(1, 8)]
    monkeypatch.setattr(crm_service.market_repository, "check_market_database", lambda: True)
    monkeypatch.setattr(crm_service.market_repository, "get_market_dashboard_from_db", lambda: {
        "source_count": 36, "signal_count": 26, "opportunity_count": 7,
        "qualified_opportunity_count": 4, "agency_count": 10,
        "brief_count": 2, "research_run_count": 4,
    })
    monkeypatch.setattr(crm_service.market_repository, "list_market_opportunities_from_db", lambda: opportunities)
    monkeypatch.setattr(
        crm_service.market_repository,
        "get_market_opportunity_from_db",
        lambda opportunity_id: next((row for row in opportunities if row["opportunity_id"] == opportunity_id), None),
    )
    monkeypatch.setattr(crm_service.market_repository, "list_market_signals_from_db", lambda: [market_signal()])
    monkeypatch.setattr(crm_service.market_repository, "get_market_signal_from_db", lambda signal_id: market_signal(signal_id))
    monkeypatch.setattr(crm_service.market_repository, "list_market_agencies_from_db", lambda: [])
    monkeypatch.setattr(crm_service.market_repository, "list_market_research_runs_from_db", lambda: [])
    monkeypatch.setattr(crm_service.market_repository, "get_market_publication_from_db", lambda: {"publication": None, "research_import": None})

    app = create_app()
    app.dependency_overrides[token_identify] = lambda: token
    return TestClient(app)


def test_crm_authentication_and_admin_required(monkeypatch):
    anonymous = build_client(monkeypatch, token=None)
    assert anonymous.get("/crm/dashboard").json()["status"] == 401

    member = build_client(monkeypatch, token="member")
    assert member.get("/crm/dashboard").json()["status"] == 403

    admin = build_client(monkeypatch)
    response = admin.get("/crm/dashboard").json()
    assert response["status"] == 200
    assert response["data"]["market_metrics"]["opportunity_count"] == 7


def test_market_api_uses_current_schema_and_detail_links(monkeypatch):
    client = build_client(monkeypatch)
    listing = client.get("/crm/market/opportunities").json()
    assert listing["status"] == 200
    assert listing["data"]["total"] == 7
    assert sum(item["research_status"] == "qualified_opportunity" for item in listing["data"]["items"]) == 4
    assert "priority" not in listing["data"]["items"][0]

    detail = client.get("/crm/market/opportunities/O-001").json()["data"]
    MarketOpportunityDto.model_validate(detail)
    assert detail["primary_source"]["canonical_url"] == "https://example.com/source"
    assert detail["linked_signals"][0]["link_type"] == "direct_demand"


def create_qualified_company_and_contact(client):
    company = client.post("/crm/companies", json={
        "name": "Northstar Operations",
        "website": "https://northstar.example",
        "status": "qualified",
        "source_url": "https://northstar.example/about",
        "value_hypothesis": "Reduce manual review time",
    }).json()["data"]
    contact = client.post("/crm/contacts", json={
        "company_id": company["id"],
        "full_name": "Avery Chen",
        "email": "avery@northstar.example",
        "verification_status": "verified",
        "source_url": "https://northstar.example/team",
    }).json()["data"]
    return company, contact


def test_external_action_is_manual_and_requires_result(monkeypatch):
    client = build_client(monkeypatch)
    company, contact = create_qualified_company_and_contact(client)
    approval = client.post("/crm/approvals", json={
        "request_type": "outreach",
        "subject": "Opportunity 1",
        "market_opportunity_id": "O-001",
        "company_id": company["id"],
        "contact_id": contact["id"],
        "title": "Manual outreach review",
        "action_pack": "User reviews and sends the approved copy manually",
    }).json()["data"]
    assert approval["execution_owner"] == "user"
    assert approval["execution_kind"] == "manual_external"

    approved = client.post(f"/crm/approvals/{approval['id']}/decision", json={
        "status": "approved_not_executed", "note": "Approved for manual use",
    }).json()
    assert approved["status"] == 200
    assert approved["data"]["task"] is None

    missing_result = client.post(f"/crm/approvals/{approval['id']}/decision", json={
        "status": "executed_confirmed", "output_note": "Sent manually",
    }).json()
    assert missing_result["status"] == 400

    completed = client.post(f"/crm/approvals/{approval['id']}/decision", json={
        "status": "executed_confirmed",
        "output_note": "Sent manually by the user",
        "output_refs": ["external-receipt-42"],
    }).json()
    assert completed["status"] == 200
    assert completed["data"]["approval"]["status"] == "executed_confirmed"


def test_internal_task_state_machine_requires_completion_result(monkeypatch):
    client = build_client(monkeypatch)
    approval = client.post("/crm/approvals", json={
        "request_type": "research_focus",
        "subject": "Opportunity 1",
        "market_opportunity_id": "O-001",
        "title": "Research blocking questions",
        "action_pack": "Verify budget and decision owner",
    }).json()["data"]
    decision = client.post(f"/crm/approvals/{approval['id']}/decision", json={
        "status": "approved_not_executed",
    }).json()
    task = decision["data"]["task"]
    assert task["execution_owner"] == "research_agent"

    illegal = client.post(f"/crm/tasks/{task['task_id']}/transition", json={"status": "completed"}).json()
    assert illegal["status"] == 400

    started = client.post(f"/crm/tasks/{task['task_id']}/transition", json={"status": "in_progress"}).json()
    assert started["status"] == 200

    missing_result = client.post(f"/crm/tasks/{task['task_id']}/transition", json={"status": "completed"}).json()
    assert missing_result["status"] == 400

    completed = client.post(f"/crm/tasks/{task['task_id']}/transition", json={
        "status": "completed",
        "output_note": "Budget evidence verified",
        "output_refs": ["SRC-1"],
    }).json()
    assert completed["status"] == 200
    assert completed["data"]["approval"]["status"] == "executed_confirmed"


def test_owner_isolation(monkeypatch):
    client = build_client(monkeypatch)
    created = client.post("/crm/companies", json={"name": "Owner One"}).json()["data"]
    assert created["owner_user_id"] == "owner-1"
    assert len(client.get("/crm/companies").json()["data"]["items"]) == 1

    monkeypatch.setattr(crm_service, "get_crm_owner_id", lambda: "owner-2")
    assert client.get("/crm/companies").json()["data"]["items"] == []


def test_market_configuration_error_does_not_break_main_health(monkeypatch):
    client = build_client(monkeypatch)

    def unavailable_market():
        raise RuntimeError("MARKET_SOURCE_DATABASE_URL is not configured")

    monkeypatch.setattr(crm_service.market_repository, "get_market_dashboard_from_db", unavailable_market)
    response = client.get("/crm/market/dashboard").json()
    assert response["status"] == 500
    assert response["message"] == "crm.unavailable"
    assert client.get("/health/live").json()["status"] == "ok"
