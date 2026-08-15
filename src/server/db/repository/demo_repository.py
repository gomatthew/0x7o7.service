# -*- coding: utf-8 -*-
from datetime import datetime

from sqlalchemy import and_

from src.server.db.models.demo_model import DemoEventModel, DemoJobModel, DemoSessionModel, LeadModel
from src.server.db.session import with_session


@with_session
def get_active_demo_session(session, user_id: str):
    return session.query(DemoSessionModel).filter(
        and_(
            DemoSessionModel.user_id == str(user_id),
            DemoSessionModel.status == "ready",
            DemoSessionModel.expires_at > datetime.now().astimezone(),
        )
    ).order_by(DemoSessionModel.created_at.desc()).first()


@with_session
def get_demo_session(session, session_id: str, user_id: str | None = None):
    query = session.query(DemoSessionModel).filter(DemoSessionModel.id == session_id)
    if user_id is not None:
        query = query.filter(DemoSessionModel.user_id == str(user_id))
    return query.first()


@with_session
def add_demo_session(session, values: dict):
    row = DemoSessionModel(**values)
    session.add(row)
    session.flush()
    return row.id


@with_session
def expire_demo_session(session, session_id: str):
    row = session.query(DemoSessionModel).filter(DemoSessionModel.id == session_id).first()
    if row:
        row.status = "expired"
    return bool(row)


@with_session
def add_demo_job(session, values: dict):
    row = DemoJobModel(**values)
    session.add(row)
    session.flush()
    return row.id


@with_session
def finish_demo_job(session, job_id: str, *, status: str, result=None, sources=None, error_code=None):
    row = session.query(DemoJobModel).filter(DemoJobModel.id == job_id).first()
    if row:
        row.status = status
        row.result = result
        row.sources = sources
        row.error_code = error_code
        row.finished_at = datetime.now().astimezone()


@with_session
def add_demo_event(session, values: dict):
    session.add(DemoEventModel(**values))


@with_session
def add_lead(session, values: dict):
    row = LeadModel(**values)
    session.add(row)
    session.flush()
    return row.id


@with_session
def list_expired_demo_sessions(session, now: datetime):
    return session.query(DemoSessionModel).filter(
        DemoSessionModel.expires_at <= now,
        DemoSessionModel.status != "deleted",
    ).all()


@with_session
def mark_demo_session_deleted(session, session_id: str):
    row = session.query(DemoSessionModel).filter(DemoSessionModel.id == session_id).first()
    if row:
        row.status = "deleted"
