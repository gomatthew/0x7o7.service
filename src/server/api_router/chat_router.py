# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends

from src.server.ai.chat_service import chat_completions
from src.server.utils import ai_rate_limit

chat_router = APIRouter(prefix="/chat", tags=["AI Chat"], dependencies=[Depends(ai_rate_limit)])

chat_router.post('/completions', summary='统一AI对话')(chat_completions)
