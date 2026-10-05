# -*- coding: utf-8 -*-
import asyncio
import json
import os
import re
import shutil
import time
import traceback
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Literal, Optional

from fastapi import BackgroundTasks, Body, File, Form, Request, UploadFile
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from src.configs import get_setting, logger
from src.server.ai.document_workflow_service import stream_document_analysis
from src.server.ai.rag.context_service import context_builder
from src.server.ai.rag.document_chunker_service import document_chunker
from src.server.ai.rag.document_loader_service import document_loader_service
from src.server.ai.rag.retrieval_service import retrieval_pipeline
from src.server.ai.rag.vector_store_service import faiss_vector_store_service
from src.server.db.repository import (
    add_demo_event,
    add_demo_job,
    add_demo_session,
    add_lead,
    expire_demo_session,
    finish_demo_job,
    get_active_demo_session,
    get_demo_session,
)
from src.server.dto import ApiCommonResponseDTO
from src.server.libs import send_mail
from src.server.libs.redis_lib import async_rate_limit
from src.server.utils import TokenChecker, get_client_ip, is_admin_user

setting = get_setting()

SAMPLE_DOCUMENT = """# Northstar AI Pilot Requirements Pack

## Business goal
Northstar Operations wants to reduce the time project teams spend searching long policy and delivery documents. The pilot must turn approved documents into traceable answers and actionable delivery plans.

## Users and workflow
Primary users are delivery managers and operations leads. They upload PDF or DOCX files, ask a question, review citations, and export requirements, risks, and next actions. High-risk conclusions must be routed to a human reviewer.

## Requirements
R1. Answers must cite the source file and page where available.
R2. The system must produce an executive summary, requirements with acceptance criteria, and a risk/action register.
R3. Files must be private to the uploader and deleted after 24 hours.
R4. Unsupported or suspicious files must be rejected before indexing.
R5. The public sample must work without account creation.

## Data retention appendix
For a controlled audit, the agency may retain a sealed delivery archive for 30 days.

## Acceptance criteria
AC1. A user can complete the sample flow in under three minutes.
AC2. Every material claim in an uploaded-document answer includes at least one source reference.
AC3. Uploaded files, indexes, and generated results are removed within 24 hours.
AC4. The service recovers automatically after a process restart.

## Risks and open questions
Prompt injection inside uploaded documents could influence the model. Model-provider downtime could interrupt live analysis. The pilot owner must decide whether export and team sharing belong in phase two.

## Owners and timeline
Jian owns engineering and deployment. The client product owner approves scope and acceptance criteria. Day 1 confirms scope; days 2-4 implement retrieval and structured analysis; day 5 runs evaluation; day 6 resolves errors; day 7 delivers source, deployment notes, and handoff.
"""

SAMPLE_RAG_CONTEXT = """[SOURCE 1]
SOURCE_FILE: northstar-ai-pilot.md; SOURCE_ID: northstar-goal
CONTENT:
Northstar Operations wants to reduce the time project teams spend searching long policy and delivery documents. The pilot must turn approved documents into traceable answers and actionable delivery plans. Primary users are delivery managers and operations leads. High-risk conclusions must be routed to a human reviewer.

[SOURCE 2]
SOURCE_FILE: northstar-ai-pilot.md; SOURCE_ID: northstar-requirements
CONTENT:
R1. Answers must cite the source file and page where available. R2. The system must produce an executive summary, requirements with acceptance criteria, and a risk/action register. R3. Files must be private to the uploader and deleted after 24 hours. R4. Unsupported or suspicious files must be rejected before indexing. R5. The public sample must work without account creation. Acceptance requires completing the sample in under three minutes, citing every material claim, deleting files, indexes and results within 24 hours, and recovering after a process restart.

[SOURCE 3]
SOURCE_FILE: northstar-ai-pilot.md; SOURCE_ID: northstar-risks
CONTENT:
Prompt injection inside uploaded documents could influence the model. Model-provider downtime could interrupt live analysis. The pilot owner must decide whether export and team sharing belong in phase two.

[SOURCE 4]
SOURCE_FILE: northstar-ai-pilot.md; SOURCE_ID: northstar-timeline
CONTENT:
Jian owns engineering and deployment. The client product owner approves scope and acceptance criteria. Day 1 confirms scope; days 2-4 implement retrieval and structured analysis; day 5 runs evaluation; day 6 resolves errors; day 7 delivers source, deployment notes, and handoff.
"""

SAMPLE_SOURCES = [
    {"source_id": "northstar-goal", "filename": "northstar-ai-pilot.md", "page": None, "chunk_index": 0,
     "excerpt": "Northstar Operations wants to reduce time spent searching long policy and delivery documents."},
    {"source_id": "northstar-requirements", "filename": "northstar-ai-pilot.md", "page": None, "chunk_index": 1,
     "excerpt": "Answers must cite source files; uploads must be private and deleted after 24 hours."},
    {"source_id": "northstar-risks", "filename": "northstar-ai-pilot.md", "page": None, "chunk_index": 2,
     "excerpt": "Prompt injection, provider downtime, and phase-two scope are open risks or decisions."},
    {"source_id": "northstar-timeline", "filename": "northstar-ai-pilot.md", "page": None, "chunk_index": 3,
     "excerpt": "Day 1 confirms scope; days 2-7 cover implementation, evaluation, fixes, and handoff."},
    {"source_id": "northstar-retention-appendix", "filename": "northstar-ai-pilot.md", "page": None, "chunk_index": 4,
     "excerpt": "For a controlled audit, the agency may retain a sealed delivery archive for 30 days."},
]

SAMPLE_ANALYSES = {
    "executive_summary": {
        "title": "Executive summary",
        "summary": "Northstar needs a private, source-backed document workflow that turns approved files into answers and delivery decisions while keeping high-risk conclusions under human review.",
        "findings": [
            {"label": "Primary outcome", "value": "Faster document review with traceable answers", "source_ids": ["northstar-goal"]},
            {"label": "Operating boundary", "value": "Human review for high-risk conclusions", "source_ids": ["northstar-goal"]},
            {"label": "Delivery shape", "value": "A seven-day fixed-scope pilot", "source_ids": ["northstar-timeline"]},
        ],
        "sources": SAMPLE_SOURCES,
        "mode": "preverified_sample",
    },
    "requirements": {
        "title": "Requirements and acceptance criteria",
        "summary": "The pilot requires private uploads, reliable citations, three structured outputs, file validation, and a zero-sign-up sample path.",
        "findings": [
            {"label": "R1 / AC2", "value": "Cite the source file and page for every material claim", "source_ids": ["northstar-requirements"]},
            {"label": "R3 / AC3", "value": "Delete files, indexes, and generated results within 24 hours", "source_ids": ["northstar-requirements"]},
            {"label": "R5 / AC1", "value": "Complete the public sample in under three minutes", "source_ids": ["northstar-goal", "northstar-requirements"]},
        ],
        "sources": SAMPLE_SOURCES,
        "mode": "preverified_sample",
    },
    "risks_actions": {
        "title": "Risks, open questions and 7-day action plan",
        "summary": "The largest risks are document prompt injection, provider downtime, and unclear phase-two scope. The plan isolates these risks before handoff.",
        "findings": [
            {"label": "Security", "value": "Treat uploaded text as untrusted data and keep it outside system instructions", "source_ids": ["northstar-risks"]},
            {"label": "Reliability", "value": "Expose provider failures rather than substituting fake live answers", "source_ids": ["northstar-risks"]},
            {"label": "Day 1-7", "value": "Scope, build, evaluate, fix, and hand off with deployment notes", "source_ids": ["northstar-timeline"]},
        ],
        "sources": SAMPLE_SOURCES,
        "mode": "preverified_sample",
    },
}

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}
ANALYSIS_TYPES = {"executive_summary", "requirements", "risks_actions", "free_question", "delivery_handoff"}


class AnalyzeRequest(BaseModel):
    # Legacy analysis types remain accepted for existing callers.  The flagship
    # workbench uses delivery_handoff, whose result is a stable JSON contract.
    analysis_type: Literal["executive_summary", "requirements", "risks_actions", "free_question", "delivery_handoff"]
    session_id: Optional[str] = None
    question: Optional[str] = Field(None, max_length=1200)
    use_sample: bool = True
    lang: Literal["en", "zh"] = "en"


class LeadRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    work_email: str = Field(min_length=5, max_length=254)
    company: str = Field(min_length=2, max_length=180)
    website: Optional[str] = Field(None, max_length=512)
    project_type: str = Field(min_length=2, max_length=80)
    project_summary: str = Field(min_length=20, max_length=4000)
    timeline: str = Field(min_length=2, max_length=80)
    budget_range: Optional[str] = Field(None, max_length=80)
    contact_consent: bool
    source_page: Optional[str] = Field(None, max_length=512)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def sample_payload():
    return {
        "document": {"name": "Northstar AI Pilot Requirements Pack", "filename": "northstar-ai-pilot.md",
                     "content": SAMPLE_DOCUMENT, "fictional": True},
        "analysis_options": [
            {"id": "executive_summary", "label": "Executive summary"},
            {"id": "requirements", "label": "Requirements & acceptance"},
            {"id": "risks_actions", "label": "Risks & 7-day plan"},
        ],
        "results": SAMPLE_ANALYSES,
        "notice": "These are pre-verified sample results. Free questions use the live model and are labelled separately.",
        "delivery_package": build_delivery_package(SAMPLE_DOCUMENT, SAMPLE_SOURCES, "preverified_sample", fictional=True),
    }


def _source_ids_for(text: str, sources: list[dict]) -> list[str]:
    """Return only IDs emitted by retrieval; model/user text never supplies IDs."""
    words = {word.lower() for word in re.findall(r"[a-zA-Z]{4,}", text)}
    matched = [source["source_id"] for source in sources
               if words.intersection(re.findall(r"[a-zA-Z]{4,}", source.get("excerpt", "").lower()))]
    return matched[:3] or ([sources[0]["source_id"]] if sources else [])


def _first_match(pattern: str, text: str, fallback: str | None = None) -> str | None:
    matched = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
    return matched.group(1).strip(" .") if matched else fallback


def looks_like_client_brief(context: str) -> bool:
    resume_markers = ("resume", "curriculum vitae", "work experience", "professional experience",
                      "education", "technical skills", "certifications")
    # Resumes often mention generic words such as "deliver" or "scope". Do
    # not turn them into a fictitious client handoff merely because they match
    # the broad brief vocabulary below.
    if sum(marker in context.lower() for marker in resume_markers) >= 2:
        return False
    keywords = ("requirement", "acceptance", "owner", "deadline", "timeline", "pilot", "deliver", "scope",
                "需求", "验收", "负责人", "截止", "时间", "试点", "交付", "范围")
    return sum(keyword in context.lower() for keyword in keywords) >= 2


def build_review_only_package(sources: list[dict]) -> dict:
    """Return a successful, source-backed result for a parsed non-brief.

    The flagship handoff contract must not invent project fields for a resume,
    invoice, or other readable but out-of-template document.  It is still
    useful to confirm that parsing succeeded and expose its evidence.
    """
    source_ids = [source["source_id"] for source in sources]
    source_count = len(sources)
    fields = [
        {"id": "document_type", "label": "Document type", "value": "Not a client brief / requirements pack",
         "status": "review", "source_ids": source_ids[:1],
         "review_reason": "The document was parsed, but it does not contain enough delivery-brief evidence."},
        {"id": "parsed_evidence", "label": "Parsed evidence", "value": f"Readable text extracted from {source_count} source section(s)",
         "status": "confirmed", "source_ids": source_ids, "review_reason": None},
        {"id": "handoff_assessment", "label": "Handoff assessment", "value": None, "status": "missing",
         "source_ids": source_ids[:1],
         "review_reason": "Upload a client brief or requirements pack to create a delivery handoff."},
    ]
    exception = {"id": "document-type-mismatch", "type": "template_mismatch",
                 "title": "Document parsed; delivery handoff is not applicable",
                 "description": "This document is readable, but it is not a client brief or requirements pack. No delivery fields were inferred.",
                 "field_ids": ["document_type", "handoff_assessment"], "source_ids": source_ids[:1],
                 "blocks_handoff": True}
    return {"title": "Parsed document review", "summary": "Text and source evidence were extracted successfully; upload a client brief to prepare a delivery handoff.",
            "mode": "review_only", "fields": fields, "exceptions": [exception], "sources": sources,
            "outcome": {"field_count": len(fields), "review_count": 1, "confirmed_count": 1},
            "handoff": {"mode": "preview_only", "target_label": "Project delivery system / API", "ready": False,
                        "blocked_by": [exception["id"]], "mappings": [],
                        "payload": {"source_references_attached": bool(sources), "review_decisions_recorded": False}}}


def build_delivery_package(context: str, sources: list[dict], mode: str, fictional: bool = False) -> dict:
    """Create the product contract without parsing model prose into UI fields.

    This deterministic package is retained for the pre-verified sample.
    Live uploads use structured model extraction and evidence validation.
    """
    project = _first_match(r"#\s*([^\n]+)", context, "Client brief")
    # Keep proper names/dates case-sensitive: the permissive regex used for
    # prose otherwise mistakes phrases such as "owner must decide" for names.
    owner_match = re.search(r"(?:[Cc]ompliance\s+[Oo]wner\s+is|[Oo]wner\s*:)\s*([A-Z][a-z]+\s+[A-Z][a-z]+)", context)
    owner = owner_match.group(1) if owner_match else None
    deadline_match = re.search(r"(?:ready by|[Dd]eadline(?: is|:)?|by)\s+([A-Z][a-z]+\s+\d{1,2})", context)
    deadline = deadline_match.group(1) if deadline_match else None
    timeline_confirmed = False
    if not deadline and re.search(r"\bDay\s+7\b", context, re.I):
        # A relative delivery commitment is still a real, source-backed due
        # date for this fixed-scope pilot; it must not masquerade as missing.
        deadline = "7-day pilot; delivery on Day 7"
        timeline_confirmed = True
    retention_24 = bool(re.search(r"(?:deleted|delete).*?24\s*hours|24\s*hours.*?(?:deleted|delete)", context, re.I | re.S))
    retention_30 = bool(re.search(r"(?:archive|retain).*?30\s*days|30\s*days.*?(?:archive|retain)", context, re.I | re.S))
    fields = [
        ("project_client", "Project / client", project, "confirmed", None),
        ("business_outcome", "Business outcome", _first_match(r"(?:goal|outcome)\s*\n?([^\n]+)", context, "Delivery-ready, source-linked work package"), "confirmed", None),
        ("primary_users", "Primary users", "Delivery managers and operations leads", "confirmed", None),
        ("required_outputs", "Required outputs", "Structured delivery fields, review queue, and handoff preview", "confirmed", None),
        ("acceptance_criteria", "Acceptance criteria", "Material claims are source-linked and exceptions are reviewed", "confirmed", None),
        ("owner", "Owner", owner, "confirmed" if owner else "missing", "No named owner was found in the document." if not owner else None),
        ("timeline", "Timeline", deadline or "Not specified", "confirmed" if timeline_confirmed else ("review" if deadline else "missing"), None if timeline_confirmed else ("Confirm the delivery deadline." if deadline else "No delivery deadline was found.")),
        ("data_privacy", "Data / privacy boundary", "Delete uploaded documents within 24 hours" if retention_24 else None, "review" if retention_30 else ("confirmed" if retention_24 else "missing"), "Two retention instructions conflict." if retention_24 and retention_30 else None),
        ("target_handoff", "Target handoff", "Project delivery system / API", "review", "Target system remains an open decision."),
    ]
    delivery_fields = [{"id": field_id, "label": label, "value": value, "status": status,
                        "source_ids": _source_ids_for(str(value or label), sources), "review_reason": reason}
                       for field_id, label, value, status, reason in fields]
    if timeline_confirmed:
        next(field for field in delivery_fields if field["id"] == "timeline")["source_ids"] = ["northstar-timeline"] if fictional else _source_ids_for("day 7 delivery handoff", sources)
    exceptions = []
    if not owner:
        exceptions.append({"id": "missing-owner", "type": "missing", "title": "Assign a delivery owner",
                           "description": "The document does not name the client product owner.", "field_ids": ["owner"],
                           "source_ids": _source_ids_for("owner client product", sources), "blocks_handoff": True})
    if retention_24 and (retention_30 or fictional):
        retention_sources = [source["source_id"] for source in sources
                             if "24 hours" in source.get("excerpt", "").lower() or "30 days" in source.get("excerpt", "").lower()]
        exceptions.append({"id": "retention-conflict", "type": "conflict", "title": "Resolve retention period",
                           "description": "The brief says delete after 24 hours; its appendix says archive for 30 days.",
                           "field_ids": ["data_privacy"], "source_ids": retention_sources or _source_ids_for("retention archive", sources), "blocks_handoff": True})
    exceptions.append({"id": "target-system-review", "type": "weak_evidence", "title": "Confirm target handoff",
                       "description": "Choose the delivery system during review; this demo only previews an API payload.",
                       "field_ids": ["target_handoff"], "source_ids": _source_ids_for("handoff delivery", sources), "blocks_handoff": False})
    blocked_by = [item["id"] for item in exceptions if item["blocks_handoff"]]
    return {"title": "Delivery work package", "summary": "Ready with review items" if exceptions else "Approved for handoff",
            "mode": mode, "fields": delivery_fields, "exceptions": exceptions, "sources": sources,
            "outcome": {"field_count": len(delivery_fields), "review_count": len(exceptions), "confirmed_count": sum(f["status"] == "confirmed" for f in delivery_fields)},
            "handoff": {"mode": "preview_only", "target_label": "Project delivery system / API", "ready": not blocked_by,
                        "blocked_by": blocked_by, "mappings": [{"source_field": "project_client", "target_field": "project_name"}, {"source_field": "required_outputs", "target_field": "scope"}, {"source_field": "acceptance_criteria", "target_field": "acceptance_criteria"}, {"source_field": "owner", "target_field": "owner"}, {"source_field": "timeline", "target_field": "due_date"}, {"source_field": "target_handoff", "target_field": "target_system"}],
                        "payload": {"project_name": project, "scope": "Structured delivery fields, review queue, and handoff preview", "acceptance_criteria": "Material claims are source-linked and exceptions are reviewed", "owner": owner, "due_date": deadline, "target_system": "Project delivery system / API", "source_references_attached": True, "review_decisions_recorded": False}}}


def validate_file(filename: str, content: bytes):
    safe_name = os.path.basename(filename or "")
    extension = Path(safe_name).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise ValueError("Only PDF, DOCX, TXT, and Markdown files are supported")
    if not content:
        raise ValueError("The uploaded file is empty")
    if len(content) > setting.DEMO_UPLOAD_MAX_BYTES:
        raise ValueError("The uploaded file exceeds the 10MB limit")
    if extension == ".pdf" and not content.startswith(b"%PDF-"):
        raise ValueError("The file content does not match the PDF extension")
    if extension == ".docx" and not content.startswith(b"PK\x03\x04"):
        raise ValueError("The file content does not match the DOCX extension")
    if extension in {".txt", ".md"}:
        if b"\x00" in content[:4096] or content.startswith((b"MZ", b"\x7fELF")):
            raise ValueError("Executable or binary content is not accepted")
    return safe_name, extension


async def get_sample():
    return ApiCommonResponseDTO(status=200, message="success", data=sample_payload()).model_dict()


async def upload_demo_document(token_checker: TokenChecker, file: UploadFile = File(...)):
    if not token_checker:
        return ApiCommonResponseDTO(status=401, message="auth.required", data={}).model_dict()
    content = await file.read(setting.DEMO_UPLOAD_MAX_BYTES + 1)
    try:
        safe_name, extension = validate_file(file.filename or "", content)
        active = get_active_demo_session(str(token_checker))
        if active:
            cleanup_demo_session_files(active)
            expire_demo_session(active.id)

        session_id = f"ds_{uuid.uuid4().hex}"
        kb_id = f"demo_{uuid.uuid4().hex}"
        session_path = Path(setting.DEMO_UPLOAD_ROOT) / str(token_checker) / session_id
        docs_path = session_path / "docs"
        docs_path.mkdir(parents=True, exist_ok=True)
        file_path = docs_path / safe_name
        file_path.write_bytes(content)

        base_metadata = {"source": safe_name, "filename": safe_name, "original_filename": safe_name}
        docs = document_loader_service.load(str(file_path), metadata=base_metadata)
        page_count = len(docs) if extension == ".pdf" else 0
        character_count = sum(len(doc.content) for doc in docs)
        if page_count > setting.DEMO_UPLOAD_MAX_PAGES:
            raise ValueError("The PDF exceeds the 50-page limit")
        if character_count > setting.DEMO_UPLOAD_MAX_CHARS:
            raise ValueError("The document exceeds the 250,000-character limit")
        if not character_count:
            raise ValueError("No readable text was found in the document")
        chunks = document_chunker.split_documents(docs, setting.RAG_CHUNK_SIZE, setting.RAG_CHUNK_OVERLAP)
        faiss_vector_store_service.save_chunks(str(session_path), chunks, embedding_model=setting.EMBEDDING_MODEL)
        expires_at = utcnow() + timedelta(hours=setting.DEMO_RETENTION_HOURS)
        add_demo_session({
            "id": session_id,
            "user_id": str(token_checker),
            "knowledge_base_id": kb_id,
            "original_filename": safe_name,
            "storage_path": str(session_path),
            "file_type": extension.lstrip("."),
            "page_count": page_count,
            "character_count": character_count,
            "status": "ready",
            "expires_at": expires_at,
        })
        add_demo_event({"session_id": session_id, "user_id": str(token_checker), "event_type": "upload",
                        "status": "success", "properties": {"file_type": extension.lstrip("."),
                        "page_count": page_count, "character_count": character_count}})
        return ApiCommonResponseDTO(status=200, message="success", data={
            "id": session_id,
            "job_id": f"upload_{session_id}",
            "status": "ready",
            "filename": safe_name,
            "page_count": page_count,
            "character_count": character_count,
            "expires_at": expires_at.isoformat(),
        }).model_dict()
    except BaseException as error:
        logger.error(error)
        return ApiCommonResponseDTO(status=400, message=str(error), data={}).model_dict()


async def get_demo_upload(upload_id: str, token_checker: TokenChecker):
    if not token_checker:
        return ApiCommonResponseDTO(status=401, message="auth.required", data={}).model_dict()
    row = get_demo_session(upload_id, str(token_checker))
    if not row or row.status != "ready" or row.expires_at <= utcnow():
        return ApiCommonResponseDTO(status=404, message="demo.uploadNotFound", data={}).model_dict()
    return ApiCommonResponseDTO(status=200, message="success", data={
        "id": row.id, "status": row.status, "filename": row.original_filename,
        "page_count": row.page_count, "character_count": row.character_count,
        "expires_at": row.expires_at.isoformat(),
    }).model_dict()


def analysis_prompt(analysis_type: str, question: str | None = None):
    directives = {
        "executive_summary": "Produce a concise executive summary, key outcomes, stakeholders, and operating boundaries.",
        "requirements": "Extract requirements and pair each with a testable acceptance criterion. Identify missing decisions.",
        "risks_actions": "Extract risks, open questions, owners, and a practical seven-day action plan.",
        "free_question": f"Answer this question using only the provided document: {question}",
    }
    return directives[analysis_type]


def parse_findings(answer: str, valid_source_ids: list[str] | None = None):
    valid_source_ids = valid_source_ids or []
    lines = [re.sub(r"^[-*#\d.()\s]+", "", line).strip() for line in answer.splitlines()]
    return [{
                "label": f"Finding {index}",
                "value": line,
                "source_ids": [source_id for source_id in valid_source_ids
                               if re.search(rf"(?<![\w-]){re.escape(source_id)}(?![\w-])", line, re.IGNORECASE)],
            }
            for index, line in enumerate([line for line in lines if len(line) > 12][:8], start=1)]


def normalize_source_citations(answer: str, valid_source_ids: list[str]) -> str:
    """Normalize model citation variants, but only for IDs returned by retrieval."""
    normalized = answer
    for source_id in valid_source_ids:
        escaped = re.escape(source_id)
        normalized = re.sub(
            rf"\[\s*(?:source[-_ ]?id\s*:\s*)?{escaped}\s*\]",
            f"[{source_id}]",
            normalized,
            flags=re.IGNORECASE,
        )
        normalized = re.sub(
            rf"(?:\|\s*)?\bsource[-_ ]?id\s*:\s*{escaped}\b",
            f" [{source_id}]",
            normalized,
            flags=re.IGNORECASE,
        )
    return re.sub(r"[ \t]{2,}", " ", normalized).strip()


async def analyze_demo(request: Request, payload: AnalyzeRequest = Body(...), token_checker: TokenChecker = None):
    if payload.analysis_type not in ANALYSIS_TYPES:
        return ApiCommonResponseDTO(status=400, message="demo.invalidAnalysis", data={}).model_dict()
    if payload.analysis_type == "free_question" and not (payload.question or "").strip():
        return ApiCommonResponseDTO(status=400, message="demo.questionRequired", data={}).model_dict()

    if payload.use_sample and payload.analysis_type != "free_question":
        result = (build_delivery_package(SAMPLE_DOCUMENT, SAMPLE_SOURCES, "preverified_sample", fictional=True)
                  if payload.analysis_type == "delivery_handoff" else SAMPLE_ANALYSES[payload.analysis_type])
        return EventSourceResponse(sample_event_stream(result))

    client_ip = get_client_ip(request)
    if token_checker and is_admin_user(token_checker):
        limited = False
    elif token_checker:
        limited, _ = await async_rate_limit(f"demo:user:{token_checker}", setting.DEMO_USER_ANALYSIS_LIMIT,
                                             setting.DEMO_USER_ANALYSIS_TTL)
    else:
        limited, _ = await async_rate_limit(f"demo:guest:{client_ip}", setting.DEMO_GUEST_QUESTION_LIMIT, 86400)
    if limited:
        return ApiCommonResponseDTO(status=429, message="demo.limitReached", data={}).model_dict()

    if not payload.use_sample and not token_checker:
        return ApiCommonResponseDTO(status=401, message="auth.required", data={}).model_dict()

    session = None
    if not payload.use_sample:
        session = get_demo_session(payload.session_id or "", str(token_checker))
        if not session or session.status != "ready" or session.expires_at <= utcnow():
            return ApiCommonResponseDTO(status=404, message="demo.uploadNotFound", data={}).model_dict()

    job_id = add_demo_job({"session_id": session.id if session else None,
                           "user_id": str(token_checker) if token_checker else None,
                           "analysis_type": payload.analysis_type, "status": "running"})
    return EventSourceResponse(live_analysis_stream(job_id, payload, session))


async def sample_event_stream(result: dict):
    for stage in ("identify", "extract", "validate", "review"):
        yield {"event": "status", "data": json.dumps({"stage": stage, "mode": "preverified_sample"})}
    yield {"event": "result", "data": json.dumps(result, ensure_ascii=False)}
    yield {"event": "done", "data": json.dumps({"mode": "preverified_sample"})}


async def live_analysis_stream(job_id: str, payload: AnalyzeRequest, session):
    started = time.monotonic()
    try:
        yield {"event": "status", "data": json.dumps({"stage": "identify", "mode": "live_model"})}
        if payload.use_sample:
            context = SAMPLE_RAG_CONTEXT
            sources = SAMPLE_SOURCES
        else:
            prompt_type = "requirements" if payload.analysis_type == "delivery_handoff" else payload.analysis_type
            query = payload.question or analysis_prompt(prompt_type)
            docs = await retrieval_pipeline.retrieve(query=query, kb_path=session.storage_path,
                                                     top_k=6, fetch_k=16,
                                                     embedding_model=setting.EMBEDDING_MODEL,
                                                     enable_reranker=False)
            context = context_builder.build(docs, max_chars=setting.RAG_MAX_CONTEXT_CHARS)
            sources = context_builder.to_sources(docs)
        if not context:
            raise RuntimeError("No relevant source context was found")
        if payload.analysis_type == "delivery_handoff" and not looks_like_client_brief(context):
            result = build_review_only_package(sources)
            finish_demo_job(job_id, status="completed", result=result, sources=sources)
            add_demo_event({"session_id": session.id if session else None,
                            "user_id": str(session.user_id) if session else None,
                            "event_type": payload.analysis_type, "status": "success",
                            "properties": {"source_count": len(sources), "mode": "review_only"}})
            yield {"event": "status", "data": json.dumps({"stage": "review", "mode": "review_only"})}
            yield {"event": "result", "data": json.dumps(result, ensure_ascii=False)}
            yield {"event": "done", "data": json.dumps({"job_id": job_id, "mode": "review_only"})}
            return
        source_ids = [source["source_id"] for source in sources]
        yield {"event": "source", "data": json.dumps({"sources": sources}, ensure_ascii=False)}
        yield {"event": "status", "data": json.dumps({"stage": "extract", "mode": "live_model"})}
        answer = ""
        final_answer = ""
        delivery_package = None
        async with asyncio.timeout(setting.LLM_STREAM_TIMEOUT):
            async for event in stream_document_analysis(
                inputs={
                    "analysis_type": payload.analysis_type,
                    "lang": payload.lang,
                    "question": payload.question or analysis_prompt("requirements" if payload.analysis_type == "delivery_handoff" else payload.analysis_type),
                    "context": context,
                },
                user=str(session.user_id) if session else f"guest-{job_id}",
                sources=sources,
            ):
                if event["event"] == "status":
                    yield {"event": "status", "data": json.dumps({"stage": event["stage"], "mode": "live_model"})}
                elif event["event"] == "text":
                    token = event["text"]
                    answer += token
                    yield {"event": "message", "data": json.dumps({"content": token}, ensure_ascii=False)}
                elif event["event"] == "finished":
                    final_answer = event["answer"]
                    delivery_package = event.get("delivery_package")
        streamed_answer = answer
        answer = normalize_source_citations(final_answer or answer, source_ids)
        if payload.analysis_type == "delivery_handoff" and not delivery_package:
            raise RuntimeError("Document analysis completed without delivery fields")
        if payload.analysis_type != "delivery_handoff" and not answer:
            raise RuntimeError("Document analysis completed without an answer")
        if answer and not streamed_answer:
            yield {"event": "message", "data": json.dumps({"content": answer}, ensure_ascii=False)}
        result = (delivery_package if payload.analysis_type == "delivery_handoff"
                  else {"title": payload.analysis_type.replace("_", " ").title(), "summary": answer,
                        "findings": parse_findings(answer, source_ids), "sources": sources, "mode": "live_model"})
        finish_demo_job(job_id, status="completed", result=result, sources=sources)
        duration_ms = int((time.monotonic() - started) * 1000)
        add_demo_event({"session_id": session.id if session else None,
                        "user_id": str(session.user_id) if session else None,
                        "event_type": payload.analysis_type, "status": "success", "duration_ms": duration_ms,
                        "properties": {"source_count": len(sources), "mode": "langgraph"}})
        yield {"event": "result", "data": json.dumps(result, ensure_ascii=False)}
        yield {"event": "done", "data": json.dumps({"job_id": job_id, "mode": "live_model"})}
    except asyncio.TimeoutError:
        logger.error("Document-to-Decision model timed out")
        finish_demo_job(job_id, status="failed", error_code="provider_timeout")
        yield {"event": "error", "data": json.dumps({
            "code": "live_analysis_timeout",
            "message": f"Document analysis timed out after {setting.LLM_STREAM_TIMEOUT} seconds.",
        })}
    except BaseException as error:
        if isinstance(error, asyncio.CancelledError):
            finish_demo_job(job_id, status="failed", error_code="client_disconnected")
            raise
        logger.error(error)
        logger.error(traceback.format_exc())
        finish_demo_job(job_id, status="failed", error_code="provider_or_analysis_error")
        yield {"event": "error", "data": json.dumps({
            "code": "live_analysis_unavailable",
            "message": str(error) or "Live analysis failed without a diagnostic.",
        })}


async def create_lead(background_tasks: BackgroundTasks, payload: LeadRequest = Body(...)):
    if not payload.contact_consent:
        return ApiCommonResponseDTO(status=400, message="lead.consentRequired", data={}).model_dict()
    if "@" not in payload.work_email or payload.work_email.startswith("@") or payload.work_email.endswith("@"):
        return ApiCommonResponseDTO(status=400, message="email.invalid", data={}).model_dict()
    values = payload.model_dump()
    values["work_email"] = str(payload.work_email).strip().lower()
    values["status"] = "new"
    lead_id = add_lead(values)
    message = "\n".join([
        f"Lead ID: {lead_id}", f"Name: {payload.name}", f"Email: {payload.work_email}",
        f"Company: {payload.company}", f"Website: {payload.website or '-'}",
        f"Project type: {payload.project_type}", f"Timeline: {payload.timeline}",
        f"Budget: {payload.budget_range or '-'}", "", payload.project_summary,
    ])
    background_tasks.add_task(send_mail, message=message, receiver_email=setting.RECEIVER,
                              subject=f"New 0x7o7 project inquiry — {payload.company}")
    return ApiCommonResponseDTO(status=200, message="lead.received", data={"lead_id": lead_id}).model_dict()


def cleanup_demo_session_files(row):
    path = Path(row.storage_path)
    root = Path(setting.DEMO_UPLOAD_ROOT).resolve()
    try:
        resolved = path.resolve()
        if root in resolved.parents and resolved.is_dir():
            shutil.rmtree(resolved)
    except FileNotFoundError:
        pass
