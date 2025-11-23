# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends
from src.server.ai.ai_service import chat
from src.server.ai.rag.kb_service import create_kb
from src.server.utils import token_identify

ai_router = APIRouter(prefix="/ai", tags=["AI"], dependencies=[Depends(token_identify)])
ai_router.post('/kb/create')(create_kb)
ai_router.post('/chat')(chat)
