# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends
from src.server.utils import ai_rate_limit, token_identify
from src.server.ai.ai_service import chat_dify
from src.server.service.ocr_service import ocr_chat

ai_router = APIRouter(prefix="/ai", tags=["AI"], dependencies=[Depends(token_identify), Depends(ai_rate_limit)])

ai_router.post('/chat')(chat_dify)
ai_router.post('/ocr')(ocr_chat)
