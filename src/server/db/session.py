# -*- coding: utf-8 -*-
from typing import Generator, Any
from functools import wraps
from contextlib import contextmanager
from sqlalchemy.orm import Session
from src.server.db.base import SessionLocal


@contextmanager
def session_scope() -> Generator[Any, Any, None]:
    """上下文管理器用于自动获取 Session, 避免错误"""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()


def with_session(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        with session_scope() as session:
            try:
                result = f(session, *args, **kwargs)
                session.commit()
                return result
            except BaseException as e:
                session.rollback()
                raise

    return wrapper
