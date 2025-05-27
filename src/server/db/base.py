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

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base: DeclarativeMeta = declarative_base()
