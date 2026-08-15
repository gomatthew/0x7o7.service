from fastapi import APIRouter
from sqlalchemy import text

from src.configs import get_setting
from src.server.db.base import engine
from src.server.libs.redis_lib import redis_store

health_router = APIRouter(prefix="/health", tags=["Health"])
setting = get_setting()


@health_router.get("/live")
def live():
    return {"status": "ok", "version": "1.0.0"}


@health_router.get("/ready")
def ready():
    checks = {"database": False, "redis": False, "model_config": bool(setting.LLM_API_KEY)}
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        checks["database"] = True
    except BaseException:
        pass
    try:
        checks["redis"] = bool(redis_store.ping())
    except BaseException:
        pass
    is_ready = all(checks.values())
    return {"status": "ready" if is_ready else "not_ready", "checks": checks}
