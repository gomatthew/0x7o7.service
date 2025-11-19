# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends
from src.server.service import user_register, get_userinfo, user_logout, reset_password
from src.server.utils import token_identify

user_router = APIRouter(prefix="/user", tags=["用户类api"])
user_router.post("/add")(user_register)
user_router.get("/get_info", dependencies=[Depends(token_identify)])(get_userinfo)
user_router.post("/logout", dependencies=[Depends(token_identify)])(user_logout)
user_router.post("/reset_password", dependencies=[Depends(token_identify)])(reset_password)
