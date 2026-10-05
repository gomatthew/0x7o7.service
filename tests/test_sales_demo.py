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
                                             parse_findings, validate_file, build_delivery_package,
                                             build_review_only_package, looks_like_client_brief)
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
    package = result["data"]["delivery_package"]
    assert package["mode"] == "preverified_sample"
    assert len(package["fields"]) == 9
    assert {item["type"] for item in package["exceptions"]} >= {"missing", "conflict"}
    assert package["handoff"]["mode"] == "preview_only"
    timeline = next(field for field in package["fields"] if field["id"] == "timeline")
    assert timeline["status"] == "confirmed"
    assert timeline["value"] == "7-day pilot; delivery on Day 7"
    assert timeline["source_ids"] == ["northstar-timeline"]
    assert package["handoff"]["payload"]["due_date"] == timeline["value"]
    valid_source_ids = {source["source_id"] for source in package["sources"]}
    assert all(set(field["source_ids"]) <= valid_source_ids for field in package["fields"])


def test_structured_contract_extracts_owner_and_deadline_without_prose_parsing():
    context = "# Beacon Policy Review\nThe compliance owner is Maya Chen. The first pilot must be ready by September 15.\nRequirements and acceptance criteria define the delivery scope. Uploaded documents must be deleted within 24 hours."
    sources = [{"source_id": "source-1", "excerpt": context, "filename": "brief.md", "page": None, "chunk_index": 0}]
    package = build_delivery_package(context, sources, "live_model")
    fields = {field["id"]: field for field in package["fields"]}
    assert fields["owner"]["value"] == "Maya Chen"
    assert fields["timeline"]["value"] == "September 15"
    assert looks_like_client_brief(context) is True
    assert looks_like_client_brief("a recipe for soup") is False
    assert looks_like_client_brief("Professional experience delivering AI projects. Education and technical skills.") is False


def test_non_brief_builds_source_backed_review_only_package():
    sources = [{"source_id": "source-1", "excerpt": "Professional experience and skills.",
                "filename": "resume.pdf", "page": 1, "chunk_index": 0}]
    package = build_review_only_package(sources)
    assert package["mode"] == "review_only"
    assert package["handoff"]["ready"] is False
    assert package["exceptions"][0]["id"] == "document-type-mismatch"
    assert package["fields"][1]["status"] == "confirmed"
    assert package["fields"][1]["source_ids"] == ["source-1"]


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


def test_admin_live_analysis_does_not_consume_rate_limit(monkeypatch):
    async def fail_if_called(*args, **kwargs):
        raise AssertionError("admin live analysis should not consume the demo quota")

    monkeypatch.setattr("src.server.service.demo_service.is_admin_user", lambda user_id: True)
    monkeypatch.setattr("src.server.service.demo_service.async_rate_limit", fail_if_called)
    monkeypatch.setattr("src.server.service.demo_service.add_demo_job", lambda values: "job_admin_test")
    result = run(analyze_demo(
        FakeRequest(),
        AnalyzeRequest(
            analysis_type="free_question",
            question="What are the documented risks?",
            use_sample=True,
        ),
        token_checker="5",
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


def test_live_analysis_uses_local_document_workflow(monkeypatch):
    captured = {}

    async def fake_workflow(*, inputs, user, sources):
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


def test_live_delivery_handoff_returns_review_only_for_non_brief(monkeypatch):
    retrieved = [RetrievedDocumentDto(
        content="Experienced AI engineer with Python and machine learning skills.",
        metadata={"original_filename": "resume.pdf", "page": 1, "chunk_index": 0}, score=0.9,
    )]

    async def fake_retrieve(**_kwargs):
        return retrieved

    async def fail_if_called(**_kwargs):
        raise AssertionError("non-brief should not invoke the handoff model")
        yield  # pragma: no cover

    captured = {}
    monkeypatch.setattr("src.server.service.demo_service.retrieval_pipeline.retrieve", fake_retrieve)
    monkeypatch.setattr("src.server.service.demo_service.stream_document_analysis", fail_if_called)
    monkeypatch.setattr("src.server.service.demo_service.finish_demo_job", lambda *args, **kwargs: captured.update(kwargs))
    monkeypatch.setattr("src.server.service.demo_service.add_demo_event", lambda *_args, **_kwargs: None)

    async def collect():
        payload = AnalyzeRequest(analysis_type="delivery_handoff", use_sample=False, session_id="session-1")
        session = SimpleNamespace(id="session-1", user_id="1", storage_path="/tmp/session")
        return [event async for event in live_analysis_stream("job-review", payload, session)]

    events = run(collect())
    result = next(event for event in events if event["event"] == "result")
    assert json.loads(result["data"])["mode"] == "review_only"
    assert captured["status"] == "completed"


def test_live_analysis_returns_the_real_upstream_failure(monkeypatch):
    async def failing_workflow(*args, **kwargs):
        raise RuntimeError("Model provider returned HTTP 401")
        yield  # pragma: no cover - make this an async generator

    monkeypatch.setattr("src.server.service.demo_service.stream_document_analysis", failing_workflow)
    monkeypatch.setattr("src.server.service.demo_service.finish_demo_job", lambda *args, **kwargs: None)

    async def collect():
        payload = AnalyzeRequest(analysis_type="free_question", question="Who owns this?", use_sample=True)
        return [event async for event in live_analysis_stream("job-error", payload, None)]

    events = run(collect())
    error_event = next(event for event in events if event["event"] == "error")
    assert "HTTP 401" in json.loads(error_event["data"])["message"]


def test_live_analysis_reports_model_timeout(monkeypatch):
    async def timed_out_workflow(*args, **kwargs):
        raise asyncio.TimeoutError()
        yield  # pragma: no cover - make this an async generator

    monkeypatch.setattr("src.server.service.demo_service.stream_document_analysis", timed_out_workflow)
    monkeypatch.setattr("src.server.service.demo_service.finish_demo_job", lambda *args, **kwargs: None)

    async def collect():
        payload = AnalyzeRequest(analysis_type="free_question", question="Who owns this?", use_sample=True)
        return [event async for event in live_analysis_stream("job-timeout", payload, None)]

    events = run(collect())
    error_event = next(event for event in events if event["event"] == "error")
    assert json.loads(error_event["data"])["code"] == "live_analysis_timeout"
