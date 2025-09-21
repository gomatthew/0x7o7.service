# -*- coding: utf-8 -*-
from fastapi import APIRouter
from src.server.ai.ai_service import chat

ai_router = APIRouter(prefix="/ai", tags=["AI"])
ai_router.post('/chat')(chat)
