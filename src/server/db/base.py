import json

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import DeclarativeMeta, declarative_base
from sqlalchemy.orm import sessionmaker
from src.configs import get_setting

setting = get_setting()

engine = create_engine(
    setting.SQLALCHEMY_DATABASE_URI,
    echo=False,
    json_serializer=lambda obj: json.dumps(obj, ensure_ascii=False), pool_recycle=1800
)

# Repository functions return ORM records after their short-lived transaction
# has committed.  Keep already-loaded scalar attributes available after that
# commit so callers never trigger a refresh on a closed session.
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
    bind=engine,
)

Base: DeclarativeMeta = declarative_base()
