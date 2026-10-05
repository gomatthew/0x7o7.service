# -*- coding: utf-8 -*-
import json
from functools import lru_cache, wraps
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from src.configs import get_setting


class CRMBase(DeclarativeBase):
    pass


def get_crm_database_url():
    configured = get_setting().CRM_DATABASE_URL.strip()
    if configured:
        return configured
    storage_path = Path(get_setting().STORAGE_PATH)
    storage_path.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{storage_path / 'crm.db'}"


CRM_DATABASE_URL = get_crm_database_url()
CRM_ENGINE_OPTIONS = {
    "echo": False,
    "pool_pre_ping": True,
    "pool_recycle": 1800,
    "json_serializer": lambda obj: json.dumps(obj, ensure_ascii=False),
}
if CRM_DATABASE_URL.startswith("sqlite"):
    CRM_ENGINE_OPTIONS["connect_args"] = {"check_same_thread": False}

crm_engine = create_engine(CRM_DATABASE_URL, **CRM_ENGINE_OPTIONS)
CRMSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
    bind=crm_engine,
)


def create_crm_tables():
    from src.server.db.models import crm_model  # noqa: F401

    CRMBase.metadata.create_all(bind=crm_engine)


def with_crm_session(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        session = CRMSessionLocal()
        try:
            result = func(session, *args, **kwargs)
            session.commit()
            return result
        except BaseException:
            session.rollback()
            raise
        finally:
            session.close()

    return wrapper


@lru_cache(maxsize=1)
def get_market_source_engine():
    configured = get_setting().MARKET_SOURCE_DATABASE_URL.strip()
    if not configured:
        raise RuntimeError("MARKET_SOURCE_DATABASE_URL is not configured")
    engine = create_engine(configured, pool_pre_ping=True, pool_recycle=1800, pool_size=6, max_overflow=6)

    @event.listens_for(engine, "before_cursor_execute")
    def enforce_read_only(connection, cursor, statement, parameters, context, executemany):
        del connection, cursor, parameters, context, executemany
        normalized = statement.lstrip().upper()
        if not normalized.startswith(("SELECT", "WITH", "SHOW", "EXPLAIN")):
            raise RuntimeError("market_source connection is read-only")

    return engine


def get_crm_owner_id():
    return get_setting().CRM_OWNER_ID


def with_market_session(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        session_factory = sessionmaker(
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
            bind=get_market_source_engine(),
        )
        session = session_factory()
        try:
            result = func(session, *args, **kwargs)
            session.rollback()
            return result
        except BaseException:
            session.rollback()
            raise
        finally:
            session.close()

    return wrapper
