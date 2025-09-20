# -*- coding: utf-8 -*-
from fastapi import APIRouter
from src.server.service import user_login



auth_router = APIRouter(prefix="/ai", tags=["AI"])
auth_router.post('/chat')(user_login)
