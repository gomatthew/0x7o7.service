from fastapi import APIRouter

from src.server.service.demo_service import create_lead

lead_router = APIRouter(tags=["Sales leads"])
lead_router.post("/leads")(create_lead)
