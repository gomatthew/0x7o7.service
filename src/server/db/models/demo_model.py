# -*- coding: utf-8 -*-
import uuid

from sqlalchemy import Boolean, Column, DateTime, Integer, JSON, String, Text, func

from src.server.db.base import Base


class DemoSessionModel(Base):
    __tablename__ = "demo_sessions"

    id = Column(String(64), primary_key=True, default=lambda: f"ds_{uuid.uuid4().hex}")
    user_id = Column(String(64), nullable=False, index=True)
    knowledge_base_id = Column(String(64), nullable=False, unique=True)
    original_filename = Column(String(256), nullable=False)
    storage_path = Column(String(512), nullable=False)
    file_type = Column(String(16), nullable=False)
    page_count = Column(Integer, nullable=False, default=0)
    character_count = Column(Integer, nullable=False, default=0)
    status = Column(String(24), nullable=False, default="ready", index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class DemoJobModel(Base):
    __tablename__ = "demo_jobs"

    id = Column(String(64), primary_key=True, default=lambda: f"job_{uuid.uuid4().hex}")
    session_id = Column(String(64), nullable=True, index=True)
    user_id = Column(String(64), nullable=True, index=True)
    analysis_type = Column(String(64), nullable=False)
    status = Column(String(24), nullable=False, default="running", index=True)
    result = Column(JSON, nullable=True)
    sources = Column(JSON, nullable=True)
    error_code = Column(String(64), nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    finished_at = Column(DateTime(timezone=True), nullable=True)


class LeadModel(Base):
    __tablename__ = "leads"

    id = Column(String(64), primary_key=True, default=lambda: f"lead_{uuid.uuid4().hex}")
    name = Column(String(120), nullable=False)
    work_email = Column(String(254), nullable=False, index=True)
    company = Column(String(180), nullable=False)
    website = Column(String(512), nullable=True)
    project_type = Column(String(80), nullable=False)
    project_summary = Column(Text, nullable=False)
    timeline = Column(String(80), nullable=False)
    budget_range = Column(String(80), nullable=True)
    contact_consent = Column(Boolean, nullable=False, default=False)
    source_page = Column(String(512), nullable=True)
    status = Column(String(24), nullable=False, default="new", index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class DemoEventModel(Base):
    __tablename__ = "demo_events"

    id = Column(String(64), primary_key=True, default=lambda: f"evt_{uuid.uuid4().hex}")
    session_id = Column(String(64), nullable=True, index=True)
    user_id = Column(String(64), nullable=True, index=True)
    event_type = Column(String(64), nullable=False, index=True)
    status = Column(String(24), nullable=False)
    duration_ms = Column(Integer, nullable=True)
    properties = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
