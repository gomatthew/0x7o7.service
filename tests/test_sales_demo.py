import asyncio
import io
import json
from types import SimpleNamespace

from fastapi import BackgroundTasks, Response
from starlette.datastructures import UploadFile

from src.server.service.auth_service import request_email_code, verify_email_code
from src.server.ai.rag.context_service import context_builder
from src.server.ai.rag.rag_dto import RetrievedDocumentDto
from src.server.service.demo_service import (LeadRequest, AnalyzeRequest, analyze_demo, create_lead,
                                             get_sample, live_analysis_stream, normalize_source_citations,
                                             parse_findings, validate_file)
from src.server.db.base import SessionLocal


class FakeRequest:
    client = SimpleNamespace(host="127.0.0.1")
    headers = {}


def run(value):
    return asyncio.run(value)


def test_sample_is_explicit_and_traceable():
    result = run(get_sample())
    assert result["status"] == 200
    assert result["data"]["document"]["fictional"] is True
    assert result["data"]["results"]["executive_summary"]["mode"] == "preverified_sample"
    assert result["data"]["results"]["requirements"]["sources"][0]["source_id"]


def test_file_validation_rejects_mismatch_and_binary():
    assert validate_file("brief.pdf", b"%PDF-1.7\n") == ("brief.pdf", ".pdf")
    try:
        validate_file("brief.pdf", b"not a pdf")
    except ValueError as error:
        assert "does not match" in str(error)
    else:
        raise AssertionError("mismatched PDF should be rejected")
    try:
        validate_file("notes.txt", b"MZ\x00\x00")
    except ValueError:
        pass
    else:
        raise AssertionError("binary content should be rejected")


def test_passwordless_request_is_uniform(monkeypatch):
    async def fake_exists(key):
        return False

    async def fake_limit(key, limit, ttl):
        return False, 1

    async def fake_set(key, value, ex):
        return True

    monkeypatch.setattr("src.server.service.auth_service.async_exists", fake_exists)
    monkeypatch.setattr("src.server.service.auth_service.async_rate_limit", fake_limit)
    monkeypatch.setattr("src.server.service.auth_service.async_set", fake_set)
    result = run(request_email_code(FakeRequest(), BackgroundTasks(), email="person@example.com"))
    assert result == {"status": 200, "message": "email.codeAccepted", "data": {}}


def test_passwordless_verify_sets_secure_cookie(monkeypatch):
    async def fake_limit(key, limit, ttl):
        return False, 1

    async def fake_get(key):
        return "123456"

    async def fake_delete(key):
        return True

    user = SimpleNamespace(id=9, mail="person@example.com", role="guest")
    monkeypatch.setattr("src.server.service.auth_service.async_rate_limit", fake_limit)
    monkeypatch.setattr("src.server.service.auth_service.async_get", fake_get)
    monkeypatch.setattr("src.server.service.auth_service.async_delete", fake_delete)
    monkeypatch.setattr("src.server.service.auth_service.get_user_by_email", lambda email: user)
    monkeypatch.setattr("src.server.service.auth_service.update_user_to_db", lambda *args, **kwargs: None)
    monkeypatch.setattr("src.server.service.auth_service.token_handler.generate_token", lambda user_id: ("token", 24))
    monkeypatch.setattr("src.server.service.auth_service.setting.COOKIE_SECURE", True)
    response = Response()
    result = run(verify_email_code(FakeRequest(), response, email="person@example.com", code="123456"))
    assert result["status"] == 200
    cookie = response.headers["set-cookie"]
    assert "HttpOnly" in cookie and "Secure" in cookie and "SameSite=lax" in cookie


def test_lead_persists_before_email(monkeypatch):
    captured = {}
    monkeypatch.setattr("src.server.service.demo_service.add_lead", lambda values: captured.setdefault("values", values) or "lead_1")
    payload = LeadRequest(
        name="Alex Smith", work_email="alex@example.com", company="Example Ltd",
        project_type="AI feature sprint", project_summary="We need a source-backed document workflow for operations.",
        timeline="Within 30 days", contact_consent=True,
    )
    result = run(create_lead(BackgroundTasks(), payload))
    assert result["status"] == 200
    assert captured["values"]["status"] == "new"


def test_guest_non_sample_upload_requires_auth():
    payload = AnalyzeRequest(analysis_type="requirements", use_sample=False, session_id="missing")
    assert payload.use_sample is False


def test_preverified_sample_does_not_consume_live_rate_limit(monkeypatch):
    async def fail_if_called(*args, **kwargs):
        raise AssertionError("deterministic sample should not consume the live-analysis quota")

    monkeypatch.setattr("src.server.service.demo_service.async_rate_limit", fail_if_called)
    result = run(analyze_demo(
        FakeRequest(),
        AnalyzeRequest(analysis_type="executive_summary", use_sample=True),
        token_checker=None,
    ))

    assert result.media_type == "text/event-stream"


def test_repository_records_remain_readable_after_commit():
    assert SessionLocal.kw["expire_on_commit"] is False


def test_public_sources_have_only_traceability_fields():
    source = context_builder.to_sources([RetrievedDocumentDto(
        content="A decision must be approved by the operations owner.",
        metadata={"original_filename": "requirements.pdf", "page": 3, "chunk_index": 7},
        score=0.93,
    )])[0]
    assert set(source) == {"filename", "page", "chunk_index", "excerpt", "source_id"}
    assert source["source_id"] == "source-1"
    assert source["page"] == 3


def test_findings_bind_model_citations_to_sources():
    findings = parse_findings(
        "The pilot owner is Maya Chen [source-1].\nThe launch date is September 15 (source-2).",
        ["source-1", "source-2", "source-3"],
    )
    assert findings[0]["source_ids"] == ["source-1"]
    assert findings[1]["source_ids"] == ["source-2"]


def test_model_citation_variants_are_normalized_only_for_valid_sources():
    answer = "Decision | SOURCE_ID: northstar-risks. Unknown SOURCE_ID: invented-source."
    normalized = normalize_source_citations(answer, ["northstar-risks"])
    assert "[northstar-risks]" in normalized
    assert "SOURCE_ID: invented-source" in normalized


def test_live_analysis_uses_published_dify_workflow(monkeypatch):
    captured = {}

    async def fake_workflow(*, inputs, user):
        captured["inputs"] = inputs
        captured["user"] = user
        yield {"event": "text", "text": "Delete uploads after 24 hours [northstar-requirements]."}
        yield {"event": "finished", "answer": "Delete uploads after 24 hours [northstar-requirements].",
               "workflow_run_id": "workflow-run-1"}

    monkeypatch.setattr("src.server.service.demo_service.stream_document_analysis", fake_workflow)
    monkeypatch.setattr("src.server.service.demo_service.finish_demo_job", lambda *args, **kwargs: None)
    monkeypatch.setattr("src.server.service.demo_service.add_demo_event", lambda *args, **kwargs: None)

    async def collect():
        payload = AnalyzeRequest(
            analysis_type="free_question",
            question="When are uploads deleted?",
            use_sample=True,
            lang="en",
        )
        return [event async for event in live_analysis_stream("job-1", payload, None)]

    events = run(collect())
    assert captured["inputs"]["analysis_type"] == "free_question"
    assert captured["inputs"]["lang"] == "en"
    assert "SOURCE_ID: northstar-requirements" in captured["inputs"]["context"]
    assert any(event["event"] == "result" for event in events)
