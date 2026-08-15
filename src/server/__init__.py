# -*- coding: utf-8 -*-
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import RedirectResponse
from src.configs.settings import VERSION
from src.configs import get_setting
from src.server.api_router import auth_router, user_router, service_router, ai_router, rag_router, chat_router, \
    demo_router, health_router, lead_router, crm_router
from src.server.utils import RateLimitException, rate_limit_exception_handler


def create_tables():
    from src.server.db.base import Base, engine
    from src.server.db import models  # noqa: F401
    from src.server.db import ai_models  # noqa: F401
    Base.metadata.create_all(bind=engine)
    from src.server.crm_db.base import create_crm_tables
    create_crm_tables()


def create_app() -> FastAPI:
    app = FastAPI(title="make money", version=VERSION)
    app.add_exception_handler(RateLimitException, rate_limit_exception_handler)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=get_setting().PUBLIC_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/", summary="swagger 文档", include_in_schema=False)
    async def document():
        return RedirectResponse(url="/docs")

    app.include_router(auth_router)
    app.include_router(user_router)
    app.include_router(service_router)
    app.include_router(ai_router)
    app.include_router(rag_router)
    app.include_router(chat_router)
    app.include_router(demo_router)
    app.include_router(lead_router)
    app.include_router(crm_router)
    app.include_router(health_router)
    return app
