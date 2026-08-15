import json
import os
from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from src.configs import get_setting


class CRMBase(DeclarativeBase):
    pass


def _crm_database_url() -> str:
    configured = os.getenv("CRM_DATABASE_URL", "").strip()
    if configured:
        return configured
    storage_path = Path(get_setting().STORAGE_PATH)
    storage_path.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{storage_path / 'crm.db'}"


CRM_DATABASE_URL = _crm_database_url()
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


def get_crm_db() -> Generator[Session, None, None]:
    session = CRMSessionLocal()
    try:
        yield session
        session.commit()
    except BaseException:
        session.rollback()
        raise
    finally:
        session.close()


def create_crm_tables() -> None:
    from src.server.crm_db import models  # noqa: F401

    CRMBase.metadata.create_all(bind=crm_engine)
