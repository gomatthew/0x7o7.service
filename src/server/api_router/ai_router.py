# -*- coding: utf-8 -*-
from fastapi import APIRouter
from src.server.ai.ai_service import chat

auth_router = APIRouter(prefix="/ai", tags=["AI"])
auth_router.post('/chat')(chat)
