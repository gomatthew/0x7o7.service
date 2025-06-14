# -*- coding: utf-8 -*-
from fastapi import APIRouter
from src.server.service import user_register

user_router = APIRouter(prefix="/user", tags=["用户类api"])
user_router.post("/add")(user_register)
