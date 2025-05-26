import uvicorn

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import RedirectResponse
from src.router import auth_router
app = FastAPI(title="0x7o7 always win", version="0.0.1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", summary="swagger 文档", include_in_schema=False)
async def document():
    return RedirectResponse(url="/docs")

app.include_router(auth_router)
uvicorn.run(app,host='0.0.0.0',port=8000)
