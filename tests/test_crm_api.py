from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from src.server import create_app
from src.server.crm_db.base import CRMBase, get_crm_db
from src.server.service.crm_service import require_crm_admin


def build_client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    CRMBase.metadata.create_all(engine)
    testing_session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    app = create_app()

    def override_db():
        session = testing_session()
        try:
            yield session
            session.commit()
        except BaseException:
            session.rollback()
            raise
        finally:
            session.close()

    app.dependency_overrides[get_crm_db] = override_db
    app.dependency_overrides[require_crm_admin] = lambda: "test-admin"
    return TestClient(app)


def test_crm_pipeline_and_dashboard():
    client = build_client()
    company = client.post(
        "/crm/companies",
        json={
            "name": "Northstar Operations",
            "website": "https://northstar.example",
            "fit_score": 92,
            "status": "qualified",
            "buying_signal": "Support team is building a knowledge base",
        },
    ).json()["data"]
    contact = client.post(
        "/crm/contacts",
        json={
            "company_id": company["id"],
            "full_name": "Avery Chen",
            "role": "Founder",
            "preferred_channel": "linkedin",
        },
    ).json()["data"]
    deal = client.post(
        "/crm/deals",
        json={
            "company_id": company["id"],
            "contact_id": contact["id"],
            "title": "Source-cited support pilot",
            "stage": "proposal",
            "amount": 1500,
            "probability": 60,
            "expected_close_date": "2026-08-31",
        },
    ).json()["data"]
    assert deal["amount"] == 1500

    dashboard = client.get("/crm/dashboard").json()["data"]
    assert dashboard["metrics"]["companies"] == 1
    assert dashboard["metrics"]["contacts"] == 1
    assert dashboard["metrics"]["active_deals"] == 1
    assert dashboard["metrics"]["pipeline_amount"] == 1500
    assert dashboard["metrics"]["weighted_pipeline"] == 900


def test_outreach_requires_explicit_approval_and_has_no_send_transition():
    client = build_client()
    company_id = client.post(
        "/crm/companies", json={"name": "Acme", "fit_score": 80}
    ).json()["data"]["id"]
    contact_id = client.post(
        "/crm/contacts", json={"company_id": company_id, "full_name": "Taylor Lee"}
    ).json()["data"]["id"]
    draft = client.post(
        "/crm/outreach-drafts",
        json={"contact_id": contact_id, "channel": "email", "body": "A reviewed outreach draft"},
    ).json()["data"]

    direct_approval = client.post(
        f"/crm/outreach-drafts/{draft['id']}/approve", json={"note": "too early"}
    )
    assert direct_approval.status_code == 409

    pending = client.post(
        f"/crm/outreach-drafts/{draft['id']}/request-approval", json={"note": "review"}
    ).json()["data"]
    assert pending["status"] == "pending_approval"

    approved = client.post(
        f"/crm/outreach-drafts/{draft['id']}/approve", json={"note": "confirmed by user"}
    ).json()["data"]
    assert approved["status"] == "approved"
    assert approved["sent_at"] is None

    no_send = client.post(
        f"/crm/outreach-drafts/{draft['id']}/send", json={"note": "not supported"}
    )
    assert no_send.status_code == 400
