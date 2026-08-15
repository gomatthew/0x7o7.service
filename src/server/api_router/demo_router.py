from fastapi import APIRouter

from src.server.service.demo_service import analyze_demo, get_demo_upload, get_sample, upload_demo_document

demo_router = APIRouter(prefix="/demo/v1", tags=["Document to Decision Demo"])
demo_router.get("/sample")(get_sample)
demo_router.post("/uploads")(upload_demo_document)
demo_router.get("/uploads/{upload_id}")(get_demo_upload)
demo_router.post("/analyze")(analyze_demo)
