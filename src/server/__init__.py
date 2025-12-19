# -*- coding: utf-8 -*-
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import RedirectResponse
from src.configs.settings import VERSION
from src.server.api_router import auth_router, user_router, service_router, ai_router, rag_router


def create_tables():
    from src.server.db.base import Base, engine
    Base.metadata.create_all(bind=engine)


def create_app() -> FastAPI:
    app = FastAPI(title="make money", version=VERSION)

    app.add_middleware(
        CORSMiddleware,
        # allow_origins=["*"],
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
    return app
